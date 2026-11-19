"""Anime movie poster production specification and aesthetic art direction contract."""

from typing import Any, Dict


def get_whispers_in_starlight_spec() -> Dict[str, Any]:
    """Return production specification for the anime romance movie poster.
    
    Movie: 『星空の約束 - Whispers in the Starlight』
    Aesthetic: Kyoto Animation / Makoto Shinkai twilight romantic celestial mood.
    """
    return {
        "title": {
            "english": "Whispers in the Starlight",
            "japanese": "星空の約束",
            "tagline": "Across infinite skies, our hearts remember.",
            "release": "COMING TO THEATERS SUMMER 2026",
            "credit": "A TOONFLOW ORIGINAL ANIME PRESENTATION",
        },
        "canvas": {
            "width": 2480,
            "height": 3508,
            "dpi": 300,
            "color_model": "RGBA",
            "color_depth": "U8",
            "name": "Whispers_In_The_Starlight_Poster",
        },
        "palette": {
            "sky_zenith": "#0B1026",        # Deep midnight indigo
            "sky_mid": "#261B4E",           # Royal violet nebula
            "sky_twilight": "#E86A82",      # Warm sunset rose
            "horizon_glow": "#FCD0A1",      # Golden twilight radiance
            "starlight_core": "#FFFFFF",    # Pure white star brilliance
            "starlight_glow": "#FFF3B0",    # Warm celestial gold
            "celestial_cyan": "#64DFDF",    # Glowing cyan comet/nebula
            "city_silhouette": "#080C1B",   # Distant skyline silhouette
            "city_lights": "#FFD166",       # Twinkling warm window dots
            "architecture_deck": "#10142A", # Observation deck railing
            "character_silhouette": "#0D1127", # Lover silhouettes
            "fate_thread": "#FF2A55",       # Red ribbon of destiny
            "fate_glow": "#FFAAA6",         # Soft fate thread bloom
            "sakura_base": "#FFB7B2",       # Delicate sakura petal
            "sakura_highlight": "#FFCAD4",  # Luminous petal highlight
            "title_kanji": "#FFFFFF",       # Pure white kanji
            "title_sub": "#FCD0A1",         # Warm gold subtitle text
        },
        "composition": {
            "rule_of_thirds": {
                "top_horizon_y": 1169,
                "bottom_horizon_y": 2338,
                "left_vertical_x": 826,
                "right_vertical_x": 1653,
            },
            "vanishing_point": [1240, 2600],
            "moon_center": [1850, 600],
            "girl_anchor": [800, 2750],
            "boy_anchor": [1680, 2750],
            "thread_control_point": [1240, 2900],
        },
        "layers": {
            "00_Sky_Celestial": {
                "type": "group",
                "blend_mode": "normal",
                "opacity": 255,
                "children": ["Sky_Gradient", "Nebula_Glow", "Stars_Field", "Crescent_Moon"],
            },
            "01_Far_Hills_City": {
                "type": "group",
                "blend_mode": "normal",
                "opacity": 255,
                "children": ["Distant_Hills", "City_Skyline", "City_Window_Lights"],
            },
            "02_Rooftop_Mid": {
                "type": "group",
                "blend_mode": "normal",
                "opacity": 255,
                "children": ["Balcony_Floor", "Observation_Railing"],
            },
            "03_Lovers_Hero": {
                "type": "group",
                "blend_mode": "normal",
                "opacity": 255,
                "children": ["Hero_Girl_Silhouette", "Hero_Boy_Silhouette", "Red_Thread_Fate", "Thread_Glow"],
            },
            "04_Petals_Particles": {
                "type": "group",
                "blend_mode": "normal",
                "opacity": 255,
                "children": ["Background_Petals", "Bokeh_Orbs", "Foreground_Swirling_Petals"],
            },
            "05_Typography_Title": {
                "type": "group",
                "blend_mode": "normal",
                "opacity": 255,
                "children": ["Header_Credit", "Japanese_Title_Kanji", "English_Subtitle", "Release_Banner"],
            },
        },
    }
