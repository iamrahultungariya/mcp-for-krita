"""Krita MCP Bridge Plugin Entry Point."""

import builtins
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

# Guard against duplicate initialization across alias module names in the same process
if hasattr(builtins, "_KRITA_MCP_BRIDGE_LOADED"):
    _log_debug("krita_mcp_bridge already loaded in this process; skipping duplicate import.")
    BridgeExtension = getattr(builtins, "_KRITA_MCP_BRIDGE_EXTENSION_CLS", None)
    KritaMainThreadDispatcher = getattr(builtins, "_KRITA_MCP_DISPATCHER_CLS", None)
    StatusDocker = getattr(builtins, "_KRITA_MCP_DOCKER_CLS", None)
else:
    builtins._KRITA_MCP_BRIDGE_LOADED = True
    _log_debug("--- Initializing krita_mcp_bridge plugin (first load) ---")

    # Dynamically resolve realpath of current plugin directory across symlinks/junctions
    real_dir = os.path.dirname(os.path.realpath(__file__))
    workspace_root = os.path.abspath(os.path.join(real_dir, "..", ".."))
    src_dir = os.path.abspath(os.path.join(workspace_root, "src"))

    for p in [src_dir, workspace_root]:
        if os.path.exists(p) and p not in sys.path:
            sys.path.insert(0, p)
            _log_debug(f"Added {p} to sys.path")

    try:
        try:
            from .bridge_extension import BridgeExtension
            from .dispatcher import KritaMainThreadDispatcher
            from .status_docker import StatusDocker
            _log_debug("Imported bridge extension, dispatcher, status docker relative")
        except Exception as e_rel:
            _log_debug(f"Relative import failed ({e_rel}), trying absolute")
            from plugins.krita_mcp_bridge.bridge_extension import BridgeExtension
            from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
            from plugins.krita_mcp_bridge.status_docker import StatusDocker
            _log_debug("Imported bridge extension, dispatcher, status docker absolute")
    except Exception as e_crit:
        _log_debug(f"CRITICAL: Failed to import bridge components: {e_crit}\n{traceback.format_exc()}")
        BridgeExtension = None
        KritaMainThreadDispatcher = None
        StatusDocker = None

    builtins._KRITA_MCP_BRIDGE_EXTENSION_CLS = BridgeExtension
    builtins._KRITA_MCP_DISPATCHER_CLS = KritaMainThreadDispatcher
    builtins._KRITA_MCP_DOCKER_CLS = StatusDocker

    # When imported by Krita inside Krita's embedded Python runtime:
    try:
        from krita import Krita, DockWidgetFactoryBase

        app = Krita.instance()
        if app and BridgeExtension is not None:
            _log_debug("Krita application instance detected")
            _extension = BridgeExtension(parent=app)
            builtins._KRITA_MCP_EXTENSION_INSTANCE = _extension
            app.addExtension(_extension)
            _log_debug("Successfully added single BridgeExtension to Krita")

            class StatusDockerFactory(DockWidgetFactoryBase):
                def __init__(self) -> None:
                    super().__init__("KritaMCPStatusDocker", DockWidgetFactoryBase.DockRight)

                def createDockWidget(self) -> StatusDocker:
                    return StatusDocker()

            try:
                app.addDockWidgetFactory(StatusDockerFactory())
                _log_debug("Successfully registered single StatusDockerFactory with Krita")
            except Exception as dfe:
                _log_debug(f"StatusDockerFactory registration note: {dfe}")

    except Exception as e:
        _log_debug(f"Krita registration block error: {e}\n{traceback.format_exc()}")

__all__ = [
    "BridgeExtension",
    "KritaMainThreadDispatcher",
    "StatusDocker",
]
