# Checklist

- [x] 服务端启动链路（`server.py` → uvicorn → `module.server.app:fastapi_app`）描述与实际代码一致
- [x] 服务端默认端口 22288 与 OCR 端口 22268 的表述与 `config/deploy.yaml` 一致
- [x] 服务端分层表覆盖 `module/server`、`module/config`、`module/daemon`、`tasks`、`module/device`、`module/atom`、`module/ocr` 等主要目录
- [x] 「一个配置文件 = 一个 ScriptProcess = 一个子进程」的实例模型描述准确
- [x] `ScriptState` 枚举与 `start/stop` 行为描述准确
- [x] `TaskScheduler` 的 FILTER/FIFO/PRIORITY 三种策略描述准确
- [x] REST 端点清单与 `script_router.py`、`home_router.py`、`tool_router.py` 实际路由一致
- [x] WebSocket 路径、客户端指令（start/stop/get_state/get_schedule）与下行消息格式描述准确
- [x] 客户端启动链路（`main.dart` → `/login` → `/main`）与路由配置一致
- [x] 客户端 api/service/controller/views/model/config/component/utils 分层职责描述准确
- [x] 客户端与服务端的连接方式（默认地址、每配置一条 WS）描述准确
- [x] 遗留模块（`module/gui`）与空文件清单已记录
- [x] 风险点（无鉴权、CORS 全开、Flutter 版本敏感、SSE 占位）已记录
