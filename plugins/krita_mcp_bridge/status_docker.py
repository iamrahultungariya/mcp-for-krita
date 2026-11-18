"""Status Docker widget for Krita UI providing real-time telemetry and bridge status."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Fallback dock widget for headless / non-Qt test environments
try:
    from krita import DockWidget
except ImportError:
    try:
        from PyQt5.QtWidgets import QDockWidget as DockWidget
    except ImportError:
        try:
            from PyQt6.QtWidgets import QDockWidget as DockWidget
        except ImportError:
            class DockWidget:  # type: ignore[no-redef]
                def __init__(self) -> None:
                    pass

                def setWindowTitle(self, title: str) -> None:
                    self.title = title

                def canvasChanged(self, canvas: Any) -> None:
                    pass


class StatusDocker(DockWidget):
    """Docker UI panel visible inside Krita's dockable interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Krita MCP Bridge")
        self._current_status = "READY"
        self._active_job_id: Optional[str] = None
        self._queue_length = 0

    def canvasChanged(self, canvas: Any) -> None:
        """Called by Krita when active canvas changes."""
        pass

    def update_status(self, status: str, active_job_id: Optional[str] = None, queue_length: int = 0) -> None:
        """Update docker telemetry state."""
        self._current_status = status
        self._active_job_id = active_job_id
        self._queue_length = queue_length

    @property
    def current_status(self) -> str:
        return self._current_status

    @property
    def queue_length(self) -> int:
        return self._queue_length
