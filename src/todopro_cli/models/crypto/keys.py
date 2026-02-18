"""Master key generation and management."""

import base64
import hashlib
import os
from dataclasses import dataclass

from .exceptions import KeyDerivationError

# AES-256 requires 256-bit (32-byte) keys
KEY_SIZE = 32  # 256 bits

# PBKDF2 parameters
PBKDF2_ITERATIONS = 100_000
SALT_SIZE = 16  # 128 bits


@dataclass
class MasterKey:
    """Represents a 256-bit master encryption key."""

    key_bytes: bytes

    def __post_init__(self) -> None:
        """Validate key size."""
        if len(self.key_bytes) != KEY_SIZE:
            raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(self.key_bytes)}")

    @classmethod
    def generate(cls) -> "MasterKey":
        """Generate a new random master key."""
        return cls(key_bytes=os.urandom(KEY_SIZE))

    @classmethod
    def from_password(cls, password: str, salt: bytes) -> "MasterKey":
        """Derive master key from password using PBKDF2."""
        try:
            if len(salt) < SALT_SIZE:
                raise KeyDerivationError(f"Salt must be at least {SALT_SIZE} bytes")

            key_bytes = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                PBKDF2_ITERATIONS,
                dklen=KEY_SIZE,
            )

            return cls(key_bytes=key_bytes)

        except Exception as e:
            raise KeyDerivationError(f"Key derivation failed: {str(e)}") from e

    @classmethod
    def from_bytes(cls, key_bytes: bytes) -> "MasterKey":
        """Create master key from raw bytes."""
        return cls(key_bytes=key_bytes)

    @classmethod
    def from_base64(cls, key_b64: str) -> "MasterKey":
        """Create master key from base64-encoded string."""
        key_bytes = base64.b64decode(key_b64)
        return cls(key_bytes=key_bytes)

    def to_base64(self) -> str:
        """Encode key as base64 string for storage."""
        return base64.b64encode(self.key_bytes).decode("ascii")

    def __repr__(self) -> str:
        """String representation (hides key material)."""
        return (
            f"MasterKey(key_hash={hashlib.sha256(self.key_bytes).hexdigest()[:16]}...)"
        )

    def __eq__(self, other: object) -> bool:
        """Compare keys securely."""
        if not isinstance(other, MasterKey):
            return NotImplemented
        return (
            hashlib.sha256(self.key_bytes).digest()
            == hashlib.sha256(other.key_bytes).digest()
        )


def generate_salt() -> bytes:
    """Generate a random salt for PBKDF2."""
    return os.urandom(SALT_SIZE)
