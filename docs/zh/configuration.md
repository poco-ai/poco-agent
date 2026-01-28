# 配置指南（环境变量）

本项目包含 4 个服务：`backend` / `executor-manager` / `executor` / `frontend`，以及 2 个依赖：`postgres` / `rustfs`（S3 兼容对象存储）。

下面列出各服务常用环境变量（含含义与默认值）。在生产环境请务必替换所有 `change-this-*`、弱口令与默认密钥。

## Backend（FastAPI）

必需（否则无法启动或关键功能不可用）：

- `DATABASE_URL`：数据库连接串（PostgreSQL），示例：`postgresql://postgres:postgres@postgres:5432/poco`
- `SECRET_KEY`：后端密钥（用于安全相关逻辑）
- `INTERNAL_API_TOKEN`：内部调用鉴权 token（Executor Manager 调用 Backend 内部接口会用到）
- `S3_ENDPOINT`：S3 兼容服务地址，示例：`http://rustfs:9000`
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`：S3 访问凭证
- `S3_BUCKET`：S3 bucket 名称（需存在；Docker Compose 默认用 init 容器创建）

常用：

- `HOST`（默认 `0.0.0.0`）、`PORT`（默认 `8000`）
- `CORS_ORIGINS`：允许来源列表（JSON 数组），示例：`["http://localhost:3000","http://127.0.0.1:3000"]`
- `EXECUTOR_MANAGER_URL`：Executor Manager 地址，示例：`http://executor-manager:8001`
- `S3_PUBLIC_ENDPOINT`：对外可访问的 S3 地址，用于生成给浏览器的预签名 URL（本地可用 `http://localhost:9000`）。未设置则使用 `S3_ENDPOINT`
- `S3_REGION`（默认 `us-east-1`）
- `S3_FORCE_PATH_STYLE`（默认 `true`，对 MinIO/RustFS 一般需要）
- `S3_PRESIGN_EXPIRES`：预签名 URL 过期秒数（默认 `300`）
- `OPENAI_API_KEY`：可选（用于会话标题自动生成等；未设置则禁用标题生成）
- `OPENAI_BASE_URL`：可选（自定义 OpenAI 兼容网关）
- `OPENAI_DEFAULT_MODEL`（默认 `gpt-4o-mini`）
- `MAX_UPLOAD_SIZE_MB`（默认 `100`）

日志（3 个 Python 服务通用）：

- `DEBUG`（默认 `false`）
- `LOG_LEVEL`（默认随 DEBUG/非 DEBUG 变化；建议显式设为 `INFO`）
- `UVICORN_ACCESS_LOG`（默认 `false`）
- `LOG_TO_FILE`（默认 `false`）：是否写本地文件日志
- `LOG_DIR`（默认 `./logs`）、`LOG_BACKUP_COUNT`（默认 `14`）
- `LOG_SQL`（默认 `false`）：是否打印 SQLAlchemy SQL（注意敏感信息）

## Executor Manager（FastAPI + APScheduler）

必需（否则无法启动或无法调度执行）：

- `BACKEND_URL`：Backend 地址，示例：`http://backend:8000`
- `INTERNAL_API_TOKEN`：必须与 Backend 的 `INTERNAL_API_TOKEN` 一致
- `CALLBACK_BASE_URL`：**必须能被 Executor 容器访问到**，Docker Compose 默认 `http://host.docker.internal:8001`
- `EXECUTOR_IMAGE`：Executor 镜像名（Executor Manager 会通过 Docker API 拉起该镜像）
- `EXECUTOR_PUBLISHED_HOST`：Executor Manager 访问“已映射到宿主机端口”的 Executor 容器时使用的 host（本地裸跑一般是 `localhost`；Compose 内推荐 `host.docker.internal`）
- `WORKSPACE_ROOT`：工作区根目录（**必须是宿主机路径**，因为会被 bind mount 到 Executor 容器）
- `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET`：用于导出 workspace 到对象存储（否则相关接口会失败）

执行模型（跑任务时必需）：

- `ANTHROPIC_AUTH_TOKEN`：Claude API token
- `ANTHROPIC_BASE_URL`（默认 `https://api.anthropic.com`）
- `DEFAULT_MODEL`（默认 `claude-sonnet-4-20250514`）

调度与拉取：

- `TASK_PULL_ENABLED`（默认 `true`）：是否从 Backend run queue 拉取任务
- `MAX_CONCURRENT_TASKS`（默认 `5`）
- `TASK_PULL_INTERVAL_SECONDS`（默认 `2`）
- `TASK_CLAIM_LEASE_SECONDS`（默认 `180`）：claim 的租约时间。需要覆盖 Manager 侧从 claim 到成功 start_run 的耗时（可能包含技能/附件 staging、拉起 Executor 容器等），否则 run 可能在租约过期后被重新 claim，导致重复调度/重复启动容器。
- `SCHEDULE_CONFIG_PATH`：可选，提供 TOML/JSON schedule 配置时会作为 source of truth

工作区清理（可选）：

- `WORKSPACE_CLEANUP_ENABLED`（默认 `false`）
- `WORKSPACE_CLEANUP_INTERVAL_HOURS`（默认 `24`）
- `WORKSPACE_MAX_AGE_HOURS`（默认 `24`）
- `WORKSPACE_ARCHIVE_ENABLED`（默认 `true`）
- `WORKSPACE_ARCHIVE_DAYS`（默认 `7`）
- `WORKSPACE_IGNORE_DOT_FILES`（默认 `true`）

## Executor（FastAPI + Claude Agent SDK）

必需（跑任务时）：

- `ANTHROPIC_AUTH_TOKEN`：Claude API token
- `ANTHROPIC_BASE_URL`：可选（同上）
- `DEFAULT_MODEL`：必需（`executor/app/core/engine.py` 会读取 `os.environ["DEFAULT_MODEL"]`）
- `WORKSPACE_PATH`：工作目录挂载点（默认 `/workspace`）

可选：

- `WORKSPACE_GIT_IGNORE`：额外写入到 `.git/info/exclude` 的忽略规则（逗号/换行分隔）
- `DEBUG` / `LOG_LEVEL` / `LOG_TO_FILE` 等日志变量（同上）

## Frontend（Next.js）

Frontend 现在默认通过 Next.js 的 **同源 API 代理**（`/api/v1/* -> Backend`）访问后端，因此后端地址可以在 **运行时（runtime）** 配置。

运行时（runtime）：

- `BACKEND_URL`：Next.js 服务器侧用于转发 `/api/v1/*` 的 Backend base URL（Docker Compose 默认：`http://backend:8000`；本地开发可用：`http://localhost:8000`；兼容旧变量：`POCO_BACKEND_URL`）

可选（构建期 build-time，仅当你希望浏览器直接访问后端、或前端做静态部署时才需要）：

- `NEXT_PUBLIC_API_URL`：浏览器侧访问 Backend 的 base URL（示例：`http://localhost:8000`）。注意该变量会被 Next.js 内联进产物。

注意：以下变量仍是构建期（build-time）生效，会被 Next.js 内联进产物（见 `docker/frontend/Dockerfile` 的 build args）。

- `NEXT_PUBLIC_SESSION_POLLING_INTERVAL`：session 轮询间隔（毫秒，默认 `2500`）
- `NEXT_PUBLIC_MESSAGE_POLLING_INTERVAL`：消息轮询间隔（毫秒，默认 `2500`）

## Postgres（Docker 镜像）

- `POSTGRES_DB`（默认 `poco`）
- `POSTGRES_USER`（默认 `postgres`）
- `POSTGRES_PASSWORD`（默认 `postgres`）
- `POSTGRES_PORT`（默认 `5432`，对宿主机映射端口）

## RustFS（S3 兼容对象存储）

Docker Compose 默认使用 `rustfs/rustfs:latest` 作为本地 S3 兼容实现（服务名为 `rustfs`）。如需替换为其他 S3 兼容实现，请按镜像参数调整，并保证 Backend/Executor Manager 使用的 `S3_*` 可用。

- `RUSTFS_IMAGE`：对象存储镜像（默认 `rustfs/rustfs:latest`）
- `S3_PORT`（默认 `9000`）
- `S3_CONSOLE_PORT`（默认 `9001`）
- `RUSTFS_DATA_DIR`：数据目录（默认 `./oss_data`，宿主机路径，会 bind mount 到容器的 `/data`）
- `RUSTFS_DATA_DIR` 在 Linux 上需要保证宿主机目录可写；如果目录不存在被 Docker 以 `root:root` 创建，可能导致 `Permission denied (os error 13)`。
- `S3_ACCESS_KEY` / `S3_SECRET_KEY`：用于访问 S3 API 的凭证（需与 rustfs 配置一致）
- `S3_BUCKET`：bucket 名称（默认 `poco`，可通过 `rustfs-init`（profile: `init`）创建或在控制台手动创建）
