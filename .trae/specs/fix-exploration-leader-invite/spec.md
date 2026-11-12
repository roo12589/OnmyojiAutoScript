# 修复探索任务队长邀请好友卡界面问题 Spec

## Why

探索任务（`tasks/Exploration`）以「队长」身份运行时，日志显示失败并非偶发的网络/好友离线问题，而是脚本自身逻辑缺陷：邀请好友界面打开后脚本既没有真正选中好友，也无法正确退出或识别标签页状态，最终要么反复回到邀请界面（用户看到的“卡在邀请界面”），要么连点同一按钮触发 `GameTooManyClickError` 导致游戏重启。

本变更新增一套对邀请流程与队长房间退出流程的修正，使队长模式能够稳定完成「建房 → 邀请指定好友 → 开战」或「明确失败并退出房间」。

## 日志证据与根因分析

### 证据一：邀请函数假成功，好友列表刚打开就被判定为“已完成”

日志 `log/2026-11-12_临时小号.txt:1633-1635`：

```
15:38:23.213 | Click (1046, 240) @ GI_ADD_2
15:38:23.570 | Click ( 370, 480) @ exploration_invite_friend_prevent
15:38:43.426 | Invitation is triggered every 20s
```

点击加号后 0.36 秒就执行了“点击空白处并 return True”，中间没有任何 `F_LIST_*` OCR 与好友选中日志。原因在 [solo.py](file:///d:/oas/tasks/Exploration/solo.py#L386-L389)：

```python
if not self.appear(self.I_ADD_2) or not self.appear(self.I_ADD_5_4):
    self.device.click(x=370, y=480, ...)
    return True
```

- 探索房间是 2 人房，`I_ADD_5_4`（五人队第 4 个加号）**永远不存在**，因此 `not I_ADD_5_4` 恒为真；
- 点击 `I_ADD_2` 后邀请面板正在弹出，加号短暂匹配失败，`not I_ADD_2` 也为真；
- 判定条件用了 `or`，于是“面板正在打开”被当成“队友已进房，邀请成功”，直接 `return True`。

上层 [general_invite.py](file:///d:/oas/tasks/Component/GeneralInvite/general_invite.py#L46-L131) 收到 `True` 后继续等待，20 秒后再次邀请，于是画面长期停在邀请列表上——即用户描述的“卡在邀请界面”。

### 证据二：标签选中态检测永远为假，连点触发 `GameTooManyClickError`

日志 `log/2026-11-12_临时小号.txt:1645-1658` 连续 10 次点击 `GI_FLAG_1_OFF` 后报错；`log/2026-11-12_临时大号.txt:1542-1555`、`log/2026-11-11_临时小号.txt:123-136` 完全一致。

原因在 [solo.py](file:///d:/oas/tasks/Exploration/solo.py#L462-L467)：

```python
while index == 0:
    self.screenshot()
    if self.I_FLAG_1_ON.match_mean_color(self.device.image, self.INVITE_FLAG_ON, 10):
        break
    if self.click(self.I_FLAG_1_OFF, interval=1):
        continue
```

`RuleImage.match_mean_color()` 内部调用 `corp(image)`，而 `corp` 默认使用 **`roi_back`**；`RuleImage.__init__` 会用 `ROI_BACK_EXPAND = 2` 把 `roi_back` 向四周扩 2 像素（[image.py](file:///d:/oas/module/atom/image.py#L17-L45)、[image.py](file:///d:/oas/module/atom/image.py#L547-L562)）。

用报错快照实测（`log/error/1794469135990`，此时“好友”标签确实处于选中态）：

| 区域 | 实测均值 RGB | 与 `INVITE_FLAG_ON=(227,193,153)` 的偏差 |
| --- | --- | --- |
| 紧凑 `roi_front` (354,126,62,21) | (227.7, 195.7, 154.7) | ≤ 2.7，可命中 |
| 扩展后 `roi_back` (352,124,66,25) | (216.6, 186.3, 148.8) | R 偏差 10.4 > bias 10，**始终不命中** |

同时 `I_FLAG_*_ON` 模板本身在该截图上匹配也全部失败（`appear=False`），所以不能只把检测换回模板匹配。由于 `while` 循环没有次数上限，又会每约 1.3 秒点一次同一坐标，最终触发设备层的 10 次点击保护。

### 证据三：无“最近”标签或未找到好友时直接返回，邀请面板不关闭

日志 `log/2026-11-12_临时大号.txt:1381-1394`：

```
Friend class: ['好友', '寮友', '跨区']
Find recent friend
No recent friend
Invite friend 1 failed
... 20 秒后再次 ... No recent friend
```

[solo.py](file:///d:/oas/tasks/Exploration/solo.py#L430-L436) 在“最近好友”模式找不到“最近”标签时直接 `return False`，跳过了后面的“点击邀请/关闭面板”逻辑，面板保持打开；上层每 20 秒重试一次，界面持续停留在邀请列表。

### 证据四：队长房间把“加号消失”当成邀请失败，退出时又不认“确认退出探索”弹窗

日志 `log/2026-11-12_临时小号.txt:1679-1694`：

```
15:39:07.601 | <<< LEADER >>>
15:39:13.934 | Wait_until_stable(GI_ADD_2) timeout
15:39:13.940 | Invite failed, quit
15:39:14.244 ~ 15:39:24.316 | Click (4x,4x) @ UI_UI_BACK_YELLOW  ×10
15:39:25.582 | ERROR | GameTooManyClickError: Too many click for a button: UI_UI_BACK_YELLOW
```

报错快照 `log/error/1794469165583` 显示当前是「确认退出探索吗？」弹窗。实测判定：

- `I_E_EXIT_CONFIRM` 在该快照上 `appear=True`（匹配分数 0.836，位置 (694,380)）；
- `I_UI_CONFIRM` 匹配失败（0.391），所以原退出循环点不到“确认”；
- `I_UI_BACK_YELLOW` 仍能匹配（0.928），但被弹窗遮挡，点击无效，循环无上限地连点。

另一个前提错误：2 人房里队友已经进房时加号 `I_ADD_2` 本就不存在，用 `wait_until_stable(I_ADD_2)` 作为“房间已就绪”的判据会把正常房间判成邀请失败。

## What Changes

- 修正 `Exploration/solo.py::invite_friend` 的“加号消失”判定：区分「邀请面板正在打开」「队友已进房」两种状态，避免假成功。
- 修正好友标签页（好友/最近/寮友/跨区）选中态检测：用紧凑 `roi_front` 计算均值颜色，并为点击次数设置上限。
- 所有失败/提前返回分支统一先关闭邀请面板，保证不把界面留在邀请列表。
- “最近好友”模式在标签不存在时退化为自动查找，而不是直接失败。
- 重写 `run_leader` 中 `Scene.TEAM` 分支：以房间标识（表情按钮/加号/挑战按钮）判断房间就绪，队友已在房时直接开战。
- 重写邀请失败后的退出流程：识别 `I_E_EXIT_CONFIRM`（确认退出探索），并用总时长上限替代无上限连点。

## Impact

- 受影响规格：无（新增修复规格，不改变既有结构分析规格）。
- 受影响代码：
  - `tasks/Exploration/solo.py`（`invite_friend`、`run_leader`）
  - 依赖但**不修改**：`tasks/Component/GeneralInvite/general_invite.py`、`tasks/Component/GeneralInvite/assets.py`、`tasks/Exploration/base.py`、`tasks/Exploration/assets.py`
- 受影响功能：探索任务队长模式的邀请与退房；单人/队员模式逻辑不变。

## ADDED Requirements

### Requirement: 邀请面板状态判定

`invite_friend` SHALL 只有在确认邀请好友面板已经打开（出现 `I_INVITE_ENSURE` 或 `I_LOAD_FRIEND`）后才开始好友查找；点击加号后若加号暂时消失，SHALL 继续等待面板出现，不得据此判定邀请成功。

“队友已进房”判定 SHALL 同时满足：`I_ADD_2` 与 `I_ADD_5_4`（以及永生之海 `I_ADD_SEA` 如适用）均不可见、邀请面板不可见，且连续两帧确认。

#### Scenario: 2 人房首次邀请
- **WHEN** 队长在 2 人探索房间点击加号打开好友列表
- **THEN** 脚本继续执行好友标签切换与好友选中，不会在 0.4 秒内以“成功”返回

#### Scenario: 队友已在房间
- **WHEN** 加号因队友已进房而消失，且邀请面板未打开
- **THEN** 脚本判定无需再次邀请并返回成功，由上层点击挑战

### Requirement: 好友标签选中态检测

标签选中态检测 SHALL 基于紧凑区域（`roi_front`）的均值颜色与 `INVITE_FLAG_ON` 比较，不得使用被 `ROI_BACK_EXPAND` 扩大的 `roi_back`。

每个标签的切换点击 SHALL 有次数上限（建议 3 次）；达到上限仍未检测到选中态时 SHALL 记录警告并跳过该标签，不得无限连点。

#### Scenario: 默认已选中“好友”标签
- **WHEN** 打开好友列表且“好友”标签本来就是选中态
- **THEN** 脚本在第一次检测时即通过，不产生任何标签点击

#### Scenario: 标签选中态无法识别
- **WHEN** 连续 3 次点击后仍未识别到选中态
- **THEN** 记录警告并继续处理下一个标签，不触发 `GameTooManyClickError`

### Requirement: 失败路径收尾

`invite_friend` 的所有失败返回与提前返回分支 SHALL 先关闭邀请面板（点击 `I_INVITE_ENSURE` 退出列表，次数有上限），再返回结果，避免界面停留在邀请列表。

当 `find_mode == RECENT_FRIEND` 但好友列表中没有“最近”标签时，SHALL 记录警告并退化为自动查找流程；只有所有标签都未找到目标好友时才返回失败。

#### Scenario: 未找到指定好友
- **WHEN** 遍历完所有可用标签仍未选中 `friend_1`
- **THEN** 关闭邀请面板、记录 `No find friend` 并返回 False，上层按失败流程退出房间

### Requirement: 队长房间就绪与退出

`run_leader` 的 `Scene.TEAM` 分支 SHALL 以房间标识（`I_GI_EMOJI_1`/`I_GI_EMOJI_2`/`I_ADD_2`/`I_FIRE`）判断房间就绪，不得仅以 `I_ADD_2` 是否稳定作为判据。

退出房间的循环 SHALL 处理 `I_E_EXIT_CONFIRM`（「确认退出探索吗？」弹窗的确认按钮），并在总时长（建议 20 秒）耗尽后记录警告并结束循环，不得对同一按钮无上限连点。

#### Scenario: 队友已在房间时重启任务
- **WHEN** 任务重启后回到已满员（2/2）的探索房间，加号不存在但挑战按钮存在
- **THEN** 脚本直接点击挑战进入战斗，不会误判为邀请失败

#### Scenario: 邀请失败后退出
- **WHEN** 邀请失败且界面弹出“确认退出探索吗？”
- **THEN** 脚本点击该弹窗的确认按钮回到探索界面；若 20 秒内仍未回到探索界面，则记录警告退出循环，不触发 `GameTooManyClickError`

## MODIFIED Requirements

### Requirement: 探索队长邀请流程

原流程为「点击加号 → 立即判断加号是否消失 → 视为邀请成功」，修改为「点击加号 → 等待邀请面板出现 → 逐标签查找并选中好友 → 点击邀请/关闭面板 → 根据是否选中返回结果」。队长在 `Scene.TEAM` 的后续处理改为「房间就绪判定 → 已在房则开战，否则邀请 → 失败则带超时退出」。

## REMOVED Requirements

无。
