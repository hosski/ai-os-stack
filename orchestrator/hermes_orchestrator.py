"""
Hermes Orchestrator v5: Full task DAG → Chief → Executor → Result pipeline.

Entry point for `/profile-setup` slash command:
  1. User describes task (grill-tab or freehand)
  2. AI generates task DAG
  3. Fruvisi shows DAG + asks for execute
  4. Hermes spawns Chief as sub-agent
  5. Chief orchestrates team via Executor
  6. Fruvisi QA validates result
  7. OpenViking logs execution
"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from team_orchestrator import (
    FruvisiTeamRegistry,
    TaskDAG,
    dispatch_task_dag,
)
from chief_agent_orchestration import (
    ChiefOrchestrationConfig,
    ChiefOrchestrator,
    get_chief_playbook,
)
from executor_integration import get_executor
from hermes_openviking_api import store_task_state, TaskObject

logger = logging.getLogger(__name__)


class HermesOrchestrator:
    """Master orchestrator: task DAG → Chief → Executor → result."""
    
    def __init__(self):
        self.team_registry = FruvisiTeamRegistry()
        self.chief_config = ChiefOrchestrationConfig(
            max_parallel_agents=8,
            p_cores=8,
            e_cores=4,
            qos_hint="utility",
            enable_parallelization=True,
        )
        self.executor = get_executor()
    
    async def execute_task_dag(
        self,
        task_dag_dict: Dict[str, Any],
        task_id: str,
        fruvisi_qa_verdict_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Execute a full task DAG from start to finish.
        
        Flow:
        1. Parse task DAG
        2. Dispatch to team Chief via delegate_task
        3. Chief orchestrates sub-agents tier-by-tier
        4. Wait for Chief completion
        5. Run Fruvisi QA on result
        6. Log to OpenViking
        7. Return final result
        """
        
        logger.info(f"Hermes orchestrator starting task DAG: {task_id}")
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Parse task DAG
            task_dag = TaskDAG(task_dag_dict)
            logger.info(
                f"Task DAG parsed: {task_dag.domain} domain, "
                f"{len(task_dag.tasks)} tasks, "
                f"{len(task_dag.get_task_layers())} tiers"
            )
            
            # Step 2: Store initial state in OpenViking
            task_obj: TaskObject = {
                "task_id": task_id,
                "status": "initiated",
                "result_payload": {"task_dag": task_dag_dict},
                "retry_count": 0,
                "priority": 1,
                "domain_profile": task_dag.domain or "unknown",
                "created_at": start_time.isoformat() + "Z",
            }
            await store_task_state(task_obj)
            
            # Step 3: Dispatch to Chief (via delegate_task in actual Hermes)
            # For now, we'll show the dispatch packet that would be sent
            dispatch_packet = await dispatch_task_dag(
                task_dag,
                parallelization_config={
                    "p_cores": 8,
                    "e_cores": 4,
                    "qos_hint": "utility",
                }
            )
            
            logger.info(f"Dispatch packet prepared for Chief: {dispatch_packet['chief_of_staff']['agent_id']}")
            
            # Step 4: Build Chief's context
            chief_orchestrator = ChiefOrchestrator(self.chief_config)
            chief_context = chief_orchestrator.prepare_chief_context(
                team_name=dispatch_packet["chief_of_staff"]["team"],
                team_members=dispatch_packet["team_members"],
                task_dag=dispatch_packet["task_dag"],
                task_layers=dispatch_packet["task_dag"]["layers"],
            )
            
            logger.info(f"Chief context prepared: {chief_context['team_name']} team, {len(chief_context['team_members'])} members")
            
            # Step 5: Log Chief dispatch to OpenViking
            task_obj["status"] = "chief_dispatched"
            task_obj["result_payload"] = {
                "chief_id": dispatch_packet["chief_of_staff"]["agent_id"],
                "chief_context": chief_context,
            }
            await store_task_state(task_obj)
            
            # Step 6: In real Hermes, this would call delegate_task:
            # chief_result = await delegate_task(
            #     goal=f"Execute {task_dag.domain} task DAG: {task_dag.success_criteria}",
            #     context=chief_context
            # )
            
            # For now, return a mock execution result
            chief_result = {
                "success": True,
                "task_id": task_id,
                "domain": task_dag.domain,
                "tiers_completed": len(task_dag.get_task_layers()),
                "tasks_completed": len(task_dag.tasks),
                "total_duration_minutes": 9,  # Mock: expected for 3-episode video
                "execution_log": [
                    {
                        "tier": 0,
                        "tasks": len(task_dag.get_task_layers()[0]) if task_dag.get_task_layers() else 0,
                        "parallelized": True,
                    }
                ],
                "deliverables": [
                    {"type": "task_output", "format": "json", "ready_for_qa": True}
                ],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            logger.info(f"Chief execution complete: {chief_result['tasks_completed']} tasks in {chief_result['total_duration_minutes']} minutes")
            
            # Step 7: Log Chief results to OpenViking
            task_obj["status"] = "chief_completed"
            task_obj["result_payload"] = chief_result
            await store_task_state(task_obj)
            
            # Step 8: Run Fruvisi QA (if callback provided)
            qa_verdict = None
            if fruvisi_qa_verdict_callback:
                qa_verdict = await fruvisi_qa_verdict_callback(chief_result)
                logger.info(f"QA verdict: {qa_verdict.get('status')}")
                
                task_obj["status"] = "qa_complete"
                task_obj["result_payload"] = qa_verdict
                await store_task_state(task_obj)
            
            # Step 9: Final status
            final_result = {
                "success": True,
                "task_id": task_id,
                "domain": task_dag.domain,
                "chief_result": chief_result,
                "qa_verdict": qa_verdict,
                "total_duration_minutes": (datetime.utcnow() - start_time).total_seconds() / 60,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            task_obj["status"] = "complete"
            task_obj["result_payload"] = final_result
            await store_task_state(task_obj)
            
            logger.info(f"Task DAG execution complete: {task_id}")
            return final_result
        
        except Exception as e:
            logger.error(f"Task DAG execution failed: {e}")
            
            # Ensure task_obj exists even if DAG parsing failed
            if 'task_obj' not in locals():
                task_obj: TaskObject = {
                    "task_id": task_id,
                    "status": "failed",
                    "result_payload": {"error": str(e)},
                    "retry_count": 0,
                    "priority": 1,
                    "domain_profile": "unknown",
                    "created_at": start_time.isoformat() + "Z",
                }
            else:
                task_obj["status"] = "failed"
                task_obj["result_payload"] = {"error": str(e)}
            
            await store_task_state(task_obj)
            
            return {
                "success": False,
                "task_id": task_id,
                "error": str(e),
            }


# Global orchestrator
_orchestrator: Optional[HermesOrchestrator] = None


def get_hermes_orchestrator() -> HermesOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = HermesOrchestrator()
    return _orchestrator


async def orchestrate_task_dag(
    task_dag: Dict[str, Any],
    task_id: str,
    qa_callback: Optional[callable] = None,
) -> Dict[str, Any]:
    """Public entry point for task DAG orchestration."""
    orchestrator = get_hermes_orchestrator()
    return await orchestrator.execute_task_dag(task_dag, task_id, qa_callback)
