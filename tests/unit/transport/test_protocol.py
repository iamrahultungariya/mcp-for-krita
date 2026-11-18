import asyncio
import io
import struct
import pytest
from krita_mcp_lazy.transport.protocol import (
    DEFAULT_MAX_PAYLOAD_SIZE,
    HEADER_SIZE,
    ProtocolError,
    read_message,
    write_message,
)


@pytest.mark.asyncio
async def test_protocol_read_write_roundtrip():
    # Use asyncio.StreamReader and StreamWriter via pipe or loopback
    data = {"action": "ping", "numbers": [1, 2, 3], "nested": {"key": "val"}}
    
    server_reader = asyncio.StreamReader()
    # Mock stream writer using mock or pipe
    class DummyWriter:
        def __init__(self, target_reader):
            self.target_reader = target_reader
            self.closed = False
        def write(self, buf):
            self.target_reader.feed_data(buf)
        async def drain(self):
            pass
        def close(self):
            self.closed = True
        async def wait_closed(self):
            pass
        def is_closing(self):
            return self.closed

    writer = DummyWriter(server_reader)
    await write_message(writer, data)
    
    received = await read_message(server_reader)
    assert received == data


@pytest.mark.asyncio
async def test_protocol_oversized_payload_rejection():
    server_reader = asyncio.StreamReader()
    # Header specifying length exceeding max limit (32MB)
    fake_header = struct.pack("!I", DEFAULT_MAX_PAYLOAD_SIZE + 10)
    server_reader.feed_data(fake_header)
    
    with pytest.raises(ProtocolError, match="exceeds maximum allowed limit"):
        await read_message(server_reader, max_payload_size=DEFAULT_MAX_PAYLOAD_SIZE)


@pytest.mark.asyncio
async def test_protocol_zero_length_rejection():
    server_reader = asyncio.StreamReader()
    fake_header = struct.pack("!I", 0)
    server_reader.feed_data(fake_header)

    with pytest.raises(ProtocolError, match="Invalid zero-length payload"):
        await read_message(server_reader)


@pytest.mark.asyncio
async def test_protocol_incomplete_read_header():
    server_reader = asyncio.StreamReader()
    server_reader.feed_data(b"\x00\x00")  # only 2 bytes instead of 4
    server_reader.feed_eof()

    with pytest.raises(ProtocolError, match="Connection closed while reading header"):
        await read_message(server_reader)


@pytest.mark.asyncio
async def test_protocol_invalid_json():
    server_reader = asyncio.StreamReader()
    corrupted_data = b"not a json object"
    fake_header = struct.pack("!I", len(corrupted_data))
    server_reader.feed_data(fake_header + corrupted_data)

    with pytest.raises(ProtocolError, match="Failed to parse JSON payload"):
        await read_message(server_reader)
