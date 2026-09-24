#!/bin/bash
# 🎸 AI OS Stack Startup — Real Services Only
# Launches: OpenViking (1933), Executor daemon (8004), Hermes, Fruvisi Hook (8005)
# NO stubs — all services are real executables

set -e

PROJECT_ROOT="$HOME/.hermes/projects/ai-os-stack"
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"

echo "🎸 AI OS Stack Startup"
echo "  Project: $PROJECT_ROOT"
echo "  Logs: $LOGS_DIR"
echo ""

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to check if service is running
check_service() {
    local name=$1
    local port=$2
    local url="http://localhost:$port"
    
    echo -n "Checking $name ($url)... "
    if curl -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Clean up old PID file
rm -f "$LOGS_DIR/.pids"
touch "$LOGS_DIR/.pids"

echo "📋 Startup Instructions"
echo ""
echo "You must start 4 services in separate terminals."
echo "This script helps coordinate them."
echo ""

# ============================================================================
# 1️⃣ OpenViking (1933) — Audit trail
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "1️⃣  ${CYAN}OpenViking${NC} (Knowledge Store — port 1933)"
echo ""
echo "   In ${YELLOW}Terminal 1${NC}:"
echo "   ${YELLOW}$ openviking${NC}"
echo ""

if check_service "OpenViking" "1933"; then
    echo "   ✓ Already running"
else
    echo "   ⚠ Not running"
fi
echo ""
read -p "   Press ENTER once OpenViking is running on port 1933..."
echo ""

# ============================================================================
# 2️⃣ Executor daemon (8004) — Tool runner
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "2️⃣  ${CYAN}Executor Daemon${NC} (Tool Runner — port 8004)"
echo ""
echo "   In ${YELLOW}Terminal 2${NC}:"
echo "   ${YELLOW}$ executor daemon run${NC}"
echo ""

if check_service "Executor" "8004"; then
    echo "   ✓ Already running"
else
    echo "   ⚠ Not running"
fi
echo ""
read -p "   Press ENTER once Executor is running on port 8004..."
echo ""

# ============================================================================
# 3️⃣ Hermes (CLI/TUI) — Orchestrator
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "3️⃣  ${CYAN}Hermes${NC} (Orchestrator — CLI/TUI)"
echo ""
echo "   In ${YELLOW}Terminal 3${NC}:"
echo "   ${YELLOW}$ hermes --tui${NC}"
echo ""
echo "   (or for CLI REPL: ${YELLOW}$ hermes${NC})"
echo ""
read -p "   Press ENTER once Hermes is running..."
echo ""

# ============================================================================
# 4️⃣ Fruvisi REST Hook (8005) — API for UI
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "4️⃣  ${CYAN}Fruvisi REST Hook${NC} (REST API — port 8005)"
echo ""
echo "   In ${YELLOW}Terminal 4${NC}:"
echo "   ${YELLOW}$ cd $PROJECT_ROOT${NC}"
echo "   ${YELLOW}$ python -m uvicorn orchestrator.fruvisi_orchestrator_hook:app --port 8005 --reload${NC}"
echo ""

log_file="$LOGS_DIR/fruvisi-hook.log"
echo "   Starting Fruvisi Hook locally..."
echo ""

cd "$PROJECT_ROOT"
python -m uvicorn orchestrator.fruvisi_orchestrator_hook:app \
  --host 0.0.0.0 --port 8005 --reload > "$log_file" 2>&1 &

pid=$!
echo "$pid" >> "$LOGS_DIR/.pids"

# Wait for it to start
sleep 3

if check_service "Fruvisi Hook" "8005"; then
    echo "   ✓ Started (PID $pid)"
else
    echo "   ✗ Failed. Check: tail -f $log_file"
    exit 1
fi
echo ""

# ============================================================================
# 5️⃣ Code Wiring (One-time) — Slash Command
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "5️⃣  ${CYAN}Wire Slash Command${NC} (one-time code change)"
echo ""
echo "   Edit: ${YELLOW}hermes_cli/slash_registry.py${NC}"
echo ""
echo "   Add to imports:"
echo "   ${CYAN}from orchestrator.slash_orchestrate_command import handle_slash_orchestrate${NC}"
echo ""
echo "   Add to SLASH_COMMANDS dict:"
echo "   ${CYAN}SLASH_COMMANDS[\"orchestrate\"] = {\"handler\": handle_slash_orchestrate}${NC}"
echo ""
read -p "   Done editing? Press ENTER..."
echo ""

# ============================================================================
# 6️⃣ Schedule Daily Cron (One-time)
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "6️⃣  ${CYAN}Schedule Daily Automation${NC} (one-time)"
echo ""
echo "   This creates a 6 AM daily briefing that auto-dispatches tasks."
echo ""
echo "   ${YELLOW}hermes cron schedule \\"
echo "     --name daily-momentum \\"
echo "     --cron \"0 6 * * *\" \\"
echo "     --command \"python $PROJECT_ROOT/orchestrator/daily_momentum_engine.py\" \\"
echo "     --deliver telegram${NC}"
echo ""
read -p "   Ready to schedule? Press ENTER..."

hermes cron schedule \
  --name daily-momentum \
  --cron "0 6 * * *" \
  --command "python $PROJECT_ROOT/orchestrator/daily_momentum_engine.py" \
  --deliver telegram

echo ""
echo "   ✓ Cron job scheduled for 6 AM daily"
echo ""

# ============================================================================
# ✅ Verification
# ============================================================================
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ ${GREEN}VERIFY ALL SYSTEMS${NC}"
echo ""
echo "Run these commands to check everything:"
echo ""
echo "   ${YELLOW}curl http://127.0.0.1:1933/health${NC}"
echo "   ${YELLOW}executor status${NC}"
echo "   ${YELLOW}/orchestrate --help${NC}"
echo "   ${YELLOW}curl http://127.0.0.1:8005/health${NC}"
echo "   ${YELLOW}hermes cron list${NC}"
echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "✨ ${GREEN}YOU'RE LIVE${NC}"
echo ""
echo "Running services:"
echo "  ${CYAN}OpenViking${NC}       http://localhost:1933    (audit trail)"
echo "  ${CYAN}Executor${NC}         http://localhost:8004    (tools)"
echo "  ${CYAN}Hermes${NC}           CLI/TUI                  (orchestrator)"
echo "  ${CYAN}Fruvisi Hook${NC}     http://localhost:8005    (REST API)"
echo ""
echo "Logs: $LOGS_DIR"
echo ""
echo "To stop all services:"
echo "  ${YELLOW}kill \$(cat $LOGS_DIR/.pids | tr '\\n' ' ')${NC}"
echo ""
echo "Next commands:"
echo "  ${YELLOW}/orchestrate --interactive${NC}          (grill-tab: 5 questions)"
echo "  ${YELLOW}/orchestrate --domain video${NC}         (target team)"
echo "  ${YELLOW}/orchestrate --file dag.json${NC}        (pre-built DAG)"
echo ""
echo "6 AM tomorrow: Daily briefing auto-runs 🎸"
echo ""
