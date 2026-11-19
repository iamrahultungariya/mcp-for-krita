"""Tests for SSIM and Edge IoU FidelityGate."""

import numpy as np
import cv2
import pytest
from krita_mcp_lazy.cel_engine.fidelity import FidelityGate, FidelityReport


def test_fidelity_gate_validates_match(tmp_path):
    """Verify fidelity gate approves matching images and rejects scribbles."""
    gate = FidelityGate(min_ssim=0.85, min_edge_iou=0.75)

    # Reference ground-truth image (face outline with flat fill)
    ref = np.full((150, 150, 3), 240, dtype=np.uint8)
    cv2.circle(ref, (75, 75), 45, (0, 0, 0), 3)
    cv2.circle(ref, (75, 75), 42, (255, 200, 150), -1)
    ref_path = str(tmp_path / "ref.png")
    cv2.imwrite(ref_path, ref)

    # Near identical match with minor edge blur
    good = ref.copy()
    cv2.GaussianBlur(good, (3, 3), 0.5, dst=good)
    good_path = str(tmp_path / "good.png")
    cv2.imwrite(good_path, good)

    # Completely different scribble/noise
    bad = np.random.randint(0, 255, (150, 150, 3), dtype=np.uint8)
    bad_path = str(tmp_path / "bad.png")
    cv2.imwrite(bad_path, bad)

    # Evaluate good match
    report_good = gate.evaluate(ref_path, good_path)
    assert isinstance(report_good, FidelityReport)
    assert report_good.is_approved is True
    assert report_good.ssim >= 0.85
    assert report_good.edge_iou >= 0.70

    # Evaluate bad match
    report_bad = gate.evaluate(ref_path, bad_path)
    assert report_bad.is_approved is False
    assert report_bad.ssim < 0.50


def test_fidelity_gate_detects_defect_regions(tmp_path):
    """Verify fidelity gate flags specific defective grid quadrants."""
    gate = FidelityGate(min_ssim=0.88, min_edge_iou=0.80)

    ref = np.full((128, 128, 3), 255, dtype=np.uint8)
    cv2.circle(ref, (64, 64), 30, (0, 0, 0), 2)
    ref_path = str(tmp_path / "ref_block.png")
    cv2.imwrite(ref_path, ref)

    # Corrupt bottom-right quadrant only
    corrupt = ref.copy()
    corrupt[64:128, 64:128] = np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8)
    corrupt_path = str(tmp_path / "corrupt.png")
    cv2.imwrite(corrupt_path, corrupt)

    report = gate.evaluate(ref_path, corrupt_path)
    assert len(report.defect_regions) >= 1
    # Check that defect region intersects the corrupted area
    has_bottom_right = any(
        r["x"] >= 64 and r["y"] >= 64 for r in report.defect_regions
    )
    assert has_bottom_right is True
