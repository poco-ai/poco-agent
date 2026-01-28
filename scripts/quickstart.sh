#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"

DATA_DIR="./oss_data"
DATA_DIR_SET=false
WORKSPACE_DIR="./tmp_workspace"
WORKSPACE_DIR_SET=false
RUSTFS_UID="10001"
RUSTFS_GID="10001"
CHOWN_RUSTFS=true
S3_BUCKET=""
S3_BUCKET_SET=false
S3_ACCESS_KEY=""
S3_ACCESS_KEY_SET=false
S3_SECRET_KEY=""
S3_SECRET_KEY_SET=false
CORS_ORIGINS=""
CORS_ORIGINS_SET=false
DOCKER_GID=""

START_ALL=true
ONLY_RUSTFS=false
INIT_BUCKET=true
PULL_EXECUTOR=true
FORCE_ENV=false

usage() {
  cat <<'USAGE'
Usage: scripts/quickstart.sh [options]

Options:
  --data-dir PATH           Host path for RustFS data (default: ./oss_data)
  --workspace-dir PATH      Host path for workspaces (default: ./tmp_workspace)
  --rustfs-uid UID          RustFS uid for data dir ownership (default: 10001)
  --rustfs-gid GID          RustFS gid for data dir ownership (default: 10001)
  --no-chown-rustfs         Skip chown for RustFS data dir
  --s3-bucket NAME          Bucket name (writes to env)
  --s3-access-key KEY       S3 access key (writes to env)
  --s3-secret-key KEY       S3 secret key (writes to env)
  --cors-origins CSV|JSON   Allowed origins (writes to env)
  --docker-gid GID          Docker socket group id (auto-detect if omitted)
  --env-file PATH           Target env file (default: ./.env)
  --no-start                Only prepare env and directories
  --only-rustfs             Start only rustfs (and rustfs-init)
  --no-init-bucket          Skip rustfs-init bucket creation
  --no-pull-executor        Skip pulling executor image
  --force-env               Overwrite existing keys in env file
  -h, --help                Show this help
USAGE
}

warn() {
  echo "[warn] $*" >&2
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[error] Missing command: $1" >&2
    exit 1
  fi
}

resolve_path() {
  local path="$1"
  if [[ "$path" = /* ]]; then
    echo "$path"
  else
    echo "${ROOT_DIR}/${path#./}"
  fi
}

to_json_array() {
  local raw="$1"
  if [[ "$raw" == "["* ]]; then
    echo "$raw"
    return
  fi
  local IFS=','
  read -r -a parts <<< "$raw"
  local json="["
  local first=true
  for item in "${parts[@]}"; do
    item="${item## }"
    item="${item%% }"
    if [[ -z "$item" ]]; then
      continue
    fi
    if [[ "$first" = true ]]; then
      first=false
    else
      json+=","
    fi
    json+="\"$item\""
  done
  json+="]"
  echo "$json"
}

detect_docker_gid() {
  local sock="/var/run/docker.sock"
  if [[ ! -S "$sock" ]]; then
    return 1
  fi
  if stat -c "%g" "$sock" >/dev/null 2>&1; then
    stat -c "%g" "$sock"
    return
  fi
  if stat -f "%g" "$sock" >/dev/null 2>&1; then
    stat -f "%g" "$sock"
    return
  fi
  return 1
}

ensure_gitignore() {
  local dir="$1"
  local path="${dir}/.gitignore"
  if [[ ! -f "$path" ]]; then
    printf "*\n" > "$path"
  fi
}

read_env_key() {
  local key="$1"
  if [[ -f "$ENV_FILE" ]]; then
    local line
    line="$(grep -E "^[[:space:]]*${key}=" "$ENV_FILE" | tail -n 1 || true)"
    if [[ -n "$line" ]]; then
      local value="${line#*=}"
      value="${value%\"}"
      value="${value#\"}"
      value="${value%\'}"
      value="${value#\'}"
      echo "$value"
      return 0
    fi
  fi
  return 1
}

write_env_key() {
  local key="$1"
  local value="$2"
  if [[ -z "$key" ]]; then
    return
  fi
  if [[ -f "$ENV_FILE" ]]; then
    if grep -qE "^${key}=" "$ENV_FILE"; then
      if [[ "$FORCE_ENV" = false ]]; then
        return
      fi
    fi
  fi
  local tmp_file
  tmp_file="$(mktemp)"
  if [[ -f "$ENV_FILE" ]]; then
    awk -v key="$key" -v val="$value" '
      BEGIN { replaced = 0 }
      $0 ~ "^" key "=" {
        print key "=" val
        replaced = 1
        next
      }
      { print }
      END {
        if (replaced == 0) {
          print key "=" val
        }
      }
    ' "$ENV_FILE" > "$tmp_file"
  else
    echo "${key}=${value}" > "$tmp_file"
  fi
  mv "$tmp_file" "$ENV_FILE"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --data-dir)
      DATA_DIR="$2"; DATA_DIR_SET=true; shift 2 ;;
    --workspace-dir)
      WORKSPACE_DIR="$2"; WORKSPACE_DIR_SET=true; shift 2 ;;
    --rustfs-uid)
      RUSTFS_UID="$2"; shift 2 ;;
    --rustfs-gid)
      RUSTFS_GID="$2"; shift 2 ;;
    --no-chown-rustfs)
      CHOWN_RUSTFS=false; shift ;;
    --s3-bucket)
      S3_BUCKET="$2"; S3_BUCKET_SET=true; shift 2 ;;
    --s3-access-key)
      S3_ACCESS_KEY="$2"; S3_ACCESS_KEY_SET=true; shift 2 ;;
    --s3-secret-key)
      S3_SECRET_KEY="$2"; S3_SECRET_KEY_SET=true; shift 2 ;;
    --cors-origins)
      CORS_ORIGINS="$2"; CORS_ORIGINS_SET=true; shift 2 ;;
    --docker-gid)
      DOCKER_GID="$2"; shift 2 ;;
    --env-file)
      ENV_FILE="$2"; shift 2 ;;
    --no-start)
      START_ALL=false; shift ;;
    --only-rustfs)
      ONLY_RUSTFS=true; shift ;;
    --no-init-bucket)
      INIT_BUCKET=false; shift ;;
    --no-pull-executor)
      PULL_EXECUTOR=false; shift ;;
    --force-env)
      FORCE_ENV=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[error] Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "${ROOT_DIR}/.env.example" ]]; then
    cp "${ROOT_DIR}/.env.example" "$ENV_FILE"
  else
    touch "$ENV_FILE"
  fi
fi

DATA_DIR_ABS="$(resolve_path "$DATA_DIR")"
WORKSPACE_DIR_ABS="$(resolve_path "$WORKSPACE_DIR")"
if [[ -n "$CORS_ORIGINS" ]]; then
  CORS_ORIGINS_JSON="$(to_json_array "$CORS_ORIGINS")"
else
  CORS_ORIGINS_JSON=""
fi

if [[ -z "$DOCKER_GID" ]]; then
  DOCKER_GID="$(detect_docker_gid || true)"
fi

if [[ "$DATA_DIR_SET" = true ]]; then
  write_env_key "RUSTFS_DATA_DIR" "$DATA_DIR"
fi
if [[ "$S3_ACCESS_KEY_SET" = true ]]; then
  write_env_key "S3_ACCESS_KEY" "$S3_ACCESS_KEY"
fi
if [[ "$S3_SECRET_KEY_SET" = true ]]; then
  write_env_key "S3_SECRET_KEY" "$S3_SECRET_KEY"
fi
if [[ "$S3_BUCKET_SET" = true ]]; then
  write_env_key "S3_BUCKET" "$S3_BUCKET"
fi
if [[ "$CORS_ORIGINS_SET" = true ]]; then
  write_env_key "CORS_ORIGINS" "$CORS_ORIGINS_JSON"
fi
if [[ -n "$DOCKER_GID" ]]; then
  write_env_key "DOCKER_GID" "$DOCKER_GID"
else
  warn "DOCKER_GID not detected; executor-manager may fail to access docker.sock"
fi

mkdir -p "$DATA_DIR_ABS"
mkdir -p "$WORKSPACE_DIR_ABS/active" "$WORKSPACE_DIR_ABS/archive" "$WORKSPACE_DIR_ABS/temp"

ensure_gitignore "$DATA_DIR_ABS"
ensure_gitignore "$WORKSPACE_DIR_ABS"

if [[ "$CHOWN_RUSTFS" = true ]]; then
  if ! chown -R "${RUSTFS_UID}:${RUSTFS_GID}" "$DATA_DIR_ABS" 2>/dev/null; then
    warn "Failed to chown RustFS data dir. You may need to run: sudo chown -R ${RUSTFS_UID}:${RUSTFS_GID} \"$DATA_DIR_ABS\""
  fi
fi

chmod -R u+rwX "$DATA_DIR_ABS" 2>/dev/null || \
  warn "Failed to chmod RustFS data dir. You may need to run: sudo chown -R ${RUSTFS_UID}:${RUSTFS_GID} \"$DATA_DIR_ABS\""

chmod -R u+rwX "$WORKSPACE_DIR_ABS" 2>/dev/null || \
  warn "Failed to chmod workspace directories. You may need to run: sudo chown -R \"$(id -u)\":\"$(id -g)\" \"$WORKSPACE_DIR_ABS\""

if [[ "$START_ALL" = true ]]; then
  require_cmd docker
  if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    echo "[error] docker compose not found" >&2
    exit 1
  fi

  if [[ "$PULL_EXECUTOR" = true ]]; then
    executor_image="${EXECUTOR_IMAGE:-}"
    if [[ -z "$executor_image" ]]; then
      executor_image="$(read_env_key "EXECUTOR_IMAGE" || true)"
    fi
    if [[ -z "$executor_image" ]]; then
      executor_image="ghcr.io/poco-ai/poco-executor:latest"
    fi
    echo "[info] Pulling executor image: $executor_image"
    docker pull "$executor_image"
  fi

  if [[ "$ONLY_RUSTFS" = true ]]; then
    "${COMPOSE[@]}" up -d rustfs
  else
    "${COMPOSE[@]}" up -d
  fi

  if [[ "$INIT_BUCKET" = true ]]; then
    "${COMPOSE[@]}" --profile init up -d rustfs-init || \
      warn "rustfs-init failed; you can retry: docker compose --profile init up -d rustfs-init"
  fi
fi

echo "[ok] Bootstrap completed."
