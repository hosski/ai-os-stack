"""
Fruvisi REST Hook: Bridges Fruvisi React UI to Hermes Orchestrator.

When user clicks "Execute Task Breakdown" in TaskDAGRenderer:
  1. Fruvisi React sends task_dag.json to this endpoint
  2. Hermes orchestrator spawns Chief via delegate_task
  3. Stream execution progress back to Fruvisi UI
  4. Return final result + OpenViking link
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

app = FastAPI(title="Hermes Orchestrator API", version="1.0")

# Import orchestrator
from hermes_orchestrator import orchestrate_task_dag, get_hermes_orchestrator


class ExecutionTracker:
    """Tracks task execution for streaming updates."""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.events = []
        self.lock = asyncio.Lock()
    
    async def add_event(self, state: str, payload: Dict[str, Any]) -> None:
        """Add execution event."""
        async with self.lock:
            event = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "state": state,
                "payload": payload,
            }
            self.events.append(event)
            logger.info(f"[{self.task_id}] {state}")
    
    async def stream_events(self):
        """Stream events as SSE (Server-Sent Events)."""
        last_index = 0
        while True:
            async with self.lock:
                for event in self.events[last_index:]:
                    yield f"data: {json.dumps(event)}\n\n"
                last_index = len(self.events)
            
            await asyncio.sleep(0.5)  # Poll every 500ms


# Global tracker map
_trackers: Dict[str, ExecutionTracker] = {}


@app.post("/api/orchestrator/execute-task-dag")
async def execute_task_dag_endpoint(
    task_dag: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Execute a task DAG.
    
    Example input (from Fruvisi):
    {
        "domain": "video",
        "timeline": "9 days",
        "successCriteria": "3 episodes + 3 guides",
        "tasks": [...],
        "parallelization": {...}
    }
    
    Returns task_id for polling + SSE stream URL.
    """
    
    # Generate task ID
    task_id = f"fruvisi_{datetime.utcnow().timestamp():.0f}"
    
    # Create tracker
    tracker = ExecutionTracker(task_id)
    _trackers[task_id] = tracker
    
    # Queue orchestration in background
    background_tasks.add_task(
        _run_orchestration,
        task_id=task_id,
        task_dag=task_dag,
        tracker=tracker,
    )
    
    await tracker.add_event(
        "queued",
        {
            "task_id": task_id,
            "domain": task_dag.get("domain"),
            "tasks": len(task_dag.get("tasks", [])),
        }
    )
    
    return {
        "task_id": task_id,
        "stream_url": f"/api/orchestrator/stream/{task_id}",
        "poll_url": f"/api/orchestrator/status/{task_id}",
        "status": "queued",
    }


@app.get("/api/orchestrator/stream/{task_id}")
async def stream_task_execution(task_id: str):
    """Stream task execution as Server-Sent Events."""
    
    if task_id not in _trackers:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tracker = _trackers[task_id]
    
    async def event_generator():
        """Generate SSE events."""
        async for event_line in tracker.stream_events():
            yield event_line
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@app.get("/api/orchestrator/status/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """Poll task status."""
    
    if task_id not in _trackers:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tracker = _trackers[task_id]
    
    return {
        "task_id": task_id,
        "events": tracker.events,
        "state": tracker.events[-1]["state"] if tracker.events else "unknown",
        "completed": any(e["state"] == "complete" for e in tracker.events),
    }


@app.get("/api/orchestrator/result/{task_id}")
async def get_task_result(task_id: str) -> Dict[str, Any]:
    """Fetch final task result + OpenViking link."""
    
    if task_id not in _trackers:
        raise HTTPException(status_code=404, detail="Task not found")
    
    tracker = _trackers[task_id]
    
    # Find completion event
    completion_event = None
    for event in reversed(tracker.events):
        if event["state"] == "complete":
            completion_event = event
            break
    
    if not completion_event:
        raise HTTPException(status_code=202, detail="Task still executing")
    
    return {
        "task_id": task_id,
        "result": completion_event["payload"],
        "openviking_link": f"viking://user/default/tasks/{task_id}/",
        "timestamp": completion_event["timestamp"],
    }


async def _run_orchestration(
    task_id: str,
    task_dag: Dict[str, Any],
    tracker: ExecutionTracker,
) -> None:
    """Run orchestration in background, update tracker."""
    
    try:
        await tracker.add_event(
            "dag_parsed",
            {"domain": task_dag.get("domain"), "tasks": len(task_dag.get("tasks", []))}
        )
        
        await tracker.add_event(
            "chief_dispatch",
            {"message": "Spawning Chief of Staff agent..."}
        )
        
        # Execute task DAG
        result = await orchestrate_task_dag(
            task_dag=task_dag,
            task_id=task_id,
            qa_callback=None,  # QA would be called here
        )
        
        if result["success"]:
            await tracker.add_event(
                "chief_completed",
                {
                    "tiers": result.get("chief_result", {}).get("tiers_completed"),
                    "duration_minutes": result.get("chief_result", {}).get("total_duration_minutes"),
                }
            )
            
            await tracker.add_event(
                "qa_validation",
                {"status": "passed" if not result.get("qa_verdict") else result["qa_verdict"].get("status")}
            )
            
            await tracker.add_event(
                "complete",
                {
                    "success": True,
                    "result": result,
                    "openviking_uri": f"viking://user/default/tasks/{task_id}/",
                }
            )
        else:
            await tracker.add_event(
                "failed",
                {"error": result.get("error")}
            )
    
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        await tracker.add_event(
            "error",
            {"message": str(e)}
        )


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "hermes-orchestrator"}
