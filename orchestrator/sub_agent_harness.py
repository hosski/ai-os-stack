"""
Sub-Agent Harness: Each sub-agent receives a task + calls Executor tools.

Sub-agents are spawned by the Chief via delegate_task with:
  - role: "designer" | "editor" | "writer" | etc.
  - task_id: unique task identifier
  - task_description: what to do
  - inputs: outputs from prior tier (if dependencies)
  - available_integrations: list of Executor tools to use
  - qos_hint: "utility" for parallelization
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from executor_integration import get_executor, ExecutorIntegration

logger = logging.getLogger(__name__)


class SubAgentRole(str, Enum):
    """Team member roles."""
    DESIGNER = "designer"
    EDITOR = "editor"
    WRITER = "writer"
    RESEARCHER = "researcher"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"


class SubAgentContext:
    """Context passed to a sub-agent by the Chief."""
    
    def __init__(
        self,
        role: str,
        task_id: str,
        task_description: str,
        team_name: str,
        inputs: Optional[Dict[str, Any]] = None,
        available_integrations: Optional[List[str]] = None,
        qos_hint: str = "utility",
    ):
        self.role = role
        self.task_id = task_id
        self.task_description = task_description
        self.team_name = team_name
        self.inputs = inputs or {}
        self.available_integrations = available_integrations or []
        self.qos_hint = qos_hint
        self.start_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "team_name": self.team_name,
            "inputs": self.inputs,
            "available_integrations": self.available_integrations,
            "qos_hint": self.qos_hint,
        }


class SubAgentExecutor:
    """Executes a sub-agent task using Executor integrations."""
    
    def __init__(self, executor: Optional[ExecutorIntegration] = None):
        self.executor = executor or get_executor()
    
    async def execute_task(self, context: SubAgentContext) -> Dict[str, Any]:
        """
        Execute a sub-agent task:
        1. Parse task description + inputs
        2. Determine which Executor tool to use
        3. Call executor.call_tool()
        4. Return result + metrics
        """
        logger.info(
            f"Sub-Agent executing: {context.role} / {context.task_id} / {context.task_description}"
        )
        
        start = datetime.utcnow()
        
        # Step 1: Analyze task + choose tool
        tool_choice = await self._choose_tool(context)
        if not tool_choice["success"]:
            logger.warning(f"No suitable tool found for task {context.task_id}")
            return {
                "success": False,
                "error": "No suitable tool found",
                "role": context.role,
                "task_id": context.task_id,
                "duration_ms": (datetime.utcnow() - start).total_seconds() * 1000,
            }
        
        integration, method, args = (
            tool_choice["integration"],
            tool_choice["method"],
            tool_choice["args"],
        )
        
        # Step 2: Call executor
        exec_result = await self.executor.call_tool(integration, method, args)
        
        if not exec_result.get("success"):
            logger.error(f"Executor call failed: {exec_result.get('error')}")
            return {
                "success": False,
                "error": exec_result.get("error"),
                "role": context.role,
                "task_id": context.task_id,
                "tool": f"{integration}:{method}",
                "duration_ms": (datetime.utcnow() - start).total_seconds() * 1000,
            }
        
        # Step 3: Return result
        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        
        return {
            "success": True,
            "role": context.role,
            "task_id": context.task_id,
            "task_description": context.task_description,
            "tool_used": f"{integration}:{method}",
            "result": exec_result.get("result"),
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    
    async def _choose_tool(self, context: SubAgentContext) -> Dict[str, Any]:
        """Heuristically choose which Executor tool to use based on role + task."""
        
        # Role → default tool mapping
        role_tool_map = {
            SubAgentRole.DESIGNER.value: ("open_design", "create_design"),
            SubAgentRole.EDITOR.value: ("graphcode", "edit_node"),
            SubAgentRole.WRITER.value: ("text_generation", "generate_text"),
            SubAgentRole.RESEARCHER.value: ("graphcode", "search_knowledge"),
            SubAgentRole.REVIEWER.value: ("graphcode", "review_node"),
        }
        
        # Get default tool for role
        if context.role not in role_tool_map:
            return {"success": False, "error": f"Unknown role: {context.role}"}
        
        integration, method = role_tool_map[context.role]
        
        # Check if tool is available
        if context.available_integrations and integration not in context.available_integrations:
            logger.warning(f"Tool {integration} not available, searching alternatives...")
            # Fallback: search for alternative
            available = await self.executor.search_tools(context.role)
            if available:
                integration = available[0]
        
        # Construct args from task description + inputs
        args = {
            "description": context.task_description,
            "role": context.role,
            "task_id": context.task_id,
            "inputs": context.inputs,
        }
        
        return {
            "success": True,
            "integration": integration,
            "method": method,
            "args": args,
        }


async def run_sub_agent(context: SubAgentContext) -> Dict[str, Any]:
    """Synchronous entry point for a sub-agent (called by Chief via delegate_task)."""
    executor_service = SubAgentExecutor()
    return await executor_service.execute_task(context)
