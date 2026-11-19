"""Security policies and cryptographic session token management."""

import hmac
import os
from pathlib import Path
import secrets
from typing import Optional


def get_or_create_shared_token() -> str:
    """Retrieve shared session token from environment or user profile file, or generate a persistent one."""
    env_token = os.environ.get("KRITA_MCP_TOKEN")
    if env_token and env_token.strip():
        return env_token.strip()

    token_dir = Path.home() / ".krita_mcp_lazy"
    token_file = token_dir / "session.token"

    if token_file.exists():
        try:
            stored = token_file.read_text(encoding="utf-8").strip()
            if stored:
                return stored
        except Exception:
            pass

    try:
        token_dir.mkdir(parents=True, exist_ok=True)
        new_token = secrets.token_hex(32)
        token_file.write_text(new_token, encoding="utf-8")
        try:
            os.chmod(token_file, 0o600)
        except Exception:
            pass
        return new_token
    except Exception:
        return secrets.token_hex(32)


class AuthTokenManager:
    """Manages generation, storage, and constant-time validation of session tokens."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token: Optional[str] = token if token is not None else get_or_create_shared_token()

    def generate_token(self, nbytes: int = 32) -> str:
        """Generate a cryptographically secure random session token."""
        self._token = secrets.token_hex(nbytes)
        return self._token

    def get_token(self) -> Optional[str]:
        """Retrieve the current active session token."""
        return self._token

    def validate_token(self, candidate: Optional[str]) -> bool:
        """Validate candidate token against current active token using constant-time comparison."""
        if not self._token or not candidate or not isinstance(candidate, str):
            return False
        return hmac.compare_digest(self._token, candidate)

    def revoke_token(self) -> None:
        """Revoke current active token."""
        self._token = None
