#!/bin/bash
# Poco 本地开发停止脚本

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}Stopping Poco local development environment...${NC}"

# 1. Stop tmux session if running
if tmux has-session -t poco 2>/dev/null; then
    tmux kill-session -t poco
    echo -e "${GREEN}✅ tmux session 'poco' stopped${NC}"
fi

# 2. Stop infrastructure (postgres, rustfs)
docker compose down

echo -e "${GREEN}✅ All services stopped${NC}"
