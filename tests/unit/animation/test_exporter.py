import os
import tempfile
import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.animation.exporter import SequenceExporter
from krita_mcp_lazy.core.errors import ErrorCode, KritaError


@pytest.mark.asyncio
async def test_png_sequence_export():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "output_directory": "/tmp/anim_export",
        "frame_count": 24,
        "missing_frames": [],
        "zero_byte_frames": [],
    }

    exporter = SequenceExporter(client=mock_client)
    res = await exporter.export_sequence(
        doc_id="doc_1",
        start_frame=0,
        end_frame=23,
        output_dir="/tmp/anim_export",
    )
    assert res["frame_count"] == 24
    assert len(res["missing_frames"]) == 0
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "animation.export_sequence"


def test_validate_frame_sequence_filesystem():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create valid frames 0 to 4
        for i in range(5):
            fp = os.path.join(tmp_dir, f"frame_{i:04d}.png")
            with open(fp, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\nfakeimagebytes")

        # Frame 5 missing, Frame 6 is zero bytes
        zero_fp = os.path.join(tmp_dir, "frame_0006.png")
        with open(zero_fp, "wb") as f:
            pass  # 0 bytes

        exporter = SequenceExporter()
        val = exporter.validate_sequence(
            output_dir=tmp_dir,
            start_frame=0,
            end_frame=6,
            prefix="frame_",
            extension="png",
        )
        assert val["valid"] is False
        assert 5 in val["missing_frames"]
        assert 6 in val["zero_byte_frames"]
        assert len(val["existing_frames"]) == 6


@pytest.mark.asyncio
async def test_export_sequence_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Export target directory does not exist",
    }

    exporter = SequenceExporter(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await exporter.export_sequence(
            doc_id="doc_1",
            start_frame=0,
            end_frame=10,
            output_dir="/nonexistent/directory",
        )
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_sequence_export_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_export_frame_sequence" in tool_names
    assert "krita_validate_frame_sequence" in tool_names
