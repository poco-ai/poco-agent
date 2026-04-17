# Workspace team kanban board rebuild plan

## 元数据

这份计划聚焦 team issues 页中的 board / issue 主工作流，目标不是继续修补现有 index→detail 页面，而是把它收敛成真正的 kanban 协作界面。

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-04-16 |
| **预期改动范围** | frontend issues feature / backend workspace issue APIs / workspace board settings flow / i18n copy / tests |
| **改动类型** | feat |
| **优先级** | P1 |
| **状态** | in_progress |

## 实施阶段

本次改造按“先收敛看板语义，再重做主界面，最后补拖拽和 destructive flow”的顺序推进，避免在错误的信息架构上继续加功能。

- [x] Phase 0: 收敛 kanban 语义与数据契约
- [x] Phase 1: 重做 issues index 为横向看板画布
- [ ] Phase 2: 将 issue 详情改为 modal / sheet
- [ ] Phase 3: 接入拖拽排序与状态流转
- [ ] Phase 4: 补齐 board 设置、删除与验收

---

## 背景

这一部分先说明为什么当前 board 模块不能只做样式微调，而需要单独立项重做。

### 问题陈述

当前 `frontend/features/issues/ui/issues-pages.tsx` 的结构，本质上仍是“board 列表 + issue 列表 + 独立 detail 页面”的 CRUD 视图：左侧是一列 board 按钮，右侧是一列 issue 卡片，点击 issue 之后，页面切换到 `TeamIssueDetailPageClient`。这与用户对“看板”的直觉不一致，也与团队协作目标不匹配。

它至少有四个问题：

1. 它展示的是“board 列表”，不是“board 本体”。真正的协作主界面应该让用户直接看到工作流列、卡片密度和状态分布。
2. issue 详情通过整页切换进入，会把 board 上下文拿掉。用户无法一边扫视当前列，一边查看或编辑某张卡片。
3. board 的更新和删除后端已经提供 API，但前端没有任何 board settings 入口，导致 board 生命周期不完整。
4. issue 虽然已有 `status` 字段，但没有“拖拽即流转”的界面，也没有持久化的列内排序语义，因此当前 status 仍更像表单字段，而不是 kanban workflow。

### 目标

这份计划要把 team issues 页收敛成一个更符合协作预期的 kanban 体验，同时保留 Poco 在 issue → AI assignee → execution 这条链路上的产品目标。

本次改造的核心目标如下：

- 在 workspace 的 issues 区域内，单次聚焦一个 named board，但这个 board 的主视图必须是横向多列 kanban canvas
- 让 issue detail 通过 modal / sheet 浮现，而不是离开当前 board 进入整页 detail
- 支持卡片在同一 board 内跨列拖拽，并把拖拽落点持久化为状态和列内顺序
- 提供 board settings dialog，承接 rename、description 编辑和删除操作
- 保留并强化 AI assignee、trigger mode、execution status 在卡片和详情中的可见性

### 关键洞察

下面几条洞察决定了这份 spec 的边界，尤其是“并排显示什么”和“拖拽跨到哪里”这两个容易混淆的问题。

#### 1. 用户口中的“几个看板并列”，在这里应落成“一个 board 内的多个 workflow 列”

workspace 下本来就可能有多个 named board，例如 `Sprint 24`、`Backlog`、`Ops`。如果把多个 named board 整体并排摊开，再在每个 board 里继续展示 issue，会立刻遇到三个问题：

- 画布宽度会被 board 实体本身吃掉，真正的状态流无法展开
- 不同 board 的字段、统计和协作上下文会混在一起
- AI assignment、execution 状态和 board 设置都会失去清晰落点

因此，本计划明确采用下面的语义：

- `board` 仍是用户切换的工作上下文实体
- 当前页面一次只打开一个 `board`
- 在这个 `board` 内，并排显示的是由 workflow 驱动的 kanban columns，而不是多个 board 实体

也就是说，用户感受到的“几个看板箱”会落成 `Todo / In progress / Done / Canceled` 这类列容器。

#### 2. issue 详情应该浮在 board 上，而不是替代 board

从团队目标看，issue detail 不只是表单，还承接 AI assignment、trigger、retry、release、open session 等执行动作。把这些内容整页铺开，会让“看板扫描”和“卡片处理”彼此打断。

更合理的结构是：

- board 仍然作为主舞台留在底层
- 点击卡片时，用大尺寸 dialog 承接详情
- 移动端退化为 sheet / full-screen panel
- 关闭详情后，用户仍停留在原 board、原列、原滚动位置

#### 3. 拖拽能力的第一期边界应是“同一 board 内跨列 + 列内重排”，而不是“多个 board 之间直接拖”

用户提到“拖到不同的看板当中”，但在当前产品语义里，直接跨 named board 拖拽并不稳妥，因为这会同时引入：

- board 字段模板是否兼容
- board 删除和 issue 归属的审计语义
- 跨 board 状态映射规则

因此第一期把拖拽边界收敛为：

- 支持同一 board 内跨列拖拽
- 支持同一列内重排
- 卡片移动到新列时，直接更新 `status`
- 跨 named board 迁移不做直接拖拽；如果后续需要，改为 issue modal 内的显式“move to board”动作单独设计

#### 4. board settings 应是独立 modal，而不是内联管理区

当前 board 的编辑和删除前端缺失，不是后端能力不够，而是没有合适的交互落点。考虑到删除 board 会级联删除其 issue，board 管理必须进入独立的 settings dialog，并带明确的 destructive confirmation，而不是在主画布里塞一排输入框。

### 外部调研结论

这次方案不是凭直觉拍板，而是先对照了几类当前主流 kanban 产品和 Agent 相关项目的官方说明。以下几条是与 Poco 最相关的共识：

- **Linear** 把 board 视作横向列画布，同时提供 `Peek` 让用户在不离开列表上下文的情况下查看 issue 详情。
  参考：<https://linear.app/docs/board-layout>、<https://linear.app/docs/peek>
- **GitHub Projects** 的 board layout 本质是“按单选字段分列”，拖动卡片会更新该字段值，这说明列是 workflow 语义而不是纯视觉容器。
  参考：<https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-board-layout>
- **Jira** 继续强化“列映射状态”的做法，用户在 board 上移动 work item，本质是在推进 workflow，而不是切换到单独的编辑页。
  参考：<https://support.atlassian.com/jira-software-cloud/docs/configure-columns/>
- **Trello** 保留了 board 作为主舞台、card detail 作为叠加层的经典模式。卡片详情是“打开一张卡”，不是“离开 board 去一个新页面”。
  参考：<https://support.atlassian.com/trello/docs/editing-cards/>
- **Plane** 在 issue / work item 模型上继续强化 AI agents 与 work item 的关系，这和 Poco 的 AI assignee 目标接近，但它依然没有放弃 kanban 作为主界面。
  参考：<https://plane.so/>

综合这些产品，最稳定的共识不是“多放几个统计盒子”，而是：

- 首屏可以有 summary metrics
- 但主界面必须是 column-based kanban
- 详情必须尽量保留 board 上下文
- 拖拽必须落到真实字段更新上

---

## 设计约束

这一部分把本计划的结构和范围钉死，避免执行时又回到“边做边猜”的状态。

### 结构约束

issues 页面完成改造后，结构必须收敛为：

1. 顶部 board context bar：board 选择器、summary metrics、board actions
2. 中部 board toolbar：搜索、筛选、创建 issue
3. 主画布：横向 kanban columns
4. 浮层：issue detail dialog / board settings dialog

明确禁止继续保留“左侧 board 列表 + 右侧 issue 列表”的双卡结构作为主视图。

### 数据约束

第一期不重做完整的 custom field workflow engine。当前 kanban columns 由系统字段 `status` 驱动，默认列为：

- `todo`
- `in_progress`
- `done`
- `canceled`

为了支持拖拽重排，需要在 issue 模型中新增持久化顺序字段，例如 `position`，并约定它在 `(board_id, status)` 范围内有意义。

### 交互约束

本期必须支持以下交互：

- 点击卡片打开 issue detail dialog
- 从一列拖到另一列，直接改变 issue `status`
- 在列内拖动，持久化列内顺序
- 打开 board settings dialog 编辑 board 名称和描述
- 在 board settings dialog 内删除 board，并展示明确的级联删除警告

本期不要求支持以下交互：

- 多个 named board 同屏并列
- 不同 named board 之间直接拖拽 issue
- 完整的 board 自定义列配置器

### 视觉约束

issues 页面仍必须服从 `2026-04-16-workspace-team-ui-constraints.md` 中的 team shell 约束，但 issues 内部的内容布局需要从“左 rail + 右列表”改成“顶部上下文 + 全宽画布”。

具体约束如下：

- board context 区可保留 3 到 4 个 summary metric boxes，但它们只是概览，不替代 kanban columns
- 列宽应固定在适合卡片扫描的范围内，桌面端允许横向滚动
- 卡片密度要高于当前普通 `Card` 列表，但不退化成纯文本表格
- modal 内保留 overview / assignment / execution 分区，不做单页大表单

---

## Phase 0: 收敛 kanban 语义与数据契约

第一阶段先解决“拖拽到底落到什么数据上”和“前后端怎么表达 board 画布”，否则 UI 一开始就会建立在不稳定的临时结构上。

### 目标

这一阶段为 kanban columns、drag state 和 board settings 补齐最小可用的数据契约。

### 任务清单

#### 0.1 为 issue 增加列内排序字段

**描述：** 当前 issue 只有 `status`，没有持久化顺序，因此拖拽重排无法落库。需要在 backend issue 模型中新增排序字段，并统一列表排序逻辑。

**涉及文件：**

- `backend/alembic/versions/` - 新增 revision，为 `workspace_issues` 增加 `position` 字段和必要索引
- `backend/app/models/workspace_issue.py` - 增加 `position`
- `backend/app/schemas/workspace_issue.py` - 在 request / response 中补齐 `position`
- `backend/app/repositories/workspace_issue_repository.py` - 统一按 `status`、`position`、`updated_at` 排序

**验收标准：**

- [x] issue 响应中包含稳定顺序字段
- [x] 同一列中的 issue 返回顺序可预测
- [x] 不修改前端时，现有 issue 页面仍能正常读取 issue 列表

#### 0.2 定义 issue move / reorder API

**描述：** 拖拽不应通过零散 `PATCH` 拼接完成，而应提供显式的 move 语义，例如“把某 issue 移动到某状态列的第 N 位”。

**涉及文件：**

- `backend/app/schemas/workspace_issue.py` - 新增 `WorkspaceIssueMoveRequest`
- `backend/app/api/v1/workspace_issues.py` - 新增 issue move / reorder 路由
- `backend/app/services/workspace_issue_service.py` - 新增 move service，负责跨列更新和列内重排
- `backend/tests/test_workspace_issue_service.py` - 覆盖跨列、列内重排和非法目标

**验收标准：**

- [x] 后端存在单独的 move / reorder API
- [x] 跨列移动会同步更新 `status`
- [x] 列内重排会重新计算受影响 issue 的顺序
- [x] 对不存在的 issue 或非法目标列返回业务错误

#### 0.3 补齐前端 board settings / move 能力的 API 客户端

**描述：** 当前前端 `issuesApi` 只接了 board list / create，没有 update / delete / move。需要把已存在的 board update / delete 后端能力接进前端 API 层，同时补上 issue move。

**涉及文件：**

- `frontend/services/api-client.ts` - 增加 board update / delete / move endpoint
- `frontend/features/issues/api/issues-api.ts` - 增加 `updateBoard`、`deleteBoard`、`moveIssue`
- `frontend/features/issues/model/types.ts` - 补齐前端类型

**验收标准：**

- [x] 前端 API 层可以完整创建、编辑、删除 board
- [x] 前端 API 层可以触发 issue move / reorder
- [x] 不需要绕过 feature `api/` 直接在组件中拼接 URL

---

## Phase 1: 重做 issues index 为横向看板画布

第二阶段开始真正替换现有主视图，把 issues 页从“board 列表 + issue 列表”改成“board 切换 + kanban canvas”。

### 目标

这一阶段让用户一进入 issues 页，就直接看到当前 board 的 workflow 结构，而不是看到另一层列表。

### 任务清单

#### 1.1 用 board context bar 替代左侧 board 列表卡

**描述：** 当前左侧 board 列表会挤占 kanban 画布宽度。需要把 board 切换收敛到顶部 context bar，并把 board actions 放到同一区域。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx` - 重构入口结构
- `frontend/features/issues/ui/team-board-context-bar.tsx` - 新增 board 选择器、summary metrics、board settings 入口
- `frontend/features/issues/index.ts` - 导出新的 issues UI 入口
- `frontend/lib/i18n/locales/*/translation.json` - 补齐 board action 文案

**验收标准：**

- [x] issues 页不再渲染左侧 board 列表卡作为主结构
- [x] 当前 board 名称、描述和 actions 都集中在顶部 context bar
- [x] summary metrics 仍保留，但位置从右侧内容区内迁移到 board context

#### 1.2 构建横向 kanban columns

**描述：** 基于 `status` 将 issue 分组为多列，在桌面端展示为横向滚动画布。每列应展示列名、数量、列内卡片和列级空态。

**涉及文件：**

- `frontend/features/issues/lib/kanban-columns.ts` - 新增按状态分列和排序的纯函数
- `frontend/features/issues/lib/kanban-columns.test.ts` - 覆盖分列和排序逻辑
- `frontend/features/issues/ui/team-kanban-board.tsx` - 新增 kanban 画布容器
- `frontend/features/issues/ui/team-kanban-column.tsx` - 新增列组件
- `frontend/features/issues/ui/team-issue-card.tsx` - 新增 issue 卡片组件

**验收标准：**

- [x] 当前 board 的 issue 以多列方式展示，而不是单列列表
- [x] 每列 header 显示状态名称和 issue 数量
- [x] 空列有清晰的 empty state，不退化为留白
- [x] 现有 AI assignment、priority、project 等信息能在卡片上被快速扫描

#### 1.3 重做移动端 issues 视图

**描述：** 横向多列在移动端不可直接照搬。移动端应退化为单列切换或 segmented view，但仍保持“当前在同一个 board 内”的语义。

**涉及文件：**

- `frontend/features/issues/ui/team-kanban-board.tsx`
- `frontend/features/issues/ui/team-kanban-column-tabs.tsx` - 如需要可新增
- `frontend/features/issues/ui/issues-pages.tsx`

**验收标准：**

- [x] 移动端不会出现不可读的横向缩略列
- [x] 用户可以明确切换当前查看的状态列
- [x] 创建 issue、打开卡片、返回 board 的路径在移动端保持通顺

---

## Phase 2: 将 issue 详情改为 modal / sheet

第三阶段把当前整页 detail 改成浮层 detail，让 issue 操作回到 board 上方完成。

### 目标

这一阶段保证 issue detail 不再把用户带离 board，同时保留 Poco 当前 issue detail 中的执行控制能力。

### 任务清单

#### 2.1 把 TeamIssueDetailPageClient 改造成 dialog 内容

**描述：** 当前 `TeamIssueDetailPageClient` 已经具备 overview、assignment、prompt、execution 四大区块，可以保留其业务逻辑，但必须脱离“整页 detail”心智，转成 modal / sheet 内容组件。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx` - 改为通过选中卡片控制 dialog 打开
- `frontend/features/issues/ui/team-issue-detail-dialog.tsx` - 新增 dialog 封装
- `frontend/features/issues/ui/team-issue-detail-content.tsx` - 从现有 detail client 抽出内容区
- `frontend/features/issues/model/use-team-kanban.ts` - 维护 `selectedIssueId` 与 dialog state

**验收标准：**

- [ ] 点击 issue card 会打开 dialog，而不是切走主画布
- [ ] 关闭 dialog 后仍保留当前 board、列和滚动位置
- [ ] `?issue=<id>` 仍可用于深链打开 detail，但表现为 modal 而非整页

#### 2.2 收敛 detail 内的分区和 destructive actions

**描述：** detail 浮层不适合继续堆成长页面。需要把内容收敛成更清晰的两个层级：问题信息 / AI assignment 在主列，execution 状态和动作在辅助列或底部区域，同时补上 issue 删除入口。

**涉及文件：**

- `frontend/features/issues/ui/team-issue-detail-content.tsx`
- `frontend/features/issues/api/issues-api.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] overview、assignment、execution 的层级比当前更清晰
- [ ] issue 删除入口存在且带确认提示
- [ ] open session、trigger、retry、cancel、release 仍可在 detail 中操作

---

## Phase 3: 接入拖拽排序与状态流转

第四阶段把 kanban 视图从“长得像看板”变成“行为上就是看板”。

### 目标

这一阶段让拖拽成为 issue 状态流转的主要交互，而不是装饰性动画。

### 任务清单

#### 3.1 用现有 dnd-kit 依赖接入 kanban drag-and-drop

**描述：** frontend 已经安装 `@dnd-kit/core`、`@dnd-kit/sortable`，本期直接复用，不新增新的拖拽库。拖拽应覆盖列内排序和跨列移动。

**涉及文件：**

- `frontend/features/issues/ui/team-kanban-board.tsx`
- `frontend/features/issues/ui/team-kanban-column.tsx`
- `frontend/features/issues/ui/team-issue-card.tsx`
- `frontend/features/issues/model/use-team-kanban.ts`

**验收标准：**

- [ ] 卡片可在同一列内重排
- [ ] 卡片可拖到其他状态列
- [ ] 拖拽过程中列容器和卡片有清晰的 drop affordance
- [ ] 不引入新的拖拽依赖

#### 3.2 实现 optimistic update 与失败回滚

**描述：** 拖拽必须足够顺滑，但也要处理后端拒绝、并发修改和网络错误。前端应先局部更新，再在失败时回滚并提示。

**涉及文件：**

- `frontend/features/issues/model/use-team-kanban.ts`
- `frontend/features/issues/lib/kanban-columns.ts`
- `frontend/features/issues/api/issues-api.ts`

**验收标准：**

- [ ] 成功拖拽时卡片不会闪回旧位置
- [ ] 后端失败时前端能回滚到拖拽前状态
- [ ] 用户能收到明确的失败提示

#### 3.3 补齐审计语义和状态同步

**描述：** 既然拖拽将成为状态流转入口，backend 需要明确 audit 语义。至少要记录 issue 的状态变化，必要时新增更明确的 `issue.moved` 事件。

**涉及文件：**

- `backend/app/services/workspace_issue_service.py`
- `backend/tests/test_audit.py`
- `backend/tests/test_workspace_issue_service.py`

**验收标准：**

- [ ] 拖拽引发的状态流转会进入审计日志
- [ ] 审计元数据能体现源状态和目标状态
- [ ] 不会因为拖拽重排产生大量无意义日志噪音

---

## Phase 4: 补齐 board 设置、删除与验收

最后一阶段把 board 生命周期补齐，并完成测试和手工验收，避免留下“主界面像看板，但管理操作还得回旧页面”的断裂体验。

### 目标

这一阶段让 board 的创建、编辑、删除和最终验证都对齐新的 kanban 结构。

### 任务清单

#### 4.1 实现 board settings dialog

**描述：** board settings dialog 是 board 管理的唯一入口，至少包含 board 名称、描述和删除动作。入口建议放在 board context bar 的 overflow action 中。

**涉及文件：**

- `frontend/features/issues/ui/team-board-settings-dialog.tsx` - 新增 board settings dialog
- `frontend/features/issues/ui/team-board-context-bar.tsx`
- `frontend/features/issues/api/issues-api.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] 当前 board 有明确的 settings 入口
- [ ] 可在 dialog 中修改 board 名称和描述
- [ ] 保存成功后 context bar 和画布上下文同步刷新

#### 4.2 补齐 board 删除确认与级联提示

**描述：** 删除 board 是高风险操作，因为 backend 目前会级联删除其 issue。前端必须把这一点显式写清，并在确认前展示当前 board 内的 issue 数量。

**涉及文件：**

- `frontend/features/issues/ui/team-board-settings-dialog.tsx`
- `frontend/features/issues/lib/kanban-columns.ts` 或相关统计函数
- `frontend/features/issues/api/issues-api.ts`

**验收标准：**

- [ ] 删除确认文案明确说明 issue 会被一并删除
- [ ] 删除前能展示当前 board 的 issue 数量
- [ ] 删除成功后自动切换到下一个可用 board；若无 board，则回到空态

#### 4.3 验证与清理

**描述：** 对 backend move 逻辑、frontend kanban 分列和最终交互做一轮完整验证，并清理旧的列表式结构。

**涉及文件：**

- `backend/tests/test_workspace_issue_service.py`
- `frontend/features/issues/lib/kanban-columns.test.ts`
- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/issues/index.ts`

**验收标准：**

- [ ] backend 相关测试覆盖跨列移动、列内重排和删除
- [ ] frontend 纯函数测试覆盖分列、排序和 optimistic rollback 所需数据转换
- [ ] `pnpm lint` 和 `pnpm build` 可通过
- [ ] 手工验证以下路径：
- [ ] 切换 board
- [ ] 创建 issue
- [ ] 点击卡片打开 modal
- [ ] 拖拽卡片跨列
- [ ] 编辑并删除 board
- [ ] 在 modal 中触发 AI assignment 动作

---

## 风险与缓解

这一部分提前记录本计划最可能踩坑的地方，避免后续执行时把风险误判成实现细节。

| 风险 | 影响 | 缓解措施 |
| ---- | ---- | -------- |
| 拖拽排序没有持久化语义 | 卡片刷新后跳回旧顺序，kanban 失真 | 在 Phase 0 先补 `position` 和 move API，再接前端拖拽 |
| board 删除是级联删除 | 用户误删后会丢失整板 issue | board settings dialog 必须有强确认文案和 issue 数量提示 |
| detail modal 仍然过长 | 从“整页大表单”退化为“弹窗大表单” | 把 detail 收敛成 overview / assignment / execution 三段，不把所有编辑都塞进首屏 |
| 横向多列在移动端不可用 | 移动端难以浏览和操作 | 移动端退化为单列切换或 sheet，不直接缩放桌面布局 |
| 当前列由系统 `status` 驱动，未来 custom field 需求会回流 | 后续再做字段驱动列时重构成本增加 | 让前端分列逻辑先走统一 adapter，避免把 `status` 写死在组件层 |

---

## 总结

这份计划要解决的不是“把 issues 页改得更像 dashboard”，而是把它重新定义为真正的 kanban 工作台。

最终目标是：用户先在顶部切换 board，再直接面对横向 workflow 列；卡片点击后通过 modal 浮现详情；拖拽直接推动 issue 状态流转；board 的编辑和删除通过独立 settings dialog 承接。这样既符合主流看板产品的稳定心智，也更贴近 Poco 在团队协作和 AI assignee 上的产品目标。
