# Tasks

- [x] Task 1: 重建设计令牌并支持可选主色
  - [x] SubTask 1.1: 在 `lib/config/design/app_theme.dart` 中按 spec 更新亮/暗色板、语义色、圆角（面板 12/卡片 8/标签 6/按钮 8）、间距（4/8/12/16/20/24）与字号（17/14/13/12/11），`AppPanel` 默认去除阴影，新增/保留 `AppSectionHeader`、`AppDivider` 等扁平组件。
  - [x] SubTask 1.2: 新增 `AppAccent { green, blue, indigo, purple }` 与 `AppPalette buildPalette({required bool dark, required AppAccent accent})`，为四种主色提供亮/暗主色、容器色与前景色；保留 `AppPalette.light/dark` 兼容既有调用。
  - [x] SubTask 1.3: 更新 `applyPalette` 签名为 `applyPalette({bool? dark, AppAccent? accent})`，同步修正 `lib/config/theme.dart`、`lib/config/defaults.dart` 与所有调用点。
  - [x] SubTask 1.4: 在 `lib/model/const/storage_key.dart` 增加 `accent` 键；在 `lib/service/theme_service.dart` 中加载/保存主色（默认绿色），提供 `setAccent(AppAccent)`，切换后刷新 `revision` 使全局重建。
  - [x] SubTask 1.5: 更新 `test/design_system_test.dart`：校验新令牌不变量、四种主色前景对比度、`applyPalette` 主色切换。

- [x] Task 2: 重做主窗口标题栏与脚本标签
  - [x] SubTask 2.1: 调整 `lib/views/layout/appbar.dart`：标题栏高度 48、底部 1px 细线；左侧 Logo + OASX 字标 + 当前脚本名；右侧功能按钮统一 28px、间距 6、分组分隔线；保留更新器/工具/更多/主题/设置入口与既有 tooltip。
  - [x] SubTask 2.2: 重写 `lib/views/layout/script_tab_bar.dart` 的 `ScriptTabChip` 视觉：分段式标签（高 30），选中项 `panel` 底 + 1px `border` + 主色底部指示，未选中透明/悬停 `panelSoft`；运行状态改为 6px 状态点；启停按钮改为扁平 14px 图标（运行=主色），保留点击与右键菜单逻辑。
  - [x] SubTask 2.3: 让 `lib/views/home/home_sub_nav.dart` 与脚本标签使用同一套分段/下划线样式；同步 `lib/views/layout/title.dart` 的窗口标题与字标间距。
  - [x] SubTask 2.4: 运行 `test/appbar_entry_test.dart`，确保 1000/1200/1500 宽度不溢出、入口 tooltip 与点击即时性保持。

- [x] Task 3: 重排总览页骨架与摘要头
  - [x] SubTask 3.1: 重写 `lib/views/overview/overview_banner.dart`：删除渐变/光晕 `CustomPainter` 与文字阴影，改为扁平面板（高度 ≤104）：脚本名、状态点 + 状态文案、主按钮（启动/停止）与次按钮（运行一次）；保留原状态判断与回调。
  - [x] SubTask 3.2: 调整 `lib/views/overview/overview_view.dart`：页面内边距 16、面板间距 12；左列宽 300–360、中间日志自适应、右侧资产默认隐藏；修正固定高度造成的拉伸/空洞，确保窄窗口与高窗口下无溢出。
  - [x] SubTask 3.3: 更新 `lib/views/overview/date_distribution_panel.dart`：7 天横向扁平条，今日使用主色浅容器 + 主色数字，其余中性；去除胶囊嵌套与多余描边。

- [x] Task 4: 重做任务列表
  - [x] SubTask 4.1: 重构 `lib/views/overview/taskitem_view.dart` 为固定高度 44–48 的单行结构：左侧等宽时间 + 次要日期、中部任务名、右侧悬停操作图标；运行中 2px 主色左边条 + 浅容器底，逾期错误色，置底次要色。
  - [x] SubTask 4.2: 调整 `lib/views/overview/task_list_panel.dart`：统一面板头 44、搜索/工具行与列表分隔样式，补空态；修复日期/时间堆叠与图标无标签的问题（保留 tooltip）。
  - [x] SubTask 4.3: 验证任务开关、立即运行/等待、设置、搜索、置底等交互与旧行为一致。

- [x] Task 5: 重做日志面板
  - [x] SubTask 5.1: 重写 `lib/views/overview/overview_log_panel.dart` 的标签与工具区：下划线式标签（选中主色文字 + 2px 底部指示），工具按钮 24px 紧凑排列并保留 tooltip；折叠态高度 44。
  - [x] SubTask 5.2: 重排日志行：级别（INFO/WARNING/ERROR 语义色）+ 时间 + 消息，行高 20–22，等宽字体；历史过滤行与数量徽标使用新的扁平样式；增加统一空态。
  - [x] SubTask 5.3: 运行 `test/overview_log_panel_test.dart`，确保标签切换、过滤、自动滚动、复制、清空、折叠逻辑不变。

- [x] Task 6: 重做设置页并接入主色选择
  - [x] SubTask 6.1: 重构 `lib/views/settings/settings_view.dart` 为单列分组行式布局（最大宽度 720，行高 52–56）：外观（主题分段控件、主色圆点 + 勾选）、语言（分段控件/下拉）、资产面板开关、服务（危险区）、账号。
  - [x] SubTask 6.2: 新增“主色”分组：四色圆点 24–28px，选中带勾选与主色描边，点击调用 `ThemeService.setAccent` 即时生效；切换主题与语言保持原逻辑。
  - [x] SubTask 6.3: 将“结束 OAS 服务”改为危险区样式（中性底、红色文字/图标、保留确认对话框）；退出登录、版本信息等行样式与全局一致。
  - [x] SubTask 6.4: 在 `lib/config/translation/i18n_content.dart`、`i18n_cn.dart`、`i18n_us.dart` 增加 `accent_color`、`accent_green`、`accent_blue`、`accent_indigo`、`accent_purple`、`appearance`、`danger_zone` 等文案。

- [x] Task 7: 统一参数配置页排版
  - [x] SubTask 7.1: 调整 `lib/views/args/args_view.dart`、`lib/views/args/group_view.dart`：分组头 44–48、面板扁平；参数行改为左标题/说明、右固定 200–240 控件的两列网格，行内边距 12、行间 1px 细线。
  - [x] SubTask 7.2: 校验窄窗口（<560）下控件收缩不溢出；开关/输入/下拉保存与轻提示逻辑保持不变。

- [x] Task 8: 其余页面与通用组件收口
  - [x] SubTask 8.1: 检查并移除 `lib/views` 下残留的硬编码渐变、发光阴影、超大圆角与旧色值（首页、登录、服务器、工具、移动端抽屉/导航树）。
  - [x] SubTask 8.2: 统一 `lib/views/common/app_widgets.dart`、`app_toast.dart` 的圆角/描边/阴影；浮层（菜单、弹窗、Toast）保留唯一一层阴影；确保亮暗两套一致。

- [x] Task 9: 回归验证与快照更新
  - [x] SubTask 9.1: 运行 `flutter analyze`，确认无 error，且无因本次改造新增的 warning（原有 store_disk/platform_utils 等历史警告保留）。
  - [x] SubTask 9.2: 运行 `flutter test`；`test/goldens/tool_view_dark.png` 已按新令牌重新生成并人工核对。
  - [x] SubTask 9.3: 通过 `flutter build windows --debug` 验证桌面端可构建；生成设置页亮/暗视觉快照并修复开关对比度问题；总览/任务/日志/参数页按关键尺寸（摘要头 96、任务行 46、日志头 44、设置 720、参数 920/控件 220）代码核对。完整业务页面运行需连接 OAS 后端，留待用户联调时最终确认。

# Task Dependencies

- Task 2、3、4、5、6、7、8 均依赖 Task 1（设计令牌与主色体系）。
- Task 4 依赖 Task 3（总览页骨架与左列宽度确定）。
- Task 5 可与 Task 4 并行，但需在 Task 3 的日志区域尺寸确定后验证折叠态。
- Task 6 依赖 Task 1.4（主色持久化）与 Task 1.3（applyPalette 新签名）。
- Task 9 依赖 Task 1–8 全部完成。
