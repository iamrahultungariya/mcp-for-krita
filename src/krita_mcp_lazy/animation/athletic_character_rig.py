"""Athletic Character Rig and Cinematic Palette Definition.

Defines the athletic redesign for Anime Creator:
- Breathable athletic sports tank top with white piping
- Running shorts with lateral motion split
- Elastic terrycloth sweatband and wristbands
- Lightweight running trainers
- Cinematic saturated color palette with warm golden-hour rim lighting
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from krita_mcp_lazy.modular_rig.models import CharacterRigMetadata


@dataclass
class AthleticRunnerPalette:
    """Cinematic high-chroma color palette for athletic character."""
    tank_top: str = "#1A365D"          # Deep Cobalt Navy
    shorts: str = "#102A43"            # Midnight Navy
    trim_white: str = "#FFFFFF"        # Athletic Crisp White
    skin_base: str = "#FAD2B8"         # Warm Saturated Peach Skin
    skin_shadow: str = "#C47B56"       # Rich Warm Amber Shadow
    hair_base: str = "#4A2810"         # Rich Brunette Hair
    hair_specular: str = "#FFE082"     # Golden Sun Rim Highlight
    sweatband: str = "#FFFFFF"         # Terrycloth White Headband
    wristband: str = "#FFFFFF"         # Terrycloth White Wristband
    trainers_primary: str = "#FFFFFF"   # White Trainers
    trainers_accent: str = "#FFB703"    # Gold/Amber Track Accents
    cel_shadow: str = "#1E152A"        # Deep Cool Cel Shadow (Multiply)
    sun_rim: str = "#FFF3B0"           # Sunlight Specular (Addition)


class AthleticRunnerCostume:
    """Manages athletic costume layers and assembly."""

    def __init__(self, palette: AthleticRunnerPalette | None = None) -> None:
        self.palette = palette or AthleticRunnerPalette()

    def get_costume_layers(self) -> List[str]:
        """Return canonical list of costume layers for modular rigging."""
        return [
            "Sweatband_Head",
            "Hair_Back",
            "Head_Base",
            "Eyes_Face",
            "Hair_Front_Bangs",
            "Tank_Top",
            "Running_Shorts",
            "Arm_L",
            "Arm_R",
            "Wristband_L",
            "Wristband_R",
            "Leg_L",
            "Leg_R",
            "Sports_Trainers",
            "FX_Sweat_Drops",
        ]


def create_athletic_character_metadata(
    character_id: str = "anime_creator_runner",
    name: str = "Anime Creator (Athletic)",
    width: int = 3840,
    height: int = 2160,
    palette: AthleticRunnerPalette | None = None,
) -> CharacterRigMetadata:
    """Generate complete CharacterRigMetadata for the athletic runner."""
    pal = palette or AthleticRunnerPalette()
    palette_dict: Dict[str, str] = {
        "tank_top": pal.tank_top,
        "shorts": pal.shorts,
        "trim_white": pal.trim_white,
        "skin_base": pal.skin_base,
        "skin_shadow": pal.skin_shadow,
        "hair_base": pal.hair_base,
        "hair_specular": pal.hair_specular,
        "sweatband": pal.sweatband,
        "cel_shadow": pal.cel_shadow,
        "sun_rim": pal.sun_rim,
    }

    bounds: Dict[str, float] = {
        "x": float(width * 0.35),
        "y": float(height * 0.30),
        "width": float(width * 0.30),
        "height": float(height * 0.60),
    }

    pivots: Dict[str, List[float]] = {
        "head": [round(width * 0.50, 1), round(height * 0.38, 1)],
        "neck": [round(width * 0.50, 1), round(height * 0.44, 1)],
        "chest": [round(width * 0.50, 1), round(height * 0.50, 1)],
        "hip": [round(width * 0.50, 1), round(height * 0.60, 1)],
        "shoulder_l": [round(width * 0.44, 1), round(height * 0.47, 1)],
        "shoulder_r": [round(width * 0.56, 1), round(height * 0.47, 1)],
        "knee_l": [round(width * 0.46, 1), round(height * 0.72, 1)],
        "knee_r": [round(width * 0.54, 1), round(height * 0.72, 1)],
        "ankle_l": [round(width * 0.46, 1), round(height * 0.84, 1)],
        "ankle_r": [round(width * 0.54, 1), round(height * 0.84, 1)],
    }

    return CharacterRigMetadata(
        character_id=character_id,
        name=name,
        style="rg_bucket_list_athletic",
        palette=palette_dict,
        bounds=bounds,
        pivots=pivots,
        expressions=["determined", "focused_breath", "grit", "smile_exhausted"],
        visemes=["rest", "heavy_breath", "panting_open", "determined_shut"],
    )
