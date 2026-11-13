# 超鬼王好友发现鬼王支持 Spec

## Why

当前 `tasks/MetaDemon` 只有「自动打共享鬼王」这一个顺带分支：自己发现的鬼王永远优先，好友发现的鬼王只处理两个固定槽位且第二条存在误判/误点，任务在 50 秒无战斗后直接退出，无法监听好友后续分享的鬼王。需要把「好友发现鬼王」变成可开关、可调优先级、可持续监听的一等能力。

## 现状分析（超鬼王操作逻辑）

### 入口流程

1. 若开启切换御魂，先到式神录完成换御魂。
2. 从庭院右侧入口进入活动页（`I_RIGHT_ENTER`），循环处理奖励弹窗、返回、进入确认与二次进入确认，直到出现 `I_FIND_DEMON` 或 `I_BATTLE_DEMON`。
3. 若开启合成，执行一星卡合成。
4. 进入主循环，`boss_timer = Timer(50)`。

### 主循环现状

每轮截图后：

1. 自己发现：`I_BOSS_EMPTY` 不匹配且出现 `I_BOSS_CONVENE`（集结）或 `I_BOOS_PUBLIC`（已公开）时，点击自己鬼王并标记 `battle_processing`；`is_star56()` 判定高星。
2. 好友发现（仅在 `auto_shared_boss` 开启且自己没打时）：
   - 槽位 1：`not I_BOSS_EMPTY_1` 且 `ocr_appear(O_BOSS_EMPTY_1)`（关键字「剩余时间」），点击槽位 1，等待 `I_BATTLE_DEMON`；
   - 槽位 2：仅判断 `not I_BOSS_EMPTY_2`，且调用 `ui_click(self.I_BOSS_EMPTY_1, ...)`，**点击目标错误地指向槽位 1**；
   - 两个槽位都被硬编码为 `is_hard_boss = True`。
3. 疲劳值 > 100：开启自动喝茶则重置计时继续，否则退出（`auto_tea` 当前被校验器强制为 False，`buy_tea()` 为空实现）。
4. `boss_timer` 到达 50 秒无战斗则退出。
5. 高星鬼王按 `O_MD_FULL_NAME` 与 `I_STAR56_HP_THRESHOLD_T/F` 选默认/策略预设队伍，然后交给 `battle_wait` 的 metademon 钩子处理胜利、失败与战中标点。
6. 自己槽位为空且疲劳 < 90 时调用 `find_demon()` 点击「寻找鬼王」。

### 现存的缺陷

1. 无「好友优先」控制：只要自己鬼王存在，好友鬼王永远排在后面。
2. 好友槽位 2 没有 OCR 校验，只靠空槽模板消失判断，易误判。
3. 好友槽位 2 的等待点击目标写成槽位 1，可能反复点错卡片。
4. 没有监听能力：50 秒无战斗即退出，好友稍后分享的鬼王不会被处理。
5. `find_demon()` 为无上限 `while` 循环，无门票/按钮缺失时可能一直空转。
6. 页面丢失时 `continue` 没有任何退出判据，长驻模式下会无限空转。
7. 选中鬼王后立即读取名称/血量阈值，未等待详情区刷新，好友鬼王可能读到上一只鬼王的数据。

## What Changes

- 复用现有 `auto_shared_boss` 作为「自动挑战好友发现鬼王」总开关（默认开启），更新其中文文案与帮助说明。
- 新增 `md_friend_boss_monitor`（监听好友超鬼王，默认关闭）。
- 新增 `md_friend_boss_first`（优先好友发现，默认关闭）。
- 主循环重写候选选择顺序：按开关与优先级决定「自己 / 好友槽位 1 / 好友槽位 2」的挑战顺序；只处理当前可见的两个好友槽位。
- 补强好友槽位识别：新增槽位 2 的「剩余时间」OCR（`O_BOSS_EMPTY_2`），槽位 1/2 统一走「空槽模板不匹配 + 剩余时间命中」。
- 修复槽位 2 点击目标错误；选中任一鬼王后先等待 `I_BATTLE_DEMON` 出现再读取名称与血量阈值，再选择预设队伍开战。
- 监听模式：无目标时保持活动页轮询（3 秒）；累计 60 秒无目标则退出到庭院并重新进入活动页刷新好友列表；新出现的好友鬼王推送一次通知。
- `find_demon()` 增加超时（10 秒）并返回是否成功，避免无门票死循环。
- 页面连续丢失 30 秒时退出，避免长驻空转。

## Impact

- 受影响规格：无（新增规格）。
- 受影响代码：
  - `tasks/MetaDemon/config.py`（新增两个布尔配置，更新文案字段）
  - `tasks/MetaDemon/script_task.py`（主循环、好友识别、监听、召唤超时）
  - `tasks/MetaDemon/md/ocr.json` 与 `tasks/MetaDemon/assets.py`（新增 `O_BOSS_EMPTY_2`，用 `dev_tools/assets_extract.py` 重新生成）
  - `assets/i18n/zh-CN.json`（新增/更新文案键）
- 不修改：`battle_wait` 策略钩子、`SwitchSoul`、`RightActivity`、其他任务。
- 兼容性：两个新开关默认关闭，默认行为与当前一致（自己优先、不监听、50 秒退出）。

## ADDED Requirements

### Requirement: 好友发现鬼王识别

系统 SHALL 只识别「好友发现」列表中当前可见的两个槽位。槽位存在鬼王的条件为：对应空槽模板（`I_BOSS_EMPTY_1` / `I_BOSS_EMPTY_2`）不匹配，且对应「剩余时间」OCR（槽位 1 `O_BOSS_EMPTY_1`，槽位 2 新增 `O_BOSS_EMPTY_2`）命中。

#### Scenario: 两个槽位都有好友鬼王
- **WHEN** 主循环截图时槽位 1、2 均存在好友鬼王
- **THEN** 两个槽位都被识别为可挑战，按优先级开关顺序处理

#### Scenario: 只有槽位 1 有好友鬼王
- **WHEN** 槽位 1 有鬼王、槽位 2 为空
- **THEN** 只挑战槽位 1，不点击槽位 2

#### Scenario: 好友列表为空
- **WHEN** 两个空槽模板都匹配或「剩余时间」均未命中
- **THEN** 不产生任何好友槽位点击

### Requirement: 好友鬼王挑战开关

系统 SHALL 通过 `auto_shared_boss` 控制是否挑战好友发现鬼王（默认开启）。关闭时 SHALL 不点击任何好友槽位，也不推送好友鬼王通知。

#### Scenario: 开关关闭
- **WHEN** `auto_shared_boss = False` 且好友槽位存在鬼王
- **THEN** 脚本忽略好友槽位，只处理自己发现的鬼王或执行召唤/退出流程

#### Scenario: 开关开启
- **WHEN** `auto_shared_boss = True` 且好友槽位存在鬼王
- **THEN** 脚本按优先级规则挑战好友鬼王

### Requirement: 好友发现优先级

系统 SHALL 提供 `md_friend_boss_first`（默认关闭）。同一轮内自己与好友都存在可挑战目标时：开启则先好友（槽位 1 → 槽位 2）后自己；关闭则先自己后好友（槽位 1 → 槽位 2）。

#### Scenario: 未开启好友优先
- **WHEN** `md_friend_boss_first = False`，自己与好友都有鬼王
- **THEN** 优先挑战自己发现的鬼王

#### Scenario: 开启好友优先
- **WHEN** `md_friend_boss_first = True`，自己与好友都有鬼王
- **THEN** 依次尝试好友槽位 1、槽位 2，再挑战自己发现的鬼王

### Requirement: 好友鬼王监听

系统 SHALL 提供 `md_friend_boss_monitor`（默认关闭）。开启后：

- 无可挑战目标时 SHALL 保持活动页每 3 秒轮询，不执行原有 50 秒超时退出；
- 累计 60 秒无可挑战目标时 SHALL 退出到庭院并重新进入活动页以刷新好友列表，刷新后重新识别；
- 某槽位由空变为有鬼王时 SHALL 通过通知器推送一次提醒；同一槽位持续占用不重复推送，变为空后可再次推送；
- 退出条件为：疲劳值 > 100 且未开启自动喝茶、活动页连续丢失 30 秒、或用户在外部停止任务。

#### Scenario: 监听期间好友分享鬼王
- **WHEN** 监听开启，好友在 30 秒后分享了一只鬼王
- **THEN** 下一轮轮询识别到该槽位并进入挑战

#### Scenario: 长时间没有目标
- **WHEN** 监听开启且连续 60 秒无任何可挑战目标
- **THEN** 脚本退到庭院再重新进入活动页刷新列表，而不是退出任务

#### Scenario: 未开启监听
- **WHEN** `md_friend_boss_monitor = False` 且 50 秒无战斗
- **THEN** 保持现有行为退出任务

#### Scenario: 通知去重
- **WHEN** 同一个好友鬼王连续多轮存在
- **THEN** 只推送一次通知

### Requirement: 好友鬼王战斗流程

系统 SHALL 在选中任一鬼王（自己或好友）后，先等待 `I_BATTLE_DEMON` 出现，再读取 `O_MD_FULL_NAME` 与血量阈值并选择预设队伍，最后进入 `battle_wait`。好友鬼王沿用当前「按 5/6 星处理」的设定。

点击好友槽位后 8 秒内未出现 `I_BATTLE_DEMON` 时，SHALL 记录警告并返回主循环重新识别，不得直接进入战斗。

#### Scenario: 好友鬼王详情加载完成
- **WHEN** 点击好友槽位后出现 `I_BATTLE_DEMON`
- **THEN** 读取该鬼王的名称与血量阈值后开战

#### Scenario: 好友鬼王已失效
- **WHEN** 点击好友槽位后 8 秒仍未出现 `I_BATTLE_DEMON`
- **THEN** 记录警告并返回主循环，不进入战斗

## MODIFIED Requirements

### Requirement: 主循环与召唤

主循环 SHALL 改为「处理弹窗 → 页面有效性检查 → 候选识别与排序 → 战斗或召唤/等待」。`find_demon()` SHALL 增加 10 秒超时并返回是否成功；召唤条件仍为自己槽位为空且疲劳值 < 90。

#### Scenario: 无门票或寻找按钮不可用
- **WHEN** 自己槽位为空且 `I_FIND_DEMON` 长时间不可点击
- **THEN** `find_demon()` 在 10 秒后返回 False，主循环继续等待/退出，不无限空转

## REMOVED Requirements

无。
