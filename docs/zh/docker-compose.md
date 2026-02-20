# Docker Compose 启动指南

仓库提供两套 Compose 文件：

- `docker-compose.yml`：本地一体化（含 `rustfs`，用于本地 S3 兼容对象存储）
  - `backend`（FastAPI）
  - `executor-manager`（FastAPI + APScheduler，会通过 Docker API 动态拉起 `executor` 容器）
  - `frontend`（Next.js）
  - `postgres`
  - `rustfs`（默认 `rustfs/rustfs:latest`，S3 兼容）+ `rustfs-init`（创建 bucket，可选）
- `docker-compose.r2.yml`：更轻量（不含 `rustfs`，适合接入 Cloudflare R2 / 其他 S3 兼容服务）

> 说明：Compose 里不会长期运行 `executor` 服务；执行任务时由 `executor-manager` 通过 Docker API 动态创建 executor 容器。

## 前置条件

- 最低配置：2C4G
- Docker Desktop / Docker Engine
- Docker Compose v2（`docker compose` 命令）
- 若 GHCR 镜像为私有：先执行 `docker login ghcr.io`

## 方式一：一键初始化脚本（首次运行，本地 rustfs 版本，推荐）

如果是首次配置、并且你使用本地 `rustfs`（`docker-compose.yml`），推荐使用脚本自动完成 `.env`、目录、权限、镜像拉取与 bucket 创建：

```bash
./scripts/quickstart.sh
```

脚本默认会进入交互模式，按提示输入 API Key（Anthropic 必填）并写入 `.env`。
如果你需要在 CI 中运行，可使用 `--non-interactive` 和 `--anthropic-key`。

脚本会：

- 复制 `.env.example` -> `.env`（若不存在）
- 自动检测并写入 `DOCKER_GID`；交互模式会写入 API Key/模型配置；其余仅在传参时写入（如 `--data-dir` / `--s3-*` / `--cors-origins`）
- 创建 `oss_data/` 与 `tmp_workspace/`；默认尝试将 `oss_data/` chown 为 `10001:10001`（RustFS 用户）
- 为 `oss_data/` 与 `tmp_workspace/` 写入 `.gitignore`（内容为 `*`）
- 默认拉取 executor 镜像并启动服务
- 通过 `rustfs-init` 创建 `S3_BUCKET`

常用参数：

- `--no-pull-executor`：跳过拉取 executor 镜像
- `--no-start`：只准备环境与目录，不启动服务
- `--no-init-bucket`：跳过创建 bucket
- `--no-chown-rustfs`：跳过将 `oss_data/` 改为 `10001:10001`

执行脚本后请确认 `.env` 里已设置 `ANTHROPIC_API_KEY`。

## 方式二：手动启动（本地开发/自部署）

在仓库根目录执行：

```bash
docker compose up -d
```

如需启用 IM（默认关闭）：

```bash
docker compose --profile im up -d im
```

默认会从 GHCR（`ghcr.io`）拉取 `backend` / `executor-manager` / `frontend` 镜像，并拉取 Postgres/RustFS 镜像。执行任务时，`executor-manager` 会使用 `EXECUTOR_IMAGE` 动态拉起 executor 容器（本机缺镜像时会自动 pull）。

> 注意：当前仓库的 `docker-compose.yml` 不包含单独的 `executor` 服务；executor 容器由 `executor-manager` 动态创建。

如果你要固定版本（例如 `v0.1.0`），可通过环境变量覆盖镜像 tag（示例）：

```bash
export BACKEND_IMAGE=ghcr.io/poco-ai/poco-backend:v0.1.0
export EXECUTOR_MANAGER_IMAGE=ghcr.io/poco-ai/poco-executor-manager:v0.1.0
export EXECUTOR_IMAGE=ghcr.io/poco-ai/poco-executor:lite
# 可选：启用可视化浏览器（noVNC + Chrome）的 executor 镜像（用于 browser_enabled=true）
# export EXECUTOR_BROWSER_IMAGE=ghcr.io/poco-ai/poco-executor:full
export FRONTEND_IMAGE=ghcr.io/poco-ai/poco-frontend:v0.1.0

docker compose up -d
```

## 方式三：轻量方案：使用 Cloudflare R2（或其他 S3 兼容服务）

当你不想在本地启动 `rustfs`，可以改用 `docker-compose.r2.yml`，并在 `.env` 里配置外部对象存储（bucket 需要提前创建好）。

典型的 R2 配置示例：

```bash
# Cloudflare R2 (S3-compatible)
S3_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
S3_REGION=auto
S3_BUCKET=<bucket-name>
S3_ACCESS_KEY=<r2-access-key-id>
S3_SECRET_KEY=<r2-secret-access-key>
S3_FORCE_PATH_STYLE=false

# 可选：用于生成给浏览器的预签名 URL；不填则默认用 S3_ENDPOINT
# S3_PUBLIC_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
```

启动（不会启动 rustfs）：

```bash
docker compose -f docker-compose.r2.yml up -d
```

如需同时启用 IM（Telegram/钉钉）服务，需要显式指定 profile：

```bash
docker compose -f docker-compose.r2.yml --profile im up -d im
```

## 关键说明（很重要）

1. `executor-manager` 需要访问 Docker daemon：
   - Compose 已默认挂载：`/var/run/docker.sock:/var/run/docker.sock`
   - 因此 `executor-manager` 才能动态创建 executor 容器
2. 回调地址（Executor -> Executor Manager）：
   - `CALLBACK_BASE_URL` 默认是 `http://host.docker.internal:8001`
   - 这是因为动态创建的 executor 容器默认不在 compose 网络里，需要通过“宿主机端口映射”回调到 manager
   - `executor-manager` 会在创建 executor 容器时注入 `host.docker.internal:host-gateway`；Compose 也为 `executor-manager` 容器配置了该映射（Linux 下也可用）
3. 工作区目录（Workspace）：
   - Compose 固定使用 `${PWD}/tmp_workspace` 作为 `WORKSPACE_ROOT`
   - 该目录会被 Executor Manager 创建的 executor 容器以 bind mount 方式挂载到 `/workspace`
   - `tmp_workspace/` 在仓库里已存在，并且通过 `tmp_workspace/.gitignore` 忽略内容，不会污染 git
4. RustFS 数据目录权限（Linux 常见坑，仅 `docker-compose.yml`）：
   - `rustfs` 会把 `${RUSTFS_DATA_DIR}` bind mount 到容器的 `/data`
   - 默认 `RUSTFS_DATA_DIR=./oss_data`（仓库根目录）
   - RustFS 容器以非 root 用户 `rustfs`（UID/GID=10001）运行；如果宿主机目录不是 `10001:10001`，可能会报：
     `Io error: Permission denied (os error 13)`
   - 解决：先在宿主机创建/修正权限（示例以仓库根目录 `oss_data/` 为例）：

   ```bash
   mkdir -p oss_data
   sudo chown -R 10001:10001 oss_data
   ```

5. 预签名 URL 对外地址：

- Backend 会用 `S3_PUBLIC_ENDPOINT` 生成给浏览器访问的预签名 URL：
  - 本地 rustfs（`docker-compose.yml`）默认是 `http://localhost:9000`
  - Cloudflare R2（`docker-compose.r2.yml`）通常保持与 `S3_ENDPOINT` 一致，或填你的自定义域名

## 常用操作

> 如果你使用的是 `docker-compose.r2.yml`，请在下列命令中追加 `-f docker-compose.r2.yml`。

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

## 其他

### 访问地址（默认端口）

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`（OpenAPI: `/docs`）
- Executor Manager: `http://localhost:8001`（OpenAPI: `/docs`）
- RustFS(S3)（仅 `docker-compose.yml`）：`http://localhost:9000`（Console: `http://localhost:9001`）

### 配置入口

大多数配置都通过环境变量完成（例如 `ANTHROPIC_API_KEY`、`S3_*`、`INTERNAL_API_TOKEN` 等）。

详见 [configuration.md](configuration.md)。

### 可选：自动创建 bucket（仅 `docker-compose.yml`）

默认启动不会运行 `rustfs-init`（避免不同 OSS 镜像/权限差异导致阻塞启动）。如需自动创建 `S3_BUCKET`：

```bash
docker compose --profile init up -d rustfs-init
```

### 可选：Tailscale 穿透访问

如果你需要在外网访问本机部署的服务、但不希望直接暴露到公网，可以用 Tailscale 在 tailnet 内穿透访问。

Tailscale Serve 会为本机端口提供一个 tailnet 内可访问的 HTTPS 地址（首次使用会引导你在 tailnet 启用 HTTPS）。

安装 Tailscale（官方文档）：[Install Tailscale](https://tailscale.com/docs/install)

示例：将本机 Frontend 的 3000 端口通过 Tailscale 暴露给 tailnet 内其他设备访问：

```bash
# 1) 登录并加入 tailnet
sudo tailscale up

# 2) 使用 Tailscale Serve 暴露 3000 端口（Frontend）
tailscale serve --bg http://127.0.0.1:3000
```

执行后终端会输出一个类似 `https://<device>.<tailnet>.ts.net` 的地址，tailnet 内设备即可通过该地址访问你的 Frontend。
