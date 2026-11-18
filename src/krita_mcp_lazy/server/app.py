"""FastMCP server initialization and tool registration for krita-MCP-lazy."""

from typing import Any, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.server.tools_document import register_document_tools
from krita_mcp_lazy.server.tools_layers import register_layer_tools
from krita_mcp_lazy.server.tools_painting import register_painting_tools
from krita_mcp_lazy.server.tools_system import register_system_tools

# Support both mcp 2.x (MCPServer) and mcp 1.x (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]
    except ImportError:
        raise ImportError("Neither 'mcp.server.mcpserver' nor 'mcp.server.fastmcp' could be imported")


def create_mcp_server(config: Optional[KritaConfig] = None) -> Any:
    """Factory function creating and configuring the primary krita-MCP-lazy MCP server."""
    cfg = config or KritaConfig()
    server = FastMCP("krita-MCP-lazy")
    
    # Register Core System Tools
    register_system_tools(server, cfg)
    # Register Document Management Tools
    register_document_tools(server, cfg)
    # Register Layer Intelligence Tools
    register_layer_tools(server, cfg)
    # Register Painting Tools
    register_painting_tools(server, cfg)
    
    return server
