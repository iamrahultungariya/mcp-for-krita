"""Krita native API handlers for brush presets, colors, and brush settings."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Mock brush state for headless environments
_mock_presets: List[dict] = [
    {"name": "b)_Basic-5_Size", "category": "Basic", "engine": "Pixel"},
    {"name": "c)_Pencil-2B", "category": "Pencil", "engine": "Pixel"},
    {"name": "d)_Ink-7_Rough", "category": "Ink", "engine": "Pixel"},
    {"name": "Airbrush_Soft", "category": "Airbrush", "engine": "Pixel"},
    {"name": "Texture_Charcoal", "category": "Texture", "engine": "Pixel"},
]

_current_brush_state: Dict[str, Any] = {
    "current_preset": "b)_Basic-5_Size",
    "size": 10.0,
    "opacity": 1.0,
    "flow": 1.0,
    "color": "#000000",
    "background_color": "#ffffff",
}


def register_painting_handlers(dispatcher: Any) -> None:
    """Register all brush and painting handlers with the main-thread dispatcher."""

    def handle_list_presets(params: dict) -> dict:
        category = params.get("category")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                presets = app.resources("KisPaintOpPreset")
                preset_list = []
                for p in presets:
                    preset_list.append({"name": p.name(), "category": "General", "engine": "Pixel"})
                if category:
                    preset_list = [p for p in preset_list if p.get("category", "").lower() == category.lower()]
                return {"presets": preset_list}
        except ImportError:
            pass

        # Headless mock mode
        if category:
            filtered = [p for p in _mock_presets if p["category"].lower() == category.lower()]
            return {"presets": filtered}
        return {"presets": _mock_presets}

    def handle_select_preset(params: dict) -> dict:
        preset_name = params.get("preset_name")
        if not preset_name:
            raise ValueError("Parameter 'preset_name' is required")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                win = app.activeWindow()
                if win and win.activeView():
                    # Attempt to look up preset resource
                    resources = app.resources("KisPaintOpPreset")
                    target = next((r for r in resources if r.name() == preset_name), None)
                    if target:
                        win.activeView().setCurrentBrushPreset(target)
                        _current_brush_state["current_preset"] = preset_name
                        return {"preset_name": preset_name, "selected": True}
        except ImportError:
            pass

        # Headless mock mode
        _current_brush_state["current_preset"] = preset_name
        return {"preset_name": preset_name, "selected": True}

    def handle_configure_brush(params: dict) -> dict:
        size = params.get("size")
        opacity = params.get("opacity")
        flow = params.get("flow")
        color = params.get("color")
        background_color = params.get("background_color")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                win = app.activeWindow()
                if win and win.activeView():
                    view = win.activeView()
                    if size is not None:
                        view.setBrushSize(float(size))
                    if opacity is not None and hasattr(view, "setPaintingOpacity"):
                        view.setPaintingOpacity(float(opacity))
                    if flow is not None and hasattr(view, "setPaintingFlow"):
                        view.setPaintingFlow(float(flow))

                    try:
                        from krita import ManagedColor
                        try:
                            from PyQt5.QtGui import QColor
                        except ImportError:
                            from PyQt6.QtGui import QColor

                        if color:
                            mc = ManagedColor.fromQColor(QColor(color))
                            view.setForeGroundColor(mc)
                        if background_color:
                            mc_bg = ManagedColor.fromQColor(QColor(background_color))
                            view.setBackGroundColor(mc_bg)
                    except Exception as e:
                        logger.debug("ManagedColor configuration fallback: %s", e)
        except ImportError:
            pass

        # Update in-memory state
        if size is not None:
            _current_brush_state["size"] = size
        if opacity is not None:
            _current_brush_state["opacity"] = opacity
        if flow is not None:
            _current_brush_state["flow"] = flow
        if color is not None:
            _current_brush_state["color"] = color
        if background_color is not None:
            _current_brush_state["background_color"] = background_color

        return {
            "configured": True,
            "size": _current_brush_state["size"],
            "opacity": _current_brush_state["opacity"],
            "flow": _current_brush_state["flow"],
            "color": _current_brush_state["color"],
        }

    def handle_current_brush(params: dict) -> dict:
        return dict(_current_brush_state)

    dispatcher.register_handler("brush.list_presets", handle_list_presets)
    dispatcher.register_handler("brush.select_preset", handle_select_preset)
    dispatcher.register_handler("brush.configure", handle_configure_brush)
    dispatcher.register_handler("brush.current", handle_current_brush)
