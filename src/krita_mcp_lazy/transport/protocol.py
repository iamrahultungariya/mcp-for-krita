"""Length-prefixed binary framing protocol for JSON IPC transport."""

import asyncio
import json
import struct
from typing import Any

DEFAULT_MAX_PAYLOAD_SIZE = 32 * 1024 * 1024  # 32 MiB
HEADER_FORMAT = "!I"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 4 bytes


class ProtocolError(Exception):
    """Raised when framing or protocol validation fails."""
    pass


async def read_message(
    reader: asyncio.StreamReader,
    max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
) -> dict[str, Any]:
    """Read a length-prefixed JSON message from the stream.

    Reads 4-byte big-endian header, verifies bounds against max_payload_size,
    reads payload bytes, and decodes JSON.
    """
    try:
        header = await reader.readexactly(HEADER_SIZE)
    except (asyncio.IncompleteReadError, ConnectionResetError) as e:
        raise ProtocolError("Connection closed while reading header") from e

    (payload_length,) = struct.unpack(HEADER_FORMAT, header)

    if payload_length == 0:
        raise ProtocolError("Invalid zero-length payload received")

    if payload_length > max_payload_size:
        raise ProtocolError(
            f"Payload size {payload_length} bytes exceeds maximum allowed limit {max_payload_size} bytes"
        )

    try:
        payload_bytes = await reader.readexactly(payload_length)
    except (asyncio.IncompleteReadError, ConnectionResetError) as e:
        raise ProtocolError("Connection closed while reading payload") from e

    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise ProtocolError(f"Failed to parse JSON payload: {e}") from e


async def write_message(
    writer: asyncio.StreamWriter,
    payload: dict[str, Any],
    max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
) -> None:
    """Serialize and write a length-prefixed JSON message to the stream."""
    try:
        payload_bytes = json.dumps(payload).encode("utf-8")
    except Exception as e:
        raise ProtocolError(f"Failed to serialize payload to JSON: {e}") from e

    payload_length = len(payload_bytes)
    if payload_length > max_payload_size:
        raise ProtocolError(
            f"Payload size {payload_length} bytes exceeds maximum allowed limit {max_payload_size} bytes"
        )

    header = struct.pack(HEADER_FORMAT, payload_length)
    writer.write(header + payload_bytes)
    await writer.drain()
