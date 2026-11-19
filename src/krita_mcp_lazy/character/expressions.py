"""Facial expression matrices, anchor alignment, and lip-sync visemes for 2D animation."""

from enum import Enum
from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class EmotionType(str, Enum):
    """Core emotional states for expression model sheets."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    SAD = "sad"
    SHOCKED = "shocked"
    SCARED = "scared"
    SMUG = "smug"
    CONFUSED = "confused"


class VisemeType(str, Enum):
    """Standard Preston Blair / anime animation lip-sync viseme mouth shapes."""

    REST = "rest"
    AI = "ai"
    E = "e"
    O = "o"
    U = "u"
    MBP = "mbp"
    FV = "fv"
    LNTD = "lntd"
    WQ = "wq"


class FacialExpressionEngine:
    """Manages facial feature breakdowns, emotion matrices, and lip-sync viseme layers."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def create_expression_matrix(
        self,
        doc_id: str,
        character_name: str = "Character",
        emotions: Optional[List[EmotionType]] = None,
    ) -> Dict[str, Any]:
        """Scaffold emotional variation layer groups with dedicated Eyes, Brows, and Mouth sub-layers."""
        if not emotions:
            emotions = [
                EmotionType.NEUTRAL,
                EmotionType.HAPPY,
                EmotionType.ANGRY,
                EmotionType.SAD,
                EmotionType.SHOCKED,
                EmotionType.SCARED,
            ]

        payload = {
            "doc_id": doc_id,
            "character_name": character_name,
            "emotions": [e.value for e in emotions],
        }

        resp = await self.client.send_job("character.expression_matrix", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Expression matrix creation failed")

    async def generate_viseme_set(
        self,
        doc_id: str,
        character_name: str = "Character",
        visemes: Optional[List[VisemeType]] = None,
    ) -> Dict[str, Any]:
        """Scaffold lip-sync mouth shape layers ready for frame-by-frame animation or cutout export."""
        if not visemes:
            visemes = [
                VisemeType.REST,
                VisemeType.AI,
                VisemeType.E,
                VisemeType.O,
                VisemeType.U,
                VisemeType.MBP,
                VisemeType.FV,
                VisemeType.LNTD,
            ]

        payload = {
            "doc_id": doc_id,
            "character_name": character_name,
            "visemes": [v.value for v in visemes],
        }

        resp = await self.client.send_job("character.generate_visemes", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Viseme set generation failed")
