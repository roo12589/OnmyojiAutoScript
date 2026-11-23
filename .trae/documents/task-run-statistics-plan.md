# 任务运行日志与统计优化方案

## 1. 目标与范围

在现有「文本日志」之外，为每个配置（script_name / config_name）增加**结构化的任务运行记录**，并持久化到 SQLite，由 OAS 后端提供统计 API，OASX 总览页展示：

- 每项任务每天的运行次数、成功次数、失败次数
- 每次任务的执行结果（成功 / 失败）、开始时间、结束时间、执行时长、异常信息
- 时间区间内的汇总：总运行次数、成功率、平均耗时、总耗时
- 最近运行记录明细，可按任务 / 状态 / 日期筛选

本次范围（已与用户确认）：

- **后端采集 + SQLite 持久化 + FastAPI 统计接口**
- **OASX Flutter 前端展示改造**
- 不改动现有文本日志格式、不新增用户配置项、不引入第三方图表库

## 2. 现状分析

### 2.1 后端

- 任务调度主循环在 [script.py](file:///d:/oas/script.py#L630-L747)：
  - `task = self.get_next_task()` 取出任务名（大驼峰）
  - `_task_start = datetime.now()` 记录开始，`success = self.run(...)` 拿到结果
  - `self.failure_record` 只统计连续失败次数，**不做持久化**
  - 进程退出 / 重启后所有运行信息丢失
- [Script.run()](file:///d:/oas/script.py#L540-L628) 的返回值：`TaskEnd` 返回 `True`；`GameStuckError`、`GameBugError`、`GamePageUnknownError` 返回 `False`；`ScriptError`、`RequestHumanTakeover`、未知异常会 `exit(1)`（抛出 `SystemExit`）
- 日志通过 [module/logger.py](file:///d:/oas/module/logger.py) 写到 `./log/YYYY-MM-DD_<config>.txt`，是纯文本，无法可靠聚合
- 后端 Web 服务入口 [module/server/app.py](file:///d:/oas/module/server/app.py)，路由按 `home_router / script_router / tool_router` 注册
- 配置文件名即脚本实例名，来自 `ConfigManager.all_script_files()`（[module/server/config_manager.py](file:///d:/oas/module/server/config_manager.py#L10-L30)）

### 2.2 前端 OASX

- 总览页日志面板 [overview_log_panel.dart](file:///d:/project/OASX/lib/views/overview/overview_log_panel.dart)
  - 已有 Tab：日志 / 运行日志 / 错误日志 / 任务统计 / 历史
  - 「任务统计」`_TaskStats` 只是对内存日志按 `ERROR/WARNING` 关键字计数，**没有任务维度数据**
  - 「历史」`_HistoryPane` 读的是 OASX 本地 `LogStore` 缓存的日志文本（[log_store.dart](file:///d:/project/OASX/lib/component/log/log_store.dart)），清理缓存会丢
- API 封装 [api_client.dart](file:///d:/project/OASX/lib/api/api_client.dart)，全局加了 `DioCacheInterceptor`（默认 GET 缓存 7 天），统计接口必须**强制刷新缓存**
- 现有任务名直接使用服务端下发的大驼峰名称（`DailyTrifles` 等），无需额外映射

## 3. 总体方案

```
OAS 任务进程                          OAS Web 服务                     OASX
┌─────────────────────────┐      ┌────────────────────────┐     ┌─────────────────────┐
│ Script.loop 任务开始/结束 │─────▶│ SQLite: data/oas_task_  │◀────│ GET /statistics/*   │
│ record_task_run()       │ 写入  │ stats.db (WAL)          │ 读取 │ 任务统计 / 运行记录  │
└─────────────────────────┘      └────────────────────────┘     └─────────────────────┘
```

- **采集点放在调度器层**（`Script.loop`），不在 `BaseTask.set_next_run` 采集，避免一个任务内部多次调用 `set_next_run` 造成重复计数，也能统一拿到真实执行时长与最终结果
- 用 Python 标准库 `sqlite3`，不新增依赖
- 一个脚本配置一个后台进程，多个进程并发写同一个库：开启 WAL + `busy_timeout`

## 4. 后端改动

### 4.1 新增 `module/stats/__init__.py` 与 `module/stats/task_record.py`

新建目录 `d:\oas\module\stats\`，提供采集与查询函数（供任务子进程和 Web 服务共用）。

数据库位置：`Path.cwd() / 'data' / 'oas_task_stats.db'`（`data/` 不存在时自动创建）。

表结构：

```sql
CREATE TABLE IF NOT EXISTS task_run (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name   TEXT NOT NULL,
    task_name     TEXT NOT NULL,
    start_time    TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM:SS'
    end_time      TEXT NOT NULL,   -- 'YYYY-MM-DD HH:MM:SS'
    day           TEXT NOT NULL,   -- 'YYYY-MM-DD'，取 start_time 所在日
    duration      REAL NOT NULL,   -- 秒
    status        TEXT NOT NULL,   -- 'success' | 'failed'
    error_type    TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_run_config_day  ON task_run(config_name, day);
CREATE INDEX IF NOT EXISTS idx_task_run_config_task ON task_run(config_name, task_name, day);
```

连接约定：

- `sqlite3.connect(DB_PATH, timeout=10)`
- 每次连接执行 `PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`
- 模块级 `_initialized` 标记，首次调用时 `init_db()`（`CREATE TABLE IF NOT EXISTS`）
- 写失败只记录 `logger.warning`，**绝不向上抛异常影响调度**
- `database is locked` 时重试 1 次

对外函数（签名固定）：

```python
RETENTION_DAYS = 180

def init_db() -> None: ...

def record_task_run(
    config_name: str,
    task_name: str,
    start_time: datetime,
    end_time: datetime,
    success: bool,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None: ...

def prune_old_records(keep_days: int = RETENTION_DAYS) -> int: ...

def query_overview(config_name: str, days: int = 7) -> dict: ...

def query_task_daily(config_name: str, task_name: str, days: int = 14) -> dict: ...

def query_records(
    config_name: str,
    task_name: str | None = None,
    status: str | None = None,
    start_date: str | None = None,   # 'YYYY-MM-DD'
    end_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict: ...
```

统计口径：

- `status='success'` 才计入「完成次数」；`failed` 计入失败次数
- 按 `day` 分组，缺失日期补 0（返回连续 `days` 天，升序）
- 成功率 = `success / runs * 100`，保留 1 位小数
- 平均耗时 = `AVG(duration)`，保留 1 位小数；总耗时 = `SUM(duration)`
- 一条记录归属 `start_time` 所在日（跨零点任务算开始日，作为已知取舍）

`query_overview` 返回结构（后端组装好，减少前端请求次数）：

```json
{
  "script_name": "日常",
  "days": 7,
  "today":  {"runs": 12, "success": 11, "failed": 1, "avg_duration": 345.2, "total_duration": 4142.0},
  "range":  {"runs": 80, "success": 74, "failed": 6, "success_rate": 92.5, "avg_duration": 360.4, "total_duration": 28832.0},
  "daily":  [{"date": "2026-11-13", "runs": 10, "success": 10, "failed": 0, "avg_duration": 340.0}],
  "tasks":  [{"task_name": "DailyTrifles", "runs": 7, "success": 7, "failed": 0, "success_rate": 100.0,
              "avg_duration": 120.3, "last_run": "2026-11-19 08:03:11", "last_status": "success"}],
  "recent": [{"id": 123, "task_name": "DailyTrifles", "start_time": "2026-11-19 08:03:11",
              "end_time": "2026-11-19 08:05:12", "duration": 121.5, "status": "success", "error": null}]
}
```

`query_task_daily` 返回：`{"task_name": "...", "daily": [同 daily 元素]}`。

`query_records` 返回：`{"total": 80, "items": [同 recent 元素]}`。

### 4.2 修改 `script.py`：采集任务运行记录

修改点 1：`Script.__init__` 增加状态字段

```python
self._task_executed = False        # 本次调度是否真的执行了任务
self._current_task_error_type = None
self._current_task_error_message = None
```

修改点 2：`Script.run()`（[script.py](file:///d:/oas/script.py#L540-L628)）

- 方法开头重置：
  ```python
  self._task_executed = False
  self._current_task_error_type = None
  self._current_task_error_message = None
  ```
- 在真正执行 `task_module.ScriptTask(...).run()` 之前设置 `self._task_executed = True`
- 各异常分支记录错误信息（成功返回的分支也记录，便于排查）：
  ```python
  self._current_task_error_type = type(e).__name__
  self._current_task_error_message = str(e)[:2000]
  ```
  覆盖：`GameNotRunningError`、`(GameStuckError, GameTooManyClickError)`、`GameBugError`、`GamePageUnknownError`、`ScriptError`、`RequestHumanTakeover`、`Exception`
- 排队等待（`_try_acquire_queue_token() is False`）和 token 丢失的提前返回分支不设置 `_task_executed`，因此不会产生记录

修改点 3：`Script.loop()`（[script.py](file:///d:/oas/script.py#L702-L747)）

把 `success = self.run(...)` 包在 `try/except SystemExit/finally` 中，在 `finally` 里落库：

```python
from module.stats.task_record import record_task_run

_task_start = datetime.now()
self._task_executed = False
success = False
try:
    success = self.run(inflection.camelize(task))
except SystemExit:
    raise
finally:
    if self._task_executed:
        record_task_run(
            config_name=self.config_name,
            task_name=inflection.camelize(task),
            start_time=_task_start,
            end_time=datetime.now(),
            success=success,
            error_type=self._current_task_error_type,
            error_message=self._current_task_error_message,
        )
```

说明：

- `ScriptError / RequestHumanTakeover / 未知异常` 会 `exit(1)`，但 `finally` 一定执行，记录不会丢
- 用户手动停止进程（SIGTERM -> `SystemExit`）同样会走 `finally`，记录为 `failed`
- `process.kill()` 强杀无法记录，作为已知限制

修改点 4：每日清理

在 `loop()` 已有的跨天分支中（[script.py](file:///d:/oas/script.py#L652-L656)，`if date.today() > start_day:`）追加：

```python
from module.stats.task_record import prune_old_records
prune_old_records()
```

### 4.3 新增 `module/server/statistics_router.py`

新建路由文件，前缀 `/statistics`：

```python
from fastapi import APIRouter, HTTPException
from module.stats import task_record

stats_app = APIRouter(prefix="/statistics", tags=["statistics"])

@stats_app.get('/overview')
def statistics_overview(script_name: str, days: int = 7): ...

@stats_app.get('/tasks/daily')
def statistics_task_daily(script_name: str, task_name: str, days: int = 14): ...

@stats_app.get('/records')
def statistics_records(script_name: str, task_name: str = '', status: str = '',
                        start_date: str = '', end_date: str = '',
                        limit: int = 50, offset: int = 0): ...
```

约定：

- 三个接口都用**同步 `def`**（FastAPI 会自动放到线程池，避免 sqlite 阻塞事件循环）
- `days` 限定 `1..365`
- 组装数据统一在 `task_record` 中完成，路由只做参数校验与调用
- 查询异常返回 `HTTPException(500, ...)`，并 `logger.exception`

### 4.4 修改 `module/server/app.py`

- 导入并注册：`from module.server.statistics_router import stats_app`，`app.include_router(stats_app)`
- `on_startup()` 中调用 `task_record.init_db()` 与 `task_record.prune_old_records()`（导入放在函数内，避免启动顺序问题）

### 4.5 修改 `.gitignore`

追加（数据库属于运行时数据）：

```
# Task run statistics
data/*.db
data/*.db-wal
data/*.db-shm
```

## 5. 前端 OASX 改动

### 5.1 `lib/api/api_client.dart`

新增三个方法，**必须强制刷新缓存**，避免命中 7 天 GET 缓存：

```dart
Future<Map<String, dynamic>?> getStatsOverview(String scriptName, {int days = 7})
Future<Map<String, dynamic>?> getTaskDailyStats(String scriptName, String taskName, {int days = 14})
Future<Map<String, dynamic>?> getTaskRunRecords(String scriptName,
    {String? taskName, String? status, String? startDate, String? endDate,
     int limit = 50, int offset = 0})
```

统一使用：

```dart
options: buildCacheOptions(Duration.zero, forceRefresh: true)
```

请求路径与后端约定一致：`/statistics/overview`、`/statistics/tasks/daily`、`/statistics/records`；空字符串参数不传。

### 5.2 新增 `lib/model/task_stats_model.dart`

纯解析模型（不引入 `BaseNetModel`，直接由 `Map` 构造）：

- `TaskRunRecord`：`id / taskName / startTime / endTime / duration / status / error`
- `TaskDailyStat`：`date / runs / success / failed / avgDuration`
- `TaskStatItem`：`taskName / runs / success / failed / successRate / avgDuration / lastRun / lastStatus`
- `TaskStatsOverview`：`today / range / daily / tasks / recent`，各为上述模型组合
- 提供 `formatDuration(double seconds)`（`mm:ss`，超过 1 小时为 `h:mm:ss`）与 `successRate` 格式化辅助
- 解析时对缺失字段使用默认值，数字统一 `(json['x'] as num?)?.toDouble() ?? 0`

### 5.3 新增 `lib/views/overview/task_stats_pane.dart`

`TaskStatsPane extends StatefulWidget`，参数 `{required String scriptName}`：

- 状态：`_days = 7`、`_loading`、`_error`、`_overview`、`Timer? _timer`
- 首次挂载请求 `/statistics/overview`；每 60 秒自动刷新，**一旦请求失败就停止定时器**（避免离线时反复弹网络错误），保留手动刷新按钮
- 布局（全部可滚动，沿用 `AppPanel / AppColors / AppText`）：
  1. 顶部工具行：`7 天 / 30 天` 时间范围 chip、刷新按钮
  2. 概览指标卡片：今日运行次数、今日成功、今日失败、今日平均耗时、区间成功率、区间平均耗时
  3. 每日趋势：用普通 `Container` 高度比例画柱状条（不引入图表库），每根柱下方显示 `MM-dd`，柱色按成功/失败拆分或失败标红；空数据显示 `I18n.task_stats_empty`
  4. 任务列表：按 `runs` 倒序，每行显示任务名、区间次数、成功/失败、成功率进度条、平均耗时、最近运行时间
  5. 点击任务行展开：调用 `/statistics/tasks/daily`，显示该任务最近 `_days` 天每天次数的小柱状图与成功/失败数字，再次点击收起
- 所有网络失败展示空态 + 重试按钮，不主动弹 snackbar

### 5.4 新增 `lib/views/overview/task_run_history_pane.dart`

`TaskRunHistoryPane({required String scriptName})`：

- 筛选条：状态 chip（全部 / 成功 / 失败）、时间范围（今天 / 7 天 / 30 天）、任务下拉（数据来自 overview 的 `tasks`，可先请求 overview 填充）
- 明细列表：每条显示任务名、开始时间、耗时、状态徽标（成功绿色 / 失败红色）、错误信息（`error` 非空时单行省略 + `Tooltip` 显示全文）
- 分页：每次 `limit=50`，「加载更多」按钮按 `offset` 追加
- 空态：`I18n.task_runs_empty`

### 5.5 修改 `lib/views/overview/overview_log_panel.dart`

- Tab 顺序调整为：日志 / 运行日志 / 错误日志 / 任务统计 / 运行记录 / 历史
- `IndexedStack` 中：
  - 原 `_TaskStats` 替换为 `TaskStatsPane(scriptName: widget.controller.logStoreName)`
  - 新增 `TaskRunHistoryPane(scriptName: widget.controller.logStoreName)`
- 删除旧的 `_TaskStats` 与仅被它使用的 `_StatTile`（避免未使用告警）
- `logStoreName` 即配置名（`OverviewController` 已按配置名分目录），后端记录使用同一名称

### 5.6 i18n

在 [i18n_content.dart](file:///d:/project/OASX/lib/config/translation/i18n_content.dart) 增加常量，并在 [i18n_cn.dart](file:///d:/project/OASX/lib/config/translation/i18n_cn.dart) 增加中文翻译（英文由 `convertCnToUsMap()` 自动回退，如需更自然英文再在 `i18n_us.dart` 覆盖）：

- `task_stats_overview`、`task_stats_today`、`task_run_history`、`task_runs_empty`、`task_stats_empty`
- `runs`、`success`、`failed`、`success_rate`、`avg_duration`、`total_duration`、`duration`
- `today_runs`、`today_success`、`today_failed`、`today_avg_duration`
- `last_run`、`last_status`、`all_tasks`、`all_status`、`last_7_days`、`last_30_days`
- `load_more`、`task_daily_detail`、`error_message`、`records_total`

## 6. 关键决策与假设

| 项 | 决策 |
| --- | --- |
| 采集层 | 调度器 `Script.loop`，保证一次任务执行只产生一条记录 |
| 「完成次数」定义 | 成功执行次数（`status='success'`）；总运行次数单独统计 |
| 任务名 | 大驼峰 `inflection.camelize(task)`，与现有调度数据一致 |
| 失败判定 | `Script.run` 返回 `False` 或抛 `SystemExit`（含 `exit(1)`） |
| 执行时长 | `end_time - start_time`，含任务内等待/战斗时间 |
| 日期归属 | `start_time` 所在自然日，本地时区（项目已设置 Asia/Shanghai） |
| 并发写入 | 每配置一个子进程 + SQLite WAL + `timeout=10` + 锁冲突重试 1 次 |
| 数据保留 | 180 天，启动时与跨天时清理 |
| 刷新方式 | 前端 60s 轮询 + 手动刷新；不新增 WebSocket 推送 |
| 文本日志 | 保持不变；历史文本日志仍走 OASX 本地 `LogStore` |

本次不做：

- 不统计任务内部战斗次数（`BaseTask.current_count` 并非所有任务都会维护，口径不统一）
- 不做跨设备同步、不改现有文本日志格式、不新增图表依赖

## 7. 风险与兼容性

1. **SQLite 跨进程并发**：WAL 模式允许读写并行；写冲突靠 busy timeout + 一次重试兜底。采集失败不影响任务执行。
2. **GET 缓存**：OASX 的 `DioCacheInterceptor` 默认缓存 GET，统计接口必须 `forceRefresh: true`，否则看到旧数据。
3. **历史数据为空**：首次上线时 UI 显示空态，不报错；老日志不会被回填（不回填是刻意选择，避免解析文本日志带来的误统计）。
4. **中文配置名**：SQLite 文本字段与 FastAPI query 均可直接处理，OASX 侧 `Uri` 会编码。
5. **强杀进程**：`process.kill()` 时任务记录缺失，仅影响异常场景，DDL 中无需特殊处理。
6. **数据体量**：单条约 200 字节，按每天 100 次任务、保留 180 天约 3.6 万行，SQLite 完全可承受；索引保证按配置/日期查询。

## 8. 验证步骤

后端：

1. 语法与导入：在 `d:\oas` 执行 `python -m compileall module\stats module\server\statistics_router.py script.py`
2. 单元级快速验证：
   ```powershell
   python -c "from datetime import datetime,timedelta;from module.stats.task_record import init_db,record_task_run,query_overview;init_db();t=datetime.now();record_task_run('oas1','DailyTrifles',t-timedelta(seconds=90),t,True);record_task_run('oas1','DailyTrifles',t-timedelta(seconds=30),t,False,'GameStuckError','stuck');print(query_overview('oas1',7))"
   ```
3. 启动服务后接口验证（默认端口以 deploy 配置为准，OASX 默认 `127.0.0.1:22288`）：
   ```powershell
   Invoke-RestMethod 'http://127.0.0.1:22288/statistics/overview?script_name=oas1&days=7'
   Invoke-RestMethod 'http://127.0.0.1:22288/statistics/records?script_name=oas1&limit=10'
   ```
4. 启动一个脚本配置，运行任意任务，确认 `data/oas_task_stats.db` 新增记录且 `status/duration` 正确；再手动停止任务，确认写入 `failed`。

前端：

5. 在 `d:\project\OASX` 执行 `flutter analyze`，确保无新增错误/警告
6. `flutter run -d windows`（或现有调试方式），验证：
   - 「任务统计」显示今日次数、区间成功率、每日柱状图、任务列表
   - 点击任务可查看该任务每天次数
   - 「运行记录」可按状态/时间/任务筛选并加载更多
   - 后端未启动时显示空态和重试按钮，不刷屏报错

## 9. 实施顺序

1. 后端存储：`module/stats/task_record.py` + `module/stats/__init__.py` + `.gitignore`
2. 后端采集：`script.py`（`run` 错误捕获、`loop` 落库与每日清理）
3. 后端 API：`module/server/statistics_router.py` + `app.py` 注册与启动初始化
4. 前端数据层：`api_client.dart` + `task_stats_model.dart`
5. 前端展示：`task_stats_pane.dart`、`task_run_history_pane.dart`、`overview_log_panel.dart`、i18n
6. 按第 8 节验证并修正
