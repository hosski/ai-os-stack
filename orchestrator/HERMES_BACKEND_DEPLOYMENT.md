# Hermes Backend Architecture Deployment Guide

**Status:** Core components built and verified. Ready for integration.

## Components

### 1. Profile Input Layer (`hermes_cli/profile_input.py`)
- Interactive CLI prompts for domain selection (video, law, architecture, homesteading)
- One-by-one capture of profile metadata
- Model defaults per domain (Video: LTX 2.5, Law: Qwen 3.8, etc.)

**Usage:**
```python
from hermes_cli.profile_input import prompt_for_domain_profile
profile = prompt_for_domain_profile()
```

### 2. Hermes ↔ OpenViking REST API Bridge (`hermes_cli/hermes_openviking_api.py`)
- Async HTTP client for unified memory management
- Task state storage/retrieval (`store_task_state`, `fetch_task_state`)
- QA result logging (`store_qa_result`)
- Default endpoint: `http://127.0.0.1:1933` (configurable)

**Usage:**
```python
from hermes_cli.hermes_openviking_api import store_task_state
await store_task_state(task_object)
```

### 3. Fruvisi QA Service (`hermes_cli/fruvisi_qa_service.py`)
- Standalone FastAPI service (port 8002)
- POST `/api/v1/qa/evaluate` — domain-specific pass/fail logic
- GET `/api/v1/qa/status/{task_id}` — verdict retrieval
- Automated rework routing (retries < MAX) / escalation (retries >= MAX)

**Launch:**
```bash
python3 -m hermes_cli.fruvisi_qa_service
```

### 4. MCP Plugin Endpoints Framework (`hermes_cli/mcp_plugin_endpoints.py`)
- JSON-RPC 2.0 over HTTP dispatcher
- Plugin registry with discovery
- Support for GraphCode (8003), Executor (8004), Open Design (8005)
- Async dispatch with timeout + error handling

**Usage:**
```python
from hermes_cli.mcp_plugin_endpoints import get_plugin_registry
registry = get_plugin_registry()
result = await registry.call_plugin(PluginType.EXECUTOR, "executor.generate", params)
```

### 5. Hermes Backend Orchestrator (`hermes_cli/hermes_orchestrator.py`)
- Core task dispatch engine
- Routing: (task_type, domain) → plugin
- State management via OpenViking
- QA verdict processing with rework loops

**Usage:**
```python
from hermes_cli.hermes_orchestrator import get_orchestrator
orch = get_orchestrator()
task_id = await orch.dispatch_task(profile, "generate", input_payload)
await orch.process_qa_verdict(task_id, verdict)
```

### 6. CLI Integration Command (`hermes_cli/orchestration_cli_command.py`)
- Entry point: `/profile-setup` slash command
- Prompts for domain, creates profile, dispatches first task
- Domain-specific task routing

## Deployment Steps

### Step 1: Verify Python Environment
```bash
python3 --version  # 3.9+
uv --version       # Package manager
```

### Step 2: Install Dependencies
```bash
cd /Users/hosski/.hermes/hermes-agent
uv pip install fastapi uvicorn httpx pydantic
```

### Step 3: Start OpenViking (if not running)
```bash
# OpenViking should be running at http://127.0.0.1:1933
# Verify: curl http://127.0.0.1:1933/health
```

### Step 4: Start Fruvisi QA Service
```bash
python3 -m hermes_cli.fruvisi_qa_service &
# Listens on http://127.0.0.1:8002
# Health check: curl http://127.0.0.1:8002/health
```

### Step 5: Stub Plugin Services (Minimal)
Create placeholder services for GraphCode, Executor, Open Design listening on 8003-8005 with JSON-RPC endpoints.

Example minimal Executor stub:
```python
from fastapi import FastAPI
app = FastAPI()

@app.post("/rpc")
async def rpc(request: dict):
    if request.get("method").startswith("executor."):
        return {
            "jsonrpc": "2.0",
            "result": {"task_id": request["params"]["task_id"], "status": "started"},
            "id": request.get("id"),
        }
    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}}

# Run: uvicorn <file>:app --host 127.0.0.1 --port 8004
```

### Step 6: Integrate CLI Command
Add to `HermesCLI` in `cli.py`:
```python
from hermes_cli.orchestration_cli_command import handle_profile_setup_command

async def _handle_profile_setup_command(self, cmd_original):
    return await handle_profile_setup_command()
```

Register in `COMMAND_REGISTRY` (hermes_cli/commands.py):
```python
CommandDef(
    "profile-setup",
    "Configure a domain profile and dispatch initial task",
    "Session",
    aliases=("setup-profile",),
)
```

### Step 7: Run Smoke Test
```bash
python3 -m hermes_cli.backend_smoke_test
# Expected output: ✓ All core components verified
```

## Verification Checklist

- [ ] Smoke test passes without errors
- [ ] OpenViking is reachable via REST API
- [ ] Fruvisi service starts on port 8002
- [ ] Plugin stubs listen on 8003-8005 and respond to JSON-RPC calls
- [ ] CLI command `/profile-setup` prompts for domain (manual test)
- [ ] Profile creation triggers task dispatch
- [ ] Task object stored in active_tasks dict
- [ ] OpenViking receives task state (if running)
- [ ] QA verdict processing updates task status

## Task Object Schema

```json
{
  "task_id": "uuid",
  "status": "pending|running|completed|failed",
  "result_payload": {...} | null,
  "retry_count": 0,
  "priority": 1,
  "domain_profile": "video|law|architecture|homesteading",
  "created_at": "2026-09-23T19:30:00Z"
}
```

## Routing Map

| Task Type | Domain | Target Plugin |
|-----------|--------|---------------|
| generate | video | Executor |
| analyze | law | GraphCode |
| design | architecture | Open Design |
| synthesize | homesteading | Executor |

## Troubleshooting

**"Plugin not available"** → Stub service not running on expected port. Start it or check endpoint in `mcp_plugin_endpoints.py`.

**"Task not found"** → OpenViking offline. Start it or verify endpoint in `hermes_openviking_api.py`.

**Import errors** → Verify Python 3.9+ and all dependencies installed via `uv pip list`.

**Type errors** → All code uses `Optional[X]`, `Union[X, Y]`, `Dict[X, Y]` (Python 3.9 compatible).

## Next: Full Integration

1. Implement stub plugin services (GraphCode, Executor, Open Design)
2. Add CLI command to Hermes command registry
3. Run full e2e test: profile setup → task dispatch → plugin execution → QA verdict → rework/complete
4. Scale to Law, Architecture, Homesteading profiles
5. Integrate with Orca Desktop for real-time visibility
