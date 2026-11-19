"""Krita MCP Bridge Plugin Entry Point."""

import os
import sys
import tempfile
import traceback

_debug_log_path = os.path.join(tempfile.gettempdir(), "krita_mcp_bridge_debug.log")

def _log_debug(msg: str) -> None:
    try:
        with open(_debug_log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

_log_debug("--- Initializing krita_mcp_bridge plugin ---")

# Ensure krita_mcp_lazy is discoverable by Krita's embedded python runtime
try:
    import krita_mcp_lazy
    _log_debug("Successfully imported existing krita_mcp_lazy from sys.path")
except ImportError:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(current_dir, "..", "..", "src")),
        os.path.abspath(os.path.join(current_dir, "..", "src")),
        os.path.abspath(os.path.join(current_dir, "src")),
    ]
    for c in candidates:
        if os.path.exists(c) and c not in sys.path:
            sys.path.insert(0, c)
            _log_debug(f"Added {c} to sys.path")
            break

try:
    from .bridge_extension import BridgeExtension
    from .dispatcher import KritaMainThreadDispatcher
    from .status_docker import StatusDocker
    _log_debug("Imported bridge extension, dispatcher, status docker relative")
except Exception as e:
    _log_debug(f"Relative import failed: {e}, falling back to absolute")
    try:
        from plugins.krita_mcp_bridge.bridge_extension import BridgeExtension
        from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
        from plugins.krita_mcp_bridge.status_docker import StatusDocker
        _log_debug("Imported bridge extension, dispatcher, status docker absolute")
    except Exception as e2:
        _log_debug(f"CRITICAL: Failed to import bridge components: {e2}\n{traceback.format_exc()}")

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
        _log_debug("Krita application instance detected")
        _extension = BridgeExtension(parent=app)
        app.addExtension(_extension)
        _log_debug("Successfully added BridgeExtension to Krita")

        class StatusDockerFactory(DockWidgetFactoryBase):
            def __init__(self) -> None:
                super().__init__()
                self.id = "KritaMCPStatusDocker"
                self.defaultArea = DockWidgetFactoryBase.DockRight

            def createDockWidget(self) -> StatusDocker:
                return StatusDocker()

        app.addDockWidgetFactory(StatusDockerFactory())
        _log_debug("Successfully registered StatusDockerFactory with Krita")
except Exception as e:
    _log_debug(f"Krita registration block result: {e}")
