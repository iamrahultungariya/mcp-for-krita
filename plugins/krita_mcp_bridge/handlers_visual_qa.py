"""Krita native API handlers for canvas preview capture and regional inspection."""

import base64
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

MOCK_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


def register_visual_qa_handlers(dispatcher: Any) -> None:
    """Register canvas capture and regional visual inspection handlers with the dispatcher."""

    def handle_capture_canvas(params: dict) -> dict:
        doc_id = params.get("doc_id")
        max_dim = int(params.get("max_dimension", 1920))
        img_format = params.get("format", "PNG").upper()

        try:
            from krita import Krita, QBuffer, QIODevice
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
                    # Calculate aspect-ratio scale for thumbnail
                    w = doc.width()
                    h = doc.height()
                    scale = min(max_dim / max(w, 1), max_dim / max(h, 1), 1.0)
                    thumb_w = max(1, int(w * scale))
                    thumb_h = max(1, int(h * scale))

                    qimg = doc.thumbnail(thumb_w, thumb_h)
                    if qimg and not qimg.isNull():
                        buf = QBuffer()
                        buf.open(QIODevice.WriteOnly)
                        qimg.save(buf, img_format)
                        b64_data = base64.b64encode(bytes(buf.data())).decode("ascii")
                        buf.close()
                        return {
                            "image_base64": b64_data,
                            "width": thumb_w,
                            "height": thumb_h,
                            "format": img_format,
                            "doc_id": doc_id,
                        }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "image_base64": MOCK_PNG_B64,
            "width": 1920,
            "height": 1080,
            "format": img_format,
            "doc_id": doc_id,
        }

    def handle_extract_region(params: dict) -> dict:
        doc_id = params.get("doc_id")
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        width = int(params.get("width", 512))
        height = int(params.get("height", 512))
        layer_id = params.get("layer_id")
        img_format = params.get("format", "PNG").upper()

        try:
            from krita import Krita, QBuffer, QImage, QIODevice
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
                    # Target layer or composite canvas
                    node = doc.nodeByName(layer_id) if layer_id else None
                    if node:
                        raw_bytes = node.pixelData(x, y, width, height)
                    else:
                        raw_bytes = doc.pixelData(x, y, width, height)

                    if raw_bytes:
                        qimg = QImage(raw_bytes, width, height, QImage.Format_RGBA8888)
                        buf = QBuffer()
                        buf.open(QIODevice.WriteOnly)
                        qimg.save(buf, img_format)
                        b64_data = base64.b64encode(bytes(buf.data())).decode("ascii")
                        buf.close()
                        return {
                            "image_base64": b64_data,
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                            "format": img_format,
                            "doc_id": doc_id,
                        }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "image_base64": MOCK_PNG_B64,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "format": img_format,
            "doc_id": doc_id,
        }

    dispatcher.register_handler("visual.capture_canvas", handle_capture_canvas)
    dispatcher.register_handler("visual.extract_region", handle_extract_region)
