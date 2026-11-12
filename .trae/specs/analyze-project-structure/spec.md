# OAS / OASX 项目结构分析 Spec

## Why

当前工作区包含两个独立仓库：`d:\oas`（OAS，Python 服务端，阴阳师自动化脚本内核 + FastAPI 服务）与 `d:\project\OASX`（OASX，Flutter 全平台客户端）。两者通过 HTTP REST + WebSocket 通信，但缺少一份可复用的结构基线。本次分析用于明确职责边界、分层结构、进程模型与通信契约，为后续任何开发任务提供参考依据。

本变更**不修改任何代码**，仅产出结构分析文档。

## What Changes

- 新增一份服务端（OAS）结构分析：启动链路、FastAPI 分层、脚本实例/进程模型、配置与调度、任务与设备/OCR 抽象。
- 新增一份客户端（OASX）结构分析：启动链路、GetX 分层（api/service/controller/view）、路由与核心页面、状态同步方式。
- 梳理两端通信契约：REST 端点清单、WebSocket 协议、配置实例与端口约定。
- 记录遗留模块、空实现与风险点，避免后续开发误入。

## Impact

- 受影响规格：无（本次仅新增分析基线，不新增/修改功能需求）。
- 受影响代码：无代码改动。
- 涉及关键文件：
  - 服务端：`server.py`、`module/server/app.py`、`module/server/script_router.py`、`module/server/main_manager.py`、`module/server/script_process.py`、`module/config/config.py`、`module/config/scheduler.py`、`config/deploy.yaml`
  - 客户端：`lib/main.dart`、`lib/api/api_client.dart`、`lib/service/script_service.dart`、`lib/service/websocket_service.dart`、`lib/views/routes.dart`

## ADDED Requirements

### Requirement: 仓库边界与启动链路

系统 SHALL 明确两个仓库的职责：OAS 为服务端（业务执行 + API），OASX 为客户端（跨平台 GUI）。

服务端启动链路（`d:\oas`）：

- `server.py`：设置时区 → 启动 OCR RPC 子服务（`ensure_ocr_server_started`）→ `uvicorn.run("module.server.app:fastapi_app", host, port)`，默认 `host=0.0.0.0`、`port=22288`（`config/deploy.yaml` 的 `Deploy.Webui.WebuiPort`）。
- `oas-backend.bat`：将内嵌 `toolkit`（Python 3.10 / Git / adb）加入 PATH 后执行 `python server.py`。
- `gui.py`：基于 Qt/FluentUI 的旧桌面端入口（`module/gui`），启动 `FluentApp` 并注入 `Setting`、`Add`、`ProcessManager`、`Utils` 上下文，属遗留方案。
- `docker-compose.yaml`：`network_mode: host` + `deploy/docker/Dockerfile` 构建 Linux 运行环境。

客户端启动链路（`d:\project\OASX`）：

- `lib/main.dart`：安装全局异常钩子 → `initService()`（logger、GetStorage、Locale/Theme/Window/UiPrefs/Notification 服务）→ `GetMaterialApp` → 初始路由 `/login`。
- 登录成功后进入 `/main`（`LayoutView`），按平台选择 `desktop`/`mobile` 布局。
- 技术栈：Flutter 3.27.1 / Dart 3.6.0、GetX（状态与路由）、`responsive_builder`（响应式）、目标平台 android/ios/windows/macos/linux/web。

#### Scenario: 服务端独立启动
- **WHEN** 在 `d:\oas` 执行 `python server.py`（或 `oas-backend.bat`）
- **THEN** 进程在 22288 端口提供 FastAPI 服务，并同时拉起 OCR RPC 服务

#### Scenario: 客户端连接服务端
- **WHEN** 用户在 OASX 登录页填写服务端地址并通过 `GET /test`
- **THEN** 客户端记录地址并进入主界面，后续 REST/WS 请求均指向该地址

### Requirement: 服务端分层结构

服务端 SHALL 按以下职责分层：

| 目录 | 职责 |
| --- | --- |
| `module/server/` | FastAPI 应用与协议层：`app.py`（应用装配、CORS、全局异常）、`home_router.py`（首页/更新/通知/诊断）、`script_router.py`（配置与脚本实例 REST + WS）、`tool_router.py`（标注工具 annotator）、`main_manager.py`（实例与数据推送）、`script_process.py`（子进程封装）、`config_manager.py`（配置文件 CRUD）、`setting.py`（`State` 全局状态/部署配置） |
| `module/config/` | 配置与调度核心：`config.py`（`Config`、`Function`、`get_next()`、`get_schedule_data()`）、`config_model.py`（pydantic 配置模型）、`scheduler.py`（FIFO/PRIORITY/FILTER 三种调度策略）、`config_watcher.py`、`config_updater.py`、`instance_guard.py` |
| `module/daemon/` | 执行器基类（`DaemonBase` 继承 `BaseTask`，关闭卡顿检测）；`benchmark.py` 用于任务耗时基准 |
| `tasks/` | 业务任务包（约 60 个，如 `DailyTrifles`、`Orochi`、`Duel`、`KekkaiUtilize`）；`base_task.py` 为任务基类；`Component/` 为战斗/式神/商店等通用组件；`Script/` 为脚本级配置模型（device/optimization/antiban 等） |
| `module/device/` | 设备控制：`connection.py`（adb/uiautomator2 连接）、`control.py`、`screenshot.py`、`app_control.py`、`emulator.py`、`handle.py` |
| `module/atom/` | 图像与交互原子操作：`click`、`long_click`、`swipe`、`scroll`、`ocr`、`image`、`image_grid`、`list`、`gif`、`animate` |
| `module/ocr/` | PPOCR 识别与 RPC 子服务（`ppocr.py`、`rpc.py`、`sub_ocr.py`） |
| `module/base/` | 基础工具：`decorator`、`timer`、`retry`、`filter`、`log_highlighter`、`cBezier`（贝塞尔滑动轨迹） |
| `module/notify/`、`module/handler/` | 通知推送、敏感信息处理 |
| `module/gui/` | 旧 Qt/FluentUI 桌面端（与 `fluentui/` 同级静态资源），已被 OASX 取代，仅保留 |

#### Scenario: 定位某个 API 实现
- **WHEN** 需要修改 REST/WS 行为
- **THEN** 业务装配位于 `module/server/app.py`，路由实现分别位于 `home_router.py`、`script_router.py`、`tool_router.py`

### Requirement: 脚本实例与进程模型

服务端 SHALL 采用「一个配置文件 = 一个脚本实例 = 一个子进程」的模型：

- `config/*.json` 每个文件即一个实例配置（`template.json` 为模板），`config_list` 返回实例名列表。
- `MainManager` 在初始化时为每个配置文件创建 `ScriptProcess`，并维护 `script_process: dict[str, ScriptProcess]`、执行 3 秒周期的数据推送线程。
- `ScriptProcess` 继承 `ScriptWSManager`，持有 `multiprocessing.Process`、日志管道与状态队列；状态枚举为 `INACTIVE/RUNNING/WARNING/UPDATING`。
- `start()` 启动子进程，`stop()` 先 `terminate()` 再 `kill()` 兜底。

#### Scenario: 启动一个实例
- **WHEN** 客户端向 `/ws/{config_name}` 发送 `start`
- **THEN** 对应 `ScriptProcess` 以 RUNNING 状态广播，并拉起子进程执行任务

### Requirement: 配置与任务调度

系统 SHALL 以 pydantic 配置模型驱动任务参数与调度：

- `Config` 加载 `config/{name}.json`，`Function` 抽取每个任务的 `scheduler.enable/next_run/priority`。
- `Config.get_next()` 计算下一个待执行任务，`get_schedule_data()` 输出 `running/pending/waiting` 三段结构供前端展示。
- `TaskScheduler` 支持 `FILTER`（按 `ConfigManual.SCHEDULER_PRIORITY` 过滤）、`FIFO`（按 `next_run`，强制 `Restart` 优先）、`PRIORITY`（按优先级分组后 FIFO）。
- 客户端通过 `PUT /{script_name}/{task}/sync_next_run` 同步手动调整的下次执行时间。

#### Scenario: 前端展示任务队列
- **WHEN** 客户端连接 WS 并发送 `get_schedule`
- **THEN** 服务端返回 `{schedule: {running, pending, waiting}}`，客户端渲染为当前任务/待执行/等待列表

### Requirement: 服务端 API 契约

服务端 SHALL 暴露以下 HTTP 接口（均为明文、CORS 允许 `*`）：

- 基础/首页：`GET /test`、`GET /script_menu`、`GET /home/home_menu`、`POST /home/notify_test`、`GET /home/kill_server`、`GET /home/update_info`、`GET /home/execute_update`、`PUT /home/chinese_translate`、`GET /home/additional_translate`、`GET /home/export_diagnostic`
- 配置管理：`GET /config_list`、`GET /config_all`、`GET /config_new_name`、`POST /config_copy`、`PUT /config`（重命名）、`DELETE /config`、`PUT /config/task/copy`、`PUT /config/task/group/copy`
- 脚本实例：`GET /{script_name}/start|stop`、`GET /{script_name}/{task}/args`、`PUT /{script_name}/{task}/{group}/{argument}/value`、`PUT /{script_name}/{task}/sync_next_run`、`GET /{script_name}/state`、`GET /{script_name}/log`
- 标注工具：`/tool/annotator/*`（会话、图片、规则、模拟器、保存/测试等，仅供 `module/server/web/annotator` 页面使用）

说明：`/{script_name}/state` 与 `/{script_name}/log` 两个 SSE 接口目前为占位实现（固定返回样例数据），实际状态与日志走 WebSocket。

#### Scenario: 动态渲染任务参数表单
- **WHEN** 客户端请求 `GET /{script_name}/{task}/args`
- **THEN** 服务端返回该任务 pydantic 模型的分组字段结构，客户端据此生成表单，并通过 `PUT .../value` 回写

### Requirement: WebSocket 协议

系统 SHALL 以单一 WebSocket 通道承载实例状态、调度与日志：

- 连接：`ws://{host}:{port}/ws/{config_name}`，连接建立后服务端立即推送一次 `{state}` 与 `{schedule}`。
- 客户端指令（纯文本）：`start`、`stop`、`get_state`、`get_schedule`。
- 服务端下行：`{state: int}`、`{schedule: {...}}`（JSON），以及非 JSON 的纯文本日志行（客户端按前缀 `{`/`}` 判定类型）。
- 客户端 `ScriptService` 为每个配置文件维护一条 WS 连接，`WebSocketService` 以 `name=config_name` 管理多个客户端。

#### Scenario: 停止实例后界面立即回正
- **WHEN** 客户端发送 `stop`，随后发送 `get_state` 与 `get_schedule`
- **THEN** 服务端广播最新状态与调度，客户端电源开关与任务列表同步刷新

### Requirement: 客户端分层结构

客户端 SHALL 按 GetX 分层组织：

| 目录 | 职责 |
| --- | --- |
| `lib/api/` | `ApiClient` 单例（基于 `flutter_nb_net`/Dio），统一 baseUrl、缓存拦截器、错误提示；`home_model.dart`、`update_info_model.dart` |
| `lib/service/` | `websocket_service`（多实例 WS 管理）、`script_service`（每配置一个 ScriptModel + WS 监听）、`notification_service`、`theme_service`、`locale_service`、`ui_prefs_service`、`window_service` |
| `lib/controller/` | `ctrl_nav`（主导航/实例切换）、`home_menu`、`nav_tab_order`、`settings`，以及 `login/`、`overview/`、`server/`、`args/` 子控制器 |
| `lib/views/` | `routes.dart`、`layout/`（desktop/mobile/tablet、appbar、script_tab_bar、content）、`home/`（tool、updater）、`overview/`（任务卡、日志面板、日期分布）、`args/`（动态参数表单）、`nav/`、`server/`、`settings/`、`login/` |
| `lib/model/` | `script_model`、`task_item_model`、`asset_model`、`window_state`、`const/storage_key` |
| `lib/config/` | `constants`（GitHub 更新地址等）、`theme`、`design/app_theme`、`translation/`（zh-CN/en-US 等 i18n） |
| `lib/component/` | 内置 `dio_http_cache`、日志组件（`log_mixin`/`log_store`/`log_widget`） |
| `lib/utils/` | `check_version`、`error_reporter`、`logger`、`platform_utils`、`yaml_utils`、`extension_utils` |

路由：`/login`（默认）→ `/main`（`LayoutView`），另有 `/settings`、`/server`。

#### Scenario: 客户端展示多实例
- **WHEN** 登录成功且服务端存在多个配置文件
- **THEN** `ScriptService` 为每个配置建立 WS 连接并生成 `ScriptModel`，布局层通过 `script_tab_bar` 切换实例

### Requirement: 遗留与风险记录

分析 SHALL 记录以下已知情况，避免后续开发误判：

- `module/gui/` 为旧 Qt/FluentUI 客户端，与 OASX 重复，属于可忽略/待清理的遗留代码。
- 客户端空文件：`lib/views/appbar/mobile_bar.dart`、`lib/views/layout/tablet.dart`、`lib/views/server/deploy_view.dart`、`lib/controller/args/group_controller.dart`。
- 服务端 `/state`、`/log` SSE 为占位实现，未接入真实数据。
- 服务端默认无鉴权（`Deploy.Webui.Password: null`）且 CORS 全开，`/home/kill_server` 可直接结束服务。
- 客户端版本强绑定 Flutter 3.27.1（README 明确提示 Flutter 版本会破坏接口）。
- 端口约定：OAS HTTP/WS 22288（`deploy.yaml`），OCR RPC 22268（`deploy.yaml`），客户端默认地址 `127.0.0.1:22288`。

#### Scenario: 修改前确认影响面
- **WHEN** 需要改动实例启停或日志展示
- **THEN** 需同时检查 `module/server/script_process.py`、`script_websocket.py` 与客户端 `lib/service/script_service.dart`、`lib/service/websocket_service.dart`
