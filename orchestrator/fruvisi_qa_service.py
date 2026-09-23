"""
Fruvisi QA Service: Automated pass/fail routing and retry logic.

Standalone FastAPI service running on dedicated port. Handles:
  - Task evaluation (pass/fail verdict)
  - Automated rework routing on failure
  - Retry count and priority management

API Endpoints:
  POST /api/v1/qa/evaluate
  GET /api/v1/qa/status/{task_id}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
from datetime import datetime
import logging

app = FastAPI(title="Fruvisi QA Service")
logger = logging.getLogger(__name__)

HERMES_ENDPOINT = "http://127.0.0.1:8000"  # Hermes backend (configurable)
OPENVIKING_ENDPOINT = "http://127.0.0.1:1933"
MAX_RETRIES = 3


class EvaluationRequest(BaseModel):
    """QA evaluation request."""
    task_id: str
    result_payload: dict
    domain_profile: str


class QAVerdict(BaseModel):
    """QA verdict: pass or fail with reasoning."""
    task_id: str
    passed: bool
    feedback: str
    next_action: Optional[str]  # "complete", "rework", "escalate"
    retry_count: int


@app.post("/api/v1/qa/evaluate")
async def evaluate_task(req: EvaluationRequest) -> QAVerdict:
    """
    Evaluate task result and emit verdict.
    
    Logic:
      1. Validate result against domain profile requirements
      2. If fail: increment retry count, route to rework if < MAX_RETRIES
      3. If pass: mark complete
      4. If fail & retries exhausted: escalate
    """
    # Stub: implement domain-specific QA logic per profile
    # For now, simple heuristic: presence of required fields
    
    required_fields = _get_required_fields_for_domain(req.domain_profile)
    missing = [f for f in required_fields if f not in req.result_payload]
    
    # Fetch current retry count from OpenViking
    async with httpx.AsyncClient() as client:
        task_resp = await client.get(
            f"{OPENVIKING_ENDPOINT}/api/v1/content/read",
            params={"uri": f"viking://tasks/{req.task_id}.json"},
        )
        if task_resp.status_code == 200:
            task_data = task_resp.json().get("content", {})
            retry_count = task_data.get("retry_count", 0)
        else:
            retry_count = 0
    
    if not missing:
        verdict_action = "complete"
        passed = True
        feedback = "All required fields present"
    else:
        passed = False
        feedback = f"Missing required fields: {', '.join(missing)}"
        retry_count += 1
        
        if retry_count < MAX_RETRIES:
            verdict_action = "rework"
        else:
            verdict_action = "escalate"
    
    return QAVerdict(
        task_id=req.task_id,
        passed=passed,
        feedback=feedback,
        next_action=verdict_action,
        retry_count=retry_count,
    )


@app.get("/api/v1/qa/status/{task_id}")
async def get_qa_status(task_id: str):
    """Fetch QA status for a task."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{OPENVIKING_ENDPOINT}/api/v1/content/read",
                params={"uri": f"viking://qa/{task_id}.json"},
            )
            if resp.status_code == 200:
                return resp.json()
            raise HTTPException(status_code=404, detail=f"No QA result for {task_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_required_fields_for_domain(domain: str) -> list[str]:
    """Return required result fields per domain."""
    requirements = {
        "video": ["output_url", "duration", "metadata"],
        "law": ["document_summary", "case_law_refs", "analysis"],
        "architecture": ["blueprint_url", "specifications", "materials_list"],
        "homesteading": ["instructions", "materials", "timeline"],
    }
    return requirements.get(domain, [])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "fruvisi-qa"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)
