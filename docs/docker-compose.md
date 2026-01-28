# Docker Compose 一键启动

`docker-compose.yml` 已包含：

- `backend`（FastAPI）
- `executor-manager`（FastAPI + APScheduler，会通过 Docker API 拉起 `executor` 容器）
- `executor`（仅用于本地调试；默认不启动，真正执行时由 manager 动态创建）
- `frontend`（Next.js）
- `postgres`
- `rustfs`（默认 `rustfs/rustfs:latest`，S3 兼容）+ `rustfs-init`（创建 bucket，可选）

## 前置条件

- Docker Desktop / Docker Engine
- Docker Compose v2（`docker compose` 命令）
- 若 GHCR 镜像为私有：先执行 `docker login ghcr.io`

## 启动（本地开发/自部署）

在仓库根目录执行：

```bash
docker compose up -d
```

默认会从 GHCR（`ghcr.io`）拉取 `backend` / `executor-manager` / `frontend` 镜像，并拉取 Postgres/RustFS 镜像。`executor` 服务默认不启动（`debug` profile），但 `executor-manager` 在执行任务时会使用 `EXECUTOR_IMAGE` 拉起 executor 容器（本机缺镜像时会自动 pull）。

如果你要固定版本（例如 `v0.1.0`），可通过环境变量覆盖镜像 tag（示例）：

```bash
export BACKEND_IMAGE=ghcr.io/poco-ai/poco-backend:v0.1.0
export EXECUTOR_MANAGER_IMAGE=ghcr.io/poco-ai/poco-executor-manager:v0.1.0
export EXECUTOR_IMAGE=ghcr.io/poco-ai/poco-executor:v0.1.0
export FRONTEND_IMAGE=ghcr.io/poco-ai/poco-frontend:v0.1.0

docker compose up -d
```

## 访问地址（默认端口）

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`（OpenAPI: `/docs`）
- Executor Manager: `http://localhost:8001`（OpenAPI: `/docs`）
- RustFS(S3): `http://localhost:9000`（Console: `http://localhost:9001`）
- Executor（调试用）:
  - API: `http://localhost:8002/health`
  - noVNC / code-server: `http://localhost:8081`

启用调试 executor（可选，仅当你需要直接访问 executor 服务时）：

```bash
docker compose --profile debug up -d executor
```

## 关键说明（很重要）

1. `executor-manager` 需要访问 Docker daemon：

- Compose 已默认挂载：`/var/run/docker.sock:/var/run/docker.sock`
- 因此 `executor-manager` 才能动态创建 executor 容器

2. 回调地址（Executor -> Executor Manager）：

- `CALLBACK_BASE_URL` 默认是 `http://host.docker.internal:8001`
- 这是因为动态创建的 executor 容器默认不在 compose 网络里，需要通过“宿主机端口映射”回调到 manager
- Compose 已为 `executor-manager`/`executor` 配置 `host.docker.internal:host-gateway`（Linux 下也可用）

3. 工作区目录（Workspace）：

- Compose 固定使用 `${PWD}/tmp_workspace` 作为 `WORKSPACE_ROOT`
- 该目录会被 Executor Manager 创建的 executor 容器以 bind mount 方式挂载到 `/workspace`
- `tmp_workspace/` 在仓库里已存在，并且通过 `tmp_workspace/.gitignore` 忽略内容，不会污染 git

4. RustFS 数据目录权限（Linux 常见坑）：

- `rustfs` 会把 `${RUSTFS_DATA_DIR}` bind mount 到容器的 `/data`
- 如果宿主机目录不存在，Docker 可能会用 `root:root` 创建它（权限通常是 `755`），而 `rustfs` 进程若以非 root 运行就会报：
  `Io error: Permission denied (os error 13)`
- 解决：先在宿主机创建/修正权限（示例以仓库根目录 `oss_data/` 为例）：

```bash
mkdir -p oss_data
sudo chown -R "$(id -u)":"$(id -g)" oss_data
```

## 常用操作

查看日志：

```bash
docker compose logs -f backend executor-manager
```

更新到最新镜像（或拉取你指定的 tag）：

```bash
docker compose pull
docker compose up -d
```

停止：

```bash
docker compose down
```

停止并清理数据（会删除 Postgres/对象存储 volume）：

```bash
docker compose down -v
```

## 配置入口

大多数配置都通过环境变量完成（例如 `ANTHROPIC_AUTH_TOKEN`、`S3_*`、`INTERNAL_API_TOKEN` 等）。

详见：`docs/configuration.md`。

## 可选：自动创建 bucket

默认启动不会运行 `rustfs-init`（避免不同 OSS 镜像/权限差异导致阻塞启动）。如需自动创建 `S3_BUCKET`：

```bash
docker compose --profile init up -d rustfs-init
```
