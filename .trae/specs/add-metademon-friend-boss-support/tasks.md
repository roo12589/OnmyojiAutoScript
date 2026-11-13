# Tasks

- [x] Task 1: 新增配置项与界面文案
  - [x] SubTask 1.1: 在 `tasks/MetaDemon/config.py::MetaDemonConfig` 新增 `md_friend_boss_monitor: bool = Field(default=False, ...)` 与 `md_friend_boss_first: bool = Field(default=False, ...)`
  - [x] SubTask 1.2: 更新 `auto_shared_boss` / `auto_shared_boss_help` 的 zh-CN 文案为「好友发现鬼王」语义
  - [x] SubTask 1.3: 在 `assets/i18n/zh-CN.json` 新增 `md_friend_boss_monitor`、`md_friend_boss_monitor_help`、`md_friend_boss_first`、`md_friend_boss_first_help`
  - [x] SubTask 1.4: 验证配置可正常 dump/加载（新字段有默认值，旧配置不受影响）

- [x] Task 2: 补强好友槽位识别资源与辅助方法
  - [x] SubTask 2.1: 在 `tasks/MetaDemon/md/ocr.json` 新增 `O_BOSS_EMPTY_2`，并同步生成 `tasks/MetaDemon/assets.py` 中的定义
  - [x] SubTask 2.2: 用用户提供截图（1527x858）按 1280x720 比例离线核对 `O_BOSS_EMPTY_1` 与 `O_BOSS_EMPTY_2` 的 ROI/关键字命中，必要时微调
  - [x] SubTask 2.3: 在 `script_task.py` 新增 `friend_boss_available(slot: int) -> bool`，统一使用「空槽模板不匹配 + 剩余时间 OCR 命中」

- [x] Task 3: 好友鬼王挑战流程与优先级
  - [x] SubTask 3.1: 新增 `select_boss(target, timeout=8)`，槽位 1 点击 `I_BOSS_EMPTY_1`、槽位 2 点击 `I_BOSS_EMPTY_2`，等待 `I_BATTLE_DEMON`，超时 8 秒返回 False
  - [x] SubTask 3.2: 重写主循环候选顺序：`auto_shared_boss` 开启时按 `md_friend_boss_first` 决定「好友槽位 1/2 ↔ 自己」的先后
  - [x] SubTask 3.3: 将「读取 `O_MD_FULL_NAME` 与血量阈值」移动到等待 `I_BATTLE_DEMON` 成功之后，保证好友鬼王读到正确的详情数据
  - [x] SubTask 3.4: 好友鬼王保持 `is_hard_boss = True`（沿用现有假设），自己鬼王仍用 `is_star56()`

- [x] Task 4: 监听模式与循环健壮性
  - [x] SubTask 4.1: 监听开启时取消 50 秒退出，改为 3 秒轮询；监听关闭时保留原 50 秒超时
  - [x] SubTask 4.2: 累计 60 秒无可挑战目标时退出到庭院并重进活动页刷新列表，复用入口弹窗处理逻辑
  - [x] SubTask 4.3: 新增槽位通知去重（每槽位记录已知状态），新出现时调用 `self.config.notifier.push(title='超鬼王', content=...)`（仅监听开启时推送）
  - [x] SubTask 4.4: `find_demon()` 增加 10 秒超时并返回 bool；页面连续丢失 30 秒时退出主循环

- [x] Task 5: 静态验证与回归检查
  - [x] SubTask 5.1: `python -m compileall tasks/MetaDemon` 与配置模型加载通过
  - [x] SubTask 5.2: 两个新开关默认关闭时，覆盖路径与当前行为一致（自己优先、50 秒退出、关闭时不碰好友槽位）
  - [x] SubTask 5.3: 离线截图验证槽位 1/2 识别与空列表场景，确认不会点击错误槽位
  - [x] SubTask 5.4: 复查主循环所有 `continue`/`break` 分支不会造成空转或重复通知

# Task Dependencies

- Task 3 依赖 Task 2 的识别辅助方法。
- Task 4 依赖 Task 3 的主循环候选顺序重构。
- Task 5 依赖 Task 1~4 完成。
