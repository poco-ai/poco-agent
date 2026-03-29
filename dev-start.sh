#!/bin/bash
# Poco 本地开发启动脚本
# 所有服务（postgres, rustfs, backend, EM, frontend）一起启动

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXECUTOR_DOCKERFILE="$SCRIPT_DIR/docker/executor/Dockerfile"

# ─── Step 1: Build local executor images ──────────────────────────────
echo -e "\n${BLUE}Step 1/4: Executor images${NC}"

LITE_EXISTS=$(docker images -q poco-executor:lite 2>/dev/null)
FULL_EXISTS=$(docker images -q poco-executor:full 2>/dev/null)

if [ -n "$LITE_EXISTS" ] || [ -n "$FULL_EXISTS" ]; then
    read -p "Rebuild local executor images? (lite + full) [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        NEED_BUILD=true
    else
        NEED_BUILD=false
    fi
else
    echo -e "${YELLOW}No local executor images found. Building...${NC}"
    NEED_BUILD=true
fi

if [ "$NEED_BUILD" = true ]; then
    echo -e "${BLUE}  Building poco-executor:lite ...${NC}"
    docker build -t poco-executor:lite \
        --build-arg SANDBOX_VARIANT=lite \
        -f "$EXECUTOR_DOCKERFILE" "$SCRIPT_DIR" \
        || { echo -e "${RED}Failed to build lite image${NC}"; exit 1; }
    echo -e "${GREEN}  ✅ poco-executor:lite${NC}"

    echo -e "${BLUE}  Building poco-executor:full ...${NC}"
    docker build -t poco-executor:full \
        --build-arg SANDBOX_VARIANT=full \
        -f "$EXECUTOR_DOCKERFILE" "$SCRIPT_DIR" \
        || { echo -e "${RED}Failed to build full image${NC}"; exit 1; }
    echo -e "${GREEN}  ✅ poco-executor:full${NC}"
else
    echo -e "${GREEN}  ✅ Using existing executor images${NC}"
fi

# ─── Step 2: Start infrastructure (postgres, rustfs) ─────────────────
echo -e "\n${BLUE}Step 2/4: Infrastructure (postgres, rustfs)${NC}"
docker compose up -d postgres rustfs
echo -e "${GREEN}  ✅ Infrastructure started${NC}"

# ─── Step 3: Check port availability ──────────────────────────────────
echo -e "\n${BLUE}Step 3/4: Port check${NC}"
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}  ⚠️  Port $1 in use ($2)${NC}"
        return 1
    fi
    return 0
}

check_port 8000 "Backend" || true
check_port 8001 "Executor Manager" || true
check_port 3000 "Frontend" || true

# ─── Step 4: Start application services ───────────────────────────────
echo -e "\n${BLUE}Step 4/4: Application services${NC}"

TMUX_MODE=false
if [ "$1" = "--manual" ]; then
    TMUX_MODE=false
elif command -v tmux &>/dev/null; then
    TMUX_MODE=true
fi

if [ "$TMUX_MODE" = true ]; then
    # ── tmux mode: all services in one session ──
    SESSION="poco"

    # Kill existing session if any
    tmux kill-session -t "$SESSION" 2>/dev/null || true

    tmux new-session -d -s "$SESSION" -c "$SCRIPT_DIR/backend" \
        "uv sync 2>&1 | tail -1 && uv run python -m app.main"
    tmux rename-window -t "$SESSION:0" backend

    tmux new-window -t "$SESSION:1" -n executor-manager -c "$SCRIPT_DIR/executor_manager" \
        "uv sync 2>&1 | tail -1 && uv run python -m app.main"

    tmux new-window -t "$SESSION:2" -n frontend -c "$SCRIPT_DIR/frontend" \
        "pnpm dev"

    tmux new-window -t "$SESSION:3" -n infra \
        "docker compose logs -f postgres rustfs"

    tmux attach-session -t "$SESSION"
else
    # ── Manual mode: print commands ──
    echo -e "\n${GREEN}✅ Infrastructure ready. Start application services in separate terminals:${NC}"
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}1. Executor Manager:${NC}"
    echo -e "   ${GREEN}cd executor_manager && uv sync && uv run python -m app.main${NC}"
    echo -e "\n${BLUE}2. Backend:${NC}"
    echo -e "   ${GREEN}cd backend && uv sync && uv run python -m app.main${NC}"
    echo -e "\n${BLUE}3. Frontend:${NC}"
    echo -e "   ${GREEN}cd frontend && pnpm dev${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "\n${YELLOW}Install tmux or run ./dev-start.sh (tmux detected automatically).${NC}"
fi

echo -e "\n${GREEN}Services:${NC}"
echo "  PostgreSQL:       localhost:5432"
echo "  RustFS:           localhost:9000 / 9001"
echo "  Executor Manager: localhost:8001"
echo "  Backend:          localhost:8000"
echo "  Frontend:         localhost:3000"
echo -e "\n${YELLOW}Logs:${NC}"
echo "  docker compose logs -f postgres rustfs"
echo -e "\n${YELLOW}Stop infrastructure:${NC}"
echo "  ./dev-stop.sh"
