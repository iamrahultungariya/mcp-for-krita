"""Computer Vision Studio Cel Decomposer with digital under-trapping and Bézier line vectorization."""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np

from krita_mcp_lazy.cel_engine.models import (
    CelArtDecomposition,
    FlatRegion,
    HighlightRegion,
    ShadowRegion,
    TaperedStroke,
)

logger = logging.getLogger(__name__)


class CelArtDecomposer:
    """Decomposes illustrations into vector lineart, trapped flats, and lighting layers."""

    def __init__(
        self,
        trapping_dilation_px: int = 2,
        dog_sigma1: float = 1.0,
        dog_sigma2: float = 2.4,
        dog_threshold: int = 15,
        min_stroke_length: int = 3,
        color_quantization_k: int = 16,
    ) -> None:
        self.trapping_dilation_px = max(1, trapping_dilation_px)
        self.dog_sigma1 = dog_sigma1
        self.dog_sigma2 = dog_sigma2
        self.dog_threshold = dog_threshold
        self.min_stroke_length = min_stroke_length
        self.color_quantization_k = color_quantization_k

    def _extract_lineart_mask(self, bgr: np.ndarray) -> np.ndarray:
        """Extract high-precision lineart mask using multi-scale Difference-of-Gaussians (DoG)."""
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        g1 = cv2.GaussianBlur(gray, (0, 0), sigmaX=self.dog_sigma1, sigmaY=self.dog_sigma1)
        g2 = cv2.GaussianBlur(gray, (0, 0), sigmaX=self.dog_sigma2, sigmaY=self.dog_sigma2)

        # Invert subtraction so lines become positive
        dog = cv2.subtract(g2, g1)

        # Threshold to binary line mask
        _, mask = cv2.threshold(dog, self.dog_threshold, 255, cv2.THRESH_BINARY)

        # Morphological clean up of tiny noise
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Also incorporate high-contrast dark contours
        adaptive = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11,
            4,
        )
        combined = cv2.bitwise_or(mask, adaptive)

        # Keep only connected ink structures of reasonable size
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(combined, connectivity=8)
        clean_mask = np.zeros_like(combined)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] >= 4:
                clean_mask[labels == i] = 255

        return clean_mask

    def _skeletonize(self, binary_mask: np.ndarray) -> np.ndarray:
        """Morphological skeletonization producing 1-pixel centerline network."""
        skel = np.zeros(binary_mask.shape, dtype=np.uint8)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        curr = binary_mask.copy()

        while cv2.countNonZero(curr) > 0:
            eroded = cv2.erode(curr, element)
            temp = cv2.dilate(eroded, element)
            temp = cv2.subtract(curr, temp)
            skel = cv2.bitwise_or(skel, temp)
            curr = eroded

        return skel

    def _trace_vector_strokes(
        self,
        skel: np.ndarray,
        dist_map: np.ndarray,
    ) -> List[TaperedStroke]:
        """Convert skeleton into continuous ordered Bézier curves with pressure tapering."""
        h, w = skel.shape
        visited = np.zeros((h, w), dtype=bool)
        strokes: List[TaperedStroke] = []

        neighbors = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1),
        ]

        # Identify degree-1 endpoints first to preserve hair tips and natural stroke starts
        skel_pts = np.argwhere(skel > 0)
        endpoints: List[Tuple[int, int]] = []
        for y, x in skel_pts:
            cnt = sum(
                1
                for dy, dx in neighbors
                if 0 <= y + dy < h and 0 <= x + dx < w and skel[y + dy, x + dx] > 0
            )
            if cnt <= 1:
                endpoints.append((y, x))

        max_dist = float(np.max(dist_map)) if np.max(dist_map) > 0 else 1.0

        # Prioritize endpoints as path origins, then unvisited loop points
        candidates = endpoints + [tuple(p) for p in skel_pts]
        stroke_idx = 0

        for sy, sx in candidates:
            if visited[sy, sx] or skel[sy, sx] == 0:
                continue

            path: List[Tuple[float, float]] = [(float(sx), float(sy))]
            visited[sy, sx] = True
            cy, cx = sy, sx

            while True:
                next_pt = None
                for dy, dx in neighbors:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and skel[ny, nx] > 0 and not visited[ny, nx]:
                        next_pt = (ny, nx)
                        break
                if next_pt is None:
                    break
                cy, cx = next_pt
                visited[cy, cx] = True
                path.append((float(cx), float(cy)))

            if len(path) >= self.min_stroke_length:
                # Simplify with Ramer-Douglas-Peucker algorithm
                pts_arr = np.array(path, dtype=np.float32).reshape(-1, 1, 2)
                approx = cv2.approxPolyDP(pts_arr, 1.2, False)
                simplified: List[Tuple[float, float]] = [
                    (float(pt[0][0]), float(pt[0][1])) for pt in approx
                ]
                if len(simplified) < 2:
                    simplified = path

                # Sample distance transform to compute dynamic pressure profile
                pressures: List[float] = []
                for px, py in simplified:
                    ix = int(np.clip(round(px), 0, w - 1))
                    iy = int(np.clip(round(py), 0, h - 1))
                    norm_val = float(dist_map[iy, ix]) / max_dist
                    # Map to [0.15, 1.0]
                    p_val = 0.15 + 0.85 * norm_val
                    pressures.append(min(1.0, max(0.15, p_val)))

                # Apply G-Pen taper to entry and exit points
                if len(pressures) >= 2:
                    pressures[0] = max(0.15, pressures[0] * 0.4)
                    pressures[-1] = max(0.15, pressures[-1] * 0.4)

                strokes.append(
                    TaperedStroke(
                        stroke_id=f"ink_stroke_{stroke_idx:04d}",
                        points=simplified,
                        pressures=pressures,
                        brush_preset="f)_Ink-3_Gpen",
                        color="#000000",
                        base_width=max_dist * 2.0,
                    )
                )
                stroke_idx += 1

        return strokes

    def _extract_trapped_flats(
        self,
        bgr: np.ndarray,
        lineart_mask: np.ndarray,
    ) -> Tuple[List[FlatRegion], np.ndarray]:
        """Extract quantized flat colors and dilate masks under ink lines to lock zero white edge fringe."""
        h, w = bgr.shape[:2]

        # Bilateral filter to smooth texture while keeping sharp edges
        smoothed = cv2.bilateralFilter(bgr, 9, 75, 75)

        # Mask out lineart before color sampling
        clean_flats_rgb = smoothed.copy()
        clean_flats_rgb[lineart_mask > 0] = [255, 255, 255]

        # Color quantization via K-Means
        pixels = clean_flats_rgb.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        k = min(self.color_quantization_k, max(2, len(np.unique(pixels, axis=0))))
        _, labels, centers = cv2.kmeans(
            pixels,
            k,
            None,
            criteria,
            3,
            cv2.KMEANS_PP_CENTERS,
        )

        centers = np.uint8(centers)
        quantized = centers[labels.flatten()].reshape(smoothed.shape)

        # Build composite trapped flats buffer (RGBA)
        composite_flats = np.zeros((h, w, 4), dtype=np.uint8)
        composite_flats[:, :, :3] = quantized
        composite_flats[:, :, 3] = 255

        # Dilation kernel for digital under-trapping
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.trapping_dilation_px * 2 + 1, self.trapping_dilation_px * 2 + 1),
        )

        flat_regions: List[FlatRegion] = []
        label_map = labels.reshape((h, w))

        for idx, center_bgr in enumerate(centers):
            # Binary mask of this color cluster
            raw_mask = (label_map == idx).astype(np.uint8) * 255
            # Ignore pure background white if empty
            if cv2.countNonZero(raw_mask) < 10:
                continue

            # Digital Under-Trapping: Dilate mask into lineart mask region
            dilated = cv2.dilate(raw_mask, kernel, iterations=self.trapping_dilation_px)
            # Confine dilation strictly to raw_mask + lineart_mask (don't bleed into adjacent colors)
            trapped_mask = cv2.bitwise_and(
                dilated,
                cv2.bitwise_or(raw_mask, lineart_mask),
            )

            # Hex color string (#RRGGBB)
            hex_color = f"#{center_bgr[2]:02x}{center_bgr[1]:02x}{center_bgr[0]:02x}"

            # Bounding box
            x, y, bw, bh = cv2.boundingRect(trapped_mask)

            flat_regions.append(
                FlatRegion(
                    region_id=f"flat_{idx:03d}",
                    color_hex=hex_color,
                    mask=trapped_mask,
                    bbox=(x, y, bw, bh),
                    pixel_count=int(cv2.countNonZero(trapped_mask)),
                )
            )

        return flat_regions, composite_flats

    def _extract_shadows_and_highlights(
        self,
        bgr: np.ndarray,
        lineart_mask: np.ndarray,
    ) -> Tuple[List[ShadowRegion], List[HighlightRegion], np.ndarray, np.ndarray]:
        """Extract cel-shadows for Multiply layers and rim/specular highlights for Screen layers."""
        h, w = bgr.shape[:2]

        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]

        # Compute adaptive luminance bounds
        l_masked = l_channel[lineart_mask == 0]
        if len(l_masked) == 0:
            l_masked = l_channel.flatten()

        p20 = float(np.percentile(l_masked, 20))
        p85 = float(np.percentile(l_masked, 85))

        # Hard cel-shadow mask (darker areas not part of ink line)
        shadow_mask = np.zeros((h, w), dtype=np.uint8)
        shadow_mask[(l_channel <= p20) & (lineart_mask == 0)] = 255

        # Highlights mask (specular and rim illumination)
        highlight_mask = np.zeros((h, w), dtype=np.uint8)
        highlight_mask[(l_channel >= p85) & (lineart_mask == 0)] = 255

        # Clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        shadow_mask = cv2.morphologyEx(shadow_mask, cv2.MORPH_OPEN, kernel)
        highlight_mask = cv2.morphologyEx(highlight_mask, cv2.MORPH_OPEN, kernel)

        # Composite Multiply buffer: Dark indigo/violet shadow (#201835) with alpha
        composite_shadows = np.zeros((h, w, 4), dtype=np.uint8)
        composite_shadows[shadow_mask > 0] = [53, 24, 32, 115]  # BGRA order: B=53, G=24, R=32, A=115 (~45% opacity)

        # Composite Highlight buffer: Warm pale gold highlight (#FFF8E0) with alpha
        composite_highlights = np.zeros((h, w, 4), dtype=np.uint8)
        composite_highlights[highlight_mask > 0] = [224, 248, 255, 178]  # BGRA order: A=178 (~70% opacity)

        shadow_regions = [
            ShadowRegion(
                region_id="cel_shadow_001",
                mask=shadow_mask,
                color_hex="#201835",
                opacity=0.45,
            )
        ]
        highlight_regions = [
            HighlightRegion(
                region_id="cel_highlight_001",
                mask=highlight_mask,
                color_hex="#FFF8E0",
                opacity=0.70,
            )
        ]

        return shadow_regions, highlight_regions, composite_shadows, composite_highlights

    def decompose(self, image_input: Union[str, np.ndarray]) -> CelArtDecomposition:
        """Execute full decomposition pipeline on reference image."""
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Reference image not found: {image_input}")
            bgr = cv2.imread(image_input)
            if bgr is None:
                raise ValueError(f"Failed to decode image from path: {image_input}")
        elif isinstance(image_input, np.ndarray):
            bgr = image_input.copy()
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        h, w = bgr.shape[:2]
        logger.info("Decomposing %dx%d cel art...", w, h)

        # 1. Lineart extraction via DoG
        lineart_mask = self._extract_lineart_mask(bgr)

        # 2. Euclidean Distance Transform for pressure profile
        dist_map = cv2.distanceTransform(lineart_mask, cv2.DIST_L2, 5)

        # 3. Medial Axis Skeletonization
        skel = self._skeletonize(lineart_mask)

        # 4. Continuous Bézier stroke tracing with G-Pen pressure profile
        vector_strokes = self._trace_vector_strokes(skel, dist_map)

        # 5. Flat colors with digital under-trapping
        flat_regions, comp_flats = self._extract_trapped_flats(bgr, lineart_mask)

        # 6. Cel-shadows and highlights
        shadows, highlights, comp_shadows, comp_highlights = self._extract_shadows_and_highlights(
            bgr, lineart_mask
        )

        logger.info(
            "Decomposition complete: %d vector strokes, %d flat regions, %d shadows, %d highlights.",
            len(vector_strokes),
            len(flat_regions),
            len(shadows),
            len(highlights),
        )

        return CelArtDecomposition(
            vector_strokes=vector_strokes,
            flat_regions=flat_regions,
            cel_shadows=shadows,
            highlights=highlights,
            lineart_mask=lineart_mask,
            composite_flats=comp_flats,
            composite_shadows=comp_shadows,
            composite_highlights=comp_highlights,
            width=w,
            height=h,
        )
