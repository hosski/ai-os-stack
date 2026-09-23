"""
Minimal plugin stub: GraphCode (code graph indexing and semantic search).

JSON-RPC 2.0 endpoint at http://127.0.0.1:8003/rpc

Methods:
  - graphcode.analyze: Analyze code structure and dependencies
  - graphcode.search: Semantic search in codebase
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any, Dict
import uuid
from datetime import datetime

app = FastAPI(title="GraphCode Plugin")


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
        if method == "graphcode.analyze":
            result = await analyze_code(params)
        elif method == "graphcode.search":
            result = await search_code(params)
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


async def analyze_code(params: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze code structure and dependencies."""
    task_id = params.get("task_id", str(uuid.uuid4()))
    domain = params.get("domain", "unknown")
    input_payload = params.get("input", {})
    
    return {
        "task_id": task_id,
        "status": "analyzed",
        "document_summary": f"Analysis of {domain} legal document structure",
        "case_law_refs": [
            "Smith v. Jones (2020)",
            "Case Law Example 1",
            "Case Law Example 2",
        ],
        "analysis": {
            "structure": "Multi-paragraph legal brief",
            "precedents_cited": 3,
            "confidence": 0.95,
        },
        "analyzed_at": datetime.utcnow().isoformat(),
    }


async def search_code(params: Dict[str, Any]) -> Dict[str, Any]:
    """Semantic search in codebase."""
    task_id = params.get("task_id", str(uuid.uuid4()))
    query = params.get("input", {}).get("query", "")
    
    return {
        "task_id": task_id,
        "query": query,
        "results": [
            {
                "file": "example1.py",
                "line": 42,
                "match": "relevant_code_snippet",
                "confidence": 0.92,
            },
            {
                "file": "example2.py",
                "line": 15,
                "match": "another_snippet",
                "confidence": 0.87,
            },
        ],
        "status": "search_complete",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "graphcode-plugin"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)
