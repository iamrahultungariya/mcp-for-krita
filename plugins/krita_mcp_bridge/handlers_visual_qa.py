"""Krita native API handlers for canvas preview capture, regional inspection, and checkpoints."""

import base64
import copy
import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

from plugins.krita_mcp_bridge.handlers_document import get_document_by_id
from plugins.krita_mcp_bridge.handlers_strokes import _mock_painted_strokes

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
                doc = get_document_by_id(doc_id)
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
                doc = get_document_by_id(doc_id)
                if doc:
                    node = doc.nodeByName(layer_id) if layer_id else None
                    if node and hasattr(node, "pixelData"):
                        raw_bytes = node.pixelData(x, y, width, height)
                    else:
                        target_node = doc.activeNode() or (
                            doc.rootNode().childNodes()[0]
                            if hasattr(doc, "rootNode") and doc.rootNode().childNodes()
                            else None
                        )
                        raw_bytes = target_node.pixelData(x, y, width, height) if target_node and hasattr(target_node, "pixelData") else None

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

        snapshot_path: Optional[str] = None
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = get_document_by_id(doc_id)
                if doc:
                    temp_dir = Path(tempfile.gettempdir()) / "krita_mcp_checkpoints"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    snapshot_file = temp_dir / f"{chk_id}_{doc.name()}.kra"
                    if doc.saveAs(str(snapshot_file)):
                        snapshot_path = str(snapshot_file)
        except Exception as exc:
            logger.warning("Failed to save Krita snapshot: %s", exc)

        entry = {
            "checkpoint_id": chk_id,
            "doc_id": doc_id,
            "label": label,
            "timestamp": time.time(),
            "snapshot_path": snapshot_path,
            "mock_strokes": copy.deepcopy(_mock_painted_strokes.get(doc_id, [])),
        }
        if doc_id not in _checkpoints:
            _checkpoints[doc_id] = []
        _checkpoints[doc_id].append(entry)

        return {
            "checkpoint_id": chk_id,
            "doc_id": doc_id,
            "label": label,
            "timestamp": entry["timestamp"],
            "snapshot_path": snapshot_path,
        }

    def handle_rollback_checkpoint(params: dict) -> dict:
        doc_id = str(params.get("doc_id", "default"))
        chk_id = params.get("checkpoint_id")

        checkpoints_for_doc = _checkpoints.get(doc_id, [])
        target_entry = None
        for entry in checkpoints_for_doc:
            if entry["checkpoint_id"] == chk_id:
                target_entry = entry
                break

        if not target_entry:
            return {
                "restored": False,
                "error": f"Checkpoint '{chk_id}' not found for document '{doc_id}'",
                "checkpoint_id": chk_id,
                "doc_id": doc_id,
            }

        # Restore live Krita document if snapshot file was recorded
        if target_entry.get("snapshot_path"):
            try:
                from krita import Krita
                app = Krita.instance()
                if app and Path(target_entry["snapshot_path"]).exists():
                    doc = get_document_by_id(doc_id)
                    if doc:
                        doc.close()
                    restored_doc = app.openDocument(target_entry["snapshot_path"])
                    if restored_doc and app.activeWindow():
                        app.activeWindow().addView(restored_doc)
            except Exception as exc:
                logger.warning("Failed to reload Krita snapshot on rollback: %s", exc)

        # Restore mock state for headless tests
        if "mock_strokes" in target_entry:
            _mock_painted_strokes[doc_id] = copy.deepcopy(target_entry["mock_strokes"])

        return {
            "restored": True,
            "checkpoint_id": chk_id,
            "doc_id": doc_id,
            "label": target_entry["label"],
            "timestamp": target_entry["timestamp"],
        }

    def handle_list_checkpoints(params: dict) -> dict:
        doc_id = str(params.get("doc_id", "default"))
        return {"checkpoints": _checkpoints.get(doc_id, [])}

    dispatcher.register_handler("visual.capture_canvas", handle_capture_canvas)
    dispatcher.register_handler("visual_qa.capture", handle_capture_canvas)
    dispatcher.register_handler("visual.capture", handle_capture_canvas)
    dispatcher.register_handler("visual.extract_region", handle_extract_region)
    dispatcher.register_handler("checkpoint.create", handle_create_checkpoint)
    dispatcher.register_handler("checkpoint.rollback", handle_rollback_checkpoint)
    dispatcher.register_handler("checkpoint.list", handle_list_checkpoints)
