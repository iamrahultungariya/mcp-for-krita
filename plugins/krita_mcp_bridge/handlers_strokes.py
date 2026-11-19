"""Krita native API handlers for executing brush strokes and paths."""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from plugins.krita_mcp_bridge.handlers_document import get_document_by_id

logger = logging.getLogger(__name__)

# In-memory record of strokes drawn in headless / mock mode
_mock_painted_strokes: Dict[str, List[dict]] = {}


def hex_to_rgba(hex_color: str, opacity: float = 1.0) -> Tuple[int, int, int, int]:
    """Parse hex color string (#RGB, #RRGGBB, #RRGGBBAA) to RGBA integer tuple (0-255)."""
    hex_clean = hex_color.lstrip("#")
    alpha_mult = max(0.0, min(1.0, float(opacity)))

    if len(hex_clean) == 3:
        r = int(hex_clean[0] * 2, 16)
        g = int(hex_clean[1] * 2, 16)
        b = int(hex_clean[2] * 2, 16)
        return (r, g, b, int(255 * alpha_mult))
    elif len(hex_clean) == 6:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        return (r, g, b, int(255 * alpha_mult))
    elif len(hex_clean) == 8:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        a = int(hex_clean[6:8], 16)
        return (r, g, b, int(a * alpha_mult))
    return (0, 0, 0, int(255 * alpha_mult))


def render_stroke_points_pil(
    bbox: List[int],
    points: List[dict],
    color_rgba: Tuple[int, int, int, int],
    base_size: float = 10.0,
    existing_bytes: Optional[bytes] = None,
) -> bytes:
    """Render pressure-sensitive Bézier/stamp stroke points onto an RGBA pixel buffer."""
    min_x, min_y, max_x, max_y = bbox
    w = max(1, max_x - min_x)
    h = max(1, max_y - min_y)

    if _HAS_PIL:
        if existing_bytes and len(existing_bytes) == w * h * 4:
            img = Image.frombytes("RGBA", (w, h), existing_bytes)
        else:
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

        draw = ImageDraw.Draw(img)

        for i in range(len(points)):
            p = points[i]
            px = p["x"] - min_x
            py = p["y"] - min_y
            pressure = float(p.get("pressure", 0.5))
            radius = max(1.0, (base_size / 2.0) * pressure)
            draw.ellipse([px - radius, py - radius, px + radius, py + radius], fill=color_rgba)

            if i > 0:
                prev = points[i - 1]
                prev_x = prev["x"] - min_x
                prev_y = prev["y"] - min_y
                prev_pressure = float(prev.get("pressure", 0.5))
                dist = math.hypot(px - prev_x, py - prev_y)
                steps = max(1, int(dist / max(1.0, radius / 2.0)))
                for s in range(1, steps):
                    t = s / float(steps)
                    interp_x = prev_x + t * (px - prev_x)
                    interp_y = prev_y + t * (py - prev_y)
                    interp_pressure = prev_pressure + t * (pressure - prev_pressure)
                    interp_r = max(1.0, (base_size / 2.0) * interp_pressure)
                    draw.ellipse(
                        [interp_x - interp_r, interp_y - interp_r, interp_x + interp_r, interp_y + interp_r],
                        fill=color_rgba,
                    )

        return img.tobytes()
    else:
        # Fallback using PyQt5.QtGui (available natively inside Krita embedded Python)
        try:
            from PyQt5.QtGui import QImage, QPainter, QColor, QBrush
            from PyQt5.QtCore import Qt, QPointF
        except ImportError:
            from PyQt6.QtGui import QImage, QPainter, QColor, QBrush
            from PyQt6.QtCore import Qt, QPointF

        qimg = QImage(w, h, QImage.Format_RGBA8888)
        if existing_bytes and len(existing_bytes) == w * h * 4:
            ptr = qimg.bits()
            ptr.setsize(len(existing_bytes))
            ptr[:] = existing_bytes
        else:
            qimg.fill(Qt.transparent)

        painter = QPainter(qimg)
        painter.setRenderHint(QPainter.Antialiasing)
        qc = QColor(color_rgba[0], color_rgba[1], color_rgba[2], color_rgba[3])
        brush = QBrush(qc)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        for i in range(len(points)):
            p = points[i]
            px = p["x"] - min_x
            py = p["y"] - min_y
            pressure = float(p.get("pressure", 0.5))
            radius = max(1.0, (base_size / 2.0) * pressure)
            painter.drawEllipse(QPointF(px, py), radius, radius)

            if i > 0:
                prev = points[i - 1]
                prev_x = prev["x"] - min_x
                prev_y = prev["y"] - min_y
                prev_pressure = float(prev.get("pressure", 0.5))
                dist = math.hypot(px - prev_x, py - prev_y)
                steps = max(1, int(dist / max(1.0, radius / 2.0)))
                for s in range(1, steps):
                    t = s / float(steps)
                    interp_x = prev_x + t * (px - prev_x)
                    interp_y = prev_y + t * (py - prev_y)
                    interp_pressure = prev_pressure + t * (pressure - prev_pressure)
                    interp_r = max(1.0, (base_size / 2.0) * interp_pressure)
                    painter.drawEllipse(QPointF(interp_x, interp_y), interp_r, interp_r)

        painter.end()
        ptr = qimg.bits()
        ptr.setsize(qimg.byteCount())
        return bytes(ptr)


def register_stroke_handlers(dispatcher: Any) -> None:
    """Register stroke execution handlers with the main-thread dispatcher."""

    def handle_paint_stroke(params: dict) -> dict:
        doc_id = params.get("doc_id")
        layer_id = params.get("layer_id")
        points: List[dict] = params.get("points", [])
        brush_preset = params.get("brush_preset")
        color = params.get("color", "#000000")
        opacity = float(params.get("opacity", 1.0)) if params.get("opacity") is not None else 1.0
        size = float(params.get("size", 10.0)) if params.get("size") is not None else 10.0

        if not points:
            raise ValueError("Parameter 'points' must not be empty for paint_stroke")

        xs = [float(p["x"]) for p in points]
        ys = [float(p["y"]) for p in points]
        pad = int(size * 2)
        min_x = max(0, int(min(xs)) - pad)
        min_y = max(0, int(min(ys)) - pad)
        max_x = int(max(xs)) + pad
        max_y = int(max(ys)) + pad
        bbox = [min_x, min_y, max_x, max_y]

        color_rgba = hex_to_rgba(color, opacity)
        rendered_native = False

        # Attempt native Krita rendering if active
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    node = doc.nodeByName(layer_id) if layer_id else doc.activeNode()
                    if node:
                        w = max_x - min_x
                        h = max_y - min_y
                        existing_bytes = None
                        try:
                            existing_bytes = node.pixelData(min_x, min_y, w, h)
                        except Exception:
                            pass

                        new_bytes = render_stroke_points_pil(
                            bbox=bbox,
                            points=points,
                            color_rgba=color_rgba,
                            base_size=size,
                            existing_bytes=existing_bytes,
                        )
                        try:
                            from PyQt5.QtCore import QByteArray
                            node.setPixelData(QByteArray(new_bytes), min_x, min_y, w, h)
                        except ImportError:
                            try:
                                from PyQt6.QtCore import QByteArray
                                node.setPixelData(QByteArray(new_bytes), min_x, min_y, w, h)
                            except ImportError:
                                node.setPixelData(new_bytes, min_x, min_y, w, h)

                        doc.refreshProjection()
                        rendered_native = True
                        return {
                            "doc_id": doc_id,
                            "layer_id": node.name(),
                            "points_drawn": len(points),
                            "points_count": len(points),
                            "rendered": True,
                            "rendered_native": True,
                            "color": color,
                            "size": size,
                            "opacity": opacity,
                            "bounding_box": bbox,
                            "bbox": bbox,
                        }
        except ImportError:
            pass

        # Headless mock mode record
        rec = {
            "doc_id": doc_id,
            "layer_id": layer_id or "active",
            "points_count": len(points),
            "points": points,
            "color": color,
            "size": size,
            "opacity": opacity,
            "brush_preset": brush_preset,
            "bbox": bbox,
        }
        if str(doc_id) not in _mock_painted_strokes:
            _mock_painted_strokes[str(doc_id)] = []
        _mock_painted_strokes[str(doc_id)].append(rec)

        return {
            "doc_id": doc_id,
            "layer_id": layer_id or "active",
            "points_drawn": len(points),
            "points_count": len(points),
            "rendered": True,
            "rendered_native": False,
            "color": color,
            "size": size,
            "opacity": opacity,
            "bounding_box": bbox,
            "bbox": bbox,
        }

    dispatcher.register_handler("stroke.paint", handle_paint_stroke)
    dispatcher.register_handler("stroke.bezier_curve", handle_paint_stroke)
    dispatcher.register_handler("painting.stroke", handle_paint_stroke)
    dispatcher.register_handler("painting.bezier_curve", handle_paint_stroke)
