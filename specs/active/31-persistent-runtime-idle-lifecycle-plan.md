# Persistent runtime idle lifecycle plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-05-30 |
| **预期改动范围** | backend persistent runtime registry / executor_manager idle controller / server agent & persistent assignment lifecycle / frontend runtime status & controls / targeted tests |
| **改动类型** | feature / architecture-evolution |
| **优先级** | P1 |
| **状态** | in_progress |
| **关联 issue** | n/a |

## 实施阶段

- [x] Phase 0: 固定 owner 范围、状态词典与 stop 边界
- [x] Phase 1: 建立 backend persistent runtime registry
- [x] Phase 2: 将 runtime activity、keepalive 与执行链路打通
- [x] Phase 3: 为 executor_manager 增加 idle controller 与 restart 路径
- [ ] Phase 4: 对外暴露 runtime summary、手动保活与睡眠动作
- [ ] Phase 5: 验证、灰度、回写 spec

---

## 背景

当前 Poco 已经有 persistent runtime 的使用场景，但还没有 persistent runtime 的生命周期控制：

- server agent mention / collaboration 会用 `container_mode="persistent"` + `agent_runtime_mode="persistent"` 触发同一个长期 agent。
- workspace issue 的 `persistent_sandbox` assignment 也会在 `AgentAssignmentService` 中保留 `session_id` 与 `container_id`。
- executor_manager 的 `ContainerPool` 会尽量复用 persistent container，但 `on_task_complete()` 只自动停止 ephemeral 容器。
- `CleanupService` 只清理 workspace，不清理 persistent container。

因此，系统当前实际上处于一种不完整的中间态：

- 状态是持久化的；
- 容器复用已经存在；
- 但 persistent compute 缺少“空闲后自动休眠、下次再自动恢复”的调度层。

这导致资源长期被占用，也让 runtime 生命周期难以被前后端解释。

## 目标

本计划要把 Poco 的 persistent runtime 从“默认常驻容器”升级成“有生命周期控制的可恢复 runtime”：

- 为 server agent 与 `persistent_sandbox` assignment 引入统一的 runtime registry。
- 把 runtime 状态收敛成 `running / warm_idle / sleeping / manually_stopped / stale / removed`。
- 让 executor_manager 定期 stop 空闲 persistent container，但保留 workspace、`/agent_state`、`sdk_session_id` 等恢复锚点。
- 让新的 persistent run 到来时自动恢复 `sleeping` runtime。
- 让前端与业务 API 能稳定表达 sleeping / keep warm / sleep now，而不是继续依赖低层 `container_id` 或原始 runtime_status。

## 非目标

- 不在本轮引入 Docker checkpoint / CRIU / VM snapshot 这类底层 suspend 能力。
- 不在本轮解决多 executor_manager 部署下的全局分布式锁问题。
- 不把 `agent_runtime_mode` 与 `container_mode` 合并成一个字段；两者职责继续分离。
- 不把普通前端轮询直接变成 keepalive 信号。
- 不在本轮重做整个 server workspace 布局。

## 关键洞察

### 1. 持久状态已经存在，真正缺的是生命周期控制

`/agent_state`、session workspace、`sdk_session_id` 都已经可以作为恢复锚点。Persistent runtime 当前的问题不是“状态会丢”，而是“计算从未进入 sleep 语义”。

### 2. `running` 与 `idle` 不足以表达产品心智

自动睡眠、手动停止、owner 被移除、状态漂移，这些都不应挤进一个模糊的 `idle`。后续 UI、调度和回收逻辑都需要更细的状态词典。

### 3. 只在 manager 里加 TTL 不够

如果没有 backend source of truth，runtime 状态在 manager 重启后会漂移；frontend 也无法解释某个 agent 为什么“明明没在跑，但也不是被 stop 了”。

### 4. keepalive 必须是显式租约，而不是任何页面停留都延长保活

一旦把普通轮询视为 activity，persistent runtime 会重新退化成“只要前端开着就永远不睡”。保活必须来自有限、可审计、可过期的 lease。

## Phase 0: 固定 owner 范围、状态词典与 stop 边界

### 目标

先把“谁拥有 persistent runtime”“哪些状态是用户可见状态”“什么情况下允许自动睡眠”全部固定下来，避免实现时继续混用 `runtime_status`、`lifecycle_state` 和 `container_id`。

### 任务清单

#### 0.1 列出所有 current persistent runtime owner

**描述：** 明确首版只覆盖两类 owner：

- server agent runtime
- `persistent_sandbox` assignment runtime

**涉及文件：**

- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/services/channel_runtime_service.py`
- `backend/app/services/agent_assignment_service.py`
- `executor_manager/app/services/container_pool.py`

**验收标准：**

- [ ] spec 中明确首版 owner 范围
- [ ] 不把普通 ephemeral chat session 纳入 persistent runtime registry

#### 0.2 固定 runtime lifecycle 词典

**描述：** 固定以下用户可见状态：

- `running`
- `warm_idle`
- `sleeping`
- `manually_stopped`
- `stale`
- `removed`

并明确：

- run/session 终态中的 `failed` 不直接作为 runtime 主状态；
- `AgentPersistentState.runtime_status` 仅保留低层兼容意义，不再作为最终 UI 语义。

**验收标准：**

- [ ] backend、manager、frontend 共用同一套 runtime lifecycle 词典
- [ ] `sleeping` 与 `manually_stopped` 在语义上明确区分

#### 0.3 固定自动睡眠的禁止条件

**描述：** 明确以下情况绝不能自动 sleep：

- 该 runtime 仍有 blocking run
- 对应 session 仍有 active queue item
- cancellation 尚未完成
- keepalive lease 尚未过期
- owner 已进入 `removed` 或显式 `manually_stopped`

**涉及文件：**

- `backend/app/services/agent_runtime_service.py`
- `backend/app/services/session_service.py`
- `backend/app/repositories/run_repository.py`
- `backend/app/repositories/session_queue_item_repository.py`

**验收标准：**

- [ ] spec 中有明确 stop boundary
- [ ] 后续 controller 逻辑不需要再猜“busy 但可不可以停”

## Phase 1: 建立 backend persistent runtime registry

### 目标

把 persistent runtime 的 owner、状态、keepalive 和最近活动时间落到 backend 持久层，成为唯一权威来源。

### 任务清单

#### 1.1 新增 persistent runtime 模型、迁移和 repository

**描述：** 新增通用 `PersistentRuntime` 模型、Alembic 迁移、repository 和 schema。

**涉及文件：**

- 新增 `backend/app/models/persistent_runtime.py`
- 新增 `backend/app/repositories/persistent_runtime_repository.py`
- 新增 `backend/app/schemas/persistent_runtime.py`
- 新增 `backend/alembic/versions/*_add_persistent_runtime_registry.py`

**验收标准：**

- [ ] 能按 `runtime_key` 唯一定位 runtime
- [ ] 能记录 owner、container、lifecycle、keepalive、最近活动等核心字段
- [ ] agent 和 assignment 两类 owner 都能被建模

#### 1.2 新增 persistent runtime service

**描述：** 新增 service 统一处理：

- upsert runtime owner
- bind / unbind container
- refresh activity
- extend / clear keepalive
- transition lifecycle state
- mark stale / removed / manually_stopped

**涉及文件：**

- 新增 `backend/app/services/persistent_runtime_service.py`
- 新增或修改 `backend/app/core/errors/error_codes.py`

**验收标准：**

- [ ] 所有 runtime transition 走 service，而不是散落在各业务 service 中直接改字段
- [ ] transition 规则可被单测覆盖

#### 1.3 暴露 manager 需要的 internal API

**描述：** 为 executor_manager 增加一组最小 internal API，用于：

- 读取 runtime by key / by container_id
- 上报 container started / stopped / stale
- 刷新 keepalive / activity

**涉及文件：**

- 新增 `backend/app/api/v1/internal_persistent_runtimes.py`
- 修改 `backend/app/api/__init__.py`
- 新增 `backend/app/schemas/internal_persistent_runtime.py`

**验收标准：**

- [ ] manager 无需直接访问数据库即可完成 runtime state 同步
- [ ] internal API 与现有 session internal API 的权限模式一致

## Phase 2: 将 runtime activity、keepalive 与执行链路打通

### 目标

让 enqueue、trigger、run start、callback、cancel、remove 这些真实业务动作都能更新 runtime registry，而不是让 registry 成为“只在 stop 时改一次”的死状态。

### 任务清单

#### 2.1 在 trigger / enqueue 路径上解析 runtime owner 并写入 runtime_key

**描述：** persistent run 入队时，统一生成 runtime key，并写入 session/run config snapshot，避免 manager 只能通过 `container_id` 或 `agent_identity_id` 猜 owner。

**涉及文件：**

- `backend/app/services/task_service.py`
- `backend/app/services/server_agent_trigger_service.py`
- `backend/app/services/channel_runtime_service.py`
- `backend/app/services/agent_assignment_service.py`
- `backend/app/schemas/session.py`
- `executor_manager/app/schemas/task.py`
- `executor/app/schemas/request.py`

**验收标准：**

- [ ] 所有 persistent run 的 snapshot 都带 `persistent_runtime_key`
- [ ] manager 不再依赖 owner-specific 分支猜测 runtime key

#### 2.2 在 callback / cancel / stop / remove 路径上同步 runtime lifecycle

**描述：** run 进入 `running`、`completed`、`failed`、`canceled`，以及 server agent stop/remove、assignment release/cancel 时，都要统一更新 runtime registry。

**涉及文件：**

- `backend/app/services/callback_service.py`
- `backend/app/services/session_service.py`
- `backend/app/services/agent_identity_service.py`
- `backend/app/services/agent_assignment_service.py`
- `backend/app/services/agent_runtime_service.py`

**验收标准：**

- [ ] runtime state 不再只依赖 manager-side stop 结果
- [ ] removed agent / released assignment 会阻断后续 auto resume

#### 2.3 建立 keepalive lease 模型

**描述：** 为 runtime 增加 bounded keepalive 规则：

- run enqueue / start / callback 会刷新基础 activity；
- 明确的手动 keep warm 或页面 presence 才会延长 `keepalive_until`；
- 普通列表轮询不刷新 keepalive。

**涉及文件：**

- `backend/app/services/persistent_runtime_service.py`
- 新增或修改 `backend/app/schemas/persistent_runtime.py`
- 可能新增 `backend/app/services/persistent_runtime_presence_service.py`

**验收标准：**

- [ ] keepalive 与 `last_activity_at` 区分开
- [ ] 可以同时表达“最近有 activity，但 keepalive 已过期”

## Phase 3: 为 executor_manager 增加 idle controller 与 restart 路径

### 目标

让 manager 能按 runtime registry 周期性 stop 空闲 persistent container，并在下一次 dispatch 时自动恢复。

### 任务清单

#### 3.1 改造 ContainerPool 以 runtime_key 为核心，而不是纯内存 session 映射

**描述：** `ContainerPool` 需要能：

- 用 `persistent_runtime_key` 定位 persistent container
- 在 manager 重启后通过 Docker labels + backend registry 重新绑定
- 区分 `container exists but sleeping`、`container exists and reusable`、`container missing/stale`

**涉及文件：**

- `executor_manager/app/services/container_pool.py`
- `executor_manager/app/schemas/task.py`

**验收标准：**

- [ ] persistent container 复用的主键变成 runtime_key
- [ ] manager 重启后 persistent runtime 仍可被恢复或标记 stale

#### 3.2 新增 idle controller 定时任务

**描述：** 参照现有 `CleanupService` 模式，新增 runtime idle controller。它按固定周期扫描 backend runtime registry，决定哪些 runtime：

- 保持 `running`
- 转成 `warm_idle`
- stop container 并转成 `sleeping`
- 标记 `stale`

**涉及文件：**

- 新增 `executor_manager/app/services/runtime_idle_service.py`
- 修改 `executor_manager/app/core/lifespan.py`
- 修改 `executor_manager/app/core/settings.py`
- 可能新增 `executor_manager/app/services/backend_client.py` 的 runtime 方法

**验收标准：**

- [ ] controller 可通过配置开关启停
- [ ] stop 结果会回写 backend runtime registry
- [ ] controller 不误停仍有 live work 的 runtime

#### 3.3 在 dispatch 路径上支持 sleeping runtime 自动恢复

**描述：** `TaskDispatcher` / `RunPullService` 触发 persistent run 时，如果 runtime 是 `sleeping` 或 `stale`，应先重建容器，再继续执行。

**涉及文件：**

- `executor_manager/app/scheduler/task_dispatcher.py`
- `executor_manager/app/services/run_pull_service.py`
- `executor_manager/app/services/container_pool.py`

**验收标准：**

- [ ] persistent run 到来时无需人工干预即可唤醒 sleeping runtime
- [ ] 恢复后能继续使用 workspace、`/agent_state` 与 `sdk_session_id`

## Phase 4: 对外暴露 runtime summary、手动保活与睡眠动作

### 目标

把新的 runtime lifecycle 收敛到 backend response 和 frontend UI，让用户能理解“它为什么睡了、现在能不能唤醒、我能不能显式保活”。

### 任务清单

#### 4.1 在 server agent 和 assignment response 中增加 runtime summary

**描述：** 返回结构化 runtime summary，而不是只暴露 `persistent_state.runtime_status` 或 `assignment.container_id`。

**涉及文件：**

- `backend/app/schemas/agent_identity.py`
- `backend/app/schemas/agent_assignment.py`
- `backend/app/services/agent_identity_service.py`
- `backend/app/services/agent_assignment_service.py`
- `frontend/features/servers/api/servers-api.ts`
- `frontend/features/issues/api/issues-api.ts`
- `frontend/features/issues/model/types.ts`

**验收标准：**

- [ ] frontend 不需要再用多处启发式组合 runtime 状态
- [ ] server agent 与 assignment 使用同一套 summary 词典

#### 4.2 改造 server colleagues UI

**描述：** 更新 server colleagues 相关 UI，展示 `warm_idle`、`sleeping`、`manually_stopped`、`stale`，并增加手动动作：

- `Keep warm`
- `Sleep now`
- `Resume`

**涉及文件：**

- `frontend/features/servers/lib/agent-runtime-status.ts`
- `frontend/features/servers/lib/agent-runtime-status.test.ts`
- `frontend/features/servers/ui/colleagues-panel.tsx`
- `frontend/features/servers/ui/colleague-detail.tsx`
- `frontend/features/servers/ui/server-conversation-page-client.tsx`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] 列表和详情显示一致的 runtime 状态
- [ ] 用户能区分 auto sleep 与 manual stop

#### 4.3 改造 issue assignment 执行信息面板

**描述：** issue 详情中的 assignment 执行信息不再只展示 `container_id` 是否存在，而要展示 runtime summary 与保活状态。

**涉及文件：**

- `frontend/features/issues/lib/issue-detail-view.ts`
- `frontend/features/issues/ui/team-issue-detail-content.tsx`
- `frontend/features/issues/lib/issue-detail-view.test.ts`
- `frontend/lib/i18n/locales/*/translation.json`

**验收标准：**

- [ ] assignment 面板能直接看出 sleeping / running / manually_stopped
- [ ] 手动 `Release container` 语义与新的 `Sleep now` / `Resume` 不再混淆

## Phase 5: 验证、灰度、回写 spec

### 目标

确保 idle lifecycle 在正确性、可恢复性和用户认知层面都成立，再决定是否进一步引入 suspend 或 warm pool。

### 任务清单

#### 5.1 后端与 manager 测试补齐

**描述：** 增加 registry、controller、auto resume、manual stop、stale reconciliation 相关测试。

**涉及文件：**

- 新增 `backend/tests/test_persistent_runtime_service.py`
- 新增 `backend/tests/test_persistent_runtime_internal_api.py`
- 新增 `executor_manager/tests/test_runtime_idle_service.py`
- 新增 `executor_manager/tests/test_container_pool_persistent_runtime.py`

**验收标准：**

- [ ] `running -> warm_idle -> sleeping` 迁移可测
- [ ] `sleeping -> running` auto resume 可测
- [ ] `manually_stopped` 不被 idle controller 自动恢复

#### 5.2 前端状态与动作验证

**描述：** 增加 runtime 状态映射和 issue/server UI 的最小测试覆盖。

**涉及文件：**

- `frontend/features/servers/lib/agent-runtime-status.test.ts`
- `frontend/features/issues/lib/issue-detail-view.test.ts`

**验收标准：**

- [ ] 新状态不会退化成 `unknown`
- [ ] manual stop 与 sleeping 的 UI 文案不同

#### 5.3 灰度与观测

**描述：** 为 rollout 增加最小观测指标和开关：

- runtime auto sleep count
- runtime auto resume count
- stale runtime count
- average sleep duration
- cold resume latency

**涉及文件：**

- `backend/app/services/persistent_runtime_service.py`
- `executor_manager/app/services/runtime_idle_service.py`
- `executor_manager/app/core/settings.py`

**验收标准：**

- [ ] 可以通过配置关闭 idle controller
- [ ] 首版 rollout 能观察“释放了多少资源、恢复代价多大”

## 验证建议

- `cd backend && uv run pytest tests/test_persistent_runtime_service.py tests/test_persistent_runtime_internal_api.py`
- `cd executor_manager && uv run pytest tests/test_runtime_idle_service.py tests/test_container_pool_persistent_runtime.py`
- `cd frontend && pnpm lint`
- `cd frontend && pnpm build`
- 手工场景 1：server agent 完成一次 run 后在 idle timeout 后自动进入 `sleeping`
- 手工场景 2：对 sleeping agent 再次 mention，确认 runtime 自动恢复并继续原有长期状态
- 手工场景 3：manual stop 后不被自动 keepalive 或普通 channel mention 拉起；只有显式 resume，或 assignment owner 侧的明确 trigger/retry，才恢复
- 手工场景 4：persistent assignment 在空闲后睡眠，再次 trigger 能恢复原 workspace

## 风险与关注点

- runtime registry 与旧 `AgentPersistentState.runtime_status` 共存期间，容易出现双状态漂移；需要明确哪一个是最终用户语义。
- manager 重启后，如果 Docker labels 与 backend registry 不一致，必须优先把 runtime 标成 `stale`，而不是假设一切正常。
- 旧的 `releaseAssignmentContainer()` 语义更像“手动 destroy/release”；引入 `Sleep now` 后需要避免用户误以为两者等价。
- 若 `sdk_session_id` 对跨容器恢复存在边界情况，必须把失败回退到“保留长期状态但从新会话继续”，而不是让恢复逻辑卡死。

## 小结

这份 plan 的目标不是单纯做一个“闲置 N 分钟就 stop”的小修，而是把 Poco 的 persistent runtime 语义补完整：**状态可持久、计算可睡眠、任务到来可恢复、前后端都能解释当前处于哪一种生命周期状态。** 只有把 registry、controller、resume 和 UI 四层一起补齐，persistent 才会从“长期占资源”变成真正可运营的能力。
