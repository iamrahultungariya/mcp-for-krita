"""Layer buffer definitions for Krita painting director."""

from dataclasses import dataclass


@dataclass
class LayerBuffer:
    """Represents a discrete paint layer buffer ready for Krita IPC transmission."""

    name: str
    pixels: bytes
    x: int
    y: int
    width: int
    height: int
    blend_mode: str = "normal"
    opacity: int = 255
