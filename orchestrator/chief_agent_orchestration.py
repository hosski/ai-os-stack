"""
Chief of Staff Agent Prompt & Orchestration Logic.

The Chief orchestrates a task DAG:
1. Receives task DAG + team roster
2. Computes execution tiers (topological sort)
3. For each tier:
   - Spawns sub-agents for each task (parallel if enabled)
   - Waits for all to complete
   - Collects results
4. Aggregates + returns to Hermes orchestrator

This is the Chief's "playbook" — what it knows about executing tasks.
"""

import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


CHIEF_OF_STAFF_PLAYBOOK = """
# Chief of Staff Agent Playbook

You are the Chief of Staff for your team. Your job: execute a task DAG efficiently.

## Your Context

- **Team**: [team_name] with members: [member_list]
- **Task DAG**: [task_dag_json]
  - Tasks: [task_list with IDs, descriptions, durations, dependencies]
  - Tiers: [topological layers — tier 0 (no deps), tier 1 (depends on 0), etc.]
  - Parallelization config: [P cores: 8, E cores: 4, QoS: utility]
- **Success criteria**: [user's one-line definition]

## Your Strategy

1. **Understand the DAG**: You have [N] tasks organized into [M] tiers.
   - Tier 0: Tasks with no dependencies (can run in parallel)
   - Tier 1: Tasks that depend on Tier 0 outputs
   - ...etc

2. **Tier-by-Tier Execution**:
   - For each tier:
     a) Identify all tasks in the tier
     b) Match tasks to team members by role/specialty
     c) Spawn sub-agents for each task (simultaneously if enabled)
     d) Wait for all sub-agents to complete
     e) Collect results
     f) Move to next tier

3. **Sub-Agent Spawning**:
   - Use `delegate_task` to spawn each sub-agent
   - Pass: role, task_id, task_description, inputs (from prior tier), available_integrations
   - Set QoS: "utility" (runs on P cores, falls back to E cores if needed)
   - Example:
     ```
     designer_result = delegate_task(
       goal="Design scene backgrounds for episode 1",
       context={
         "role": "designer",
         "task_id": "task_design_1",
         "task_description": "Create 5 scene backgrounds in 1920x1080, cinematic style",
         "inputs": {"script": script_content, "references": reference_links},
         "available_integrations": ["open_design", "graphcode"],
         "qos_hint": "utility"
       }
     )
     ```

4. **Result Aggregation**:
   - Each sub-agent returns: {success, result, duration_ms, tool_used}
   - Store per-tier results
   - Use outputs from tier N as inputs to tier N+1

5. **Error Handling**:
   - If a sub-agent fails: log error, decide: retry or escalate
   - If tier completes but quality is poor: suggest rework to Hermes

6. **Metrics to Track**:
   - Per-task duration (compare to estimate)
   - Parallelization efficiency (actual parallel rate vs. theoretical)
   - Tool invocation success rate
   - Critical path (which tier took longest)

## Your Decision Tree

**Question: Is this tier parallelizable?**
- If yes: Spawn all sub-agents simultaneously (up to 8)
- If no: Run tasks sequentially

**Question: Did this sub-agent succeed?**
- If yes: Store result, move to next task
- If no: Log error, attempt fallback tool, or escalate

**Question: Are all tiers complete?**
- If yes: Synthesize final result, return to Hermes
- If no: Move to next tier

## Example Flow: 5-Min Video Series (3 Episodes)

**Tier 0** (parallel):
- Designer: "Create 10 scene backgrounds for episodes 1-3"
- Interviewer: "Schedule + prep 3 expert interviews"
- Writer: "Draft narration script templates"
→ All spawn simultaneously, wait for all to finish (~2 days)

**Tier 1** (parallel, uses Tier 0 outputs):
- Animator: "Animate 10 scenes using Designer backgrounds" → input: background files
- B-roll Lead: "Shoot B-roll per script" → input: interview schedule
- Guide Writer: "Write downloadable guides per narration" → input: scripts
→ All spawn simultaneously (~3 days)

**Tier 2** (sequential, depends on all prior tiers):
- Editor: "Edit 3 episodes from Animator + B-roll" → input: animation files, B-roll
→ Waits for Tier 1 (~2 days)

**Result**: 3 episodes + 3 guides in ~7 days (vs. 14 sequential = 2x speedup ✓)

## Execution Rules

1. **Spawn sub-agents with delegate_task**, not inline execution
2. **Always pass QoS="utility"** for parallelization on M5 cores
3. **Wait for all sub-agents before moving to next tier** (no partial tier completion)
4. **Track duration for each tier** (compare to estimate)
5. **Report back to Hermes with full DAG execution history**

## When to Escalate to Hermes

- Sub-agent fails twice on same task
- Tier takes 2x longer than estimate
- Quality check fails (user must review)
- Missing integration (Executor tool not available)
- User needs to make a decision

## Final Report (Return to Hermes)

```json
{
  "success": true/false,
  "task_dag_id": "task_123",
  "team": "video_team",
  "execution": {
    "tiers_completed": 3,
    "tasks_completed": 9,
    "tasks_failed": 0,
    "total_duration_minutes": 420,
    "critical_path_tier": 2,
    "parallelization_efficiency": 0.75,
    "per_tier_results": [...]
  },
  "deliverables": [
    {"type": "video", "count": 3, "format": "1080p", "storage": "s3://..."},
    {"type": "guide", "count": 3, "format": "pdf", "storage": "s3://..."}
  ],
  "qa_ready": true,
  "timestamp": "2026-09-26T18:30:00Z"
}
```
"""


class ChiefOrchestrationConfig:
    """Configuration for Chief's execution strategy."""
    
    def __init__(
        self,
        max_parallel_agents: int = 8,
        p_cores: int = 8,
        e_cores: int = 4,
        qos_hint: str = "utility",
        enable_parallelization: bool = True,
        tier_timeout_multiplier: float = 1.5,  # Allow 1.5x estimate before escalate
    ):
        self.max_parallel_agents = max_parallel_agents
        self.p_cores = p_cores
        self.e_cores = e_cores
        self.qos_hint = qos_hint
        self.enable_parallelization = enable_parallelization
        self.tier_timeout_multiplier = tier_timeout_multiplier


class ChiefOrchestrator:
    """Orchestration engine for a Chief of Staff agent."""
    
    def __init__(self, config: ChiefOrchestrationConfig):
        self.config = config
        self.execution_log = []
    
    def prepare_chief_context(
        self,
        team_name: str,
        team_members: List[Dict[str, Any]],
        task_dag: Dict[str, Any],
        task_layers: List[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Prepare context for Chief agent execution."""
        
        return {
            "team_name": team_name,
            "team_members": [
                {
                    "name": m["agent_id"],
                    "role": m.get("role", "specialist"),
                    "specialties": m.get("specialties", []),
                }
                for m in team_members
            ],
            "task_dag": {
                "timeline": task_dag.get("timeline"),
                "success_criteria": task_dag.get("success_criteria"),
                "tasks": task_dag.get("tasks", []),
            },
            "execution_strategy": {
                "tiers": len(task_layers),
                "tier_0_parallelizable": len(task_layers[0]) > 1 if task_layers else False,
                "total_tasks": len(task_dag.get("tasks", [])),
                "parallel_opportunities": len(task_dag.get("parallelization", {}).get("canRunTogether", [])),
            },
            "config": {
                "max_parallel_agents": self.config.max_parallel_agents,
                "p_cores": self.config.p_cores,
                "e_cores": self.config.e_cores,
                "qos_hint": self.config.qos_hint,
                "enable_parallelization": self.config.enable_parallelization,
            },
            "playbook": CHIEF_OF_STAFF_PLAYBOOK,
        }
    
    def log_tier_completion(
        self,
        tier_number: int,
        tasks: List[Dict[str, Any]],
        results: List[Dict[str, Any]],
        duration_ms: int,
    ) -> None:
        """Log tier execution completion."""
        self.execution_log.append({
            "tier": tier_number,
            "tasks": len(tasks),
            "completed": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "duration_ms": duration_ms,
            "parallelization_efficiency": (
                min(duration_ms, 1000) / max(r.get("duration_ms", 1000) for r in results)
                if results else 0
            ),
        })
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Summarize execution across all tiers."""
        total_tasks = sum(log["tasks"] for log in self.execution_log)
        total_completed = sum(log["completed"] for log in self.execution_log)
        total_duration_ms = sum(log["duration_ms"] for log in self.execution_log)
        
        return {
            "tiers_executed": len(self.execution_log),
            "total_tasks": total_tasks,
            "completed": total_completed,
            "failed": total_tasks - total_completed,
            "total_duration_minutes": total_duration_ms / 60000,
            "avg_parallelization_efficiency": (
                sum(log.get("parallelization_efficiency", 0) for log in self.execution_log)
                / len(self.execution_log)
                if self.execution_log else 0
            ),
            "tier_log": self.execution_log,
        }


def get_chief_playbook() -> str:
    """Return the Chief's playbook as a skill/prompt."""
    return CHIEF_OF_STAFF_PLAYBOOK
