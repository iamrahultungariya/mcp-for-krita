"""Registry and definitions of the 60 comprehensive dogfooding challenges across 8 disciplines."""

from typing import List
from pydantic import BaseModel, Field


class Challenge(BaseModel):
    """Specification of an individual dogfooding production test."""

    id: int = Field(ge=1, le=60)
    title: str
    category: str
    description: str
    target_score: float = Field(default=85.0, ge=0.0, le=100.0)


# 1. Character Illustration (Tests 01-10)
_CHARACTER_CHALLENGES = [
    Challenge(id=1, title="Hero Character Concept", category="character_illustration", description="Scaffold and render primary hero character with baseline proportions and lineart"),
    Challenge(id=2, title="Turnaround Model Sheet (4 Views)", category="character_illustration", description="Generate front, 3/4, side, and back views with strict eye/chin guide alignment"),
    Challenge(id=3, title="Expression Sheet (6 Emotions)", category="character_illustration", description="Build neutral, happy, angry, sad, shocked, and scared facial variation groups"),
    Challenge(id=4, title="Visemes & Mouth Shapes", category="character_illustration", description="Scaffold standard 8-viseme mouth shape set for 2D animation lip sync"),
    Challenge(id=5, title="Hair Locks & Strand Dynamics", category="character_illustration", description="Render tapered Bézier locks with highlight ribbon shading"),
    Challenge(id=6, title="Hands & Fingers Anatomical Structure", category="character_illustration", description="Verify hand anatomy, knuckle guides, and finger segment proportions"),
    Challenge(id=7, title="Clothing Folds & Drapery", category="character_illustration", description="Render tension, pipe, and diaper folds with fabric shading layers"),
    Challenge(id=8, title="Dynamic Action Pose", category="character_illustration", description="Construct line-of-action dynamic silhouette with foreshortening"),
    Challenge(id=9, title="Lighting Variation on Character", category="character_illustration", description="Apply key, fill, and rim light contrast on character portrait"),
    Challenge(id=10, title="Dual-Character Interaction", category="character_illustration", description="Align height ratios, eye-lines, and contact points between two characters"),
]

# 2. Environment & Background (Tests 11-18)
_ENVIRONMENT_CHALLENGES = [
    Challenge(id=11, title="Horror Interior Room", category="environment_background", description="Design distressed indoor room with moody shadows and atmospheric haze"),
    Challenge(id=12, title="Natural Forest Canopy", category="environment_background", description="Render multi-depth organic foliage with tree trunks and ground foliage"),
    Challenge(id=13, title="Cyberpunk Rainy Urban Alley", category="environment_background", description="Construct high-contrast city street with neon reflections and wet ground"),
    Challenge(id=14, title="Interior Architecture & Living Room", category="environment_background", description="Set up 1-point perspective interior with furniture alignment"),
    Challenge(id=15, title="Multi-Room Basement Layout", category="environment_background", description="Scaffold architectural floor plan and wall planes"),
    Challenge(id=16, title="2-Point Perspective Building Exterior", category="environment_background", description="Calculate vanishing points and draw converging architectural facades"),
    Challenge(id=17, title="Night Scene with Multi-Light Radiance", category="environment_background", description="Render dark ambient background with warm lantern and cool moonlight"),
    Challenge(id=18, title="Daylight Atmospheric Depth", category="environment_background", description="Generate 5-plane depth hierarchy with distance-based haze desaturation"),
]

# 3. Props & Material Studies (Tests 19-26)
_PROP_CHALLENGES = [
    Challenge(id=19, title="Furniture Set (Chair, Table, Bed)", category="props_materials", description="Author modular furniture props with correct isometric/perspective scale"),
    Challenge(id=20, title="Fabric & Velvet Curtains", category="props_materials", description="Simulate soft cloth sheen, ambient occlusion, and edge rim highlights"),
    Challenge(id=21, title="Natural Assets (Rocks & Vegetation)", category="props_materials", description="Construct mossy stones and fern foliage with layered shading"),
    Challenge(id=22, title="Mechanical Clockwork Prop", category="props_materials", description="Model precision brass gears and metallic casing"),
    Challenge(id=23, title="Realistic Wood Grain Texture", category="props_materials", description="Build base, ring texture, knot details, and specular varnish"),
    Challenge(id=24, title="Glass & Mirror Reflections", category="props_materials", description="Author transparent glass bottle with refraction and specular glints"),
    Challenge(id=25, title="Stone Wall & Surface Cracks", category="props_materials", description="Generate chiseled stone block contours and deep crevices"),
    Challenge(id=26, title="Water Surface & Caustic Shading", category="props_materials", description="Render water depth gradients, foam highlights, and caustic ripples"),
]

# 4. Drawing & Painting Intelligence (Tests 27-34)
_PAINTING_CHALLENGES = [
    Challenge(id=27, title="Brush Stroke Fidelity (Pencil vs Ink vs Airbrush)", category="drawing_intelligence", description="Verify preset parameters, size scaling, and stroke execution"),
    Challenge(id=28, title="Bézier Curve Smoothing & Taper", category="drawing_intelligence", description="Interpolate cubic Bézier curves with natural inking pressure envelope"),
    Challenge(id=29, title="Line Art Cleanup & Contour Closure", category="drawing_intelligence", description="Produce clean contiguous line boundaries suitable for flat color fills"),
    Challenge(id=30, title="Multi-Layer Skin Shading", category="drawing_intelligence", description="Render skin base, subsurface scatter rim, core shadow, and specular"),
    Challenge(id=31, title="Hair Highlights & Ribbon Strands", category="drawing_intelligence", description="Paint specular ring highlights following hair curvature"),
    Challenge(id=32, title="Cloth & Garment Shading", category="drawing_intelligence", description="Apply non-destructive clipping mask shadows across garment folds"),
    Challenge(id=33, title="Smooth Gradient Soft-Edge Blending", category="drawing_intelligence", description="Blend color transitions smoothly with airbrush and flow control"),
    Challenge(id=34, title="Complex Mask Shading", category="drawing_intelligence", description="Use transparency and filter masks for non-destructive local adjustment"),
]

# 5. Advanced Visual Challenges (Tests 35-42)
_ADVANCED_VISUAL_CHALLENGES = [
    Challenge(id=35, title="Cinematic Chiaroscuro Lighting", category="advanced_visual", description="High-contrast dramatic lighting with deep shadows and sharp key lights"),
    Challenge(id=36, title="3-Point Perspective Cityscape", category="advanced_visual", description="Calculate low-angle skyscraper vanishing points including vertical zenith"),
    Challenge(id=37, title="Visual FX (Glow & Sparks)", category="advanced_visual", description="Add color dodge fire embers, laser glow, and energy sparks"),
    Challenge(id=38, title="Atmospheric Volumetric Fog", category="advanced_visual", description="Layer diffuse fog planes between foreground characters and background"),
    Challenge(id=39, title="Golden Hour Sunset Palette", category="advanced_visual", description="Harmonize warm amber highlights with purple atmospheric ambient bounce"),
    Challenge(id=40, title="Underwater Light Rays & Caustics", category="advanced_visual", description="Render god-rays breaking through ocean surface with caustic nets"),
    Challenge(id=41, title="Dramatic Rim Light Silhouette", category="advanced_visual", description="Render dark character silhouette defined strictly by bright rim contours"),
    Challenge(id=42, title="Epic Scale Landscape with Tiny Explorer", category="advanced_visual", description="Establish immense composition with monumental background elements"),
]

# 6. Document & Layer Stress Tests (Tests 43-48)
_STRESS_CHALLENGES = [
    Challenge(id=43, title="100-Layer Complex Artwork Hierarchy", category="document_stress", description="Manage 100 deep layers without performance degradation or IPC timeout"),
    Challenge(id=44, title="Deeply Nested Groups & Multi-Level Masks", category="document_stress", description="Traverse and mutate 5-level nested group hierarchies with clipping"),
    Challenge(id=45, title="4K Canvas Stress Test (3840x2160 @ 300 DPI)", category="document_stress", description="Create and paint 4K ultra-high-resolution canvas within RAM budget"),
    Challenge(id=46, title="Multi-Document Concurrent Handling", category="document_stress", description="Switch active document context across multiple simultaneously open files"),
    Challenge(id=47, title="KRA Save-Close-Reopen Fidelity", category="document_stress", description="Verify 100% layer tree, opacity, and mask preservation upon reload"),
    Challenge(id=48, title="50-Asset Batch Slice Export", category="document_stress", description="Batch export 50 individual prop elements to transparent PNGs"),
]

# 7. Animation & Production Tests (Tests 49-54)
_ANIMATION_CHALLENGES = [
    Challenge(id=49, title="5-Second Hand-Drawn Idle Loop", category="animation_production", description="Scaffold 120-frame timeline with raster keyframes and timing"),
    Challenge(id=50, title="Walk-Cycle Key Poses & In-Betweens", category="animation_production", description="Structure contact, down, pass, and up poses with onion skinning"),
    Challenge(id=51, title="Facial Expression Morph", category="animation_production", description="Transition neutral to happy expression across keyframe intervals"),
    Challenge(id=52, title="10-Second Frame Sequence with RAM Guard", category="animation_production", description="Render 240 frames staying strictly below the 500 MiB cache budget"),
    Challenge(id=53, title="PNG Sequence Render Verification", category="animation_production", description="Export frame sequence and audit for zero-byte or missing files"),
    Challenge(id=54, title="Complete Layered Tahoma2D Export", category="animation_production", description="Package rigged character cutouts and generate valid .tnz scene project"),
]

# 8. Visual Correction Challenges (Tests 55-60)
_CORRECTION_CHALLENGES = [
    Challenge(id=55, title="Anatomical Proportion Auto-Correction", category="visual_correction", description="Detect head-ratio discrepancy and adjust guide markers"),
    Challenge(id=56, title="Perspective Horizon Distortion Repair", category="visual_correction", description="Realign misaligned vanishing points to horizontal level"),
    Challenge(id=57, title="Missing Finger Anatomical Fix", category="visual_correction", description="Reconstruct hand contour structure with 5-finger anatomical standard"),
    Challenge(id=58, title="Layer Order Semantic Auto-Fix", category="visual_correction", description="Reorganize lines above color fills and background beneath characters"),
    Challenge(id=59, title="Color Inconsistency Harmonization", category="visual_correction", description="Re-map out-of-gamut/clashing colors to chosen style palette tokens"),
    Challenge(id=60, title="Interrupted Job Checkpoint Rollback", category="visual_correction", description="Restore clean pre-mutation canvas snapshot upon simulated failure"),
]


def get_all_challenges() -> List[Challenge]:
    """Retrieve the complete list of 60 official production challenges."""
    all_ch = (
        _CHARACTER_CHALLENGES
        + _ENVIRONMENT_CHALLENGES
        + _PROP_CHALLENGES
        + _PAINTING_CHALLENGES
        + _ADVANCED_VISUAL_CHALLENGES
        + _STRESS_CHALLENGES
        + _ANIMATION_CHALLENGES
        + _CORRECTION_CHALLENGES
    )
    assert len(all_ch) == 60, f"Expected exactly 60 challenges, got {len(all_ch)}"
    return all_ch
