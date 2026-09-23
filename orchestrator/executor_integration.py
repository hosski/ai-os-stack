"""
Executor Integration: Wrapper around Executor CLI for tool invocation.

Executor is the universal integration catalog. Sub-agents call tools via:
  executor tools search "query"
  executor call <integration> <method> '{json_args}'
  executor mcp (MCP endpoint for nested agents)
"""

import subprocess
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)


class ExecutorIntegration:
    """High-level wrapper around Executor CLI."""
    
    def __init__(self, executor_bin: str = "executor"):
        self.executor_bin = executor_bin
        self._integration_cache: Optional[List[str]] = None
    
    async def call_tool(
        self,
        integration: str,
        method: str,
        args: Dict[str, Any],
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """
        Call an Executor tool synchronously.
        
        Example:
          result = await executor.call_tool(
            "open_design",
            "create_scene",
            {"name": "Scene 1", "dimensions": "1920x1080"}
          )
        """
        try:
            cmd = [
                self.executor_bin,
                "call",
                f"{integration}:{method}",
                json.dumps(args)
            ]
            
            logger.info(f"Executor call: {integration}:{method}")
            
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"Executor error: {result.stderr}")
                return {
                    "success": False,
                    "error": result.stderr,
                    "integration": integration,
                    "method": method,
                }
            
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                output = {"success": True, "raw_output": result.stdout}
            
            return {
                "success": True,
                "integration": integration,
                "method": method,
                "result": output,
            }
        
        except subprocess.TimeoutExpired:
            logger.error(f"Executor timeout after {timeout}s")
            return {
                "success": False,
                "error": f"Timeout after {timeout}s",
                "integration": integration,
                "method": method,
            }
        except Exception as e:
            logger.error(f"Executor call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "integration": integration,
                "method": method,
            }
    
    async def search_tools(self, query: str = "") -> List[str]:
        """Search available Executor integrations."""
        try:
            cmd = [self.executor_bin, "tools", "search", query]
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"Tool search failed: {result.stderr}")
                return []
            
            try:
                tools = json.loads(result.stdout).get("tools", [])
                self._integration_cache = tools
                return tools
            except json.JSONDecodeError:
                # Parse plain text output
                return [line.strip() for line in result.stdout.split("\n") if line.strip()]
        
        except Exception as e:
            logger.error(f"Tool search error: {e}")
            return []
    
    async def get_integrations(self) -> List[str]:
        """Get list of available integrations (cached)."""
        if self._integration_cache is not None:
            return self._integration_cache
        return await self.search_tools()
    
    async def describe_tool(self, integration: str, method: str) -> Dict[str, Any]:
        """Get tool schema/description."""
        try:
            cmd = [
                self.executor_bin,
                "tools",
                "describe",
                f"{integration}:{method}"
            ]
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            return {"error": result.stderr}
        
        except Exception as e:
            logger.error(f"Describe tool error: {e}")
            return {"error": str(e)}


# Global executor instance
_executor: Optional[ExecutorIntegration] = None


def get_executor() -> ExecutorIntegration:
    global _executor
    if _executor is None:
        _executor = ExecutorIntegration()
    return _executor
