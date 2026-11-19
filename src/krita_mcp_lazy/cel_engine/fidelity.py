"""Vision diff fidelity evaluator computing SSIM and Edge IoU between reference and canvas render."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FidelityReport:
    """Quantitative fidelity scorecard certifying near-identical ('ditto') art reproduction."""

    ssim: float
    edge_iou: float
    mean_squared_error: float
    is_approved: bool
    defect_regions: List[Dict[str, int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ssim": round(self.ssim, 4),
            "edge_iou": round(self.edge_iou, 4),
            "mean_squared_error": round(self.mean_squared_error, 4),
            "is_approved": self.is_approved,
            "defect_count": len(self.defect_regions),
        }


class FidelityGate:
    """Verifies that an autonomous digital painting meets professional studio fidelity thresholds."""

    def __init__(
        self,
        min_ssim: float = 0.88,
        min_edge_iou: float = 0.80,
        grid_divisions: int = 4,
    ) -> None:
        self.min_ssim = min_ssim
        self.min_edge_iou = min_edge_iou
        self.grid_divisions = grid_divisions

    def _compute_ssim(
        self,
        img1: np.ndarray,
        img2: np.ndarray,
    ) -> Tuple[float, np.ndarray]:
        """Compute exact Structural Similarity Index (SSIM) map and scalar mean."""
        # Convert to float32 normalized [0.0, 1.0]
        i1 = img1.astype(np.float32) / 255.0
        i2 = img2.astype(np.float32) / 255.0

        c1 = (0.01) ** 2
        c2 = (0.03) ** 2

        # Gaussian smoothing filter
        mu1 = cv2.GaussianBlur(i1, (11, 11), 1.5)
        mu2 = cv2.GaussianBlur(i2, (11, 11), 1.5)

        mu1_sq = mu1 * mu1
        mu2_sq = mu2 * mu2
        mu1_mu2 = mu1 * mu2

        sigma1_sq = cv2.GaussianBlur(i1 * i1, (11, 11), 1.5) - mu1_sq
        sigma2_sq = cv2.GaussianBlur(i2 * i2, (11, 11), 1.5) - mu2_sq
        sigma12 = cv2.GaussianBlur(i1 * i2, (11, 11), 1.5) - mu1_mu2

        num = (2.0 * mu1_mu2 + c1) * (2.0 * sigma12 + c2)
        den = (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)
        ssim_map = num / np.maximum(den, 1e-7)

        return float(np.mean(ssim_map)), ssim_map

    def _compute_edge_iou(self, img1: np.ndarray, img2: np.ndarray) -> float:
        """Compute Intersection-over-Union of Canny edge maps."""
        edges1 = cv2.Canny(img1, 50, 150)
        edges2 = cv2.Canny(img2, 50, 150)

        # Dilate slightly by 1px to accommodate anti-aliased subpixel drift
        kernel = np.ones((3, 3), np.uint8)
        dilated1 = cv2.dilate(edges1, kernel, iterations=1)
        dilated2 = cv2.dilate(edges2, kernel, iterations=1)

        intersection = np.logical_and(dilated1 > 0, dilated2 > 0)
        union = np.logical_or(edges1 > 0, edges2 > 0)

        u_sum = np.sum(union)
        if u_sum == 0:
            return 1.0
        return float(np.sum(intersection) / u_sum)

    def evaluate(self, ref_path: str, render_path: str) -> FidelityReport:
        """Evaluate visual similarity between reference image and canvas render."""
        if not os.path.exists(ref_path):
            raise FileNotFoundError(f"Reference image not found: {ref_path}")
        if not os.path.exists(render_path):
            raise FileNotFoundError(f"Rendered image not found: {render_path}")

        ref_bgr = cv2.imread(ref_path)
        render_bgr = cv2.imread(render_path)

        # Scale render to match reference resolution if necessary
        if ref_bgr.shape != render_bgr.shape:
            render_bgr = cv2.resize(
                render_bgr,
                (ref_bgr.shape[1], ref_bgr.shape[0]),
                interpolation=cv2.INTER_LANCZOS4,
            )

        ref_gray = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
        render_gray = cv2.cvtColor(render_bgr, cv2.COLOR_BGR2GRAY)

        # Mean Squared Error
        mse = float(np.mean((ref_gray.astype(np.float32) - render_gray.astype(np.float32)) ** 2))

        # SSIM calculation
        mean_ssim, ssim_map = self._compute_ssim(ref_gray, render_gray)

        # Edge IoU calculation
        edge_iou = self._compute_edge_iou(ref_gray, render_gray)

        # Detect regional defect blocks
        h, w = ref_gray.shape
        step_y = max(1, h // self.grid_divisions)
        step_x = max(1, w // self.grid_divisions)
        defect_regions: List[Dict[str, int]] = []

        for gy in range(0, h, step_y):
            for gx in range(0, w, step_x):
                block = ssim_map[gy : min(h, gy + step_y), gx : min(w, gx + step_x)]
                if block.size > 0 and float(np.mean(block)) < (self.min_ssim - 0.12):
                    defect_regions.append({
                        "x": gx,
                        "y": gy,
                        "width": min(step_x, w - gx),
                        "height": min(step_y, h - gy),
                    })

        is_approved = bool(mean_ssim >= self.min_ssim and edge_iou >= self.min_edge_iou)

        logger.info(
            "Fidelity check: SSIM=%.4f (target >= %.2f), Edge IoU=%.4f (target >= %.2f) -> Approved=%s",
            mean_ssim,
            self.min_ssim,
            edge_iou,
            self.min_edge_iou,
            is_approved,
        )

        return FidelityReport(
            ssim=mean_ssim,
            edge_iou=edge_iou,
            mean_squared_error=mse,
            is_approved=is_approved,
            defect_regions=defect_regions,
        )
