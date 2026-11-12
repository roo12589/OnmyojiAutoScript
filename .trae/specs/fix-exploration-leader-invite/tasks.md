# Tasks

- [x] Task 1: 修复 `Exploration/solo.py::invite_friend` 的面板打开与“队友已进房”判定
  - [x] SubTask 1.1: 点击加号后改为等待 `I_INVITE_ENSURE`/`I_LOAD_FRIEND` 出现再进入好友查找，超时再判定是否面板未打开
  - [x] SubTask 1.2: 将 `not I_ADD_2 or not I_ADD_5_4` 改为“两个加号与面板均不可见且连续两帧确认”才算队友已进房
  - [x] SubTask 1.3: 抽取统一的“打开邀请面板并确认已进入”辅助方法，消除重复逻辑

- [x] Task 2: 修复好友标签选中态检测并限制点击次数
  - [x] SubTask 2.1: 新增紧凑 ROI 均值颜色判定辅助方法（基于 `roi_front`，配色 `INVITE_FLAG_ON`，bias 10）
  - [x] SubTask 2.2: 将 index 0~3 的 `while` 循环改为带上限（3 次）的切换逻辑，超限记录警告并跳过
  - [x] SubTask 2.3: 保留 `I_FLAG_2_ON` 的 ROI 修正逻辑，确保“最近”分支仍可用

- [x] Task 3: 统一失败收尾，避免停留在邀请列表
  - [x] SubTask 3.1: 抽出“关闭邀请面板”方法（点击 `I_INVITE_ENSURE`，上限 3 次）
  - [x] SubTask 3.2: 在 `No recent friend` 与 `No find friend` 等提前返回前调用关闭面板
  - [x] SubTask 3.3: `RECENT_FRIEND` 模式缺少“最近”标签时退化为自动查找，而不是直接返回失败

- [x] Task 4: 修复 `run_leader` 的 `Scene.TEAM` 房间就绪与失败退出
  - [x] SubTask 4.1: 用房间标识（`I_GI_EMOJI_1`/`I_GI_EMOJI_2`/`I_ADD_2`/`I_FIRE`）替代 `wait_until_stable(I_ADD_2)`
  - [x] SubTask 4.2: 加号不存在但 `I_FIRE` 存在时直接开战，不进入邀请
  - [x] SubTask 4.3: 退出循环增加 `I_E_EXIT_CONFIRM` 处理与 20 秒总时长上限，去掉无上限连点

- [x] Task 5: 静态验证与回归检查
  - [x] SubTask 5.1: 用报错快照离线验证标签均值颜色判定（选中/未选中两种情况）与 `I_E_EXIT_CONFIRM` 匹配
  - [x] SubTask 5.2: 复查 `invite_friend` 所有 `return` 分支均不会把界面留在邀请列表
  - [x] SubTask 5.3: 确认单人 `run_solo`、队员 `run_member` 行为未被改动

# Task Dependencies

- Task 2、Task 3 依赖 Task 1 的辅助方法抽取。
- Task 4 依赖 Task 1/Task 3 的返回值语义（邀请成功/失败判定）。
- Task 5 依赖 Task 1~4 完成。
