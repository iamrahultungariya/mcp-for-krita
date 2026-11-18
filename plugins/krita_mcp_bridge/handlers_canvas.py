"""Krita native API handlers for canvas transformations and pixel sampling."""

import logging
from typing import Any

from plugins.krita_mcp_bridge.handlers_document import _mock_documents

logger = logging.getLogger(__name__)


def register_canvas_handlers(dispatcher: Any) -> None:
    """Register canvas-level handlers with the main-thread dispatcher."""

    def handle_resize_canvas(params: dict) -> dict:
        doc_id = params.get("doc_id")
        width = params.get("width", 1920)
        height = params.get("height", 1080)
        x_offset = params.get("x_offset", 0)
        y_offset = params.get("y_offset", 0)

        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid dimensions: width={width}, height={height}")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    doc.resizeImage(x_offset, y_offset, width, height)
                    return {
                        "doc_id": doc_id or "active",
                        "width": doc.width(),
                        "height": doc.height(),
                        "resized": True,
                    }
        except ImportError:
            pass

        # Headless mock mode
        if doc_id and doc_id in _mock_documents:
            _mock_documents[doc_id]["width"] = width
            _mock_documents[doc_id]["height"] = height
        return {
            "doc_id": doc_id or "doc_1",
            "width": width,
            "height": height,
            "x_offset": x_offset,
            "y_offset": y_offset,
            "resized": True,
        }

    def handle_crop_canvas(params: dict) -> dict:
        doc_id = params.get("doc_id")
        x = params.get("x", 0)
        y = params.get("y", 0)
        width = params.get("width", 1920)
        height = params.get("height", 1080)

        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid crop dimensions: width={width}, height={height}")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    doc.crop(x, y, width, height)
                    return {
                        "doc_id": doc_id or "active",
                        "x": x,
                        "y": y,
                        "width": doc.width(),
                        "height": doc.height(),
                        "cropped": True,
                    }
        except ImportError:
            pass

        # Headless mock mode
        if doc_id and doc_id in _mock_documents:
            _mock_documents[doc_id]["width"] = width
            _mock_documents[doc_id]["height"] = height
        return {
            "doc_id": doc_id or "doc_1",
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "cropped": True,
        }

    def handle_rotate_canvas(params: dict) -> dict:
        doc_id = params.get("doc_id")
        angle_degrees = params.get("angle_degrees", 0.0)

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    doc.rotateImage(angle_degrees)
                    return {
                        "doc_id": doc_id or "active",
                        "angle_degrees": angle_degrees,
                        "rotated": True,
                    }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "doc_id": doc_id or "doc_1",
            "angle_degrees": angle_degrees,
            "rotated": True,
        }

    def handle_canvas_bounds(params: dict) -> dict:
        doc_id = params.get("doc_id")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    return {
                        "doc_id": doc_id or "active",
                        "x": doc.x(),
                        "y": doc.y(),
                        "width": doc.width(),
                        "height": doc.height(),
                        "resolution_dpi": doc.resolution(),
                    }
        except ImportError:
            pass

        # Headless mock mode
        doc = _mock_documents.get(doc_id) if doc_id else next(iter(_mock_documents.values()), None)
        if doc:
            return {
                "doc_id": doc["doc_id"],
                "x": 0,
                "y": 0,
                "width": doc["width"],
                "height": doc["height"],
                "resolution_dpi": doc.get("resolution_dpi", 300.0),
            }
        return {"doc_id": doc_id or "none", "x": 0, "y": 0, "width": 1920, "height": 1080}

    def handle_sample_pixel(params: dict) -> dict:
        doc_id = params.get("doc_id")
        x = params.get("x", 0)
        y = params.get("y", 0)

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    # Sample 1x1 pixel data using doc.pixelData()
                    pixel_bytes = doc.pixelData(x, y, 1, 1)
                    if pixel_bytes and len(pixel_bytes) >= 4:
                        # Default RGBA ordering in Krita is BGRA or RGBA based on color model
                        b, g, r, a = pixel_bytes[0], pixel_bytes[1], pixel_bytes[2], pixel_bytes[3]
                        return {"sampled_color": {"r": r, "g": g, "b": b, "a": a}}
        except ImportError:
            pass

        # Headless mock mode default sample
        return {"sampled_color": {"r": 255, "g": 255, "b": 255, "a": 255}}

    dispatcher.register_handler("canvas.resize", handle_resize_canvas)
    dispatcher.register_handler("canvas.crop", handle_crop_canvas)
    dispatcher.register_handler("canvas.rotate", handle_rotate_canvas)
    dispatcher.register_handler("canvas.bounds", handle_canvas_bounds)
    dispatcher.register_handler("canvas.sample_pixel", handle_sample_pixel)
