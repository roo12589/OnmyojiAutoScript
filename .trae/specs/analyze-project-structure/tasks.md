# Tasks

- [x] Task 1: 梳理服务端（OAS）目录与启动链路
  - [x] SubTask 1.1: 确认入口 `server.py`、`gui.py`、`oas-backend.bat`、`docker-compose.yaml` 的作用
  - [x] SubTask 1.2: 确认 FastAPI 装配方式与三个路由模块（home/script/tool）
  - [x] SubTask 1.3: 确认默认端口与部署配置来源（`config/deploy.yaml`）

- [x] Task 2: 梳理服务端核心机制
  - [x] SubTask 2.1: 确认「配置文件 = ScriptProcess = 子进程」的实例模型
  - [x] SubTask 2.2: 确认 `Config`/`Function`/`get_next`/`get_schedule_data` 的调度数据结构
  - [x] SubTask 2.3: 确认 `TaskScheduler` 的三种调度策略
  - [x] SubTask 2.4: 确认 `tasks/`、`module/device`、`module/atom`、`module/ocr` 的职责边界

- [x] Task 3: 梳理服务端 API 与 WebSocket 契约
  - [x] SubTask 3.1: 汇总 REST 端点（首页、配置管理、脚本实例、标注工具）
  - [x] SubTask 3.2: 确认 WS 路径 `/ws/{script_name}` 与指令/下行消息格式
  - [x] SubTask 3.3: 标注 SSE 接口为占位实现

- [x] Task 4: 梳理客户端（OASX）目录与启动链路
  - [x] SubTask 4.1: 确认 `main.dart` 服务初始化与路由（`/login` → `/main`）
  - [x] SubTask 4.2: 确认 api/service/controller/views/model/config/component/utils 分层职责
  - [x] SubTask 4.3: 确认 `ScriptService` 与 `WebSocketService` 的多实例同步方式
  - [x] SubTask 4.4: 确认动态参数表单的数据来源（`/{script_name}/{task}/args`）

- [x] Task 5: 汇总遗留模块与风险点
  - [x] SubTask 5.1: 标记 `module/gui` 旧桌面端与客户端空文件
  - [x] SubTask 5.2: 记录鉴权缺失、CORS 全开、Flutter 版本敏感、端口约定

# Task Dependencies

- Task 5 依赖 Task 1、Task 2、Task 4 的结论。
- 本变更为纯分析交付，无代码改动，任务均在分析过程中完成并核对。
