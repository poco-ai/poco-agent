# Docker Compose Guide

This repo ships two Compose files:

- `docker-compose.yml`: all-in-one local setup (includes `rustfs` as local S3-compatible storage)
  - `backend` (FastAPI)
  - `executor-manager` (FastAPI + APScheduler; spawns `executor` containers via Docker API)
  - `frontend` (Next.js)
  - `postgres`
  - `rustfs` (default `rustfs/rustfs:latest`, S3-compatible) + `rustfs-init` (optional bucket creation)
- `docker-compose.r2.yml`: lighter setup (no `rustfs`; use Cloudflare R2 / any S3-compatible storage)

> Note: there is no long-running `executor` service in Compose. Executors are created on-demand by `executor-manager`.

## Prerequisites

- Minimum requirements: 2C4G
- Docker Desktop / Docker Engine
- Docker Compose v2 (`docker compose`)
- If GHCR images are private: `docker login ghcr.io`

## Option 1: Bootstrap script (first run, local rustfs, recommended)

If you are setting up for the first time and use local `rustfs` (`docker-compose.yml`), use the script to prepare `.env`, directories, permissions, pull images, and create the bucket:

```bash
./scripts/quickstart.sh
```

By default, the script runs in interactive mode and will prompt for your API keys (Anthropic is required) and write them into `.env`.
Use `--non-interactive` and `--anthropic-key` if you need to run it in CI.

The script will:

- Copy `.env.example` -> `.env` if missing
- Detect and write `DOCKER_GID`; in interactive mode write API keys/model settings; other keys are only written when flags are provided (e.g. `--data-dir` / `--s3-*` / `--cors-origins`)
- Create `oss_data/` and `tmp_workspace/`; by default try to chown `oss_data/` to `10001:10001` (RustFS user)
- Write `.gitignore` into `oss_data/` and `tmp_workspace/` (content is `*`)
- Pull the executor image and start services by default
- Create `S3_BUCKET` via `rustfs-init`

Common flags:

- `--no-pull-executor`: skip pulling executor image
- `--no-start`: only prepare env and directories
- `--no-init-bucket`: skip bucket creation
- `--no-chown-rustfs`: skip chowning `oss_data/` to `10001:10001`

After running the script, ensure `ANTHROPIC_API_KEY` is set in `.env`.

## Option 2: Manual start (local / self-hosted)

Run in the repo root:

```bash
docker compose up -d
```

To enable IM (disabled by default):

```bash
docker compose --profile im up -d im
```

By default it pulls `backend` / `executor-manager` / `frontend` from GHCR and Postgres/RustFS images. When running tasks, `executor-manager` will start `EXECUTOR_IMAGE` dynamically (it may auto-pull if missing).

> Note: the current `docker-compose.yml` does not define a standalone `executor` service; executors are created by `executor-manager`.

To pin versions (e.g. `v0.1.0`), override image tags via environment variables:

```bash
export BACKEND_IMAGE=ghcr.io/poco-ai/poco-backend:v0.1.0
export EXECUTOR_MANAGER_IMAGE=ghcr.io/poco-ai/poco-executor-manager:v0.1.0
export EXECUTOR_IMAGE=ghcr.io/poco-ai/poco-executor:lite
# Optional: executor image with desktop/browser stack (used when browser_enabled=true)
# export EXECUTOR_BROWSER_IMAGE=ghcr.io/poco-ai/poco-executor:full
export FRONTEND_IMAGE=ghcr.io/poco-ai/poco-frontend:v0.1.0

docker compose up -d
```

## Option 3: Lighter setup with Cloudflare R2 (or other S3-compatible storage)

If you do not want to run `rustfs` locally, use `docker-compose.r2.yml` and configure external object storage in `.env` (the bucket must already exist).

Typical R2 config:

```bash
# Cloudflare R2 (S3-compatible)
S3_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
S3_REGION=auto
S3_BUCKET=<bucket-name>
S3_ACCESS_KEY=<r2-access-key-id>
S3_SECRET_KEY=<r2-secret-access-key>
S3_FORCE_PATH_STYLE=false

# Optional: public endpoint for presigned URLs; defaults to S3_ENDPOINT if unset
# S3_PUBLIC_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com
```

Start (no rustfs):

```bash
docker compose -f docker-compose.r2.yml up -d
```

To enable IM (Telegram/DingTalk), you must explicitly enable the profile:

```bash
docker compose -f docker-compose.r2.yml --profile im up -d im
```

## Key notes (important)

1. `executor-manager` needs Docker daemon access:
   - Compose mounts `/var/run/docker.sock:/var/run/docker.sock`
   - So it can create executor containers dynamically

2. Callback URL (Executor -> Executor Manager):
   - `CALLBACK_BASE_URL` defaults to `http://host.docker.internal:8001`
   - Executors are created outside the compose network, so they call back through host-mapped ports
   - `executor-manager` injects `host.docker.internal:host-gateway` when creating executor containers; Compose also adds it for the manager container (works on Linux too)

3. Workspace directory:
   - Compose uses `${PWD}/tmp_workspace` as `WORKSPACE_ROOT`
   - The directory is bind-mounted into executor containers at `/workspace`
   - `tmp_workspace/` is already in the repo and ignored by git (`tmp_workspace/.gitignore`)

4. RustFS data directory permissions (common on Linux, `docker-compose.yml` only):
   - `rustfs` bind-mounts `${RUSTFS_DATA_DIR}` to `/data`
   - Default `RUSTFS_DATA_DIR=./oss_data` (repo root)
   - RustFS runs as non-root user `rustfs` (UID/GID=10001); if the host directory is not owned by `10001:10001`, it can fail with:
     `Io error: Permission denied (os error 13)`
   - Fix on the host (example uses repo `oss_data/`):

   ```bash
   mkdir -p oss_data
   sudo chown -R 10001:10001 oss_data
   ```

5. Public URL for presigned URLs:
   - Backend uses `S3_PUBLIC_ENDPOINT` to generate browser-accessible presigned URLs:
     - local rustfs (`docker-compose.yml`) default is `http://localhost:9000`
     - Cloudflare R2 (`docker-compose.r2.yml`) is typically the same as `S3_ENDPOINT`, or your custom domain

## Common operations

> If you use `docker-compose.r2.yml`, add `-f docker-compose.r2.yml` to the commands below.

View logs:

```bash
docker compose logs -f backend executor-manager
```

Update to latest images (or your specified tags):

```bash
docker compose pull
docker compose up -d
```

Stop:

```bash
docker compose down
```

Stop and remove data (deletes Postgres/object storage volumes):

```bash
docker compose down -v
```

## Other

### Default URLs (default ports)

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000` (OpenAPI: `/docs`)
- Executor Manager: `http://localhost:8001` (OpenAPI: `/docs`)
- RustFS(S3) (only `docker-compose.yml`): `http://localhost:9000` (Console: `http://localhost:9001`)

### Configuration

Most configuration is via environment variables (e.g. `ANTHROPIC_API_KEY`, `S3_*`, `INTERNAL_API_TOKEN`).

See: [configuration.md](configuration.md).

### Optional: auto-create bucket (`docker-compose.yml` only)

`rustfs-init` is not started by default (to avoid startup blocking due to OSS image/permission differences). To create `S3_BUCKET` automatically:

```bash
docker compose --profile init up -d rustfs-init
```

### Optional: Tailscale for remote access

If you need to access your local deployment from outside your machine without exposing it to the public internet, you can use Tailscale to expose services over your tailnet.

Tailscale Serve provides an HTTPS URL reachable within your tailnet for a local port (the first time you use it, you will be guided to enable HTTPS on your tailnet).

Install Tailscale: [Install Tailscale](https://tailscale.com/docs/install)

Example: expose the Frontend on port 3000 to other devices on your tailnet:

```bash
# 1) Log in and join your tailnet
sudo tailscale up

# 2) Expose port 3000 (Frontend) with Tailscale Serve
tailscale serve --bg http://127.0.0.1:3000
```

The command prints a URL like `https://<device>.<tailnet>.ts.net`; devices on your tailnet can use it to access the Frontend.
