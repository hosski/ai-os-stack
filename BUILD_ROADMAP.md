# AI OS Stack - Build Roadmap (Sep 26)

## Phase 1: Grill-Tab-5 Integration (TODAY - 2 hours)

### Step 1: Create Grill-Tab-5 Skill ✅
- Skill created at `~/.hermes/skills/grilling/grill-tab-5/`
- 5-question one-round interrogation
- Outputs structured task list with DAG + parallelization hints

### Step 2: Wire Fruvisi Task Creation Modal
**File:** `/Users/hosski/.hermes/plugins/fruvisi/src/components/TaskCreationModal.tsx`

**Changes:**
```tsx
// Add toggle: Grill-Tab vs. Freehand vs. Quick Repeat

const TaskCreationModal = () => {
  const [mode, setMode] = useState<'grill-tab' | 'freehand' | 'repeat'>();

  if (mode === 'grill-tab') {
    // Launch grill-tab-5 skill via Hermes chat
    // Wait for task breakdown
    // Render TaskDAGRenderer
  }
  
  if (mode === 'freehand') {
    // Text input
    // Call AI refiner agent
    // Render TaskDAGRenderer
  }
  
  if (mode === 'repeat') {
    // Load template
    // Show task list
  }
};
```

### Step 3: Create Task DAG Renderer
**File:** `/Users/hosski/.hermes/plugins/fruvisi/src/components/TaskDAGRenderer.tsx`

**Inputs:**
```typescript
interface TaskDAG {
  tasks: {
    id: string;
    name: string;
    duration: string;
    dependsOn: string[];  // task IDs
    owner: string;
    type: 'cpu' | 'io' | 'mixed';
  }[];
  parallelizationHints: {
    canRunTogether: string[];  // task IDs
    mustBeSequential: string[];
    expectedSpeedup: number;
  };
}
```

**Output:** Mermaid DAG or ASCII diagram + timeline visualization

---

## Phase 2: Hermes Orchestrator Updates (2-3 hours)

### Step 4: Update Team Orchestrator for Task DAG
**File:** `/Users/hosski/.hermes/projects/ai-os-stack/orchestrator/team_orchestrator.py`

**New function:**
```python
def dispatch_task_dag(
    team: Team,
    task_dag: Dict[str, Task],  # {task_id: Task}
    parallelization_config: Dict  # P cores, QoS, etc.
) -> str:
    """
    1. Read task DAG
    2. Identify parallelization tiers (tasks with no deps = tier 0)
    3. For each tier:
       - Spawn sub-agents (one per task)
       - Set QoS: 'utility' for sub-agents
       - Wait for all to complete
    4. Move to next tier
    5. Return task completion report
    """
    pass
```

### Step 5: Chief Agent Prompt Enhancement
**File:** `/Users/hosski/.hermes/projects/ai-os-stack/orchestrator/chief_agent_prompt.py`

**Chief gets:**
```python
chief_context = {
    "team": video_team,  # Members: Designer, Editor, Writer
    "task_dag": task_dag,  # Serialized JSON DAG
    "parallelization_config": {
        "p_cores": 8,
        "e_cores": 4,
        "qos_hint": "utility",
    },
    "executor_integrations": [
        "open_design_cli",
        "graphcode_cli",
        "text_generation_mcp"
    ]
}
```

**Chief behavior:**
- Read DAG
- For tier 0 (no deps): spawn Designer, Editor, Writer via `delegate_task` simultaneously
- Wait for all 3 to finish
- Move to tier 1 (waits on tier 0)
- Synthesize results

---

## Phase 3: Sub-Agent Executor Integration (3-4 hours)

### Step 6: Sub-Agent Harness
**File:** `/Users/hosski/.hermes/projects/ai-os-stack/orchestrator/sub_agent_harness.py`

**Each sub-agent receives:**
```python
{
    "role": "designer" | "editor" | "writer" | "specialist",
    "task_id": "task_1",
    "task_description": "Create scene designs for episode 1",
    "inputs": {  # If task depends on prior tier
        "prior_asset": "episode_1_script.md"
    },
    "available_integrations": [
        "open_design",
        "graphcode",
        ...
    ],
    "executor_integration": "MCP or CLI"
}
```

**Sub-agent execution:**
1. Read task + inputs
2. Call Executor tool(s):
   - `executor tools search "design"` → find matching tools
   - `executor call open_design 'create_scene' '{json}'` → invoke
   - OR via MCP: call mcp_tool("open_design", "create_scene", {...})
3. Collect result
4. Report back to Chief

### Step 7: Executor CLI Integration
**File:** `/Users/hosski/.hermes/projects/ai-os-stack/orchestrator/executor_integration.py`

**Wrapper functions:**
```python
def call_executor_tool(tool_name: str, method: str, args: Dict) -> Dict:
    """
    Wrapper around: executor call <tool> <method> '{json}'
    Returns result or error
    """
    pass

def list_executor_integrations() -> List[str]:
    """
    Run: executor tools search ""
    Returns all available integrations
    """
    pass
```

---

## Phase 4: Task Execution & Logging (1-2 hours)

### Step 8: Task Execution Loop
**File:** `/Users/hosski/.hermes/projects/ai-os-stack/orchestrator/task_executor.py`

```python
def execute_task_dag(
    task_dag: Dict,
    chief_agent: Agent,
    team: Team
) -> TaskExecutionResult:
    """
    1. Call chief_agent.dispatch(task_dag)
    2. Poll chief_agent for status updates
    3. Collect sub-agent results per tier
    4. Aggregate into final result
    5. Return to Fruvisi + OpenViking
    """
    pass
```

### Step 9: OpenViking Logging
**File:** `/Users/hosski/.hermes/projects/ai-os-stack/orchestrator/hermes_openviking_api.py`

**Store:**
```
viking://user/default/task_execution/{task_id}/
  ├─ dag.json  (original task DAG)
  ├─ tier_0/
  │  ├─ designer_output.json
  │  ├─ editor_output.json
  │  ├─ writer_output.json
  ├─ tier_1/
  │  ├─ refinement_output.json
  ├─ timeline.json  (execution times, parallelization efficiency)
  ├─ qa_result.json  (Fruvisi QA verdict)
```

---

## Phase 5: Fruvisi UI Completion (2-3 hours)

### Step 10: Task Progress Dashboard
**File:** `/Users/hosski/.hermes/plugins/fruvisi/src/components/TaskProgressDashboard.tsx`

**Show:**
- Current tier executing (real-time)
- Sub-agent status (running, completed, error)
- Timeline progress bar
- Estimated completion time
- Parallelization efficiency badge (actual vs. optimal)

### Step 11: Results Display
**File:** `/Users/hosski/.hermes/plugins/fruvisi/src/components/TaskResultsPanel.tsx`

**Show:**
- Per-task output (Designer → scene designs, Editor → refined cuts, Writer → narration)
- Combined deliverable (video ready to export)
- Execution timeline (which tasks ran in parallel, which sequential)
- OpenViking link (audit trail)

---

## Implementation Order (Recommended)

**Day 1 (Today): Foundation**
1. ✅ Grill-Tab-5 skill created
2. Fruvisi TaskCreationModal (grill-tab vs. freehand toggle)
3. TaskDAGRenderer (visualize dependencies)
4. Hermes orchestrator update (dispatch_task_dag function)

**Day 2: Executor Integration**
5. Sub-agent harness (receives role + task, calls Executor)
6. Executor CLI integration wrapper
7. Task execution loop (poll chief, aggregate results)

**Day 3: Polish**
8. OpenViking logging (durable audit trail)
9. Task progress dashboard (real-time UI)
10. Results display (deliverable + timeline)

---

## Testing Checklist

- [ ] Grill-Tab-5 generates valid task DAG
- [ ] Fruvisi renders DAG with dependencies
- [ ] Chief agent spawns sub-agents simultaneously
- [ ] Sub-agents call Executor tools successfully
- [ ] Results aggregated and returned to Fruvisi
- [ ] OpenViking stores execution timeline
- [ ] Parallelization efficiency measured (actual vs. optimal)
- [ ] 3-5 task project completes in <N minutes

---

## Success Metrics

✅ **Grill-Tab-5 → Task DAG**: User describes task in freehand → AI outputs structured 3-5 task list in <5 min

✅ **Fruvisi Visualization**: DAG rendered with dependency arrows + parallelization hints + timeline estimate

✅ **Chief Dispatch**: Hermes spawns Chief who spawns 3 sub-agents simultaneously (Designer, Editor, Writer) on M5 P cores

✅ **Executor Integration**: Each sub-agent calls Executor CLI tool successfully, returns result

✅ **1.5-2× Speedup**: 5-min video series completes in ~1.5× the time of sequential execution (not 3×)

✅ **Durable Audit Trail**: Full execution DAG stored in OpenViking with timestamps + sub-agent outputs

---

## Git Commits (as we go)

```
feat: grill-tab-5 skill — 5-question task breakdown

feat: fruvisi task creation modal — grill-tab vs. freehand toggle

feat: hermes orchestrator task DAG dispatch with parallelization

feat: executor integration — sub-agents call tools via CLI/MCP

feat: openviking audit logging — full execution DAG + timeline

feat: fruvisi task progress dashboard — real-time sub-agent monitoring
```

---

## Let's Rock & Roll 🎸

Ship order:
1. Test grill-tab-5 with a real task
2. Wire Fruvisi TaskCreationModal
3. Build Chief agent
4. Executor integration
5. Done!

Ready?
