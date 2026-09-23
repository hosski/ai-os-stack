#!/bin/bash
# AI OS Stack startup script
# Launches: OpenViking (1933), mlx-serve (11234), project MCPs
# Only MCPs for this project (Fruvisi, GraphCode, Executor, Open Design on 8002-8005)

set -e

PROJECT_ROOT="$HOME/.hermes/projects/ai-os-stack"
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"

echo "🚀 AI OS Stack Startup"
echo "  Project: $PROJECT_ROOT"
echo "  Logs: $LOGS_DIR"
echo ""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to start a service
start_service() {
    local name=$1
    local port=$2
    local command=$3
    local log_file="$LOGS_DIR/${name}.log"
    
    echo -n "Starting $name (port $port)... "
    
    # Start in background
    eval "$command" > "$log_file" 2>&1 &
    local pid=$!
    
    # Give it 2 seconds to start
    sleep 2
    
    # Check if still running
    if ps -p $pid > /dev/null; then
        echo -e "${GREEN}✓${NC} (PID $pid)"
        echo "$pid" >> "$LOGS_DIR/.pids"
    else
        echo -e "${RED}✗${NC}"
        echo "  Error: Check $log_file"
        return 1
    fi
}

# Clean up old PID file
rm -f "$LOGS_DIR/.pids"
touch "$LOGS_DIR/.pids"

# 1. OpenViking (1933)
echo "1️⃣  Knowledge Store"
start_service "OpenViking" "1933" "openviking serve --port 1933"

# 2. MLX-Serve (11234) — local inference backend
echo ""
echo "2️⃣  Inference Engine"
start_service "mlx-serve" "11234" "mlx-serve serve --port 11234 --model Qwen/Qwen2.5-7B-Instruct"

# 3. Project MCPs (parallel execution)
echo ""
echo "3️⃣  Agents"

# Fruvisi QA Service (8002)
start_service "Fruvisi-QA" "8002" "cd $PROJECT_ROOT && python3 orchestrator/fruvisi_qa_service.py"

# Executor Plugin (8004) — CORE PARALLEL ENGINE
start_service "Executor" "8004" "cd $PROJECT_ROOT && python3 orchestrator/executor_plugin_stub.py"

# GraphCode Plugin (8003)
start_service "GraphCode" "8003" "cd $PROJECT_ROOT && python3 orchestrator/graphcode_plugin_stub.py"

# Open Design Plugin (8005)
start_service "Open-Design" "8005" "cd $PROJECT_ROOT && python3 orchestrator/open_design_plugin_stub.py"

echo ""
echo -e "${GREEN}✓ All services running${NC}"
echo ""
echo "Services:"
echo "  OpenViking:    http://localhost:1933"
echo "  MLX-Serve:     http://localhost:11234"
echo "  Executor:      http://localhost:8004  (PARALLEL AGENT DISPATCH)"
echo "  GraphCode:     http://localhost:8003"
echo "  Fruvisi-QA:    http://localhost:8002"
echo "  Open-Design:   http://localhost:8005"
echo ""
echo "Logs: $LOGS_DIR"
echo ""
echo "Stop with: kill \$(cat $LOGS_DIR/.pids | tr '\n' ' ')"
echo ""
echo "🎯 Ready for /profile-setup"
