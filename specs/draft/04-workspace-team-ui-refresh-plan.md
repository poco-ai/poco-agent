# Workspace team UI refresh plan

## 元数据

先记录这份计划的范围、优先级和当前状态，便于与其他 workspace spec 对齐。

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-04-16 |
| **预期改动范围** | frontend workspaces feature / frontend issues feature / shared page shell and states / i18n copy |
| **改动类型** | refactor |
| **优先级** | P1 |
| **状态** | in-progress |

## 实施阶段

本次改造按“先骨架、再页面、后验收”的顺序推进，避免在未统一结构前就进入局部 polish。

- [x] Phase 0: 收敛信息架构与共享 shell
- [x] Phase 1: 重做 team overview / members / invites
- [ ] Phase 2: 重做 team issues index 与 board 导航
- [ ] Phase 3: 重做 issue detail 与 execution 区域
- [ ] Phase 4: 补齐状态、移动端与验收

---

## 背景

这一部分先说明为什么 team UI 需要单独立项，而不是继续在现有页面上零碎修补。

### 问题陈述

Workspace / team 能力已经有了完整的产品语义和第一轮实现，但当前前端页面仍明显是“先把接口放上来”的状态。`frontend/features/workspaces/ui/team-pages.tsx` 和 `frontend/features/issues/ui/issues-pages.tsx` 虽然功能可用，但在页面骨架、导航层级、创建流、状态表达和移动端收敛上，都没有对齐 `capabilities`、`projects`、`scheduled-tasks` 等成熟模块。

这不是单纯的视觉 polish 问题，而是信息架构问题。当前 team header 承担了过多输入和切换动作，issues 页面也把 board、issue、assignment、execution 混在若干普通卡片里。随着 `03-workspace-agent-execution-hardening-plan.md` 进一步引入 assignee impact preview、next run、retained container 等状态，当前结构会更难承载。

### 目标

本计划的目标是把 workspace / team / issue UI 收敛到与现有 Poco 前端一致的产品层级，重点覆盖以下方向：

- 建立共享的 team shell 与二级导航
- 重做 overview、members、invites 三个 team 页面
- 重做 issues index，使 board 与 issue 扫描路径清晰
- 重做 issue detail，使问题信息与 execution controls 分离
- 补齐 loading、empty、error、destructive action、移动端和 i18n 文案

本计划不改动 backend 的 workspace、issue、agent assignment 数据模型，也不重新定义 `03-workspace-agent-execution-hardening-plan.md` 中的行为语义；这里只负责前端承接方式和交互信息架构。

### 关键洞察

下面这些洞察决定了这份计划的推进顺序和拆分方式。

#### 1. 当前问题主要来自没有复用现有 shell 模式

仓库里已经有稳定的 `PageHeaderShell`、双栏 grid、toolbar + dialog、显式 empty / skeleton 这些模式。team 前端的问题不是“缺一套视觉设计系统”，而是没有把这些成熟模式带过来。

#### 2. 必须先抽共享骨架，再分别做各页面

如果继续在 `team-pages.tsx` 和 `issues-pages.tsx` 里局部改样式，很快又会出现 overview、members、invites、issues 四页各长各的。先抽 TeamShell、section nav、workspace switcher / action host，后续页面才不会再次分叉。

#### 3. issue detail 的改造必须提前兼容 hardening spec

`03-workspace-agent-execution-hardening-plan.md` 要求前端承接 impact preview、next run、retained container 释放选项和高风险确认。如果 detail 页继续是单页长表单，后面只能不断插字段。现在就要把 detail 分成 summary column 和 execution sidebar。

#### 4. 这次改造更适合拆组件，不适合继续扩展大文件

当前 `frontend/features/workspaces/ui/team-pages.tsx` 和 `frontend/features/issues/ui/issues-pages.tsx` 已经在同时承载容器、header、列表、详情和 mutation 逻辑。继续扩展只会让 feature-first 结构失效。本次改造应顺手把共享 UI 提取成更小的 feature 组件。

---

## Phase 0: 收敛信息架构与共享 shell

第一阶段先修“地基”，让后续所有页面都建立在同一套容器和导航语法上。

### 目标

这一阶段先建立 team 区域的统一页面骨架和导航层级，为后续页面重做提供稳定落点。

### 任务清单

这一阶段的任务聚焦在共享骨架和动作落点，不追求一次完成所有视觉细节。

#### 0.1 提取 TeamShell 与 section nav

**描述：** 从当前 `frontend/features/workspaces/ui/team-pages.tsx` 和 `frontend/features/issues/ui/issues-pages.tsx` 中抽出共享骨架，形成 team 区域统一的 header、section nav 和内容容器。

建议抽出的内容包括：

- `TeamShell`：统一 `PageHeaderShell`、`main` 容器和 `max-w-6xl` 内容宽度
- `TeamSectionNav`：overview / members / invites / issues 共享二级导航
- `WorkspaceContextSummary`：当前 workspace 名称、kind、role 等轻量上下文展示

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/workspaces/index.ts`
- `frontend/app/[lng]/(shell)/team/*`

**验收标准：**

- [ ] team overview、members、invites、issues 共享同一套 header 和 section nav
- [ ] issues 路由不再脱离 team shell 单独渲染一套页头
- [ ] team 相关路由在桌面端和移动端都有统一容器边距与 section gap

#### 0.2 收敛动作落点

**描述：** 把 workspace 创建、invite 创建、board 创建、issue 创建这些动作从常驻内联输入改成 dialog / sheet / toolbar 触发，让浏览页恢复扫描优先。

这一步先定义动作落点，不要求一次性完成所有视觉细节，但必须把“边看边输入”的结构拆掉。

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/components/ui/dialog.tsx`
- `frontend/components/ui/sheet.tsx`

**验收标准：**

- [ ] 页头右侧不再常驻 workspace 创建输入框
- [ ] issues index 不再同时展示 board 创建输入和 issue 创建输入的两排 inline form
- [ ] 新建动作都有统一入口按钮和独立承载容器

---

## Phase 1: 重做 team overview / members / invites

第二阶段先把 team 的基础管理页拉齐，因为这些页面最直接体现 workspace 上下文和协作入口。

### 目标

这一阶段把 team 的基础协作页先拉齐到可用且统一的产品层级。

### 任务清单

这一阶段的任务重点是 overview 的信息层级，以及 members / invites 的一致性。

#### 1.1 重做 overview 页面

**描述：** overview 页面需要从“几张统计卡 + 活动列表”升级为更清晰的团队概览页。建议结构为：

- 顶部 workspace summary hero：当前 workspace 名称、kind、当前用户角色、主动作
- 中部 summary cards：成员数、有效 invite 数、board / issue 等关键指标
- 下部 activity section：时间线或列表，带 refresh 和 empty state

此页面要突出“当前团队是什么、最近发生了什么”，而不是只展示数字。

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/workspaces/model/workspace-context.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] overview 首屏能在不滚动的情况下让用户理解当前 workspace 上下文
- [ ] summary cards、activity list、empty / loading state 层级清晰
- [ ] refresh 和主动作都位于一致的 toolbar / section header 中

#### 1.2 重做 members 与 invites 页面

**描述：** members 和 invites 需要采用一致的“列表页 + 主动作”结构，避免两个页面各自是一张大卡片。

建议：

- members：成员列表、角色 badge、加入时间、后续可扩展的角色管理入口
- invites：invite 列表、状态 badge、过期时间、复制动作、新建 invite dialog
- 二者都使用统一 section header、列表容器和空态组件

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/workspaces/lib/format.ts`
- `frontend/components/ui/empty.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] members 与 invites 的列表项密度和状态表达一致
- [ ] role / revoked / expired 等状态不再以裸文本直接输出
- [ ] 新建 invite 使用 dialog 或 sheet，而不是占据内容区首行

---

## Phase 2: 重做 team issues index 与 board 导航

第三阶段开始处理 issue board 的浏览路径，把当前双卡 CRUD 结构升级为真正的协作入口。

### 目标

这一阶段把 issues index 从双卡 CRUD 页改造成真正可浏览、可扩展的 board 入口。

### 任务清单

这里的任务优先解决 board 选择和 issue 扫描，再去考虑更复杂的交互增强。

#### 2.1 建立 board rail + issue list 结构

**描述：** issues index 至少需要分成两个层次：

- 左侧 board rail：展示 boards、当前选中态、board 创建入口
- 右侧 issue pane：展示当前 board 的 summary、toolbar、issue list、empty state

如果数据规模变大，再往右扩 issue preview 或 filters 也有结构余量。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/issues/index.ts`
- `frontend/app/[lng]/(shell)/team/issues/page.tsx`

**验收标准：**

- [ ] board 选择与 issue 浏览在视觉上明确分层
- [ ] 当前 board 的名称、说明、主动作不再淹没在列表里
- [ ] issue list 支持至少一层轻量筛选或排序入口

#### 2.2 收敛 issue 创建与列表项样式

**描述：** issue 创建入口移入 dialog 或 header action 后，列表项需要承担更多信息扫描责任。每个 issue item 至少应稳定展示：

- 标题
- status / priority
- assignee 或 assignment status
- 最近更新时间或相关 project

列表项必须比现在的“标题 + 两个枚举值 + 一个 badge”更像协作对象，而不是临时链接。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/issues/model/types.ts`
- `frontend/components/ui/badge.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] issue list item 的信息密度提升，但仍保持可扫描
- [ ] create issue 不再通过列表顶部 inline input 完成
- [ ] 空 board、空 issue、加载中三种状态有清晰差异

---

## Phase 3: 重做 issue detail 与 execution 区域

第四阶段集中重构 detail 页，因为这里既承接协作信息，也承接 AI execution 的复杂状态。

### 目标

这一阶段让 issue detail 能同时承接协作信息和 AI execution，而不是继续演变成单页大表单。

### 任务清单

这一阶段的任务都围绕“拆层级”和“为 hardening 预留结构”展开。

#### 3.1 拆分 detail 的信息层级

**描述：** issue detail 建议采用“主内容列 + 执行侧栏”的结构：

- 主内容列：标题、描述、状态、优先级、相关 project、上下文字段
- 执行侧栏：当前 assignee、trigger mode、session、container、next run、执行动作

prompt 编辑、assignee 切换、schedule 修改不必都在首屏展开。可以采用 summary + edit dialog，或 summary + collapsible advanced section 的方式收敛复杂度。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/app/[lng]/(shell)/team/issues/[issueId]/page.tsx`
- `frontend/components/ui/card.tsx`
- `frontend/components/ui/collapsible.tsx`

**验收标准：**

- [ ] issue narrative 与 execution controls 不再混在同一个长表单流中
- [ ] session、container、assignment status 具备稳定的信息区块
- [ ] detail 页首屏能直接回答“这是什么问题”“当前 AI 在做什么”

#### 3.2 为 hardening 交互预留结构

**描述：** 对齐 `03-workspace-agent-execution-hardening-plan.md`，为以下交互预留信息位和组件结构：

- assignee 切换前的 impact preview
- retained container 是否释放的确认
- scheduled assignment 的 next run 展示
- scheduled mode 的首次执行说明

如果 backend API 还未全部就绪，这一阶段至少也要把布局和组件边界准备好，避免后续再拆一次 detail 页。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/issues/api/issues-api.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] detail 页存在容纳 impact preview 和 next run 的明确区域
- [ ] 高风险动作有确认容器，不依赖 toast 解释副作用
- [ ] scheduled 与 persistent 两种 trigger mode 的差异能在 UI 上被看见

---

## Phase 4: 补齐状态、移动端与验收

最后一阶段负责把通用状态、移动端行为和质量门禁全部补齐，避免留下只在桌面端可用的半成品。

### 目标

最后一阶段统一状态表达、移动端行为和回归验证，确保这次改造不是只在桌面端“变得更好看”。

### 任务清单

这一阶段不引入新的业务范围，只做状态收口和验证闭环。

#### 4.1 补齐共享状态组件与文案

**描述：** team / issues 页面统一接入 `Empty`、`Skeleton`、语义 badge 和 i18n 文案，补齐 destructive action 说明和辅助文案。

这一步也要顺手检查枚举值展示，避免直接把 backend status 原样暴露给用户。

**涉及文件：**

- `frontend/components/ui/empty.tsx`
- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] loading / empty / error / refreshing / destructive action 有统一表达
- [ ] 用户可见状态文本经过格式化，不直接输出原始枚举
- [ ] 所有新增文案完成 i18n 覆盖

#### 4.2 完成前端验收

**描述：** 在完成 UI 改造后，按现有前端质量门禁执行 lint、build 和关键手动路径验证。

重点手动路径包括：

- team overview / members / invites / issues 的页面切换
- workspace 切换与基础创建流
- board 创建、issue 创建、issue 详情进入
- AI assignment 保存、trigger、cancel、release 等关键动作
- 移动端下 team nav、issues index、issue detail 的可用性

**涉及文件：**

- `frontend/`

**验收标准：**

- [ ] `pnpm lint` 通过
- [ ] `pnpm build` 通过
- [ ] team 相关关键路径完成手动验证并记录结果

---

## 风险与缓解

下面列出这次 UI 改造最可能出现的几个偏差，以及对应的收敛方式。

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 只改样式，不改信息架构 | 页面看起来更新了，但问题仍然存在 | 先做 Phase 0，把 shell、导航、动作落点收敛后再做页面细节 |
| `team-pages.tsx` 和 `issues-pages.tsx` 继续膨胀 | 后续任何变更都难维护 | 本次改造同步拆组件，避免把新逻辑继续堆进大文件 |
| hardening spec 后续插入新状态时再次打断布局 | issue detail 需要二次返工 | 在 Phase 3 先为 impact preview、next run、retained container 预留结构 |
| 只优化桌面端 | 移动端 team 页面仍然难用 | 在每个 Phase 的验收标准中加入移动端行为约束，并在 Phase 4 集中验证 |

## 结语

这份计划的目标不是给 team 区域“补一层皮肤”，而是让它重新回到 Poco 已有的交互语法中。只有 team / workspace / issue 页面先和现有模块对齐，后续的 hardening、execution、协作扩展才不会继续建立在松散页面之上。
