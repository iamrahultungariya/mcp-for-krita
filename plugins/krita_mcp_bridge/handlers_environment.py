"""Krita native API handlers for perspective grid guides and environment depth planes."""

import logging
from typing import Any, Dict, List, Optional

try:
    from PIL import Image, ImageDraw
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

from plugins.krita_mcp_bridge.handlers_document import get_document_by_id

logger = logging.getLogger(__name__)

# In-memory record of generated perspective grids for headless testing & verification
_mock_grid_records: Dict[str, dict] = {}


def register_environment_handlers(dispatcher: Any) -> None:
    """Register perspective grid and environment layout handlers with the dispatcher."""

    def handle_create_grid(params: dict) -> dict:
        doc_id = params.get("doc_id")
        p_type = params.get("perspective_type", "two_point")
        horizon_y = float(params.get("horizon_y", 1080.0))
        vp1_x = params.get("vp1_x")
        vp2_x = params.get("vp2_x")
        line_density = int(params.get("line_density", 12))
        opacity = float(params.get("opacity", 0.4))

        vp_left = [float(vp1_x) if vp1_x is not None else -500.0, horizon_y]
        vp_right = [float(vp2_x) if vp2_x is not None else 4340.0, horizon_y]

        w = 1920
        h = 1080
        doc = None

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    w = doc.width()
                    h = doc.height()
        except ImportError:
            pass

        grid_bytes = None
        total_lines_drawn = 0

        vps = [vp_left, vp_right] if p_type in ("two_point", "three_point") else [vp_left]
        step = max(1, w // max(1, line_density))

        if _HAS_PIL:
            # Draw actual perspective geometry lines using Pillow
            grid_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(grid_img)

            # Draw horizon line
            draw.line([(0, int(horizon_y)), (w, int(horizon_y))], fill=(60, 160, 255, 230), width=2)
            total_lines_drawn = 1

            for vp in vps:
                vpx, vpy = vp[0], vp[1]
                for target_x in range(0, w + step, step):
                    draw.line([(vpx, vpy), (target_x, h)], fill=(100, 200, 255, 140), width=1)
                    total_lines_drawn += 1
                    if horizon_y > 0:
                        draw.line([(vpx, vpy), (target_x, 0)], fill=(100, 200, 255, 100), width=1)
                        total_lines_drawn += 1

            grid_bytes = grid_img.tobytes("raw", "RGBA")
        else:
            # Fallback using PyQt5.QtGui inside Krita
            try:
                from PyQt5.QtGui import QImage, QPainter, QPen, QColor
                from PyQt5.QtCore import Qt, QPointF
            except ImportError:
                from PyQt6.QtGui import QImage, QPainter, QPen, QColor
                from PyQt6.QtCore import Qt, QPointF

            qimg = QImage(w, h, QImage.Format_RGBA8888)
            qimg.fill(Qt.transparent)
            painter = QPainter(qimg)
            painter.setRenderHint(QPainter.Antialiasing)

            pen_horizon = QPen(QColor(60, 160, 255, 230), 2)
            painter.setPen(pen_horizon)
            painter.drawLine(0, int(horizon_y), w, int(horizon_y))
            total_lines_drawn = 1

            pen_ray = QPen(QColor(100, 200, 255, 140), 1)
            painter.setPen(pen_ray)

            for vp in vps:
                vpx, vpy = vp[0], vp[1]
                for target_x in range(0, w + step, step):
                    painter.drawLine(int(vpx), int(vpy), target_x, h)
                    total_lines_drawn += 1
                    if horizon_y > 0:
                        painter.drawLine(int(vpx), int(vpy), target_x, 0)
                        total_lines_drawn += 1

            painter.end()
            ptr = qimg.bits()
            ptr.setsize(qimg.byteCount())
            grid_bytes = bytes(ptr)

        if doc and grid_bytes:
            try:
                root = doc.rootNode()
                grid_layer = doc.createNode(f"Perspective_Grid_{p_type}", "paintLayer")
                grid_layer.setOpacity(int(opacity * 255))
                root.addChildNode(grid_layer, None)
                grid_layer.setPixelData(grid_bytes, 0, 0, w, h)
                doc.refreshProjection()
                return {
                    "perspective_type": p_type,
                    "vp_left": vp_left,
                    "vp_right": vp_right,
                    "horizon_y": horizon_y,
                    "grid_layer_id": f"lyr_grid_{p_type}",
                    "lines_drawn": total_lines_drawn,
                    "doc_id": doc_id,
                }
            except Exception as exc:
                logger.warning("Failed to commit grid pixel data to Krita: %s", exc)

        # Headless mock mode record
        result = {
            "perspective_type": p_type,
            "vp_left": vp_left,
            "vp_right": vp_right,
            "horizon_y": horizon_y,
            "grid_layer_id": f"lyr_grid_{p_type}",
            "lines_drawn": total_lines_drawn,
            "doc_id": doc_id,
        }
        _mock_grid_records[str(doc_id or "default")] = result
        return result

    def handle_setup_depth_planes(params: dict) -> dict:
        doc_id = params.get("doc_id")
        planes: List[str] = params.get("planes", ["00_Sky", "01_Far_BG", "02_Mid_BG", "03_Play_Area", "04_Near_FG"])
        atmospheric_haze = bool(params.get("atmospheric_haze", True))

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    root = doc.rootNode()
                    depth_grp = doc.createGroupLayer("Environment_Depth_Planes")
                    root.addChildNode(depth_grp, None)

                    for plane in planes:
                        p_grp = doc.createGroupLayer(plane)
                        depth_grp.addChildNode(p_grp, None)
                        lines = doc.createNode(f"{plane}_Lines", "paintLayer")
                        color = doc.createNode(f"{plane}_Color", "paintLayer")
                        p_grp.addChildNode(color, None)
                        p_grp.addChildNode(lines, None)

                    if atmospheric_haze:
                        haze = doc.createNode("Atmospheric_Haze", "paintLayer")
                        haze.setOpacity(76)
                        depth_grp.addChildNode(haze, None)

                    doc.refreshProjection()
                    return {
                        "doc_id": doc_id,
                        "group_name": "Environment_Depth_Planes",
                        "planes": planes,
                        "atmospheric_haze": atmospheric_haze,
                        "created_native": True,
                    }
        except ImportError:
            pass

        return {
            "doc_id": doc_id,
            "group_name": "Environment_Depth_Planes",
            "planes": planes,
            "atmospheric_haze": atmospheric_haze,
            "created_native": False,
        }

    dispatcher.register_handler("environment.create_grid", handle_create_grid)
    dispatcher.register_handler("environment.setup_depth_planes", handle_setup_depth_planes)
