"""Security policies and cryptographic session token management."""

import hmac
import secrets
from typing import Optional


class AuthTokenManager:
    """Manages generation, storage, and constant-time validation of session tokens."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token: Optional[str] = token

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
