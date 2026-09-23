"""
Hermes ↔ OpenViking API bridge: unified memory and orchestration.

Handles all REST communication between Hermes orchestrator and OpenViking knowledge base.
Single source of truth for data, task state, and QA results.

Entry points:
  - hermes_openviking_client(): Get or create client
  - store_task_state()
  - fetch_task_state()
  - store_qa_result()
"""

from typing import Optional, Any, TypedDict
import json
import httpx
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

OPENVIKING_ENDPOINT = "http://127.0.0.1:1933"  # Default OpenViking endpoint


class TaskObject(TypedDict):
    """Standardized task object for orchestration."""
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    result_payload: Optional[dict[str, Any]]
    retry_count: int
    priority: int
    domain_profile: str  # e.g., "video", "law"
    created_at: str


class QAResult(TypedDict):
    """QA pass/fail verdict with feedback."""
    task_id: str
    passed: bool
    feedback: str
    checked_at: str


class HermesOpenVikingClient:
    """REST client for Hermes ↔ OpenViking communication."""
    
    def __init__(self, endpoint: str = OPENVIKING_ENDPOINT):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def store_task(self, task: TaskObject) -> bool:
        """Store task state in OpenViking."""
        try:
            payload = {
                "task_id": task["task_id"],
                "status": task["status"],
                "result_payload": task["result_payload"],
                "retry_count": task["retry_count"],
                "priority": task["priority"],
                "domain_profile": task["domain_profile"],
                "created_at": task["created_at"],
            }
            resp = await self.client.post(
                f"{self.endpoint}/api/v1/content/write",
                json={"content": json.dumps(payload), "uri": f"viking://tasks/{task['task_id']}.json"},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to store task in OpenViking: {e}")
            return False
    
    async def fetch_task(self, task_id: str) -> Optional[TaskObject]:
        """Fetch task state from OpenViking."""
        try:
            resp = await self.client.get(
                f"{self.endpoint}/api/v1/content/read",
                params={"uri": f"viking://tasks/{task_id}.json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("content")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch task from OpenViking: {e}")
            return None
    
    async def store_qa_result(self, result: QAResult) -> bool:
        """Store QA result in OpenViking."""
        try:
            payload = {
                "task_id": result["task_id"],
                "passed": result["passed"],
                "feedback": result["feedback"],
                "checked_at": result["checked_at"],
            }
            resp = await self.client.post(
                f"{self.endpoint}/api/v1/content/write",
                json={"content": json.dumps(payload), "uri": f"viking://qa/{result['task_id']}.json"},
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to store QA result in OpenViking: {e}")
            return False
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


_client_instance: Optional[HermesOpenVikingClient] = None


def hermes_openviking_client() -> HermesOpenVikingClient:
    """Get or create singleton client."""
    global _client_instance
    if _client_instance is None:
        _client_instance = HermesOpenVikingClient()
    return _client_instance


async def store_task_state(task: TaskObject) -> bool:
    """Store task state via REST API."""
    client = hermes_openviking_client()
    return await client.store_task(task)


async def fetch_task_state(task_id: str) -> Optional[TaskObject]:
    """Fetch task state via REST API."""
    client = hermes_openviking_client()
    return await client.fetch_task(task_id)


async def store_qa_result(result: QAResult) -> bool:
    """Store QA result via REST API."""
    client = hermes_openviking_client()
    return await client.store_qa_result(result)
