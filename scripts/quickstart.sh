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
S3_PUBLIC_ENDPOINT=""
S3_PUBLIC_ENDPOINT_SET=false
CORS_ORIGINS=""
CORS_ORIGINS_SET=false
DOCKER_GID=""
START_ALL=true
ONLY_RUSTFS=false
INIT_BUCKET=true
PULL_EXECUTOR=true
FORCE_ENV=false
# Default interactive mode only when stdin is a TTY.
INTERACTIVE=false
if [[ -t 0 ]]; then
  INTERACTIVE=true
fi
ANTHROPIC_KEY=""
OPENAI_KEY=""
ANTHROPIC_BASE_URL=""
OPENAI_BASE_URL=""
DEFAULT_MODEL=""
OPENAI_DEFAULT_MODEL=""
# Language setting (en or zh)
LANG="en"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Localization function
msg() {
  local key="$1"
  case "$key" in
    # Usage messages
    "usage.header") [[ "$LANG" == "zh" ]] && echo "用法: scripts/quickstart.sh [选项]" || echo "Usage: scripts/quickstart.sh [options]" ;;
    "usage.options") [[ "$LANG" == "zh" ]] && echo "选项:" || echo "Options:" ;;
    "usage.interactive") [[ "$LANG" == "zh" ]] && echo "  -i, --interactive         交互模式（在终端运行时默认启用）" || echo "  -i, --interactive         Interactive mode (default when run in a terminal)" ;;
    "usage.non_interactive") [[ "$LANG" == "zh" ]] && echo "  --non-interactive         禁用交互式提示（推荐用于 CI）" || echo "  --non-interactive         Disable interactive prompts (recommended for CI)" ;;
    "usage.no_start") [[ "$LANG" == "zh" ]] && echo "  --no-start                仅准备环境和目录" || echo "  --no-start                Only prepare env and directories" ;;
    "usage.force_env") [[ "$LANG" == "zh" ]] && echo "  --force-env               覆盖环境文件中的现有密钥" || echo "  --force-env               Overwrite existing keys in env file" ;;
    "usage.anthropic_key") [[ "$LANG" == "zh" ]] && echo "  --anthropic-key KEY       Anthropic API 密钥（写入环境文件）" || echo "  --anthropic-key KEY       Anthropic API key (writes to env)" ;;
    "usage.openai_key") [[ "$LANG" == "zh" ]] && echo "  --openai-key KEY          OpenAI API 密钥（写入环境文件，可选）" || echo "  --openai-key KEY          OpenAI API key (writes to env, optional)" ;;
    "usage.lang") [[ "$LANG" == "zh" ]] && echo "  --lang LANG               语言设置 (en 或 zh，默认: en)" || echo "  --lang LANG               Language setting (en or zh, default: en)" ;;
    "usage.help") [[ "$LANG" == "zh" ]] && echo "  -h, --help                显示此帮助信息" || echo "  -h, --help                Show this help" ;;
    "usage.advanced") [[ "$LANG" == "zh" ]] && echo "高级选项:" || echo "Advanced options:" ;;
    "usage.examples") [[ "$LANG" == "zh" ]] && echo "示例:" || echo "Examples:" ;;
    "usage.example1") [[ "$LANG" == "zh" ]] && echo "  # 交互式设置（默认）" || echo "  # Interactive setup (default)" ;;
    "usage.example2") [[ "$LANG" == "zh" ]] && echo "  # 交互式设置但不启动服务" || echo "  # Interactive setup without starting services" ;;
    "usage.example3") [[ "$LANG" == "zh" ]] && echo "  # 通过 CLI 快速设置并提供 API 密钥" || echo "  # Quick setup with API keys via CLI" ;;
    "usage.example4") [[ "$LANG" == "zh" ]] && echo "  # 使用中文界面" || echo "  # Use Chinese interface" ;;

    # Print messages
    "print.success") [[ "$LANG" == "zh" ]] && echo "成功" || echo "ok" ;;
    "print.warn") [[ "$LANG" == "zh" ]] && echo "警告" || echo "warn" ;;
    "print.error") [[ "$LANG" == "zh" ]] && echo "错误" || echo "error" ;;
    "print.info") [[ "$LANG" == "zh" ]] && echo "信息" || echo "info" ;;

    # Error messages
    "error.missing_cmd") [[ "$LANG" == "zh" ]] && echo "缺少命令" || echo "Missing command" ;;
    "error.unknown_option") [[ "$LANG" == "zh" ]] && echo "未知选项" || echo "Unknown option" ;;
    "error.docker_not_found") [[ "$LANG" == "zh" ]] && echo "未找到 docker compose" || echo "docker compose not found" ;;
    "error.anthropic_not_set") [[ "$LANG" == "zh" ]] && echo "未设置 Anthropic 认证。请在 .env 中设置 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN（二选一），或运行 ./scripts/quickstart.sh（交互式）并传递 --anthropic-key。" || echo "Anthropic credential is not set. Configure exactly one of ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN in .env, or run ./scripts/quickstart.sh (interactive) / pass --anthropic-key." ;;
    "error.anthropic_conflict") [[ "$LANG" == "zh" ]] && echo "检测到同时设置了 ANTHROPIC_API_KEY 和 ANTHROPIC_AUTH_TOKEN。请仅保留一个。" || echo "Both ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN are set. Keep only one." ;;

    # Headers
    "header.quickstart") [[ "$LANG" == "zh" ]] && echo "Poco 快速启动" || echo "Poco Quickstart" ;;
    "header.interactive_setup") [[ "$LANG" == "zh" ]] && echo "Poco 交互式设置" || echo "Poco Interactive Setup" ;;
    "header.required_config") [[ "$LANG" == "zh" ]] && echo "必需配置" || echo "Required Configuration" ;;
    "header.optional_config") [[ "$LANG" == "zh" ]] && echo "可选配置" || echo "Optional Configuration" ;;
    "header.s3_endpoint") [[ "$LANG" == "zh" ]] && echo "S3 公共端点配置" || echo "S3 Public Endpoint Configuration" ;;
    "header.setup_complete") [[ "$LANG" == "zh" ]] && echo "设置完成" || echo "Setup Complete" ;;
    "header.lang_select") [[ "$LANG" == "zh" ]] && echo "语言选择" || echo "Language Selection" ;;

    # Interactive setup
    "setup.welcome") [[ "$LANG" == "zh" ]] && echo "欢迎使用 Poco！此向导将帮助您配置基本设置。" || echo "Welcome to Poco! This wizard will help you configure the essential settings." ;;
    "setup.input") [[ "$LANG" == "zh" ]] && echo "请输入" || echo "Input" ;;
    "setup.keep_current") [[ "$LANG" == "zh" ]] && echo "按 Enter 保留" || echo "Press Enter to keep" ;;
    "setup.skipping") [[ "$LANG" == "zh" ]] && echo "跳过" || echo "Skipping" ;;
    "setup.optional") [[ "$LANG" == "zh" ]] && echo "可选" || echo "optional" ;;
    "setup.required") [[ "$LANG" == "zh" ]] && echo "是必需的" || echo "is required" ;;

    # API Key prompts
    "prompt.anthropic_key") [[ "$LANG" == "zh" ]] && echo "请输入您的 Anthropic API 密钥（在 https://console.anthropic.com/ 获取）" || echo "Enter your Anthropic API key (get one at https://console.anthropic.com/)" ;;
    "prompt.anthropic_warn") [[ "$LANG" == "zh" ]] && echo "Anthropic API 密钥通常以 'sk-ant-' 开头，请仔细检查。" || echo "Anthropic API key usually starts with 'sk-ant-'. Please double-check." ;;
    "prompt.openai_key") [[ "$LANG" == "zh" ]] && echo "请输入您的 OpenAI API 密钥（或按 Enter 跳过）" || echo "Enter your OpenAI API key (or press Enter to skip)" ;;
    "prompt.openai_warn") [[ "$LANG" == "zh" ]] && echo "OpenAI API 密钥通常以 'sk-' 开头，请仔细检查。" || echo "OpenAI API key usually starts with 'sk-'. Please double-check." ;;

    # Success messages
    "success.env_created") [[ "$LANG" == "zh" ]] && echo "已从 .env.example 创建 .env" || echo "Created .env from .env.example" ;;
    "success.anthropic_configured") [[ "$LANG" == "zh" ]] && echo "已配置 Anthropic API 密钥" || echo "Anthropic API key configured" ;;
    "success.anthropic_base_url") [[ "$LANG" == "zh" ]] && echo "已配置 Anthropic 基础 URL" || echo "Anthropic base URL configured" ;;
    "success.default_model") [[ "$LANG" == "zh" ]] && echo "已配置默认模型" || echo "Default model configured" ;;
    "success.openai_configured") [[ "$LANG" == "zh" ]] && echo "已配置 OpenAI API 密钥" || echo "OpenAI API key configured" ;;
    "success.openai_base_url") [[ "$LANG" == "zh" ]] && echo "已配置 OpenAI 基础 URL" || echo "OpenAI base URL configured" ;;
    "success.openai_model") [[ "$LANG" == "zh" ]] && echo "已配置 OpenAI 默认模型" || echo "OpenAI default model configured" ;;
    "success.s3_endpoint") [[ "$LANG" == "zh" ]] && echo "已配置 S3 公共端点" || echo "S3 public endpoint configured" ;;
    "success.bootstrap") [[ "$LANG" == "zh" ]] && echo "引导完成！" || echo "Bootstrap completed!" ;;

    # Info messages
    "info.anthropic_configured") [[ "$LANG" == "zh" ]] && echo "已配置 Anthropic API 密钥" || echo "Anthropic API key is configured" ;;
    "info.openai_not_set") [[ "$LANG" == "zh" ]] && echo "未设置 OpenAI API 密钥（可选）" || echo "OpenAI API key not set (optional)" ;;
    "info.pulling_images") [[ "$LANG" == "zh" ]] && echo "正在拉取执行器镜像..." || echo "Pulling executor images..." ;;

    # Warnings
    "warn.docker_gid") [[ "$LANG" == "zh" ]] && echo "未检测到 DOCKER_GID；executor-manager 可能无法访问 docker.sock" || echo "DOCKER_GID not detected; executor-manager may fail to access docker.sock" ;;
    "warn.chown_failed") [[ "$LANG" == "zh" ]] && echo "chown RustFS 数据目录失败。您可能需要运行: sudo chown -R" || echo "Failed to chown RustFS data dir. You may need to run: sudo chown -R" ;;
    "warn.chmod_data_failed") [[ "$LANG" == "zh" ]] && echo "chmod RustFS 数据目录失败。您可能需要运行: sudo chown -R" || echo "Failed to chmod RustFS data dir. You may need to run: sudo chown -R" ;;
    "warn.chmod_workspace_failed") [[ "$LANG" == "zh" ]] && echo "chmod 工作空间目录失败。您可能需要运行: sudo chown -R" || echo "Failed to chmod workspace directories. You may need to run: sudo chown -R" ;;
    "warn.rustfs_init_failed") [[ "$LANG" == "zh" ]] && echo "rustfs-init 失败；您可以重试: docker compose --profile init up -d rustfs-init" || echo "rustfs-init failed; you can retry: docker compose --profile init up -d rustfs-init" ;;
    "warn.anthropic_not_set") [[ "$LANG" == "zh" ]] && echo "未设置 Anthropic 认证（ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN）！" || echo "Anthropic credential is not set (ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN)!" ;;
    "warn.anthropic_conflict") [[ "$LANG" == "zh" ]] && echo "检测到 ANTHROPIC_API_KEY 和 ANTHROPIC_AUTH_TOKEN 同时设置，运行时会失败。" || echo "ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN are both set; runtime will fail." ;;
    "warn.default_model") [[ "$LANG" == "zh" ]] && echo "DEFAULT_MODEL 看起来不像 Claude 模型（应以 'claude-' 开头）。" || echo "DEFAULT_MODEL doesn't look like a Claude model (expected prefix 'claude-')." ;;
    "warn.use_openai_model") [[ "$LANG" == "zh" ]] && echo "如果您想使用 OpenAI 模型，请设置 OPENAI_DEFAULT_MODEL。" || echo "If you meant an OpenAI model, set OPENAI_DEFAULT_MODEL instead." ;;
    "warn.openai_model") [[ "$LANG" == "zh" ]] && echo "OPENAI_DEFAULT_MODEL 看起来不像典型的 OpenAI 模型名称（例如 gpt-4o-mini）。" || echo "OPENAI_DEFAULT_MODEL doesn't look like a typical OpenAI model name (e.g. gpt-4o-mini)." ;;

    # Language selection
    "lang.prompt") [[ "$LANG" == "zh" ]] && echo "请选择语言 / Please select language:" || echo "Please select language / 请选择语言:" ;;
    "lang.english") echo "1) English" ;;
    "lang.chinese") echo "2) 中文" ;;
    "lang.choice") [[ "$LANG" == "zh" ]] && echo "请输入选择 [1-2]" || echo "Enter choice [1-2]" ;;

    *) echo "$key" ;;
  esac
}

usage() {
  echo "$(msg "usage.header")"
  echo ""
  echo "$(msg "usage.options")"
  echo "$(msg "usage.interactive")"
  echo "$(msg "usage.non_interactive")"
  echo "$(msg "usage.no_start")"
  echo "$(msg "usage.force_env")"
  echo "$(msg "usage.anthropic_key")"
  echo "$(msg "usage.openai_key")"
  echo "$(msg "usage.lang")"
  echo "$(msg "usage.help")"
  echo ""
  echo "$(msg "usage.advanced")"
  if [[ "$LANG" == "zh" ]]; then
    cat <<'ADVANCED'
  --data-dir PATH           RustFS 数据的主机路径（默认: ./oss_data）
  --workspace-dir PATH      工作空间的主机路径（默认: ./tmp_workspace）
  --rustfs-uid UID          数据目录所有权的 RustFS uid（默认: 10001）
  --rustfs-gid GID          数据目录所有权的 RustFS gid（默认: 10001）
  --no-chown-rustfs         跳过 RustFS 数据目录的 chown 操作
  --s3-bucket NAME          存储桶名称（写入环境文件）
  --s3-access-key KEY       S3 访问密钥（写入环境文件）
  --s3-secret-key KEY       S3 密钥（写入环境文件）
  --s3-public-endpoint URL  用于访问构件的 S3 公共端点（写入环境文件）
  --cors-origins CSV|JSON   允许的来源（写入环境文件）
  --docker-gid GID          Docker 套接字组 ID（如省略则自动检测）
  --env-file PATH           目标环境文件（默认: ./.env）
  --only-rustfs             仅启动 rustfs（和 rustfs-init）
  --no-init-bucket          跳过 rustfs-init 存储桶创建
  --no-pull-executor        跳过拉取执行器镜像
ADVANCED
  else
    cat <<'ADVANCED'
  --data-dir PATH           Host path for RustFS data (default: ./oss_data)
  --workspace-dir PATH      Host path for workspaces (default: ./tmp_workspace)
  --rustfs-uid UID          RustFS uid for data dir ownership (default: 10001)
  --rustfs-gid GID          RustFS gid for data dir ownership (default: 10001)
  --no-chown-rustfs         Skip chown for RustFS data dir
  --s3-bucket NAME          Bucket name (writes to env)
  --s3-access-key KEY       S3 access key (writes to env)
  --s3-secret-key KEY       S3 secret key (writes to env)
  --s3-public-endpoint URL  S3 public endpoint for artifact access (writes to env)
  --cors-origins CSV|JSON   Allowed origins (writes to env)
  --docker-gid GID          Docker socket group id (auto-detect if omitted)
  --env-file PATH           Target env file (default: ./.env)
  --only-rustfs             Start only rustfs (and rustfs-init)
  --no-init-bucket          Skip rustfs-init bucket creation
  --no-pull-executor        Skip pulling executor image
ADVANCED
  fi
  echo ""
  echo "$(msg "usage.examples")"
  echo "$(msg "usage.example1")"
  echo "  ./scripts/quickstart.sh"
  echo ""
  echo "$(msg "usage.example2")"
  echo "  ./scripts/quickstart.sh --no-start"
  echo ""
  echo "$(msg "usage.example3")"
  echo "  ./scripts/quickstart.sh --non-interactive --anthropic-key sk-ant-xxx"
  echo ""
  echo "$(msg "usage.example4")"
  echo "  ./scripts/quickstart.sh --lang zh"
}

print_header() {
  local title="$1"
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}  $title${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo ""
}

print_success() {
  echo -e "${GREEN}[$(msg "print.success")]${NC} $*"
}

print_warn() {
  echo -e "${YELLOW}[$(msg "print.warn")]${NC} $*" >&2
}

print_error() {
  echo -e "${RED}[$(msg "print.error")]${NC} $*" >&2
}

print_info() {
  echo -e "${BLUE}[$(msg "print.info")]${NC} $*"
}

warn() {
  print_warn "$@"
}

read_line() {
  local var_name="$1"
  local value=""
  if [[ -r /dev/tty ]]; then
    IFS= read -r value < /dev/tty
  else
    IFS= read -r value
  fi
  printf -v "$var_name" '%s' "$value"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    print_error "$(msg "error.missing_cmd"): $1"
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
      # 将空值视为"未设置"
      if [[ -z "$value" ]]; then
        return 1
      fi
      # 将示例占位符视为"未设置"
      if [[ "$key" == "ANTHROPIC_API_KEY" && "$value" == "sk-ant-xxxxx" ]]; then
        return 1
      fi
      if [[ "$key" == "ANTHROPIC_AUTH_TOKEN" && "$value" == "sk-ant-xxxxx" ]]; then
        return 1
      fi
      if [[ "$key" == "OPENAI_API_KEY" && "$value" == "sk-xxxxx" ]]; then
        return 1
      fi
      echo "$value"
      return 0
    fi
  fi
  return 1
}

anthropic_credential_state() {
  local has_api_key=false
  local has_auth_token=false

  if read_env_key "ANTHROPIC_API_KEY" >/dev/null 2>&1; then
    has_api_key=true
  fi
  if read_env_key "ANTHROPIC_AUTH_TOKEN" >/dev/null 2>&1; then
    has_auth_token=true
  fi

  if [[ "$has_api_key" = true ]] && [[ "$has_auth_token" = true ]]; then
    echo "conflict"
    return
  fi
  if [[ "$has_api_key" = true ]]; then
    echo "api_key"
    return
  fi
  if [[ "$has_auth_token" = true ]]; then
    echo "auth_token"
    return
  fi
  echo "missing"
}

anthropic_credential_target_key() {
  local state
  state="$(anthropic_credential_state)"
  if [[ "$state" == "auth_token" ]]; then
    echo "ANTHROPIC_AUTH_TOKEN"
    return
  fi
  echo "ANTHROPIC_API_KEY"
}

write_env_key() {
  local key="$1"
  local value="$2"
  if [[ -z "$key" ]]; then
    return
  fi
  
  # 修复: 改进逻辑以允许在值不同时覆盖
  if [[ "$FORCE_ENV" = false ]]; then
    local existing_value
    existing_value="$(read_env_key "$key" || true)"
    # 仅当值完全相同时才跳过
    if [[ -n "$existing_value" ]] && [[ "$existing_value" == "$value" ]]; then
      return 0
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

prompt_for_key() {
  local key_name="$1"
  local prompt_msg="$2"
  local is_optional="${3:-false}"
  local current_value="$4"
  local input_value=""

  # 修复: 移除了 "保留当前值? [Y/n]" 逻辑
  # 改为使用标准的默认值提示样式

  local display_default=""
  if [[ -n "$current_value" ]]; then
     # 为显示掩码密钥
     if [[ "${#current_value}" -gt 12 ]]; then
        display_default="${current_value:0:8}...${current_value: -4}"
     else
        display_default="$current_value"
     fi
  fi

  while true; do
    echo "$prompt_msg" >&2
    if [[ -n "$display_default" ]]; then
        echo -n -e "$(msg "setup.input") ($(msg "setup.keep_current") [${GREEN}${display_default}${NC}]): " >&2
    else
        echo -n "$(msg "setup.input"): " >&2
    fi

    read_line input_value
    echo "" >&2

    # User hit enter
    if [[ -z "$input_value" ]]; then
      if [[ -n "$current_value" ]]; then
        echo "$current_value"
        return
      elif [[ "$is_optional" == "true" ]]; then
        print_info "$(msg "setup.skipping") ${key_name} ($(msg "setup.optional"))" >&2
        echo ""
        return
      else
        print_warn "${key_name} $(msg "setup.required")"
        continue
      fi
    else
      # User entered a value
      echo "$input_value"
      return
    fi
  done
}

prompt_for_text() {
  local prompt_msg="$1"
  local default_value="$2"
  local is_optional="${3:-true}"
  local input_value=""

  if [[ -n "$default_value" ]]; then
    echo -n "$prompt_msg [$default_value]: " >&2
  else
    echo -n "$prompt_msg: " >&2
  fi
  read_line input_value

  if [[ -z "$input_value" ]]; then
    if [[ "$is_optional" == "true" ]]; then
      echo "$default_value"
    else
      echo ""
    fi
  else
    echo "$input_value"
  fi
}

prompt_for_s3_public_endpoint() {
  local current_value="$1"
  local input_value=""

  print_header "$(msg "header.s3_endpoint")" >&2

  if [[ "$LANG" == "zh" ]]; then
    cat >&2 <<'EOF'

S3 公共端点用于直接从浏览器访问生成的构件（图片、HTML 文件等）。
这是前端用来下载存储在 S3/R2 中的构件的 URL。

EOF
    echo -e "${YELLOW}什么时候需要这个配置？${NC}" >&2
    cat >&2 <<'EOF'
  • 远程部署（VPS、云服务器）- 用户从不同网络访问
  • Cloudflare R2 或其他云 S3 兼容存储 - 有公共域名
  • 与他人共享构件 - 需要可访问的 URL

EOF
    echo -e "${YELLOW}什么时候可以跳过？${NC}" >&2
    cat >&2 <<'EOF'
  • 仅本地开发 - 您从 localhost 访问所有内容
  • 使用内置 MinIO（默认）- 本地 S3 位于 localhost:9000

EOF
    local display_msg="请输入 S3 公共端点（或按 Enter 跳过）"
  else
    cat >&2 <<'EOF'

The S3 Public Endpoint is used to access generated artifacts (images, HTML files, etc.)
directly from your browser. This is the URL that your frontend will use to download
artifacts stored in S3/R2.

EOF
    echo -e "${YELLOW}When do you need this?${NC}" >&2
    cat >&2 <<'EOF'
  • Remote deployments (VPS, cloud servers) - Users access from different networks
  • Cloudflare R2 or other cloud S3-compatible storage - Has a public domain
  • Sharing artifacts with others - Need accessible URLs

EOF
    echo -e "${YELLOW}When can you skip this?${NC}" >&2
    cat >&2 <<'EOF'
  • Local development only - You access everything from localhost
  • Using built-in MinIO (default) - Local S3 at localhost:9000

EOF
    local display_msg="Enter S3 public endpoint (or press Enter to skip)"
  fi

  if [[ -n "$current_value" ]]; then
      echo -n "$display_msg [$current_value]: " >&2
  else
      echo -n "$display_msg: " >&2
  fi

  read_line input_value
  echo "" >&2

  if [[ -z "$input_value" ]]; then
    if [[ -n "$current_value" ]]; then
        echo "$current_value"
        return
    fi
    if [[ "$LANG" == "zh" ]]; then
      print_info "跳过 S3 公共端点（本地开发模式）" >&2
    else
      print_info "Skipping S3 public endpoint (local development mode)" >&2
    fi
    echo ""
    return
  fi

  echo "$input_value"
}

select_language() {
  if [[ -t 0 ]]; then
    print_header "$(msg "header.lang_select")"
    echo "$(msg "lang.prompt")"
    echo "$(msg "lang.english")"
    echo "$(msg "lang.chinese")"
    echo ""
    echo -n "$(msg "lang.choice"): "

    local choice
    read_line choice

    case "$choice" in
      1) LANG="en" ;;
      2) LANG="zh" ;;
      *) LANG="en" ;;
    esac
  fi
}

interactive_setup() {
  print_header "$(msg "header.interactive_setup")"

  echo ""
  echo "$(msg "setup.welcome")"
  echo ""

  # Check for existing values in env
  local existing_anthropic
  local existing_anthropic_base_url
  local existing_default_model
  local existing_openai
  local existing_openai_base_url
  local existing_openai_model
  local existing_s3_endpoint

  existing_anthropic="$(read_env_key "ANTHROPIC_API_KEY" || true)"
  if [[ -z "$existing_anthropic" ]]; then
    existing_anthropic="$(read_env_key "ANTHROPIC_AUTH_TOKEN" || true)"
  fi
  existing_anthropic_base_url="$(read_env_key "ANTHROPIC_BASE_URL" || true)"
  existing_default_model="$(read_env_key "DEFAULT_MODEL" || true)"
  existing_openai="$(read_env_key "OPENAI_API_KEY" || true)"
  existing_openai_base_url="$(read_env_key "OPENAI_BASE_URL" || true)"
  existing_openai_model="$(read_env_key "OPENAI_DEFAULT_MODEL" || true)"
  existing_s3_endpoint="$(read_env_key "S3_PUBLIC_ENDPOINT" || true)"

  # FIX: Allow CLI args to override .env defaults during interactive setup
  if [[ -n "$ANTHROPIC_KEY" ]]; then existing_anthropic="$ANTHROPIC_KEY"; fi
  if [[ -n "$OPENAI_KEY" ]]; then existing_openai="$OPENAI_KEY"; fi

  # Prompt for Anthropic key (required)
  print_header "$(msg "header.required_config")"
  ANTHROPIC_KEY="$(prompt_for_key "Anthropic API Key" \
    "$(msg "prompt.anthropic_key")" \
    "false" \
    "$existing_anthropic")"
  if [[ -n "$ANTHROPIC_KEY" ]] && [[ "$ANTHROPIC_KEY" != sk-ant-* ]]; then
    print_warn "$(msg "prompt.anthropic_warn")"
  fi

  # Prompt for Anthropic Base URL (optional)
  if [[ "$LANG" == "zh" ]]; then
    cat <<'EOF'

如果您使用代理或 Anthropic 的自定义 API 端点，请在下面输入基础 URL。
否则，按 Enter 使用默认值 (https://api.anthropic.com)。

EOF
  else
    cat <<'EOF'

If you use a proxy or custom API endpoint for Anthropic, enter the base URL below.
Otherwise, press Enter to use the default (https://api.anthropic.com).

EOF
  fi
  local anthropic_label=$([[ "$LANG" == "zh" ]] && echo "Anthropic 基础 URL" || echo "Anthropic Base URL")
  ANTHROPIC_BASE_URL="$(prompt_for_text "$anthropic_label" "${existing_anthropic_base_url:-https://api.anthropic.com}" "true")"

  # Prompt for Default Model (optional)
  if [[ "$LANG" == "zh" ]]; then
    cat <<'EOF'

请输入要使用的默认 Claude 模型。按 Enter 使用默认值。
常用选项: claude-sonnet-4-20250514, claude-opus-4-20250514

EOF
  else
    cat <<'EOF'

Enter the default Claude model to use. Press Enter to use the default.
Common options: claude-sonnet-4-20250514, claude-opus-4-20250514

EOF
  fi
  local model_label=$([[ "$LANG" == "zh" ]] && echo "默认 Claude 模型" || echo "Default Claude Model")
  DEFAULT_MODEL="$(prompt_for_text "$model_label" "${existing_default_model:-claude-sonnet-4-20250514}" "true")"
  if [[ -n "$DEFAULT_MODEL" ]] && [[ "$DEFAULT_MODEL" != claude-* ]]; then
    print_warn "$(msg "warn.default_model")"
    print_warn "$(msg "warn.use_openai_model")"
  fi

  # Prompt for OpenAI key (optional)
  print_header "$(msg "header.optional_config")"
  if [[ "$LANG" == "zh" ]]; then
    cat <<'EOF'

OpenAI API 密钥是可选的，但如果您想要以下功能则建议配置：
  • 与 Claude 一起使用 GPT 模型
  • 访问 OpenAI 的工具和功能
  • 比较不同 AI 提供商之间的结果

EOF
  else
    cat <<'EOF'

OpenAI API Key is optional but recommended if you want to:
  • Use GPT models alongside Claude
  • Access OpenAI's tools and capabilities
  • Compare results between different AI providers

EOF
  fi
  OPENAI_KEY="$(prompt_for_key "OpenAI API Key" \
    "$(msg "prompt.openai_key")" \
    "true" \
    "$existing_openai")"
  if [[ -n "$OPENAI_KEY" ]] && [[ "$OPENAI_KEY" != sk-* ]]; then
    print_warn "$(msg "prompt.openai_warn")"
  fi

  if [[ -n "$OPENAI_KEY" ]]; then
    # Prompt for OpenAI Base URL (only if key is set)
    if [[ "$LANG" == "zh" ]]; then
      cat <<'EOF'

如果您使用代理或 OpenAI 的自定义 API 端点，请在下面输入基础 URL。
否则，按 Enter 使用默认值 (https://api.openai.com/v1)。

EOF
    else
      cat <<'EOF'

If you use a proxy or custom API endpoint for OpenAI, enter the base URL below.
Otherwise, press Enter to use the default (https://api.openai.com/v1).

EOF
    fi
    local openai_base_label=$([[ "$LANG" == "zh" ]] && echo "OpenAI 基础 URL" || echo "OpenAI Base URL")
    OPENAI_BASE_URL="$(prompt_for_text "$openai_base_label" "${existing_openai_base_url:-https://api.openai.com/v1}" "true")"

    # Prompt for OpenAI Default Model
    if [[ "$LANG" == "zh" ]]; then
      cat <<'EOF'

请输入要使用的默认 GPT 模型。按 Enter 使用默认值。
常用选项: gpt-4o, gpt-4o-mini, gpt-4-turbo

EOF
    else
      cat <<'EOF'

Enter the default GPT model to use. Press Enter to use the default.
Common options: gpt-4o, gpt-4o-mini, gpt-4-turbo

EOF
    fi
    local openai_model_label=$([[ "$LANG" == "zh" ]] && echo "OpenAI 默认模型" || echo "OpenAI Default Model")
    OPENAI_DEFAULT_MODEL="$(prompt_for_text "$openai_model_label" "${existing_openai_model:-gpt-4o-mini}" "true")"
    if [[ -n "$OPENAI_DEFAULT_MODEL" ]] && [[ "$OPENAI_DEFAULT_MODEL" != gpt-* && "$OPENAI_DEFAULT_MODEL" != o1* && "$OPENAI_DEFAULT_MODEL" != o3* ]]; then
      print_warn "$(msg "warn.openai_model")"
    fi
  fi

  # Prompt for S3 public endpoint
  S3_PUBLIC_ENDPOINT="$(prompt_for_s3_public_endpoint "$existing_s3_endpoint")"

  # Write all collected keys
  # NOTE: write_env_key now handles check-before-write logic correctly
  if [[ -n "$ANTHROPIC_KEY" ]]; then
    local anthropic_key_target
    anthropic_key_target="$(anthropic_credential_target_key)"
    write_env_key "$anthropic_key_target" "$ANTHROPIC_KEY"
    print_success "$(msg "success.anthropic_configured")"
  fi

  if [[ -n "$ANTHROPIC_BASE_URL" ]]; then
    write_env_key "ANTHROPIC_BASE_URL" "$ANTHROPIC_BASE_URL"
    print_success "$(msg "success.anthropic_base_url")"
  fi

  if [[ -n "$DEFAULT_MODEL" ]]; then
    write_env_key "DEFAULT_MODEL" "$DEFAULT_MODEL"
    print_success "$(msg "success.default_model")"
  fi

  if [[ -n "$OPENAI_KEY" ]]; then
    write_env_key "OPENAI_API_KEY" "$OPENAI_KEY"
    print_success "$(msg "success.openai_configured")"
  fi

  if [[ -n "$OPENAI_BASE_URL" ]]; then
    write_env_key "OPENAI_BASE_URL" "$OPENAI_BASE_URL"
    print_success "$(msg "success.openai_base_url")"
  fi

  if [[ -n "$OPENAI_DEFAULT_MODEL" ]]; then
    write_env_key "OPENAI_DEFAULT_MODEL" "$OPENAI_DEFAULT_MODEL"
    print_success "$(msg "success.openai_model")"
  fi

  if [[ -n "$S3_PUBLIC_ENDPOINT" ]]; then
    write_env_key "S3_PUBLIC_ENDPOINT" "$S3_PUBLIC_ENDPOINT"
    print_success "$(msg "success.s3_endpoint")"
  fi

  echo ""
}

# --- MAIN EXECUTION START ---

# First pass: parse CLI args to override defaults
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
    --s3-public-endpoint)
      S3_PUBLIC_ENDPOINT="$2"; S3_PUBLIC_ENDPOINT_SET=true; shift 2 ;;
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
    -i|--interactive)
      INTERACTIVE=true; shift ;;
    --non-interactive|--no-interactive)
      INTERACTIVE=false; shift ;;
    --anthropic-key)
      ANTHROPIC_KEY="$2"; shift 2 ;;
    --openai-key)
      OPENAI_KEY="$2"; shift 2 ;;
    --lang)
      LANG="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      print_error "$(msg "error.unknown_option"): $1"
      usage
      exit 1
      ;;
  esac
done

# Select language if not specified and in interactive mode
if [[ "$INTERACTIVE" = true ]] && [[ "$LANG" == "en" ]]; then
  select_language
fi

print_header "$(msg "header.quickstart")"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "${ROOT_DIR}/.env.example" ]]; then
    cp "${ROOT_DIR}/.env.example" "$ENV_FILE"
    print_success "$(msg "success.env_created")"
  else
    touch "$ENV_FILE"
  fi
fi

# Run interactive setup if requested
if [[ "$INTERACTIVE" = true ]]; then
  interactive_setup
fi

# Handle API keys from CLI arguments (non-interactive mode).
if [[ "$INTERACTIVE" = false ]]; then
  if [[ -n "$ANTHROPIC_KEY" ]]; then
    anthropic_key_target="$(anthropic_credential_target_key)"
    write_env_key "$anthropic_key_target" "$ANTHROPIC_KEY"
    print_success "$(msg "success.anthropic_configured")"
  fi

  if [[ -n "$OPENAI_KEY" ]]; then
    write_env_key "OPENAI_API_KEY" "$OPENAI_KEY"
    print_success "$(msg "success.openai_configured")"
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
if [[ "$S3_PUBLIC_ENDPOINT_SET" = true ]]; then
  write_env_key "S3_PUBLIC_ENDPOINT" "$S3_PUBLIC_ENDPOINT"
  print_success "S3 public endpoint configured"
fi
if [[ "$CORS_ORIGINS_SET" = true ]]; then
  write_env_key "CORS_ORIGINS" "$CORS_ORIGINS_JSON"
fi
if [[ -n "$DOCKER_GID" ]]; then
  write_env_key "DOCKER_GID" "$DOCKER_GID"
else
  warn "$(msg "warn.docker_gid")"
fi

mkdir -p "$DATA_DIR_ABS"
mkdir -p "$WORKSPACE_DIR_ABS/active" "$WORKSPACE_DIR_ABS/archive" "$WORKSPACE_DIR_ABS/temp"

ensure_gitignore "$DATA_DIR_ABS"
ensure_gitignore "$WORKSPACE_DIR_ABS"

if [[ "$CHOWN_RUSTFS" = true ]]; then
  if ! chown -R "${RUSTFS_UID}:${RUSTFS_GID}" "$DATA_DIR_ABS" 2>/dev/null; then
    warn "$(msg "warn.chown_failed") ${RUSTFS_UID}:${RUSTFS_GID} \"$DATA_DIR_ABS\""
  fi
fi

chmod -R u+rwX "$DATA_DIR_ABS" 2>/dev/null || \
  warn "$(msg "warn.chmod_data_failed") ${RUSTFS_UID}:${RUSTFS_GID} \"$DATA_DIR_ABS\""

chmod -R u+rwX "$WORKSPACE_DIR_ABS" 2>/dev/null || \
  warn "$(msg "warn.chmod_workspace_failed") \"$(id -u)\":\"$(id -g)\" \"$WORKSPACE_DIR_ABS\""

if [[ "$START_ALL" = true ]]; then
  anthropic_credential_state_value="$(anthropic_credential_state)"
  if [[ "$anthropic_credential_state_value" == "conflict" ]]; then
    print_error "$(msg "error.anthropic_conflict")"
    exit 1
  fi
  if [[ "$anthropic_credential_state_value" == "missing" ]]; then
    print_error "$(msg "error.anthropic_not_set")"
    exit 1
  fi
fi

if [[ "$START_ALL" = true ]]; then
  require_cmd docker
  if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
  elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    print_error "$(msg "error.docker_not_found")"
    exit 1
  fi

  if [[ "$PULL_EXECUTOR" = true ]]; then
    # Pull both lite and full executor images
    executor_lite_image="${EXECUTOR_IMAGE:-}"
    if [[ -z "$executor_lite_image" ]]; then
      executor_lite_image="$(read_env_key "EXECUTOR_IMAGE" || true)"
    fi
    if [[ -z "$executor_lite_image" ]]; then
      executor_lite_image="ghcr.io/poco-ai/poco-executor:lite"
    fi

    executor_full_image="${EXECUTOR_BROWSER_IMAGE:-}"
    if [[ -z "$executor_full_image" ]]; then
      executor_full_image="$(read_env_key "EXECUTOR_BROWSER_IMAGE" || true)"
    fi
    if [[ -z "$executor_full_image" ]]; then
      executor_full_image="ghcr.io/poco-ai/poco-executor:full"
    fi

    print_info "$(msg "info.pulling_images")"
    print_info "  - $executor_lite_image"
    docker pull "$executor_lite_image"
    print_info "  - $executor_full_image"
    docker pull "$executor_full_image"
  fi

  if [[ "$ONLY_RUSTFS" = true ]]; then
    "${COMPOSE[@]}" up -d rustfs
  else
    "${COMPOSE[@]}" up -d
  fi

  if [[ "$INIT_BUCKET" = true ]]; then
    "${COMPOSE[@]}" --profile init up -d rustfs-init || \
      warn "$(msg "warn.rustfs_init_failed")"
  fi
fi

# Final status check
print_header "$(msg "header.setup_complete")"

# Check Anthropic credential state
anthropic_credential_state_value="$(anthropic_credential_state)"
if [[ "$anthropic_credential_state_value" == "conflict" ]]; then
  print_warn "$(msg "warn.anthropic_conflict")"
  if [[ "$LANG" == "zh" ]]; then
    cat <<EOF

  请在 .env 中仅保留一个变量：
    - ANTHROPIC_API_KEY（推荐）
    - ANTHROPIC_AUTH_TOKEN（兼容 Bearer 网关）

  在此获取密钥: https://console.anthropic.com/
EOF
  else
    cat <<EOF

  Keep exactly one credential variable in .env:
    - ANTHROPIC_API_KEY (recommended)
    - ANTHROPIC_AUTH_TOKEN (for bearer-token gateways)

  Get credentials at: https://console.anthropic.com/
EOF
  fi
elif [[ "$anthropic_credential_state_value" == "missing" ]]; then
  print_warn "$(msg "warn.anthropic_not_set")"
  if [[ "$LANG" == "zh" ]]; then
    cat <<EOF

  请在 .env 中设置以下任一变量：
    - ANTHROPIC_API_KEY（推荐）
    - ANTHROPIC_AUTH_TOKEN（兼容 Bearer 网关）

  或运行:
    ./scripts/quickstart.sh

  在此获取密钥: https://console.anthropic.com/
EOF
  else
    cat <<EOF

  Set one credential variable in .env:
    - ANTHROPIC_API_KEY (recommended)
    - ANTHROPIC_AUTH_TOKEN (for bearer-token gateways)

  Or run:
    ./scripts/quickstart.sh

  Get credentials at: https://console.anthropic.com/
EOF
  fi
else
  print_success "$(msg "info.anthropic_configured")"
fi

# Remind about optional keys
if ! read_env_key "OPENAI_API_KEY" >/dev/null 2>&1; then
  print_info "$(msg "info.openai_not_set")"
  if [[ "$LANG" == "zh" ]]; then
    echo "  如果您想使用 GPT 模型，可以稍后在 .env 中添加"
  else
    echo "  Add it later in .env if you want to use GPT models"
  fi
fi

echo ""
print_success "$(msg "success.bootstrap")"
echo ""
if [[ "$LANG" == "zh" ]]; then
  echo "后续步骤:"
  echo "  1. 确保在 .env 中仅设置了 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN（只能一个）"
  if [[ "$START_ALL" = true ]]; then
    echo "  2. 打开浏览器: http://localhost:3000"
    echo "  3. 查看日志: docker compose logs -f backend executor-manager frontend"
  else
    echo "  2. 启动服务: docker compose up -d"
    echo "  3. 打开浏览器: http://localhost:3000"
  fi
else
  echo "Next steps:"
  echo "  1. Make sure exactly one of ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN is set in .env"
  if [[ "$START_ALL" = true ]]; then
    echo "  2. Open browser: http://localhost:3000"
    echo "  3. View logs: docker compose logs -f backend executor-manager frontend"
  else
    echo "  2. Start services: docker compose up -d"
    echo "  3. Open browser: http://localhost:3000"
  fi
fi
echo ""
