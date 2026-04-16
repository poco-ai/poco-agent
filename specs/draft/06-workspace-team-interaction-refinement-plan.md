# Workspace team interaction refinement plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-04-16 |
| **预期改动范围** | frontend workspaces feature / frontend issues feature / shared section shell / i18n copy |
| **改动类型** | refactor |
| **优先级** | P1 |
| **状态** | drafting |

## 实施阶段

本计划是对 `05-workspace-team-library-layout-plan.md` 的后续修正，专门响应交互层面的两个问题：issues 的 index→detail 结构不对齐，以及 members / invites 的 section 拆分过细。

- [x] Phase 0: 精简左侧 section rail 并合并 invites 到 members
- [ ] Phase 1: 重构 issues 为内部状态驱动的 index→detail 模式
- [ ] Phase 2: 清理废弃路由和冗余代码
- [ ] Phase 3: 移动端对齐与验收

---

## 背景

### 问题陈述

`05-workspace-team-library-layout-plan.md` 已经把 team 区域的结构从"顶部 pills + 内容卡片"改为"左侧 section rail + 右侧 detail pane"的双栏模式。但实际使用后暴露了两个交互层面的问题。

第一，issues 区域仍然使用路由跳转来展示详情（`/team/issues` → `/team/issues/[issueId]`）。用户点击某个 issue 后，浏览器地址栏变化、左侧 rail 的 active state 丢失、无法通过返回按钮回到 issue 列表。这不符合 `capabilities` 模块中"右侧 pane 内部切换视图"的成熟模式，也不符合 constitution 中"index / detail 结构约束"的要求——"列表页面先解决 board 选择、issue 扫描和筛选；详情页面再承接 issue 内容、AI assignee 和 execution 控制"。

第二，members 和 invites 被拆成两个独立 section，但它们本质上都是"管理团队里的人"。invites 只是"还没加入的成员"，为它单独占一个 rail 入口既浪费导航空间，也增加了用户理解成本。用户在管理成员时，"发一个邀请"应该是一个从属于成员管理的动作，而不是一个独立的导航目的地。

### 目标

1. 左侧 section rail 从 4 个精简为 3 个：Overview、Members、Issues
2. Invites 作为 Members 页面内的 dialog 操作，不再拥有独立 section
3. Issues 改为内部状态驱动的 index→detail 模式：右侧 pane 在 issue 列表和 issue 详情之间切换，有明确的返回按钮
4. 移动端行为与桌面端保持一致

### 关键洞察

#### 1. issues 的 detail 不应该是独立路由

当前 `/team/issues/[issueId]` 路由的设计让 issue 详情脱离了 team 的双栏上下文。用户进入详情后：
- 左侧 rail 的 "Issues" active state 丢失（因为 `resolveSectionFromPath` 匹配不到）
- 页面 header 的标题从 "Issues" 变成了 issue title，脱离了 section 上下文
- 没有返回按钮，只能用浏览器返回键
- 移动端无法从详情返回到 issue 列表

capabilities 模块已经验证过正确的模式：view state 由内部管理（`?view=xxx`），detail 在右侧 pane 内渲染，左侧 rail 始终保持选中态。

#### 2. invites 的信息量不足以支撑独立 section

invites 页面的全部内容是：一个"创建邀请"按钮 + 一个邀请列表。这完全可以在 members 页面内通过 dialog 承载。把它提升为和 members 平级的 section，会让左侧 rail 变得臃肿，用户每次切换都要多跳一级导航。

#### 3. index→detail 是 team section 的通用模式

capabilities 用的是"左侧选 capability → 右侧渲染 detail"。Issues 应该用同样的模式："左侧选 issue → 右侧渲染 detail"，detail 内部还有返回按钮回到 index。这种模式在 team 的其他 section 中不需要（overview 和 members 都没有二级 detail），但 issues 是一个天然需要 index→detail 的 section。

---

## 设计约束

### 结构约束

- 左侧 section rail 只保留 3 个入口：Overview、Members、Issues
- Issues section 的 detail pane 内部维护 index（board 列表 + issue 列表）和 detail（issue 详情）两层
- Issue detail 的切换由内部状态管理，不改变 URL 路由
- `/team/invites` 和 `/team/issues/[issueId]` 路由在本次改造中废弃

### 交互约束

- Issue index→detail 必须有明确的返回按钮（桌面端和移动端）
- Issue detail 中的返回按钮回到 issue index，而不是回到 overview
- Members 页面的邀请功能通过 dialog 触发，dialog 内同时展示邀请列表和创建入口
- 创建 invite 的 dialog 可以复用现有的 `CreateInviteDialog` 组件

### 视觉约束

- 左侧 rail 的 section 减少后，每个 item 的间距和呼吸感应适当增加
- Issue index→detail 切换时不应有页面级闪烁或布局跳动
- Members 页面保持现有的 `TeamContentShell` + Card 结构

---

## Phase 0: 精简左侧 section rail 并合并 invites 到 members

### 目标

把左侧 rail 从 4 个 section 减为 3 个，把 invites 功能整合到 members 页面。

### 任务清单

#### 0.1 从 section rail 移除 invites

**描述：** 更新 `team-sections.ts` 中的 `TeamSectionId` 类型，移除 `"invites"`，只保留 `"overview" | "members" | "issues"`。更新 `buildTeamSectionHref` 移除 invites 的路由映射。更新 `TeamLibraryShell` 中的 sections 构建逻辑，不再包含 invites。

**涉及文件：**

- `frontend/features/workspaces/lib/team-sections.ts` — 移除 invites section ID 和路由
- `frontend/features/workspaces/ui/team-library-shell.tsx` — 更新 sections 构建
- `frontend/features/workspaces/ui/team-section-rail.tsx` — 无需改动（通用组件，只渲染传入的 sections）

**验收标准：**

- [x] `TeamSectionId` 类型不再包含 `"invites"`
- [x] 左侧 rail 只显示 3 个 section：Overview、Members、Issues
- [x] 点击 Overview / Members / Issues 仍能正确导航

#### 0.2 将 invites 整合到 members 页面

**描述：** 修改 `TeamMembersPageClient`，在成员列表上方添加"邀请"按钮，点击后打开一个 dialog。Dialog 内展示当前 invites 列表（复用现有的 invite 渲染逻辑）和"创建邀请"按钮。现有的 `TeamInvitesPageClient` 中的邀请列表渲染和 `CreateInviteDialog` 可以复用。

**涉及文件：**

- `frontend/features/workspaces/ui/team-pages.tsx` — 修改 `TeamMembersPageClient`，添加邀请 dialog
- `frontend/features/workspaces/index.ts` — 移除 `TeamInvitesPageClient` 导出（如果不再需要独立页面）

**验收标准：**

- [x] Members 页面顶部有"邀请"按钮
- [x] 点击"邀请"按钮打开 dialog，内含邀请列表和创建入口
- [x] 邀请列表的复制、状态展示、过期处理保持不变

#### 0.3 废弃 /team/invites 路由

**描述：** 移除 `frontend/app/[lng]/(shell)/team/invites/page.tsx` 路由文件，或将其重定向到 `/team/members`。

**涉及文件：**

- `frontend/app/[lng]/(shell)/team/invites/page.tsx` — 删除或改为重定向

**验收标准：**

- [x] `/team/invites` 路由不再渲染独立的 invites 页面
- [x] 访问 `/team/invites` 应重定向到 `/team/members` 或返回 404

---

## Phase 1: 重构 issues 为内部状态驱动的 index→detail 模式

### 目标

把 issues 从路由跳转改为内部 state 切换的 index→detail 模式，在右侧 detail pane 内完成切换。

### 任务清单

#### 1.1 为 issues section 建立 index→detail 状态管理

**描述：** 在 issues 页面中引入 `selectedIssueId` 状态（`string | null`）。当 `selectedIssueId` 为 `null` 时展示 issue index（board 列表 + issue 列表）；当有值时展示 issue detail。使用 URL query param（如 `?issue=<id>`）来持久化选中状态，参照 capabilities 的 `?view=` 模式。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx` — 重构 `TeamIssuesPageClient`

**验收标准：**

- [ ] `selectedIssueId` 为 `null` 时右侧显示 issue index
- [ ] `selectedIssueId` 有值时右侧显示 issue detail
- [ ] URL query param `?issue=<id>` 能持久化选中状态
- [ ] 左侧 rail 始终选中 "Issues"

#### 1.2 在 issue detail 中添加返回按钮

**描述：** 当处于 detail 视图时，在 issue 详情顶部添加返回按钮。点击后清除 `selectedIssueId`，回到 issue index。移动端同样显示此按钮。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx` — 在 detail 视图顶部添加返回按钮

**验收标准：**

- [ ] detail 视图顶部有明确的返回按钮
- [ ] 点击返回后回到 issue index，board 和 issue 列表保持之前的选中状态
- [ ] 移动端同样显示返回按钮

#### 1.3 废弃 /team/issues/[issueId] 路由

**描述：** 移除 `frontend/app/[lng]/(shell)/team/issues/[issueId]/page.tsx` 路由文件。issue 详情不再通过独立路由访问。如果存在从其他页面（如 chat session）链接到 `/team/issues/[issueId]` 的地方，改为链接到 `/team/issues?issue=<id>`。

**涉及文件：**

- `frontend/app/[lng]/(shell)/team/issues/[issueId]/page.tsx` — 删除
- 搜索代码库中引用 `/team/issues/${issueId}` 的链接并更新

**验收标准：**

- [ ] `/team/issues/[issueId]` 路由不再存在
- [ ] 从外部链接到 issue 详情使用 `/team/issues?issue=<id>` 格式
- [ ] `TeamIssueDetailPageClient` 仍可复用，只是渲染方式从路由级改为 pane 内切换

---

## Phase 2: 清理废弃路由和冗余代码

### 目标

清理 Phase 0 和 Phase 1 遗留的废弃文件和代码。

### 任务清单

#### 2.1 移除不再需要的导出和组件

**描述：** 从 `features/workspaces/index.ts` 移除 `TeamInvitesPageClient` 导出。如果 `TeamInvitesPageClient` 的逻辑已完全整合到 `TeamMembersPageClient`，可以删除该组件。从 `features/issues/index.ts` 确认 `TeamIssueDetailPageClient` 的导出仍然保留（它作为 detail 视图组件仍在使用）。

**涉及文件：**

- `frontend/features/workspaces/index.ts` — 移除 `TeamInvitesPageClient`
- `frontend/features/workspaces/ui/team-pages.tsx` — 可选删除 `TeamInvitesPageClient`

**验收标准：**

- [ ] barrel export 不再导出 `TeamInvitesPageClient`
- [ ] 无未使用的导入或导出

#### 2.2 清理 i18n 中的废弃 key

**描述：** 检查是否有仅被已删除页面使用的 i18n key，但注意不要删除仍在 members dialog 中使用的 invites 相关 key（如 `workspaces.invites.title`、`workspaces.invites.description` 等）。

**涉及文件：**

- `frontend/lib/i18n/locales/*/translation.json` — 审查并清理

**验收标准：**

- [ ] 无仅被已删除页面使用的孤立 i18n key
- [ ] members dialog 中使用的 invites key 保持不变

---

## Phase 3: 移动端对齐与验收

### 目标

确保精简后的 3-section rail 和 issues 的 index→detail 模式在移动端正常工作。

### 任务清单

#### 3.1 验证移动端 3-section rail 行为

**描述：** 确认移动端在 `/team` 路由时显示 section list（Overview、Members、Issues），点击后进入 detail。返回按钮回到 section list。

**涉及文件：**

- `frontend/features/workspaces/ui/team-library-shell.tsx` — 确认移动端逻辑仍正确

**验收标准：**

- [ ] 移动端 section list 只显示 3 个入口
- [ ] 点击 Members / Issues 进入 detail，有返回按钮
- [ ] 返回按钮回到 section list

#### 3.2 验证移动端 issues index→detail

**描述：** 确认移动端在 issues section 中，index→detail 切换正常工作。detail 视图有返回按钮回到 index。

**涉及文件：**

- `frontend/features/issues/ui/issues-pages.tsx`

**验收标准：**

- [ ] 移动端 issues index 正常显示 board 列表和 issue 列表
- [ ] 点击 issue 进入 detail，有返回按钮
- [ ] 返回按钮回到 issue index

#### 3.3 构建与质量验收

**描述：** 运行 lint 和 build，确认所有改动不引入错误。

**涉及文件：**

- `frontend/`

**验收标准：**

- [ ] `pnpm lint` 通过
- [ ] `pnpm build` 通过
- [ ] 新增或调整的用户文案全部完成 i18n 覆盖
- [ ] 更新 `05-workspace-team-library-layout-plan.md` 中相关验收状态

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 移除 `/team/issues/[issueId]` 路由后，外部链接失效 | 从 chat session 或其他页面跳转到 issue 详情的链接会 404 | 全局搜索代码库中的 issueId 链接并更新为 query param 格式 |
| issue detail 的数据加载在 pane 内切换时可能闪烁 | 用户从 index 点进 detail 时，右侧 pane 会先空再加载 | 使用 Suspense 或在 index 中预取选中 issue 的数据 |
| invites 合并到 members 后，dialog 内容过多 | 邀请列表很长时 dialog 高度溢出 | dialog 内容区使用 `max-h-[60vh] overflow-y-auto` 限制高度 |
| 移动端 issues index→detail 的返回按钮位置不明确 | 用户不知道如何从 detail 回到 index | 在 detail 视图顶部左侧放置 ChevronLeft 返回按钮，与 capabilities 的 mobile back 一致 |

---

## 总结

这份 spec 的核心是把 team 区域的交互从"路由驱动的独立页面堆叠"收敛为"内部状态驱动的 index→detail 切换"。section rail 精简到 3 个入口后导航更清晰；issues 的 detail 在 pane 内切换后上下文不丢失；invites 合并到 members 后操作路径更短。这些改动让 team 区域真正对齐 capabilities 的模块语法，而不是形似神不似。
