# OASX 现代极简界面重做 Spec

## Why

当前 OASX（Flutter 版，`d:\project\OASX`）界面由多轮局部改造叠加而成：深色渐变光晕横幅、大量圆角卡片、胶囊标签、嵌套的徽章与阴影并存，信息层级依赖颜色和装饰而非排版，整体观感偏“游戏启动器”，不符合工具类软件的主流审美，也导致任务、状态、日志三类信息互相抢视觉焦点。需要在不改变业务逻辑的前提下，建立一套现代、克制、可扩展的设计体系，并重做桌面端核心页面。

## What Changes

- 重建全局设计令牌：中性色板（亮/暗）、语义状态色、圆角、间距、字号、阴影策略，统一由 `app_theme.dart` 输出。
- 主色改为**用户可选**：绿色（默认）/ 蓝色 / 靛蓝 / 紫色，选择持久化，切换后全局即时生效。
- 主窗口框架扁平化：标题栏、脚本标签、功能按钮统一高度、间距与选中态；去掉胶囊堆叠与多余描边。
- 重做总览页：移除渐变光晕横幅，改为扁平的信息摘要头；重排任务列表、日期分布、日志面板。
- 重做设置页：统一为分组行式布局，新增主色选择，危险操作与普通操作分离。
- 统一参数配置页：标签/描述左对齐、控件右对齐的网格行，扁平分组头。
- 其余页面（首页/登录/服务器/导航树）继承新令牌，清除硬编码渐变与重阴影。
- **BREAKING**（仅限内部 API）：`applyPalette` 签名扩展为主色参数；`AppPanel` 默认不再投影；视觉快照需重新生成。业务接口与数据流不变。

## Impact

- 受影响规格：无既有 spec 冲突，新增本规格。
- 受影响代码（`d:\project\OASX`）：
  - 设计体系：`lib/config/design/app_theme.dart`、`lib/config/theme.dart`、`lib/config/defaults.dart`、`lib/model/const/storage_key.dart`
  - 主题服务：`lib/service/theme_service.dart`
  - 布局框架：`lib/views/layout/appbar.dart`、`lib/views/layout/script_tab_bar.dart`、`lib/views/layout/title.dart`、`lib/views/home/home_sub_nav.dart`
  - 总览：`lib/views/overview/overview_view.dart`、`overview_banner.dart`、`date_distribution_panel.dart`、`task_list_panel.dart`、`taskitem_view.dart`、`overview_log_panel.dart`
  - 设置：`lib/views/settings/settings_view.dart`
  - 参数：`lib/views/args/args_view.dart`、`lib/views/args/group_view.dart`
  - 通用组件：`lib/views/common/app_widgets.dart`、`app_toast.dart`
  - 国际化：`lib/config/translation/i18n_content.dart`、`i18n_cn.dart`、`i18n_us.dart`
  - 测试：`test/design_system_test.dart`、`test/tool_view_golden_test.dart` 及其快照
- 不修改：WebSocket/API/RPC、任务调度、日志采集与落盘、配置读写、窗口行为、通知服务等业务逻辑。

## Design Tokens（本次重做的基准）

### 色彩

- 亮色：`bg #F6F7F9`、`panel #FFFFFF`、`panelSoft #F8F9FA`、`panelHi #F1F3F5`、`border #E4E7EB`、`textPrimary #1F2329`、`textSecondary #5C6570`、`textMuted #8B939D`。
- 暗色：`bg #101215`、`panel #16181C`、`panelSoft #1B1E23`、`panelHi #21252B`、`border #2A2F36`、`textPrimary #E8EAED`、`textSecondary #A0A7B0`、`textMuted #6E7681`。
- 主色（亮/暗）：绿 `#16A34A / #34D399`、蓝 `#2563EB / #60A5FA`、靛蓝 `#4F46E5 / #818CF8`、紫 `#7C3AED / #A78BFA`；每个主色配对应的浅色容器色，用于选中行/今日高亮。
- 语义色：运行=主色、空闲=中性灰、警告=琥珀、错误=红、同步=蓝。状态色不得用作装饰。

### 形状与层级

- 圆角：面板 12、卡片 8、标签/输入 6、按钮 8。
- 间距：4/8/12/16/20/24；页面内边距 16、面板间距 12、面板内边距 16。
- 阴影：面板默认**无阴影**，仅浮层（菜单、弹窗、Toast、下拉）使用阴影；禁止渐变背景、发光描边、斜纹纹理。
- 分隔：优先 1px 细线（`borderSoft`）与留白，不用嵌套卡片分层。

### 字体

- 页面标题 17/w600、区块标题 14/w600、正文 13/1.45、辅助 12、说明 11、等宽 12；时间与数字使用 tabular figures。
- 中文继续使用系统中文字体回退，英文保持 Lato。

## ADDED Requirements

### Requirement: 统一设计令牌

系统 SHALL 通过 `AppPalette` / `AppColors` / `AppRadius` / `AppMetrics` / `AppText` / `AppDecorations` 提供全部颜色、圆角、间距、字号与容器装饰；页面代码 SHALL NOT 直接硬编码十六进制颜色、任意圆角或自定义阴影（浮层除外）。

#### Scenario: 亮暗主题切换
- **WHEN** 用户切换亮色/暗色
- **THEN** 所有页面通过令牌同步换色，无残留深色块或丢失对比度的文字

#### Scenario: 新增页面复用令牌
- **WHEN** 开发者新增一个面板
- **THEN** 使用 `AppPanel`/`AppSectionHeader`/`AppText` 即可获得一致的圆角、描边、字号与间距

### Requirement: 可选主色

系统 SHALL 在设置页提供主色选择：绿色（默认）、蓝色、靛蓝、紫色。选择 SHALL 持久化（`StorageKey.accent`），重启后保持；切换 SHALL 立即更新整个界面且不跳转路由。

#### Scenario: 切换主色
- **WHEN** 用户在设置页点击“靛蓝”
- **THEN** 主按钮、选中态、运行状态、今日高亮等所有主色元素立即变为靛蓝，并写入本地存储

#### Scenario: 重启恢复
- **WHEN** 用户选择紫色后重启应用
- **THEN** 应用以紫色主色启动

#### Scenario: 默认主色
- **WHEN** 用户从未选择过主色
- **THEN** 使用绿色主色

### Requirement: 主色对比度

系统 SHALL 保证任一主色在亮/暗两套主题下，主色与其前景色（`accentFg`）的亮度差大于 60，且主色文字在面板底色上可读。

#### Scenario: 四种主色均通过
- **WHEN** 依次应用四种主色
- **THEN** 主按钮文字、选中标签、运行徽标均清晰可读

## MODIFIED Requirements

### Requirement: 主窗口与脚本标签

标题栏 SHALL 高度 48、底部 1px 细线，左侧为 Logo + OASX 字标 + 当前脚本名，中部为脚本标签区，右侧为功能按钮组（更新器、工具、更多、主题、设置）。脚本标签 SHALL 呈现为分段式标签：默认无边框、选中项使用 `panel` 底 + 1px `border` + 主色文字/底部指示，运行状态用 6px 状态点表示；启停按钮保持可点击但改为扁平图标，不使用圆形描边徽章。

#### Scenario: 窄窗口不溢出
- **WHEN** 窗口宽度为 1000/1200/1500
- **THEN** 标题栏不产生 RenderFlex overflow，标签区可横向滚动

#### Scenario: 标签状态可见
- **WHEN** 某脚本处于运行中
- **THEN** 对应标签显示主色状态点与主色启停图标，切换标签不误触启停

### Requirement: 总览页

总览页 SHALL 采用扁平布局：左侧为日期分布 + 任务列表（宽度 300–360），中间为脚本摘要头 + 日志面板，右侧资产面板默认隐藏。摘要头 SHALL 移除渐变、光晕与文字阴影，改为纯色面板：脚本名、状态点 + 状态文案、主按钮（启动/停止）与次按钮（运行一次）；高度不超过 104。

#### Scenario: 运行状态切换
- **WHEN** 用户点击“启动”/“停止”
- **THEN** 摘要头状态点、状态文案与按钮样式立即切换，行为与现有一致

#### Scenario: 无任务
- **WHEN** 当前脚本没有可调度任务
- **THEN** 摘要头显示空闲状态，任务列表显示空态说明与切换入口

### Requirement: 任务列表

任务行 SHALL 为固定高度（44–48）的单行结构：左侧时间（等宽、主色只在运行/逾期时使用），中部任务名，右侧悬停显示操作图标。运行中行使用 2px 主色左边条 + 主色浅容器底；逾期使用错误色文字；置底使用次要文字色。行与行之间用 1px 细线分隔，SHALL NOT 使用独立圆角卡片堆叠。

#### Scenario: 悬停操作
- **WHEN** 鼠标悬停在任务行
- **THEN** 立即运行、立即等待、设置三个图标完整显示且可点击

#### Scenario: 运行中任务
- **WHEN** 任务正在运行
- **THEN** 该行有主色左边条与浅色底，任务名加粗

### Requirement: 日志面板

日志面板 SHALL 使用下划线式标签（选中项主色文字 + 2px 底部指示），右侧工具按钮（自动滚动、复制、清空、折叠）保持 24px 紧凑排列；日志内容按“级别 + 时间 + 消息”着色排版，INFO 中性、WARNING 琥珀、ERROR 红色，行高 20–22。无日志时 SHALL 显示统一空态（图标 + 文案），不得出现大片纯空白。

#### Scenario: 级别筛选
- **WHEN** 用户切换到“错误日志”标签
- **THEN** 只显示 ERROR 行，数量徽标保持可见

#### Scenario: 折叠与展开
- **WHEN** 用户点击折叠
- **THEN** 面板收缩到 44 高的标题栏，再次点击恢复

### Requirement: 设置页

设置页 SHALL 使用单列分组行式布局（最大宽度 720）：每组为一块扁平面板，行高 52–56，左侧标题/说明、右侧控件；分组顺序为外观（主题、主色）、语言、界面（资产面板）、服务、账号。破坏性操作（结束 OAS 服务）SHALL 使用“危险区”样式：中性底 + 红色文字/图标，不得整块高饱和红底。

#### Scenario: 主色选择
- **WHEN** 用户打开设置页
- **THEN** 可见四个主色圆点，当前项带勾选标记，点击立即生效

#### Scenario: 危险操作确认
- **WHEN** 用户点击“结束 OAS 服务”
- **THEN** 弹出确认对话框，确认后执行原逻辑

### Requirement: 参数配置页

参数页 SHALL 使用两列对齐：左侧参数标题 + 说明（可换行），右侧固定宽度（200–240）的输入控件；每行垂直内边距 12，行间 1px 细线；分组头高 44–48，带展开/折叠箭头与数量。参数保存逻辑与提示 SHALL 保持不变。

#### Scenario: 修改布尔参数
- **WHEN** 用户切换某个开关
- **THEN** 立即调用原有保存接口并给出成功/失败轻提示

#### Scenario: 窄窗口
- **WHEN** 内容宽度不足 560
- **THEN** 控件列收缩到可用宽度，不出现横向溢出

### Requirement: 其他页面一致性

首页（含更新器、工具）、登录页、服务器页、移动端抽屉/导航树 SHALL 继承新令牌：无渐变背景、无发光阴影、选中态统一为主色浅容器 + 主色文字或左侧指示条。

#### Scenario: 首页子页切换
- **WHEN** 用户在首页切换“主页 / 更新器 / 工具”
- **THEN** 切换条与内容面板风格与全局一致

## REMOVED Requirements

### Requirement: 渐变光晕横幅

**Reason**: 与工具类软件的信息密度和克制审美冲突，且亮暗两套需要维护额外绘制逻辑。
**Migration**: 由纯色摘要面板替代，状态信息通过状态点、文案和按钮表达。

### Requirement: 面板默认阴影与嵌套圆角卡片

**Reason**: 多层圆角 + 阴影造成视觉噪声和层级混乱。
**Migration**: 面板默认无阴影，统一 12px 圆角；层级通过留白、1px 描边和字号区分。浮层保留阴影。
