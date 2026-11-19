"""Data models for R.G. Bucket List and Anime modular character rigs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class CharacterRigMetadata:
    """Rig definition describing modular character parts, pivots, expressions, and palette."""

    character_id: str
    name: str
    style: str = "rg_bucket_list"
    pivots: Dict[str, List[float]] = field(default_factory=dict)
    expressions: List[str] = field(
        default_factory=lambda: ["normal", "blink", "shocked", "smile"]
    )
    visemes: List[str] = field(
        default_factory=lambda: ["rest", "A", "E", "O", "smirk"]
    )
    palette: Dict[str, str] = field(default_factory=dict)
    bounds: Dict[str, float] = field(default_factory=dict)
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to JSON-serializable dictionary."""
        return asdict(self)
