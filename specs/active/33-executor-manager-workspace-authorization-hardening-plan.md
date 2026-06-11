# Executor Manager API authentication hardening plan

## 元数据

| 字段 | 值 |
| --- | --- |
| **创建日期** | 2026-06-11 |
| **预期改动范围** | executor_manager API auth dependencies / backend EM clients / executor callback clients / tests / deployment notes |
| **改动类型** | fix / security-hardening |
| **优先级** | P0 |
| **状态** | implemented |
| **关联 issue** | `poco-ai/poco-claw#133` |
| **关联 constitution** | `specs/constitution/2026-06-11-executor-manager-workspace-authorization.md` |

## 实施阶段

- [x] Phase 0: 路由盘点与失败测试
- [x] Phase 1: 内部控制面接口补 `X-Internal-Token`
- [x] Phase 2: Executor 回传/工具代理接口补 callback token
- [x] Phase 3: 用户态功能和部署边界回归
- [x] Phase 4: 验证、文档回写和后续加固记录

---

## 背景

### 问题陈述

`poco-ai/poco-claw#133` 报告的是 Executor Manager 的 `/api/v1/workspace/*` 没有鉴权，导致调用方可以通过 URL 中的 `user_id/session_id/path` 访问别人的执行 workspace。

复查 EM 路由后，问题不只是一条 workspace file route。当前 EM 中只有少数接口已经有 token：

- `/api/v1/internal/runs/notify` 已有 `X-Internal-Token`。
- `/api/v1/skills/submit` 已有 callback token。

其余多组接口在 HTTP 层没有 token。为了避免只补 issue PoC 而留下同类裸控制面，本计划按调用方分两步补齐：

1. Backend/internal service 调 EM 的控制面接口使用 `X-Internal-Token`。
2. Executor container 调 EM 的回传/工具代理接口使用 callback token。

### 目标

- `/api/v1/workspace/*` 直接无 token 访问返回 `403`。
- `/api/v1/tasks`、`/api/v1/executor/*`、`/api/v1/schedules` 只有带 `X-Internal-Token` 的内部调用可以访问。
- `/api/v1/callback`、`/api/v1/computer/screenshots`、`/api/v1/memories`、`/api/v1/agent-channel-*`、`/api/v1/user-input-requests` 只有带 callback token 的 executor 可以访问。
- Backend 用户态 `/sessions/{session_id}/workspace/*`、`/runs/{run_id}/workspace/*` 体验不变。
- 不把 `INTERNAL_API_TOKEN` 暴露给 executor container。
- 不把 callback token 授予控制面能力。

### 非目标

- 不在 v1 引入 session-scoped workspace capability。
- 不重做 Backend 用户态 session/run 鉴权。
- 不改变 workspace export manifest 格式。
- 不改变 share link、share to channel、channel artifacts 的产品语义。
- 不在本轮解决多 EM 部署下的 token rotation/revocation。

---

## Phase 0: 路由盘点与失败测试

### 目标

先把当前裸接口和预期鉴权方式固定下来，避免实现时漏掉调用方同步。

### 任务清单

#### 0.1 固定 EM 路由鉴权矩阵

**描述：** 在测试或文档注释中固定以下分类，作为实现检查表。

**涉及文件：**

- `executor_manager/app/api/v1/__init__.py`
- `executor_manager/app/api/v1/workspace.py`
- `executor_manager/app/api/v1/tasks.py`
- `executor_manager/app/api/v1/executor.py`
- `executor_manager/app/api/v1/schedules.py`
- `executor_manager/app/api/v1/callback.py`
- `executor_manager/app/api/v1/computer.py`
- `executor_manager/app/api/v1/memories.py`
- `executor_manager/app/api/v1/agent_channel_runtime.py`
- `executor_manager/app/api/v1/agent_channel_artifacts.py`
- `executor_manager/app/api/v1/agent_channel_tasks.py`
- `executor_manager/app/api/v1/user_input_requests.py`
- `executor_manager/app/api/v1/skills_upload.py`
- `executor_manager/app/api/v1/internal_runs.py`

**验收标准：**

- [x] health/root route 明确保持无 token。
- [x] `/internal/runs/notify` 明确保持 `X-Internal-Token`。
- [x] `/skills/submit` 明确保持 callback token。
- [x] workspace/tasks/executor/schedules 明确归类为 internal control plane。
- [x] callback/computer/memories/agent-channel/user-input 明确归类为 executor callback/tool proxy。

#### 0.2 增加 control plane 鉴权失败测试

**描述：** 新增或扩展 EM API auth 测试，先证明无 token 访问会失败。

**涉及文件：**

- 新增 `executor_manager/tests/test_control_plane_auth.py`
- `executor_manager/app/api/v1/workspace.py`
- `executor_manager/app/api/v1/tasks.py`
- `executor_manager/app/api/v1/executor.py`
- `executor_manager/app/api/v1/schedules.py`

**建议用例：**

- `GET /api/v1/workspace/file/victim/{session}?path=secret.txt` without token returns `403`
- `GET /api/v1/workspace/files/victim/{session}` without token returns `403`
- `POST /api/v1/workspace/archive/victim/{session}` without token returns `403`
- `DELETE /api/v1/workspace/victim/{session}` without token returns `403`
- `POST /api/v1/tasks` without token returns `403`
- `POST /api/v1/executor/delete` without token returns `403`
- `GET /api/v1/executor/load` without token returns `403`
- `GET /api/v1/schedules` without token returns `403`
- `GET /api/v1/health` still returns `200`

**验收标准：**

- [x] 当前未修复代码下这些测试能暴露缺口。
- [x] 修复后全部返回预期状态。
- [x] 测试不依赖 Docker daemon 或真实 object storage。

#### 0.3 增加 executor proxy 鉴权失败测试

**描述：** 覆盖 executor 回传/工具代理接口，未带 callback token 应返回 `403`。

**涉及文件：**

- 新增 `executor_manager/tests/test_executor_proxy_auth.py`
- `executor_manager/app/api/v1/callback.py`
- `executor_manager/app/api/v1/computer.py`
- `executor_manager/app/api/v1/memories.py`
- `executor_manager/app/api/v1/agent_channel_runtime.py`
- `executor_manager/app/api/v1/agent_channel_artifacts.py`
- `executor_manager/app/api/v1/agent_channel_tasks.py`
- `executor_manager/app/api/v1/user_input_requests.py`

**建议用例：**

- `POST /api/v1/callback` without bearer token returns `403`
- `POST /api/v1/computer/screenshots` without bearer token returns `403`
- `POST /api/v1/memories` without bearer token returns `403`
- `POST /api/v1/agent-channel-runtime/messages/read` without bearer token returns `403`
- `POST /api/v1/agent-channel-artifacts/list` without bearer token returns `403`
- `POST /api/v1/agent-channel-tasks/list` without bearer token returns `403`
- `POST /api/v1/user-input-requests` without bearer token returns `403`
- same endpoints with valid callback token preserve existing behavior through mocked services

**验收标准：**

- [x] 无 token 请求全部拒绝。
- [x] 带合法 callback token 请求不破坏现有 mock/service 调用。
- [x] `/api/v1/skills/submit` 继续通过现有 callback token 测试。

---

## Phase 1: 内部控制面接口补 `X-Internal-Token`

### 目标

把 Backend/internal service 调用的 EM 控制面接口收成 internal-only。

### 任务清单

#### 1.1 给 control plane routers 加 `require_internal_token`

**描述：** 给以下 router 或 route 增加 `Depends(require_internal_token)`：

- `/api/v1/workspace/*`
- `/api/v1/tasks`
- `/api/v1/executor/*`
- `/api/v1/schedules`

**涉及文件：**

- `executor_manager/app/api/v1/workspace.py`
- `executor_manager/app/api/v1/tasks.py`
- `executor_manager/app/api/v1/executor.py`
- `executor_manager/app/api/v1/schedules.py`
- `executor_manager/app/core/deps.py`
- `executor_manager/tests/test_control_plane_auth.py`

**验收标准：**

- [x] 无 `X-Internal-Token` 时返回 `403`。
- [x] 错误 `X-Internal-Token` 时返回 `403`。
- [x] 正确 `X-Internal-Token` 时保持原有功能。
- [x] health/root route 不受影响。

#### 1.2 更新 Backend 调 EM 的 control plane client

**描述：** Backend 调 EM control plane 时必须带 `X-Internal-Token`。

**涉及文件：**

- `backend/app/services/executor_manager_client.py`
- `backend/app/api/v1/schedules.py`
- 可能涉及创建任务的 Backend service/client 调用路径
- `backend/tests/test_executor_manager_notify_service.py`
- 新增或扩展 `backend/tests/test_executor_manager_client.py`

**验收标准：**

- [x] `ExecutorManagerClient.delete_container()` 请求 `/api/v1/executor/delete` 时带 `X-Internal-Token`。
- [x] Backend schedules proxy 请求 `/api/v1/schedules` 时带 `X-Internal-Token`。
- [x] 如果 Backend 仍直接请求 `/api/v1/tasks`，该请求也带 `X-Internal-Token`。
- [x] 既有 `/api/v1/internal/runs/notify` 调用继续带 `X-Internal-Token`。

#### 1.3 保留 workspace 产品入口在 Backend

**描述：** 不把前端文件浏览改到 EM；只加固 EM 底层接口。

**涉及文件：**

- `backend/app/api/v1/sessions.py`
- `backend/app/api/v1/runs.py`
- `frontend/features/chat/api/chat-api.ts`
- `frontend/services/api-client.ts`

**验收标准：**

- [x] Frontend `chatService.getFiles()` 继续走 `/sessions/{session_id}/workspace/files`。
- [x] Frontend `chatService.getRunFiles()` 继续走 `/runs/{run_id}/workspace/files`。
- [x] Backend session/run workspace owner check 保持在读取 manifest 和生成 presigned URL 之前。

---

## Phase 2: Executor 回传/工具代理接口补 callback token

### 目标

把 executor container 调 EM 的回传和工具代理接口收成 callback-token-only，同时同步 executor client，避免执行链路被打断。

### 任务清单

#### 2.1 给 executor proxy routers 加 `require_callback_token`

**描述：** 给以下 router 或 route 增加 `Depends(require_callback_token)`：

- `/api/v1/callback`
- `/api/v1/computer/screenshots`
- `/api/v1/memories`
- `/api/v1/agent-channel-runtime/*`
- `/api/v1/agent-channel-artifacts/*`
- `/api/v1/agent-channel-tasks/*`
- `/api/v1/user-input-requests`

**涉及文件：**

- `executor_manager/app/api/v1/callback.py`
- `executor_manager/app/api/v1/computer.py`
- `executor_manager/app/api/v1/memories.py`
- `executor_manager/app/api/v1/agent_channel_runtime.py`
- `executor_manager/app/api/v1/agent_channel_artifacts.py`
- `executor_manager/app/api/v1/agent_channel_tasks.py`
- `executor_manager/app/api/v1/user_input_requests.py`
- `executor_manager/app/core/deps.py`
- `executor_manager/tests/test_executor_proxy_auth.py`

**验收标准：**

- [x] 无 `Authorization: Bearer <callback_token>` 时返回 `403`。
- [x] 错误 callback token 时返回 `403`。
- [x] 正确 callback token 时保持原有转发和上传行为。
- [x] `/api/v1/skills/submit` 保持现有 callback token 鉴权，不重复实现。

#### 2.2 Executor clients 统一带 callback token

**描述：** executor 侧所有调 EM 的回传/工具 client 都要带 `Authorization: Bearer <callback_token>`。

**涉及文件：**

- `executor/app/api/v1/task.py`
- `executor/app/core/callback.py`
- `executor/app/core/computer.py`
- `executor/app/core/memory.py`
- `executor/app/core/channel_runtime.py`
- `executor/app/core/user_input.py`
- `executor/tests/test_channel_runtime_tools.py`
- 新增或扩展 executor client auth tests

**验收标准：**

- [x] `CallbackClient` 初始化时接收 callback token，并在 `/api/v1/callback` 请求中发送 Bearer token。
- [x] `ComputerClient` 初始化时接收 callback token，并在 screenshot upload 请求中发送 Bearer token。
- [x] `MemoryClient` 初始化时接收 callback token，并在 memory proxy 请求中发送 Bearer token。
- [x] `ChannelRuntimeClient` 初始化时接收 callback token，并在 runtime/artifact/task proxy 请求中发送 Bearer token。
- [x] `UserInputClient` 初始化时接收 callback token，并在 user input 请求中发送 Bearer token。
- [x] `executor/app/api/v1/task.py` 从 `TaskRun.callback_token` 传给上述 client。

#### 2.3 保持 callback token 不进入控制面

**描述：** callback token 只能用于 executor 回传/工具代理接口，不能用于 `/tasks`、`/executor/*`、`/workspace/*`、`/schedules`。

**涉及文件：**

- `executor_manager/tests/test_control_plane_auth.py`
- `executor_manager/tests/test_executor_proxy_auth.py`

**验收标准：**

- [x] 用 callback token 调 `/api/v1/workspace/stats` 返回 `403`。
- [x] 用 callback token 调 `/api/v1/tasks` 返回 `403`。
- [x] 用 callback token 调 `/api/v1/executor/delete` 返回 `403`。
- [x] 用 internal token 调 `/api/v1/callback` 返回 `403`，除非它恰好等于 callback token。

---

## Phase 3: 用户态功能和部署边界回归

### 目标

确认安全加固不影响正常用户体验，并记录部署边界。

### 任务清单

#### 3.1 Backend 用户态 workspace 回归

**涉及文件：**

- `backend/app/api/v1/sessions.py`
- `backend/app/api/v1/runs.py`
- `backend/tests/test_session_share_service.py`
- 新增或扩展 `backend/tests/test_session_workspace_authorization.py`

**验收标准：**

- [x] owner 可以继续读取 session workspace files。
- [x] owner 可以继续读取 run workspace files。
- [x] non-owner 继续返回 `403`。
- [x] share link public response 不暴露 `workspace_manifest_key`、`workspace_files_prefix`、source session id 或 owner user id。

#### 3.2 Frontend API boundary 回归

**涉及文件：**

- `frontend/features/chat/api/chat-api.ts`
- `frontend/features/chat/components/execution/file-panel/hooks/use-artifacts.ts`
- `frontend/services/api-client.ts`

**验收标准：**

- [x] Artifacts panel 仍通过 Backend session/run API 拉文件。
- [x] Frontend 代码中没有 direct EM `/api/v1/workspace/*` 调用。
- [x] `pnpm lint` 和 `pnpm build` 通过，或记录明确阻塞。

#### 3.3 部署文档更新

**涉及文件：**

- `README.md` 或部署相关文档
- `docker-compose.yml`
- `docker-compose.r2.yml`
- `.env.example` 类文件，如存在

**验收标准：**

- [x] 文档说明 EM 8001 不应公网暴露。
- [x] 文档说明 `INTERNAL_API_TOKEN` 供 Backend/internal service 调 EM 控制面。
- [x] 文档说明 `CALLBACK_TOKEN` 供 executor container 调 EM 回传/工具代理接口。
- [x] 不把真实 token 写入文档。

---

## Phase 4: 验证、文档回写和后续加固记录

### 目标

跑 targeted tests 和最小静态检查，并把实际结果回写到 spec。

### 任务清单

#### 4.1 Executor Manager 验证

**验证命令：**

```bash
cd executor_manager
uv run python -m unittest tests.test_control_plane_auth tests.test_executor_proxy_auth
uv run python -m py_compile app/api/v1/workspace.py app/api/v1/tasks.py app/api/v1/executor.py app/api/v1/schedules.py app/api/v1/callback.py app/api/v1/computer.py app/api/v1/memories.py app/api/v1/agent_channel_runtime.py app/api/v1/agent_channel_artifacts.py app/api/v1/agent_channel_tasks.py app/api/v1/user_input_requests.py app/core/deps.py
uv run ruff check app/api/v1/workspace.py app/api/v1/tasks.py app/api/v1/executor.py app/api/v1/schedules.py app/api/v1/callback.py app/api/v1/computer.py app/api/v1/memories.py app/api/v1/agent_channel_runtime.py app/api/v1/agent_channel_artifacts.py app/api/v1/agent_channel_tasks.py app/api/v1/user_input_requests.py tests/test_control_plane_auth.py tests/test_executor_proxy_auth.py
```

**验收标准：**

- [x] workspace PoC 无 token 返回 `403`。
- [x] control plane 只有 internal token 可访问。
- [x] executor proxy 只有 callback token 可访问。
- [x] health/root 无 token 可访问。

#### 4.2 Backend / Executor 验证

**验证命令：**

```bash
cd backend
uv run python -m unittest tests.test_executor_manager_client tests.test_schedules_proxy tests.test_executor_manager_notify_service tests.test_agent_assignment_service
uv run python -m py_compile app/services/executor_manager_client.py app/api/v1/schedules.py app/api/v1/sessions.py app/api/v1/runs.py

cd ../executor
uv run python -m unittest tests.test_manager_auth_clients tests.test_channel_runtime_tools tests.test_engine_channel_artifact_tools tests.test_engine_channel_reaction_tools tests.test_engine_channel_task_hint tests.test_engine_channel_runtime_hint tests.test_engine_persistent_state_hint
uv run python -m py_compile app/api/v1/task.py app/core/callback.py app/core/computer.py app/core/memory.py app/core/channel_runtime.py app/core/user_input.py
```

**验收标准：**

- [x] Backend 调 EM control plane 带 internal token。
- [x] Executor 调 EM callback/tool proxy 带 callback token。
- [x] 现有 channel runtime tools 测试通过。
- [x] session/run workspace 用户态回归通过。

#### 4.3 Frontend 验证

**验证命令：**

```bash
cd frontend
rg -n "executor_manager|/api/v1/workspace|workspace/file/" app features services
```

**验收标准：**

- [x] Frontend 没有 direct EM workspace 调用。
- [x] 本次未修改 frontend；执行边界扫描即可，未跑 `pnpm lint` / `pnpm build`。

#### 4.4 Spec 回写

**涉及文件：**

- `specs/active/33-executor-manager-workspace-authorization-hardening-plan.md`
- `specs/constitution/2026-06-11-executor-manager-workspace-authorization.md`

**验收标准：**

- [x] 完成 phase 标记为 `[x]`。
- [x] 写入实际验证命令和结果。
- [x] 如果实现中改变接口分类，更新 constitution 的 EM API 分类表。
- [x] 记录后续更细粒度加固项：session-scoped capability、token rotation、生产默认 token fail-fast。

---

## 实施记录

### 2026-06-11

**实际落地：**

- `workspace/tasks/executor/schedules` 已统一挂 `require_internal_token`。
- `callback/computer/memories/agent-channel-runtime/agent-channel-artifacts/agent-channel-tasks/user-input-requests` 已统一挂 `require_callback_token`。
- Backend `ExecutorManagerClient.delete_container()` 和 schedules proxy 已补 `X-Internal-Token`。
- Executor `CallbackClient`、`ComputerClient`、`MemoryClient`、`ChannelRuntimeClient`、`UserInputClient` 已接收并发送 callback token。
- `executor/app/api/v1/task.py` 已把 `TaskRun.callback_token` 传给上述 executor client。
- Frontend 文件浏览仍通过 Backend `/sessions/{session_id}/workspace/files` 和 `/runs/{run_id}/workspace/files`。

**已执行验证：**

```bash
cd executor_manager
uv run python -m unittest tests.test_control_plane_auth tests.test_executor_proxy_auth
uv run python -m unittest tests.test_agent_channel_runtime_api tests.test_agent_channel_artifacts_api tests.test_agent_channel_tasks_api tests.test_internal_runs_notify tests.test_control_plane_auth tests.test_executor_proxy_auth
uv run python -m unittest discover -s tests

cd ../executor
uv run python -m unittest tests.test_manager_auth_clients
uv run python -m unittest tests.test_manager_auth_clients tests.test_channel_runtime_tools tests.test_engine_channel_artifact_tools tests.test_engine_channel_reaction_tools tests.test_engine_channel_task_hint tests.test_engine_channel_runtime_hint tests.test_engine_persistent_state_hint
uv run python -m unittest discover -s tests

cd ../backend
uv run python -m unittest tests.test_executor_manager_client tests.test_schedules_proxy
uv run python -m unittest tests.test_executor_manager_client tests.test_schedules_proxy tests.test_executor_manager_notify_service tests.test_agent_assignment_service

cd ..
rg -n "executor_manager|/api/v1/workspace|workspace/file/|workspace/files|sessionWorkspaceFiles|runWorkspaceFiles" frontend/app frontend/features frontend/services backend/app/api/v1/sessions.py backend/app/api/v1/runs.py
```

**验证结果：**

- 上述 `unittest` 命令均通过。
- `executor_manager` 完整 unittest discover：41 tests passed。
- `executor` 完整 unittest discover：45 tests passed。
- Backend targeted unittest：8 tests passed。
- `pytest` 当前未安装在各服务 venv 中，因此本轮按仓库现有 `unittest` 测试风格验证。
- Frontend 未改代码；边界扫描确认没有 direct EM workspace 调用，仍走 Backend session/run workspace API。

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
| --- | --- | --- |
| 只给 EM route 加 token，忘记更新调用方 | Backend 或 executor 调用失败 | 每个 phase 都包含调用方同步和测试 |
| 把 executor proxy 错套 `X-Internal-Token` | executor container 需要拿 internal token，扩大权限 | executor proxy 统一用 callback token |
| 把 control plane 错套 callback token | executor token 可创建任务或删容器 | control plane 统一用 internal token，并测试 callback token 不可访问 |
| EM 8001 仍公网暴露 | 攻击面仍大 | 代码 fail closed + 部署文档明确不公网暴露 |
| 默认 token 未改 | token 等同公开 | 后续加固记录 production fail-fast，文档强调非默认 |

---

## 总结

v1 修复不是“只修 workspace file”，也不是“所有 EM 接口用同一个 token”。正确边界是：

- Backend/internal service 调 EM 控制面：`X-Internal-Token`。
- Executor container 调 EM 回传/工具代理：callback token。
- Frontend 继续只调 Backend 用户态 API。
- Health/root 保持无 token。

这能直接关闭 issue #133 的 workspace 裸接口风险，也把 EM 其他裸接口纳入同一轮可审核的加固计划。
