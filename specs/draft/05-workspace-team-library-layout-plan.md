# Workspace team library layout alignment plan

## 元数据

这份计划是对 `04-workspace-team-ui-refresh-plan.md` 的后续修正，专门响应最新的产品反馈：team 区域虽然已经完成第一轮重构，但整体结构和视觉语言仍然没有真正对齐 `capabilities`。

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-04-16 |
| **预期改动范围** | frontend workspaces feature / frontend issues feature / shared section shell / i18n copy |
| **改动类型** | refactor |
| **优先级** | P1 |
| **状态** | drafting |

## 实施阶段

这次改造不再以“补几张卡片”为目标，而是把 team 区域整体改成 capabilities 那种左侧选项、右侧内容的稳定结构。

- [x] Phase 0: 收敛 team 区域的双栏信息架构
- [ ] Phase 1: 用 library-style shell 重构 overview / members / invites / issues
- [ ] Phase 2: 清理视觉噪音并修正纵向间距
- [ ] Phase 3: 补齐移动端行为、状态与验收

---

## 背景

这一轮 spec 不是推翻 team 功能本身，而是修正“结构像业务后台临时页，不像 Poco 正式模块”的问题。

### 问题陈述

`frontend/features/workspaces/ui/team-shell.tsx` 和相关 team 页面已经做过一轮整理，但当前形态依然更像“页头下面再塞一块 workspace summary + 顶部 pills + 内容卡片”。这和 `capabilities` 的交互模式不一致。`capabilities` 已经验证过更清晰的结构：进入模块后，右侧主区域本身再拆成左侧选项列表和右侧内容面板，用户不需要先理解一排顶部按钮再去找内容。

现在的 team UI 还有两个直接可感知的问题。第一，overview 里的渐变 hero 太显眼，既不符合当前 Poco 大部分页面的克制风格，也会把注意力从“团队操作入口”拉走。第二，部分页面顶部留白明显不足，例如 invites 页里“邀请 / 查看待处理和已撤销的空间邀请。”几乎贴着上边界，页面呼吸感不够，也削弱了层级。

### 目标

这份计划要把 team 区域重新收敛到与 `capabilities` 一致的模块结构和视觉基线上，同时保留现有 team / issues 路由语义。

- team 区域改为与 `capabilities` 相同的双栏模式
- 左侧使用 section rail 展示 overview / members / invites / issues
- 右侧使用统一 content shell 渲染各 section 的具体内容
- 去掉 team 区域里不必要的渐变、hero 式视觉强调和过重装饰
- 修正每个 section 内容区的顶部 padding、section 间距和标题呼吸感
- 保持桌面端与移动端的交互一致性，尤其是移动端的 list/detail 切换

本计划不改 backend API，不改 workspace / issue 数据模型，也不重新定义 `03-workspace-agent-execution-hardening-plan.md` 的行为。

### 关键洞察

这次改造的重点不是再做一轮“卡片美化”，而是统一模块语法。

#### 1. team 的问题已经从“缺样式”变成“缺模块结构”

当前 team 页面并不是单个组件不好看，而是整个模块没有采用 Poco 已经成熟的 library-style 布局。只继续调整局部卡片、padding 或按钮样式，最后仍然会留下一个和 `capabilities`、`scheduled-tasks` 不同语法的 team 模块。

#### 2. 顶部 pills 导航不适合继续扩展

overview、members、invites、issues 现在仍通过 team shell 顶部的一组按钮来切换。随着 issues detail、workspace settings、future team actions 持续增加，顶部导航会越来越像“页头二次堆叠控件”。把 section nav 移到内容区左侧 rail，扩展成本会更低，也更符合用户对“模块内部子菜单”的心智。

#### 3. capabilities 的 content shell 已经给出正确的 spacing 基线

`frontend/features/capabilities/components/capability-content-shell.tsx` 已经固定了 `px-4 py-6 sm:px-6` 的内容区节奏。team 这次最明显的 spacing 问题，本质上是没有使用类似的 detail pane shell。只要 team detail pane 也回到同一套基线，顶部 padding 不够的问题会系统性消失，而不是每页手工补 `pt-*`。

#### 4. 渐变 hero 破坏了 team 作为“工具型模块”的稳定性

overview 当前的渐变 hero 虽然能制造视觉焦点，但它和 `capabilities`、`scheduled-tasks`、`memories` 这些成熟模块的克制风格不一致。team 页更需要稳定的信息密度和操作清晰度，而不是首页式情绪表达。

---

## 设计约束

这一节先把必须遵守的 UI 约束说清楚，避免后续实现时又回到上一轮的视觉方向。

### 结构约束

team 区域在桌面端必须采用和 `capabilities` 同类的双栏结构，而不是顶部 pills + 下方卡片。

- 左栏：section rail，负责展示 overview / members / invites / issues
- 右栏：detail pane，负责展示当前 section 的标题、操作和内容
- section 的切换结果必须在 detail pane 内表达，不再依赖顶部一排圆角按钮
- 已有 team 路由仍然保留，用路由映射当前激活 section，而不是为了 UI 强行改成 query-only 模式

### 视觉约束

这次改造要有明确的“减法”，而不是继续叠加修饰。

- 去掉 team overview 中的大面积渐变背景
- 优先使用 `bg-card`、`bg-muted/20`、`border-border/60` 这类现有设计变量
- 不新增新的高饱和背景、发光效果或首页式 hero 装饰
- section rail、detail pane、toolbar 和内容卡片的层级关系，要与 `capabilities` 保持接近

### 间距约束

这一轮必须把“标题贴边”的问题作为验收项，而不是顺手调整。

- team detail pane 需要有稳定的顶部内容 padding，至少对齐 `CapabilityContentShell`
- 像 invites、members、issues 这种列表页，标题块上方不能直接贴近容器顶边
- 标题、描述、toolbar、列表之间要形成一致的垂直节奏，不再每页各写一套 gap

---

## Phase 0: 收敛 team 区域的双栏信息架构

这一阶段先把 team 区域的骨架定义清楚，否则后面每个 section 都会以不同方式“模仿 capabilities”。

### 目标

这一阶段要确定 team 区域在桌面端和移动端分别如何承载 section rail 与 detail pane，并决定是否抽出共享 shell。

### 任务清单

#### 0.1 定义 team library shell

**描述：** 参考 `frontend/features/capabilities/components/capabilities-page-client.tsx`，为 team 区域定义新的 library-style shell。该 shell 应负责：

- 页面级 header
- 桌面端 `grid-cols-[240px_minmax(0,1fr)]` 一类的双栏结构
- 左侧 section rail
- 右侧 detail pane
- 移动端 list/detail 切换

推荐方向：

- 保留 `PageHeaderShell`
- 新增 `TeamLibraryShell` 或 `TeamSectionLayout`
- 让 `TeamShell` 从“顶部 summary + pills + toolbar”转型为“页面 header + body split layout”

**涉及文件：**

- `frontend/features/workspaces/ui/team-shell.tsx`
- `frontend/features/workspaces/lib/team-sections.ts`
- `frontend/features/workspaces/index.ts`
- `frontend/app/[lng]/(shell)/team/*.tsx`

**验收标准：**

- [x] team 桌面端采用双栏结构，而不是顶部 pills 导航
- [x] 左侧 section rail 与右侧 detail pane 的职责边界清晰
- [x] 移动端存在与 capabilities 一致的 list/detail 切换策略

#### 0.2 保留 team 路由语义并映射到 rail 选中态

**描述：** `capabilities` 主要依赖内部 view state，但 team 已经有稳定的路由：`/team`、`/team/members`、`/team/invites`、`/team/issues`。本阶段需要明确：UI 改成 library-style 后，仍保留这些 deep link，并让当前路由驱动左侧 rail 的 active state。

**涉及文件：**

- `frontend/app/[lng]/(shell)/team/page.tsx`
- `frontend/app/[lng]/(shell)/team/members/page.tsx`
- `frontend/app/[lng]/(shell)/team/invites/page.tsx`
- `frontend/app/[lng]/(shell)/team/issues/page.tsx`
- `frontend/features/workspaces/lib/team-sections.ts`

**验收标准：**

- [x] 现有 team 路由全部保留
- [x] 当前 section 的 active state 由路由稳定驱动
- [x] 切换 section 不需要额外理解”顶部 nav + 页面内容”两套结构

---

## Phase 1: 用 library-style shell 重构 overview / members / invites / issues

这一阶段开始把具体页面迁移到新的双栏骨架内，并让右侧 detail pane 真正长成 capabilities 那种内容容器。

### 目标

这一阶段要让 overview、members、invites、issues 四个 section 全部进入统一的 detail pane 语法中，不再保持“各页一个大卡片”的旧状态。

### 任务清单

#### 1.1 把 section 导航迁入左侧 rail

**描述：** 当前 team shell 中的 section pills 需要被替换为左侧 section rail。这个 rail 应该参考 `CapabilitiesSidebar` 的交互密度和选中态，而不是保留现在的按钮组外观。

建议内容：

- overview
- members
- invites
- issues

如果需要展示 workspace name / kind，应作为左栏顶部的轻量上下文，而不是单独再占一整块厚卡片。

**涉及文件：**

- `frontend/features/workspaces/ui/team-shell.tsx`
- `frontend/features/capabilities/components/capabilities-sidebar.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] 顶部圆角 pills 导航被移除
- [ ] 左侧 rail 具备明确的 active / hover / mobile 行为
- [ ] workspace 上下文信息不再喧宾夺主

#### 1.2 把四个 section 收敛到统一 detail pane

**描述：** overview、members、invites、issues 四个 section 都要回到统一的右侧内容容器中。detail pane 的标题、描述、toolbar、主体内容需要遵循固定顺序，避免每页各自决定 header 在哪里。

推荐 detail pane 顺序：

1. section title
2. section description
3. toolbar / primary action
4. content body

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/capabilities/components/capability-content-shell.tsx`

**验收标准：**

- [ ] overview、members、invites、issues 的右侧内容区结构一致
- [ ] toolbar 位置稳定，不再有页面把 action 塞到顶部 summary card 里
- [ ] issues section 也属于 team detail pane，而不是视觉上脱离 team 模块

---

## Phase 2: 清理视觉噪音并修正纵向间距

这一阶段把“像 capabilities”落实到视觉层，而不是只停留在双栏结构层面。

### 目标

这一阶段要去掉 team 模块里不必要的视觉强调，并统一 detail pane 的 padding、gap 与标题留白。

### 任务清单

#### 2.1 去掉渐变和过重装饰

**描述：** overview 中的 gradient hero 需要被替换为更克制的普通信息块，成员、邀请、issues 页里的卡片也要统一到现有 design token 上，不再额外制造“首页感”。

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/workspaces/ui/team-shell.tsx`
- `frontend/app/globals.css`

**验收标准：**

- [ ] team overview 不再使用大面积渐变背景
- [ ] 所有 team section 的主要表面统一为 token 驱动的 card / muted / border 样式
- [ ] 页面主层级依靠 spacing 和 typography，而不是背景特效

#### 2.2 系统性修复顶部 padding 不够的问题

**描述：** 这次不能只针对 invites 页补一个 `pt-2`。应当为 team detail pane 提供统一 content shell，并明确 section 标题区和内容区的顶部留白规则。

需要重点关注：

- invites 页标题块上方留白
- members 页标题块上方留白
- issues 页 summary / list 区顶部留白
- overview 页去掉 hero 后新的首屏间距

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/issues/ui/issues-pages.tsx`
- `frontend/features/workspaces/ui/team-shell.tsx`

**验收标准：**

- [ ] “邀请 / 查看待处理和已撤销的空间邀请。” 上方不再显得贴边
- [ ] 所有 section 标题块与容器顶边之间的留白稳定一致
- [ ] detail pane 内 section 间距由共享 shell 控制，而不是散落在各个页面组件里

---

## Phase 3: 补齐移动端行为、状态与验收

这一阶段确保新的 library-style team UI 不只是桌面端成立，也不会在移动端退化成又一套例外逻辑。

### 目标

这一阶段要补齐 mobile list/detail、loading/empty/error、i18n 和验证闭环。

### 任务清单

#### 3.1 对齐 mobile list/detail 行为

**描述：** 参考 `CapabilitiesPageClient`，移动端 team 区域应先展示 section list，再进入 detail。不要在移动端继续硬塞桌面双栏的缩窄版本。

**涉及文件：**

- `frontend/features/workspaces/ui/team-shell.tsx`
- `frontend/features/workspaces/ui/team-pages.tsx`
- `frontend/features/issues/ui/issues-pages.tsx`

**验收标准：**

- [ ] 移动端 team 首先展示 section list
- [ ] 点击某个 section 后进入 detail view
- [ ] 返回行为清晰，不会让用户困在 detail 内

#### 3.2 完成样式与质量验收

**描述：** 在结构和视觉完成后，统一验证 spacing、状态、i18n 和构建结果，并明确记录人工检查点。

重点检查：

- team section rail 的 active / hover / mobile 状态
- invites 标题块顶部留白
- overview 去渐变后的层级是否仍然清晰
- issues 在双栏 shell 中是否保持可扫描

**涉及文件：**

- `frontend/`
- `specs/draft/05-workspace-team-library-layout-plan.md`

**验收标准：**

- [ ] `pnpm lint` 通过
- [ ] `pnpm build` 通过
- [ ] team 关键 section 的桌面端与移动端完成手动检查
- [ ] 新增或调整的用户文案全部完成 i18n 覆盖

---

## 风险与缓解

这一轮的主要风险不是“做不出双栏”，而是实现时又把旧结构和新结构混在一起，最后得到一个更复杂的折中版本。

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 只是在现有 team shell 外面包一层双栏 | 页面层级会变得更重，顶部和左栏同时竞争导航职责 | 在 Phase 0 明确移除顶部 pills，让 rail 成为唯一 section nav |
| 继续保留渐变 hero，只调整布局 | 结构对齐了，但视觉语言仍然脱离 capabilities | 在 Phase 2 把“去掉渐变”写成硬性验收项 |
| 只修 invites 的 padding，没有建立共享 spacing 基线 | 之后 members / issues 仍会反复出现贴边问题 | 为 detail pane 抽统一 content shell，让 spacing 从共享容器下发 |
| 移动端沿用桌面压缩版布局 | list 和 detail 同时拥挤，交互变差 | 直接参考 capabilities 的 mobile list/detail 模式，而不是压缩桌面双栏 |

---

## 总结

这份 spec 的核心不是再做一轮 team 页面 polish，而是把 team 真正拉回 Poco 已有的模块语法里。只有当 team 也像 `capabilities` 一样，明确区分左侧 section rail 和右侧 detail pane，去掉不必要的视觉噪音，并建立统一的 spacing 基线，这个区域才算真正稳定下来。
