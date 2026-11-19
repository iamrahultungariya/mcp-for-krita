"""Status Docker widget for Krita UI providing real-time telemetry and bridge status."""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Fallback dock widget and Qt widgets for headless / non-Qt test environments
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

try:
    from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
except ImportError:
    try:
        from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget
    except ImportError:
        QWidget = None  # type: ignore[assignment, misc]
        QVBoxLayout = None  # type: ignore[assignment, misc]
        QLabel = None  # type: ignore[assignment, misc]
        QPushButton = None  # type: ignore[assignment, misc]


class StatusDocker(DockWidget):
    """Docker UI panel visible inside Krita's dockable interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Krita MCP Bridge")
        self._current_status = "READY"
        self._active_job_id: Optional[str] = None
        self._queue_length = 0

        self._lbl_status: Optional[Any] = None
        self._lbl_job: Optional[Any] = None
        self._lbl_queue: Optional[Any] = None
        self._main_widget: Optional[Any] = None

        if QWidget is not None and hasattr(self, "setWidget"):
            try:
                self._main_widget = QWidget()
                layout = QVBoxLayout()

                title_lbl = QLabel("<b>Krita MCP Lazy Bridge</b>")
                self._lbl_status = QLabel(f"Status: {self._current_status}")
                self._lbl_job = QLabel("Active Job: None")
                self._lbl_queue = QLabel("Queue Size: 0")

                layout.addWidget(title_lbl)
                layout.addWidget(self._lbl_status)
                layout.addWidget(self._lbl_job)
                layout.addWidget(self._lbl_queue)
                layout.addStretch()

                self._main_widget.setLayout(layout)
                self.setWidget(self._main_widget)
            except Exception as exc:
                logger.debug("Headless or simulated environment: Qt layout skipped: %s", exc)

    def canvasChanged(self, canvas: Any) -> None:
        """Called by Krita when active canvas changes."""
        pass

    def update_status(self, status: str, active_job_id: Optional[str] = None, queue_length: int = 0) -> None:
        """Update docker telemetry state and Qt label displays."""
        self._current_status = status
        self._active_job_id = active_job_id
        self._queue_length = queue_length

        if self._lbl_status is not None and hasattr(self._lbl_status, "setText"):
            self._lbl_status.setText(f"Status: {status}")
        if self._lbl_job is not None and hasattr(self._lbl_job, "setText"):
            self._lbl_job.setText(f"Active Job: {active_job_id or 'None'}")
        if self._lbl_queue is not None and hasattr(self._lbl_queue, "setText"):
            self._lbl_queue.setText(f"Queue Size: {queue_length}")

    @property
    def current_status(self) -> str:
        return self._current_status

    @property
    def active_job_id(self) -> Optional[str]:
        return self._active_job_id

    @property
    def queue_length(self) -> int:
        return self._queue_length
