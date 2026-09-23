"""
MCP Endpoint Framework: JSON-RPC over HTTP for plugins (GraphCode, Executor, Open Design).

Each plugin runs as independent service exposing JSON-RPC methods.
Hermes backend discovers and dispatches to these endpoints.

Supported plugins:
  - GraphCode (code-graph indexing and semantic search)
  - Executor (code execution and test orchestration)
  - Open Design (visual design generation)
"""

from typing import Any, Optional, Callable, Dict, Union
from pydantic import BaseModel
import httpx
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PluginType(Enum):
    """Plugin types available for dispatch."""
    GRAPHCODE = "graphcode"
    EXECUTOR = "executor"
    OPEN_DESIGN = "open_design"


class PluginConfig(BaseModel):
    """Plugin configuration with MCP endpoint."""
    plugin_type: PluginType
    endpoint: str  # e.g., "http://127.0.0.1:8003"
    enabled: bool = True
    timeout_seconds: int = 60


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None


class PluginRegistry:
    """Registry and dispatcher for MCP plugins."""
    
    def __init__(self):
        self.plugins: Dict[PluginType, PluginConfig] = {}
        self.client = httpx.AsyncClient()
    
    def register(self, config: PluginConfig) -> None:
        """Register a plugin endpoint."""
        self.plugins[config.plugin_type] = config
        logger.info(f"Registered plugin {config.plugin_type.value} at {config.endpoint}")
    
    def get_plugin(self, plugin_type: PluginType) -> Optional[PluginConfig]:
        """Get plugin config by type."""
        return self.plugins.get(plugin_type)
    
    async def call_plugin(
        self,
        plugin_type: PluginType,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Optional[Any]:
        """
        Call a plugin method via JSON-RPC over HTTP.
        
        Args:
            plugin_type: Which plugin to target
            method: RPC method name (e.g., "graphcode.index_repo", "executor.run_test")
            params: RPC method parameters
            request_id: Optional request ID for tracing
        
        Returns:
            Result from plugin RPC response, or None on error
        """
        config = self.get_plugin(plugin_type)
        if not config or not config.enabled:
            logger.error(f"Plugin {plugin_type.value} not registered or disabled")
            return None
        
        request = JSONRPCRequest(
            method=method,
            params=params or {},
            id=request_id or "hermes-dispatch",
        )
        
        try:
            resp = await self.client.post(
                f"{config.endpoint}/rpc",
                json=request.model_dump(),
                timeout=config.timeout_seconds,
            )
            if resp.status_code == 200:
                data = resp.json()
                json_resp = JSONRPCResponse(**data)
                if json_resp.error:
                    logger.error(f"Plugin RPC error: {json_resp.error}")
                    return None
                return json_resp.result
            else:
                logger.error(f"Plugin RPC failed with status {resp.status_code}")
                return None
        except httpx.TimeoutException:
            logger.error(f"Plugin RPC timeout for {plugin_type.value}")
            return None
        except Exception as e:
            logger.error(f"Plugin RPC call failed: {e}")
            return None
    
    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


# Global registry singleton
_registry: Optional[PluginRegistry] = None


def get_plugin_registry() -> PluginRegistry:
    """Get or create global plugin registry."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def init_default_plugins() -> None:
    """Initialize default plugin endpoints (configurable via config.yaml)."""
    registry = get_plugin_registry()
    
    # Default endpoints (can be overridden in config)
    plugins = [
        PluginConfig(
            plugin_type=PluginType.GRAPHCODE,
            endpoint="http://127.0.0.1:8003",
        ),
        PluginConfig(
            plugin_type=PluginType.EXECUTOR,
            endpoint="http://127.0.0.1:8004",
        ),
        PluginConfig(
            plugin_type=PluginType.OPEN_DESIGN,
            endpoint="http://127.0.0.1:8005",
        ),
    ]
    
    for plugin in plugins:
        registry.register(plugin)
