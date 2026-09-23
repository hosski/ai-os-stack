"""
Hermes Backend Orchestrator v2: Executor-driven parallel dispatch.

Executor (port 8004) is the parallel agent engine:
  - Spawns independent workers per domain (Video, Law, Architecture, Homesteading)
  - All agents run in parallel, not sequentially
  - Each agent: task execution → Fruvisi QA → rework loops
  - Results flow back through OpenViking

Flow:
  /profile-setup → orchestration_cli_command.py → dispatch_parallel_tasks()
    → Executor (JSON-RPC) spawns 4 domain agents in parallel
    → Each agent processes independently
    → Fruvisi QA validates results
    → Rework or escalation as needed
"""

from typing import Optional, Any, List, Dict
import asyncio
from datetime import datetime
import httpx

from profile_input import DomainProfile
from hermes_openviking_api import (
    TaskObject,
    store_task_state,
    fetch_task_state,
    store_qa_result,
    QAResult,
)

# Executor is the parallel dispatch engine
EXECUTOR_PORT = 8004
EXECUTOR_BASE = f"http://localhost:{EXECUTOR_PORT}"

# Domain → primary model mapping
DOMAIN_MODELS = {
    "video": "ltx-2.5",
    "law": "qwen-3.8",
    "architecture": "claude-opus",
    "homesteading": "llama-2",
}


class ExecutorOrchestrator:
    """Routes tasks to Executor for parallel agent dispatch."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=EXECUTOR_BASE, timeout=30.0)
        self.active_tasks: Dict[str, TaskObject] = {}
    
    async def dispatch_task(
        self,
        domain_profile: DomainProfile,
        task_type: str,
        input_payload: Dict[str, Any],
    ) -> str:
        """Dispatch single task to Executor.
        
        Args:
            domain_profile: Domain configuration
            task_type: "generate", "analyze", "design", "synthesize"
            input_payload: Task input data
        
        Returns:
            task_id from Executor
        """
        task_id = f"task_{datetime.utcnow().isoformat()}"
        
        task: TaskObject = {
            "task_id": task_id,
            "status": "pending",
            "result_payload": None,
            "retry_count": 0,
            "priority": 1,
            "domain_profile": domain_profile["domain"],
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        
        # Store in OpenViking
        await store_task_state(task)
        self.active_tasks[task_id] = task
        
        # Send to Executor via JSON-RPC
        rpc_payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "executor.dispatch",
            "params": [{
                "task_id": task_id,
                "domain": domain_profile["domain"],
                "task_type": task_type,
                "input_payload": input_payload,
                "models": {
                    "primary": domain_profile["primary_model"],
                    "aux": domain_profile["aux_models"],
                },
            }]
        }
        
        try:
            response = await self.client.post("/rpc", json=rpc_payload)
            result = response.json()
            
            if "result" in result:
                return task_id
            else:
                raise RuntimeError(f"Executor error: {result.get('error', 'unknown')}")
        
        except Exception as e:
            raise RuntimeError(f"Failed to dispatch to Executor: {e}")
    
    async def dispatch_parallel_tasks(
        self,
        profiles: List[DomainProfile],
        task_specs: List[Dict[str, Any]],
    ) -> List[str]:
        """Dispatch multiple domain tasks in parallel.
        
        PARALLEL EXECUTION: All domains run simultaneously via Executor.
        
        Args:
            profiles: List of domain profiles
            task_specs: List of task specs (task_type, input_payload)
        
        Returns:
            List of task_ids (all dispatched in parallel)
        """
        tasks = [
            self.dispatch_task(profile, spec["task_type"], spec["input_payload"])
            for profile, spec in zip(profiles, task_specs)
        ]
        
        # All tasks dispatched to Executor in parallel
        return await asyncio.gather(*tasks)
    
    async def check_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Poll Executor for task status."""
        rpc_payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "executor.status",
            "params": [task_id]
        }
        
        try:
            response = await self.client.post("/rpc", json=rpc_payload)
            return response.json().get("result")
        except Exception:
            return None
    
    async def process_qa_verdict(self, task_id: str, verdict: Dict[str, Any]) -> None:
        """Process QA verdict from Fruvisi.
        
        Logic:
          - If passed: mark complete
          - If failed & retries < 3: rework (dispatch again)
          - If failed & retries >= 3: escalate (human review)
        """
        task = await fetch_task_state(task_id)
        if not task:
            return
        
        if verdict["passed"]:
            task["status"] = "completed"
        else:
            if task["retry_count"] < 3:
                task["status"] = "pending"
                task["retry_count"] += 1
                # Re-dispatch to Executor
                await self.dispatch_task(
                    {"domain": task["domain_profile"], "primary_model": "default", "aux_models": []},
                    "rework",
                    verdict.get("feedback", {}),
                )
            else:
                task["status"] = "failed"
        
        # Store updated task
        await store_task_state(task)
        
        # Store QA result for audit
        qa_result: QAResult = {
            "task_id": task_id,
            "passed": verdict["passed"],
            "feedback": verdict.get("feedback", ""),
            "checked_at": datetime.utcnow().isoformat() + "Z",
        }
        await store_qa_result(qa_result)


# Global orchestrator singleton
_orchestrator: Optional[ExecutorOrchestrator] = None


def get_orchestrator() -> ExecutorOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ExecutorOrchestrator()
    return _orchestrator
