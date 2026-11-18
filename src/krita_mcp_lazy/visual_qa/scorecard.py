"""8-Pillar quality scorecard evaluator enforcing >=85/100 production gate."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field

WEIGHTS = {
    "anatomy_proportions": 0.15,
    "line_quality": 0.15,
    "composition_perspective": 0.15,
    "lighting_shading": 0.15,
    "color_materials": 0.10,
    "reference_fidelity": 0.15,
    "detail_finish": 0.10,
    "layer_editability": 0.05,
}


class QualityCriteria(BaseModel):
    """The 8 professional art studio evaluation categories (each 0.0 to 100.0)."""

    anatomy_proportions: float = Field(ge=0.0, le=100.0)
    line_quality: float = Field(ge=0.0, le=100.0)
    composition_perspective: float = Field(ge=0.0, le=100.0)
    lighting_shading: float = Field(ge=0.0, le=100.0)
    color_materials: float = Field(ge=0.0, le=100.0)
    reference_fidelity: float = Field(ge=0.0, le=100.0)
    detail_finish: float = Field(ge=0.0, le=100.0)
    layer_editability: float = Field(ge=0.0, le=100.0)


class ScorecardEvaluator:
    """Calculates weighted composite score and determines whether artwork satisfies studio criteria."""

    def calculate_total(self, criteria: QualityCriteria) -> float:
        """Calculate weighted score out of 100.0 across all 8 pillars."""
        total = 0.0
        data = criteria.model_dump()
        for key, weight in WEIGHTS.items():
            total += data[key] * weight
        return round(total, 2)

    def passes_production_gate(self, score: float, threshold: float = 85.0) -> bool:
        """True if the score meets or exceeds the required threshold (default 85/100)."""
        return score >= threshold

    def evaluate(self, criteria: QualityCriteria, threshold: float = 85.0) -> Dict[str, Any]:
        """Perform comprehensive evaluation with per-pillar breakdown and actionable feedback."""
        total_score = self.calculate_total(criteria)
        passed = self.passes_production_gate(total_score, threshold)

        breakdown = criteria.model_dump()
        recommendations: List[str] = []

        if breakdown["anatomy_proportions"] < 80.0:
            recommendations.append("Review head-to-body ratios and eye/chin guide line alignments")
        if breakdown["line_quality"] < 80.0:
            recommendations.append("Apply dynamic pressure taper and smooth vector Bézier interpolation to lineart")
        if breakdown["composition_perspective"] < 80.0:
            recommendations.append("Align key focal anchors to Rule of Thirds or vanishing point horizon lines")
        if breakdown["lighting_shading"] < 80.0:
            recommendations.append("Strengthen 3-point illumination contrast (key, fill, and rim separation)")
        if breakdown["color_materials"] < 80.0:
            recommendations.append("Refine PBR material layers (specular, core shadows, and ambient reflections)")
        if breakdown["reference_fidelity"] < 80.0:
            recommendations.append("Match silhouette, costume landmarks, and palette tokens to reference sheet")
        if breakdown["detail_finish"] < 80.0:
            recommendations.append("Add edge highlights, ambient occlusion crevices, and atmospheric haze")
        if breakdown["layer_editability"] < 80.0:
            recommendations.append("Organize layers into semantic groups with non-destructive clipping masks")

        return {
            "total_score": total_score,
            "threshold": threshold,
            "passed": passed,
            "breakdown": breakdown,
            "weights": WEIGHTS,
            "recommendations": recommendations,
        }
