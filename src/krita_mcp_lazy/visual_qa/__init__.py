"""Visual QA, canvas preview capture, regional inspection, scorecard evaluations, and checkpoints."""

from krita_mcp_lazy.visual_qa.capture import VisualCaptureService
from krita_mcp_lazy.visual_qa.rollback import CheckpointManager
from krita_mcp_lazy.visual_qa.scorecard import (
    WEIGHTS,
    QualityCriteria,
    ScorecardEvaluator,
)

__all__ = [
    "CheckpointManager",
    "QualityCriteria",
    "ScorecardEvaluator",
    "VisualCaptureService",
    "WEIGHTS",
]
