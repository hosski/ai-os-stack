# 🎸 AI OS Stack — Startup Checklist

**What needs to run before you can rock and roll.**

---

## ✅ STEP 1: Start 3 Services (Order matters!)

### Terminal 1: OpenViking (Audit trail)
```bash
openviking
# Expected: ✅ http://127.0.0.1:1933 (ready in ~3 sec)
```

### Terminal 2: Executor daemon (Tool runner)
```bash
executor daemon run
# Expected: ✅ Daemon listening on localhost:8004
```

### Terminal 3: Hermes (Orchestrator)
```bash
hermes --tui
# Expected: ✅ Hermes TUI loaded (or `hermes` for CLI REPL)
```

**Verify all 3 running before proceeding.**

---

## ✅ STEP 2: Wire Slash Command (Code change)

**File:** `hermes_cli/slash_registry.py`

Add this to the imports section:
```python
from orchestrator.slash_orchestrate_command import (
    handle_slash_orchestrate,
    SLASH_COMMAND_META,
)
```

Add to `SLASH_COMMANDS` dict:
```python
SLASH_COMMANDS["orchestrate"] = {
    "handler": handle_slash_orchestrate,
    "meta": SLASH_COMMAND_META,
}
```

**Verify:** Restart Hermes, then:
```bash
/orchestrate --help
```

Expected: Shows command help + options.

---

## ✅ STEP 3: Start Fruvisi REST Hook (API server)

**Terminal 4:** (New terminal window)
```bash
cd /Users/hosski/.hermes/projects/ai-os-stack
python -m uvicorn orchestrator.fruvisi_orchestrator_hook:app \
  --host 0.0.0.0 --port 8005 --reload
# Expected: ✅ Uvicorn running on http://127.0.0.1:8005
```

**Verify:** 
```bash
curl http://127.0.0.1:8005/health
# Expected: {"status": "ok"}
```

---

## ✅ STEP 4: Wire Daily Momentum Cron (Automation)

**Terminal 5:** (New terminal window, run ONCE)
```bash
hermes cron schedule \
  --name daily-momentum \
  --cron "0 6 * * *" \
  --command "python /Users/hosski/.hermes/projects/ai-os-stack/orchestrator/daily_momentum_engine.py" \
  --deliver telegram
```

**Verify:**
```bash
hermes cron list
# Expected: daily-momentum listed with cron "0 6 * * *"
```

**Test it NOW (don't wait for 6 AM):**
```bash
hermes cron run daily-momentum --now
```

---

## 📋 Full Startup Sequence (Copy-Paste Ready)

### **Terminal 1: OpenViking**
```bash
openviking
```

### **Terminal 2: Executor**
```bash
executor daemon run
```

### **Terminal 3: Hermes**
```bash
hermes --tui
# (or `hermes` for CLI REPL)
```

### **Terminal 4: Fruvisi API**
```bash
cd /Users/hosski/.hermes/projects/ai-os-stack && \
python -m uvicorn orchestrator.fruvisi_orchestrator_hook:app \
  --host 0.0.0.0 --port 8005 --reload
```

### **Terminal 5: Register Cron (run once)**
```bash
hermes cron schedule \
  --name daily-momentum \
  --cron "0 6 * * *" \
  --command "python /Users/hosski/.hermes/projects/ai-os-stack/orchestrator/daily_momentum_engine.py" \
  --deliver telegram
```

### **Then test Cron NOW:**
```bash
hermes cron run daily-momentum --now
```

---

## 🔍 Verification Checklist

After all 5 steps, verify everything:

```bash
# 1. OpenViking health
curl http://127.0.0.1:1933/health
# ✅ Expected: {"status":"ok","healthy":true}

# 2. Executor daemon running
executor status
# ✅ Expected: daemon running

# 3. Hermes slash command works
/orchestrate --help
# ✅ Expected: command help shown

# 4. Fruvisi API responds
curl http://127.0.0.1:8005/health
# ✅ Expected: {"status":"ok"}

# 5. Cron job registered
hermes cron list
# ✅ Expected: daily-momentum listed

# 6. Full E2E test
python /Users/hosski/.hermes/projects/ai-os-stack/orchestrator/e2e_integration_test.py
# ✅ Expected: all 5 tests pass
```

---

## 🚨 If Something Fails

### OpenViking won't start
```bash
# Check if already running
lsof -i :1933
# Kill old process if stuck
kill -9 <PID>
# Restart
openviking
```

### Executor daemon won't start
```bash
# Check if already running
lsof -i :8004
# Kill old process if stuck
kill -9 <PID>
# Restart
executor daemon run
```

### Fruvisi API won't start
```bash
# Check if port 8005 is in use
lsof -i :8005
# Kill old process if stuck
kill -9 <PID>
# Restart
python -m uvicorn orchestrator.fruvisi_orchestrator_hook:app \
  --host 0.0.0.0 --port 8005 --reload
```

### Hermes slash command not found
```bash
# 1. Verify file edit: grep "slash_orchestrate" hermes_cli/slash_registry.py
# 2. Restart Hermes: kill + rerun `hermes --tui`
# 3. Try again: /orchestrate --help
```

### Cron job won't run
```bash
# Check if scheduled
hermes cron list

# Check recent runs
hermes cron logs daily-momentum

# Re-register
hermes cron delete daily-momentum
hermes cron schedule --name daily-momentum ...
```

---

## 📊 Startup State (Visual)

```
6:00 AM → Daily Momentum Engine runs (automated)
         → Reads yesterday's completed tasks
         → Extracts patterns + learning
         → Suggests today's workflow
         → Auto-executes or waits for user input

8:00 AM → You open Hermes
         → Type /orchestrate --interactive
         → Grill-Tab-5 asks 5 questions
         → Task DAG generated + visualized
         → Dispatch to Chief of Staff
         → Sub-agents spawn + execute in parallel
         → Results collected, QA validated
         → Dashboard + metrics returned

5:00 PM → Evening report generated
         → Metrics posted (Telegram, Slack, Discord, Email)
         → Learning loop updates tomorrow's suggestions
         → Cycle repeats
```

---

## ✅ DONE!

Once all 5 steps complete + verification passes:

```
🎸 YOUR SYSTEM IS LIVE 🎸

Ready to:
  ✓ Ship code daily
  ✓ Measure speedup (2.1x)
  ✓ Save 14 hours/day
  ✓ Rock and roll every day
```

---

## 📞 Quick Commands

```bash
# Start everything (fast)
openviking &  # background
executor daemon run &  # background
hermes --tui

# In Hermes:
/orchestrate --interactive

# Watch daily job
hermes cron logs daily-momentum --follow

# Debug
/orchestrate --file /path/to/dag.json --domain video
```

---

**Status: Ready to ROCK AND ROLL** 🎸
