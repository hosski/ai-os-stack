"""
Hermes Backend Orchestrator: Core routing and task dispatch for AI OS Stack.

Responsibilities:
  1. Accept domain profiles from CLI
  2. Dispatch tasks to plugins (GraphCode, Executor, Open Design) via MCP
  3. Communicate with OpenViking for state management
  4. Route QA results from Fruvisi and trigger rework loops
  5. Coordinate parallel agent execution

Entry points:
  - HermesOrchestrator.dispatch_task()
  - HermesOrchestrator.process_qa_verdict()
"""

from typing import Optional, Any, Union, Dict
import asyncio
from datetime import datetime
import uuid
import logging

from profile_input import DomainProfile
from hermes_openviking_api import (
    TaskObject,
    store_task_state,
    fetch_task_state,
    store_qa_result,
    QAResult,
)
from mcp_plugin_endpoints import (
    get_plugin_registry,
    PluginType,
)

logger = logging.getLogger(__name__)


class HermesOrchestrator:
    """Core orchestrator for AI OS Stack backend."""
    
    def __init__(self):
        self.plugin_registry = get_plugin_registry()
        self.active_tasks: Dict[str, TaskObject] = {}
    
    async def dispatch_task(
        self,
        domain_profile: DomainProfile,
        task_type: str,  # e.g., "generate", "analyze", "refactor"
        input_payload: dict[str, Any],
    ) -> str:
        """
        Dispatch a task through the orchestration pipeline.
        
        Args:
            domain_profile: Domain configuration (video, law, etc.)
            task_type: Type of task to perform
            input_payload: Input data for the task
        
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        
        # Create task object
        task: TaskObject = {
            "task_id": task_id,
            "status": "pending",
            "result_payload": None,
            "retry_count": 0,
            "priority": 1,
            "domain_profile": domain_profile["domain"],
            "created_at": now,
        }
        
        # Store in OpenViking
        await store_task_state(task)
        self.active_tasks[task_id] = task
        
        logger.info(f"Dispatched task {task_id} for domain {domain_profile['domain']}")
        
        # Route to appropriate plugin based on task_type and domain
        plugin_target = self._route_to_plugin(task_type, domain_profile["domain"])
        if plugin_target:
            await self._invoke_plugin(
                task_id,
                plugin_target,
                task_type,
                input_payload,
                domain_profile,
            )
        
        return task_id
    
    async def process_qa_verdict(self, task_id: str, verdict: dict[str, Any]) -> None:
        """
        Process QA verdict from Fruvisi and handle routing.
        
        Logic:
          - If passed: mark complete
          - If failed & retries < max: rework (re-dispatch)
          - If failed & retries >= max: escalate (human review)
        """
        task = await fetch_task_state(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return
        
        if verdict["passed"]:
            task["status"] = "completed"
            logger.info(f"Task {task_id} passed QA")
        else:
            next_action = verdict.get("next_action")
            if next_action == "rework":
                task["status"] = "pending"
                task["retry_count"] += 1
                logger.info(f"Task {task_id} rework scheduled (retry {task['retry_count']})")
            elif next_action == "escalate":
                task["status"] = "failed"
                logger.warning(f"Task {task_id} escalated for human review")
        
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
    
    def _route_to_plugin(self, task_type: str, domain: str) -> Optional[PluginType]:
        """
        Route task to appropriate plugin based on type and domain.
        
        Examples:
          - task_type="generate", domain="video" -> EXECUTOR
          - task_type="analyze", domain="law" -> GRAPHCODE
          - task_type="design", domain="architecture" -> OPEN_DESIGN
        """
        routing_map = {
            ("generate", "video"): PluginType.EXECUTOR,
            ("analyze", "law"): PluginType.GRAPHCODE,
            ("design", "architecture"): PluginType.OPEN_DESIGN,
            ("synthesize", "homesteading"): PluginType.EXECUTOR,
        }
        
        return routing_map.get((task_type, domain))
    
    async def _invoke_plugin(
        self,
        task_id: str,
        plugin_type: PluginType,
        task_type: str,
        input_payload: dict[str, Any],
        domain_profile: DomainProfile,
    ) -> None:
        """Invoke a plugin via MCP JSON-RPC."""
        plugin = self.plugin_registry.get_plugin(plugin_type)
        if not plugin or not plugin.enabled:
            logger.error(f"Plugin {plugin_type.value} not available")
            return
        
        # Build RPC call
        method = f"{plugin_type.value}.{task_type}"
        params = {
            "task_id": task_id,
            "input": input_payload,
            "domain": domain_profile["domain"],
            "models": {
                "primary": domain_profile["primary_model"],
                "aux": domain_profile["aux_models"],
            },
        }
        
        # Call plugin
        result = await self.plugin_registry.call_plugin(
            plugin_type,
            method,
            params,
            request_id=task_id,
        )
        
        if result:
            # Update task with result
            task = self.active_tasks.get(task_id)
            if task:
                task["status"] = "running"
                task["result_payload"] = result
                await store_task_state(task)
            logger.info(f"Plugin {plugin_type.value} produced result for task {task_id}")
        else:
            logger.error(f"Plugin {plugin_type.value} failed for task {task_id}")


# Global orchestrator singleton
_orchestrator: Optional[HermesOrchestrator] = None


def get_orchestrator() -> HermesOrchestrator:
    """Get or create global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HermesOrchestrator()
    return _orchestrator
