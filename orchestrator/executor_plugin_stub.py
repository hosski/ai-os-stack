"""
Minimal plugin stub: Executor (code generation and test execution).

JSON-RPC 2.0 endpoint at http://127.0.0.1:8004/rpc

Methods:
  - executor.generate: Generate code/content for a task
  - executor.test: Run tests on generated output
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any, Dict
import uuid
from datetime import datetime

app = FastAPI(title="Executor Plugin")


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


@app.post("/rpc")
async def handle_rpc(request: JSONRPCRequest):
    """Handle JSON-RPC 2.0 requests."""
    method = request.method
    params = request.params or {}
    
    try:
        if method == "executor.generate":
            result = await execute_generate(params)
        elif method == "executor.test":
            result = await execute_test(params)
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": "Method not found"},
                "id": request.id,
            }
        
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.id,
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "error": {"code": -32603, "message": str(e)},
            "id": request.id,
        }


async def execute_generate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate content for a task."""
    task_id = params.get("task_id", str(uuid.uuid4()))
    domain = params.get("domain", "unknown")
    input_payload = params.get("input", {})
    models = params.get("models", {})
    
    # Stub: simulate generation
    return {
        "task_id": task_id,
        "status": "generated",
        "output_url": f"s3://generated/{domain}/{task_id}/output.mp4",
        "duration": 180,  # 3 minutes for video
        "metadata": {
            "domain": domain,
            "model": models.get("primary", "unknown"),
            "generated_at": datetime.utcnow().isoformat(),
        },
    }


async def execute_test(params: Dict[str, Any]) -> Dict[str, Any]:
    """Test generated output."""
    task_id = params.get("task_id", str(uuid.uuid4()))
    
    return {
        "task_id": task_id,
        "tests_passed": 3,
        "tests_failed": 0,
        "status": "all_passed",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "executor-plugin"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)
