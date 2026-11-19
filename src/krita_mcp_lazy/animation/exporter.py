"""PNG and raster animation frame sequence export and post-render validation."""

import os
from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class SequenceExporter:
    """Manages full batch export of timeline frames to numbered PNGs and performs integrity checks."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def export_sequence(
        self,
        doc_id: str,
        start_frame: int,
        end_frame: int,
        output_dir: str,
        prefix: str = "frame_",
        file_format: str = "PNG",
    ) -> Dict[str, Any]:
        """Trigger Krita batch timeline rendering of frames to disk."""
        payload = {
            "doc_id": doc_id,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "output_dir": output_dir,
            "prefix": prefix,
            "format": file_format.upper(),
        }

        resp = await self.client.send_job("animation.export_sequence", payload)
        return check_job_response(resp, ErrorCode.DOCUMENT_ERROR, "Sequence export failed")

    def validate_sequence(
        self,
        output_dir: str,
        start_frame: int,
        end_frame: int,
        prefix: str = "frame_",
        extension: str = "png",
    ) -> Dict[str, Any]:
        """Scan target export directory to detect missing frames, gaps, or 0-byte corrupted outputs."""
        missing_frames: List[int] = []
        zero_byte_frames: List[int] = []
        existing_frames: List[str] = []

        total_expected = end_frame - start_frame + 1

        for i in range(start_frame, end_frame + 1):
            filename = f"{prefix}{i:04d}.{extension.lower()}"
            filepath = os.path.join(output_dir, filename)

            if not os.path.exists(filepath):
                missing_frames.append(i)
            else:
                existing_frames.append(filepath)
                try:
                    size = os.path.getsize(filepath)
                    if size == 0:
                        zero_byte_frames.append(i)
                except OSError:
                    missing_frames.append(i)

        is_valid = len(missing_frames) == 0 and len(zero_byte_frames) == 0

        return {
            "valid": is_valid,
            "total_expected": total_expected,
            "existing_frames": existing_frames,
            "missing_frames": missing_frames,
            "zero_byte_frames": zero_byte_frames,
            "output_directory": output_dir,
        }
