"""Krita native API handlers for perspective grid guides and environment depth planes."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def register_environment_handlers(dispatcher: Any) -> None:
    """Register perspective grid and environment layout handlers with the dispatcher."""

    def handle_create_grid(params: dict) -> dict:
        doc_id = params.get("doc_id")
        p_type = params.get("perspective_type", "two_point")
        horizon_y = float(params.get("horizon_y", 1080.0))
        vp1_x = params.get("vp1_x")
        vp2_x = params.get("vp2_x")
        line_density = params.get("line_density", 12)
        opacity = params.get("opacity", 0.4)

        vp_left = [float(vp1_x) if vp1_x is not None else -500.0, horizon_y]
        vp_right = [float(vp2_x) if vp2_x is not None else 4340.0, horizon_y]

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = None
                for d in app.documents():
                    if getattr(d, "_lazy_id", None) == doc_id or d.fileName() == doc_id:
                        doc = d
                        break
                if not doc:
                    doc = app.activeDocument()

                if doc:
                    root = doc.rootNode()
                    grid_layer = doc.createNode(f"Perspective_Grid_{p_type}", "paintLayer")
                    grid_layer.setOpacity(int(opacity * 255))
                    root.addChildNode(grid_layer, None)
                    doc.refreshProjection()
                    return {
                        "perspective_type": p_type,
                        "vp_left": vp_left,
                        "vp_right": vp_right,
                        "horizon_y": horizon_y,
                        "grid_layer_id": f"lyr_grid_{p_type}",
                        "doc_id": doc_id,
                    }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "perspective_type": p_type,
            "vp_left": vp_left,
            "vp_right": vp_right,
            "horizon_y": horizon_y,
            "grid_layer_id": f"lyr_grid_{p_type}",
            "doc_id": doc_id,
        }

    def handle_setup_depth_planes(params: dict) -> dict:
        doc_id = params.get("doc_id")
        planes: List[str] = params.get("planes", ["00_Sky", "01_Far_BG", "02_Mid_BG", "03_Play_Area", "04_Near_FG"])
        atmospheric_haze = bool(params.get("atmospheric_haze", True))

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = None
                for d in app.documents():
                    if getattr(d, "_lazy_id", None) == doc_id or d.fileName() == doc_id:
                        doc = d
                        break
                if not doc:
                    doc = app.activeDocument()

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
                        haze.setOpacity(50)
                        depth_grp.addChildNode(haze, None)

                    doc.refreshProjection()
                    return {
                        "planes_created": planes,
                        "atmospheric_haze": atmospheric_haze,
                        "depth_group_id": "grp_depth_planes",
                        "doc_id": doc_id,
                    }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "planes_created": planes,
            "atmospheric_haze": atmospheric_haze,
            "depth_group_id": "grp_depth_planes",
            "doc_id": doc_id,
        }

    dispatcher.register_handler("environment.create_grid", handle_create_grid)
    dispatcher.register_handler("environment.setup_depth_planes", handle_setup_depth_planes)
