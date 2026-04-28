# 团队协作与 Agent 执行设计决策

## 元数据

| 字段 | 值 |
|------|-----|
| **决策日期** | 2026-04-15 |
| **关联 spec** | `00-workspace-tenancy-foundation-plan.md`、`01-workspace-collaboration-plan.md`、`02-workspace-agent-execution-plan.md` |

---

## 背景

在确定 workspace tenancy 的基础架构（AUTH_MODE、workspace、membership、invite、role）之后，团队协作的设计进入第二层问题：团队内部到底共享什么资源、如何协作、以及如何让 AI agent 参与到团队工作流中。

这引出了几个需要收敛的设计问题：

1. **spec 如何拆分**——最初的调研建议拆成两份 spec（tenancy foundation + collaboration），但随着讨论深入，"issue 分配给 preset 让 AI 自动执行"这个需求逐渐清晰。它不是共享资源的范畴，而是一个新的执行触发机制。如果硬塞进 collaboration plan，那份 spec 的范围会膨胀到不可控。

2. **issue 的 assignee 到底是什么**——传统 issue 系统的 assignee 是"分配给谁做"。但在 Poco 中，"谁"可以是一个人，也可以是一个 preset（代表一组 AI agent 能力）。这两种 assignee 的后续行为完全不同：人需要通知和跟踪，AI 需要触发执行。如果只支持其中一种，要么丧失人工协作能力，要么丧失 AI 自动化能力。

3. **AI 如何执行团队任务**——当前 Poco 的执行模型是严格的请求-响应：用户发 prompt → 容器启动 → agent 运行 → 响应返回 → 容器销毁。但"给 AI 分配一个 issue 让它自主完成"需要的是一种不同的执行模式：agent 可能需要持续工作数小时，保持上下文，甚至周期性地执行。

4. **issue board 的灵活性边界**——不同团队的协作习惯差异很大（游戏团队需要"平台"字段，后端团队需要"服务"字段），但如果第一版就做完全自定义字段平台，范围会失控。

这些问题相互关联：assignee 设计决定了 issue board 的数据模型，issue 数据模型决定了执行触发的方式，执行触发方式反过来又影响了 spec 的拆分策略。因此需要在一个统一的决策中收敛所有这些问题。

---

## 用户叙事：AI 参与团队工作流

以下是第一版团队协作 + AI 执行预期实现的功能流程，聚焦于上一次用户叙事中未覆盖的新能力：

**Bob 是团队成员，他想让 AI 帮忙完成一个 issue。**

1. **创建 issue 并分配 AI**：Bob 在 "Sprint 24" 看板上创建了一个 issue："为所有 API 端点添加速率限制"。他点击 assignee 选择器，选择"Backend Specialist" preset 而非某个团队成员。系统弹出触发方式选择：Bob 选择"持久化 sandbox"——因为这个任务需要 agent 持续阅读代码、修改多个文件、保持上下文。

2. **自动生成 prompt 并执行**：系统根据 issue 标题、描述和关联的 project 自动生成 prompt，Bob 确认后，系统创建了一个持久化容器，agent 开始在容器中工作。Bob 在 issue 详情页看到"执行中"状态和实时进度。

3. **追加指令**：agent 工作了一段时间后，Bob 发现它遗漏了一个边缘 case。他在 issue 下方的对话框中发送追加指令："别忘了处理 admin 角色的速率限制豁免"。agent 收到指令后继续工作，上下文保持连续。

4. **审核结果**：agent 完成工作后，issue 状态自动变为 done。Bob 点击查看执行 session，检查 agent 的代码变更。他满意后手动将变更合并到项目主分支。系统没有自动创建 PR——第一版的结果采纳由人类决定。

5. **定时任务场景**：另一天，Alice 创建了一个 issue："每日检查 staging 环境的错误日志并生成摘要"，分配给"Log Analyzer" preset，选择"定时任务"触发方式，设置 cron 为每天早上 9 点。系统每天自动触发 agent 执行，执行结果作为 issue comment 记录。

   > 团队中的定时任务，与 issue 本身可以独立；也就是 issue 本身可以具有持久/临时性容器

6. **人类和 AI 之间的切换**：Carol 原本被分配了一个 issue，但她请产假了。Alice 将该 issue 的 assignee 从 Carol 切换为"Frontend Fixer" preset。旧的人类 assignee 自动清除，AI preset assignee 接管，无需手动删除旧的分配关系。

7. **自定义字段**：Alice 在 "Sprint 24" 看板的设置中添加了一个自定义字段"影响范围"（select 类型：全局 / 模块 / 组件）。团队成员在创建 issue 时可以选择这个字段，但系统字段（标题、状态、优先级等）不可删除或修改类型。

---

## 决策结论

> 团队协作能力拆分为三份 spec：tenancy foundation（P0）负责基础设施和审计日志，collaboration（P1）负责共享资源和 issue board（含双模 assignee、可配置字段模板），agent execution（P1）负责 issue → preset → agent 执行链路（持久化 sandbox + 定时任务双触发模式）。Issue 支持 人类 + AI preset 双模 assignee（互斥），执行结果由人类审核而非自动采纳。

---

## 关键论点

### 为什么双模 assignee 采用互斥设计而非并存

双模的意思是"两种类型都支持"，但一个 issue 在同一时间只应该有一个 assignee。这不是技术限制，而是产品设计选择：

- **责任归属必须明确**——如果一个 issue 同时分配给了 Bob 和"Backend Specialist" preset，当 issue 被完成时，谁算"完成了这个任务"？如果出问题了，谁负责？并存的语义在责任追踪上会产生歧义。
- **切换场景需要清晰的状态转换**——Carol 请假时，Alice 把 issue 从 Carol 切换给 AI preset。如果两者并存，Alice 需要先"移除"Carol 再"添加"AI preset，两步操作比一步切换更容易出错。互斥设计让"切换 assignee"变成一个原子操作。
- **数据模型更简洁**——互斥意味着 `assignee_user_id` 和 `assignee_preset_id` 两个 nullable 字段加上一个 check constraint，不需要额外的"assignee_type"枚举字段或关联表。

### 为什么 issue board 采用"系统字段 + 可配置自定义字段"的两层模型

完全固定系统字段的问题已经说过（团队协作习惯各异）。但为什么不做完全自定义字段平台？

- **完全自定义字段平台的工程量**：需要字段类型引擎（text、number、date、select、multi_select、relation……）、字段排列和分组 UI、字段级权限（谁可以创建/编辑/查看哪些字段）、字段模板导入导出。这些在 Jira/Airtable 中是数百人年的工程量。
- **Poco 的后端复杂度不匹配**：当前 backend 的 issue 模型还是简单的系统字段表，直接上字段引擎意味着 schema 设计、repository 查询、service 层逻辑全部重构。
- **两层模型是务实的折中**：系统字段（title、status、priority 等）不可删改，保证 issue 数据的基本结构稳定；board 级自定义字段（通过 `workspace_board_fields` + `workspace_issue_field_values` 两张表实现）满足灵活性。自定义字段值用独立关联表存储，不影响主表的查询性能。

---

## 约束与前提

- 持久化 sandbox 依赖现有 `container_mode: "persistent"` 基础设施（`ContainerPool` 已支持 persistent 容器的创建、复用和销毁），不重新设计容器管理
- 执行层（executor / executor_manager）不感知 workspace，权限校验留在 backend
- 定时任务轮询间隔不低于 60 秒，避免对 backend 造成过大压力
- 双模 assignee 的互斥约束在数据库层通过 check constraint 保证，不依赖应用层逻辑

---

## 历史变更

| 日期 | 变更内容 | 原因 |
|------|----------|------|
| 2026-04-15 | 初次记录 | spec 拆分和 agent execution 设计讨论后达成共识 |
