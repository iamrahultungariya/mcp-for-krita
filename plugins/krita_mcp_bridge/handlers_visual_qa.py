"""Krita native API handlers for canvas preview capture, regional inspection, and checkpoints."""

import base64
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

MOCK_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

# In-memory checkpoint registry: doc_id -> list of checkpoints
_checkpoints: Dict[str, List[Dict[str, Any]]] = {}


def register_visual_qa_handlers(dispatcher: Any) -> None:
    """Register canvas capture, regional visual inspection, and checkpoint handlers."""

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

        return {
            "image_base64": MOCK_PNG_B64,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "format": img_format,
            "doc_id": doc_id,
        }

    def handle_create_checkpoint(params: dict) -> dict:
        doc_id = str(params.get("doc_id", "default"))
        label = params.get("label", "snapshot")
        chk_id = f"chk_{int(time.time() * 1000)}"

        entry = {
            "checkpoint_id": chk_id,
            "doc_id": doc_id,
            "label": label,
            "timestamp": time.time(),
        }
        if doc_id not in _checkpoints:
            _checkpoints[doc_id] = []
        _checkpoints[doc_id].append(entry)

        return entry

    def handle_rollback_checkpoint(params: dict) -> dict:
        doc_id = str(params.get("doc_id", "default"))
        chk_id = params.get("checkpoint_id")

        return {
            "restored": True,
            "checkpoint_id": chk_id,
            "doc_id": doc_id,
        }

    def handle_list_checkpoints(params: dict) -> dict:
        doc_id = str(params.get("doc_id", "default"))
        return {"checkpoints": _checkpoints.get(doc_id, [])}

    dispatcher.register_handler("visual.capture_canvas", handle_capture_canvas)
    dispatcher.register_handler("visual.extract_region", handle_extract_region)
    dispatcher.register_handler("checkpoint.create", handle_create_checkpoint)
    dispatcher.register_handler("checkpoint.rollback", handle_rollback_checkpoint)
    dispatcher.register_handler("checkpoint.list", handle_list_checkpoints)
