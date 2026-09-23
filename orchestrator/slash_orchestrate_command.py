"""
/orchestrate Slash Command: Direct entry point for task DAG execution from Hermes CLI.

Usage:
  /orchestrate --domain video --file /path/to/task_dag.json
  /orchestrate --domain video --inline '{"tasks": [...]}'
  
Or use /profile-setup for interactive grill-tab-5 setup.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class OrchestrationSlashCommand:
    """Handler for /orchestrate slash command."""
    
    def __init__(self):
        pass
    
    async def execute(
        self,
        domain: str,
        file_path: Optional[str] = None,
        inline_dag: Optional[str] = None,
        interactive: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute orchestration from slash command.
        
        Args:
            domain: "video", "law", "architecture", "homesteading"
            file_path: Path to task_dag.json
            inline_dag: JSON string with task DAG
            interactive: Run grill-tab-5 first
        
        Returns:
            Execution result with OpenViking link
        """
        
        # Step 1: Get task DAG
        task_dag = None
        
        if interactive:
            # Run grill-tab-5 skill (user answers 5 questions)
            logger.info("Starting grill-tab-5 interrogation...")
            task_dag = await self._run_grill_tab_5(domain)
        
        elif file_path:
            # Load from file
            logger.info(f"Loading task DAG from {file_path}")
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Task DAG file not found: {file_path}")
            
            with open(path) as f:
                task_dag = json.load(f)
        
        elif inline_dag:
            # Parse inline JSON
            logger.info("Parsing inline task DAG")
            task_dag = json.loads(inline_dag)
        
        else:
            raise ValueError("Must provide --file, --inline, or --interactive")
        
        # Step 2: Validate DAG
        if not task_dag.get("domain"):
            task_dag["domain"] = domain
        
        if not task_dag.get("tasks"):
            raise ValueError("Task DAG must contain 'tasks' array")
        
        logger.info(f"Task DAG validated: {len(task_dag['tasks'])} tasks")
        
        # Step 3: Execute orchestration
        from hermes_orchestrator import orchestrate_task_dag
        from openviking_audit_dashboard import create_audit_dashboard_ascii
        
        result = await orchestrate_task_dag(
            task_dag=task_dag,
            task_id=f"cmd_{datetime.utcnow().timestamp():.0f}",
        )
        
        if not result["success"]:
            raise RuntimeError(f"Orchestration failed: {result.get('error')}")
        
        # Step 4: Render audit dashboard
        events = [
            {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "state": "complete",
                "payload": result,
            }
        ]
        
        dashboard = create_audit_dashboard_ascii(result["task_id"], events)
        
        return {
            "success": True,
            "task_id": result["task_id"],
            "result": result,
            "dashboard": dashboard,
            "openviking_uri": f"viking://user/default/tasks/{result['task_id']}/",
        }
    
    async def _run_grill_tab_5(self, domain: str) -> Dict[str, Any]:
        """Run grill-tab-5 skill to generate task DAG."""
        
        # This would call the grill-tab-5 skill via Hermes' skill engine
        # For now, return a mock DAG
        logger.info(f"Running grill-tab-5 for domain: {domain}")
        
        return {
            "domain": domain,
            "timeline": "9 days",
            "successCriteria": "Deliverables ready for QA",
            "tasks": [
                {
                    "id": f"task_1",
                    "name": "Research & Planning",
                    "duration": "2 days",
                    "dependsOn": [],
                    "owner": "researcher",
                    "type": "cpu"
                },
            ],
            "parallelization": {
                "canRunTogether": [],
                "mustBeSequential": [],
                "expectedSpeedup": 1.0
            }
        }


async def slash_orchestrate(
    domain: str,
    file_path: Optional[str] = None,
    inline_dag: Optional[str] = None,
    interactive: bool = False,
) -> str:
    """
    Slash command handler for /orchestrate.
    
    Returns formatted result for chat output.
    """
    
    handler = OrchestrationSlashCommand()
    
    try:
        result = await handler.execute(
            domain=domain,
            file_path=file_path,
            inline_dag=inline_dag,
            interactive=interactive,
        )
        
        # Format output
        output = f"""
✅ **Orchestration Complete**

**Task ID:** `{result['task_id']}`

**Result:**
{json.dumps(result['result'], indent=2)}

**Audit Dashboard:**
```
{result['dashboard']}
```

**OpenViking:** {result['openviking_uri']}
"""
        
        return output
    
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        return f"❌ **Orchestration Failed:** {str(e)}"


# Hermes slash command registration
SLASH_COMMAND_META = {
    "name": "orchestrate",
    "description": "Execute a task DAG with Hermes orchestrator",
    "options": [
        {
            "name": "domain",
            "description": "Team domain: video, law, architecture, homesteading",
            "required": True,
        },
        {
            "name": "file",
            "description": "Path to task_dag.json file",
            "required": False,
        },
        {
            "name": "inline",
            "description": "Inline JSON task DAG",
            "required": False,
        },
        {
            "name": "interactive",
            "description": "Run grill-tab-5 first (interactive)",
            "required": False,
        },
    ],
}


async def handle_slash_orchestrate(**kwargs) -> str:
    """Handler called by Hermes when user runs /orchestrate."""
    return await slash_orchestrate(**kwargs)


from datetime import datetime
