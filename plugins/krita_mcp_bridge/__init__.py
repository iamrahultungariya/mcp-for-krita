"""Krita MCP Bridge Plugin Entry Point."""

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
