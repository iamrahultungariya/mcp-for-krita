"""Krita MCP Bridge Plugin Entry Point."""

import os
import sys

# Ensure krita_mcp_lazy is discoverable by Krita's embedded python runtime
try:
    import krita_mcp_lazy
except ImportError:
    repo_src = r"c:\Users\Rahul\OneDrive\Desktop\Krita MCP\src"
    if os.path.exists(repo_src) and repo_src not in sys.path:
        sys.path.insert(0, repo_src)

try:
    from .bridge_extension import BridgeExtension
    from .dispatcher import KritaMainThreadDispatcher
    from .status_docker import StatusDocker
except ImportError:
    from plugins.krita_mcp_bridge.bridge_extension import BridgeExtension
    from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
    from plugins.krita_mcp_bridge.status_docker import StatusDocker

__all__ = [
    "BridgeExtension",
    "KritaMainThreadDispatcher",
    "StatusDocker",
]

# When imported by Krita inside Krita's embedded Python runtime:
try:
    from krita import Krita, DockWidgetFactoryBase

    app = Krita.instance()
    if app:
        _extension = BridgeExtension(parent=app)
        app.addExtension(_extension)

        class StatusDockerFactory(DockWidgetFactoryBase):
            def __init__(self) -> None:
                super().__init__()
                self.id = "KritaMCPStatusDocker"
                self.defaultArea = DockWidgetFactoryBase.DockRight

            def createDockWidget(self) -> StatusDocker:
                return StatusDocker()

        app.addDockWidgetFactory(StatusDockerFactory())
except ImportError:
    pass
