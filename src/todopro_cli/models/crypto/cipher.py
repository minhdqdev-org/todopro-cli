"""AES-256-GCM encryption and decryption utilities.

This module provides authenticated encryption using AES-256-GCM.
All operations use cryptographically secure random number generation.
"""

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .exceptions import DecryptionError

# Constants
IV_SIZE = 12  # 96 bits (recommended for GCM)
TAG_SIZE = 16  # 128 bits (authentication tag)


@dataclass
class EncryptedData:
    """Represents encrypted data with all necessary components."""

    ciphertext: str
    iv: str
    auth_tag: str
    version: str = "1"

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ciphertext": self.ciphertext,
            "iv": self.iv,
            "authTag": self.auth_tag,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EncryptedData":
        """Create from dictionary (from JSON)."""
        return cls(
            ciphertext=data["ciphertext"],
            iv=data["iv"],
            auth_tag=data.get("authTag", data.get("auth_tag", "")),
            version=data.get("version", "1"),
        )


def encrypt(plaintext: str, master_key: "MasterKey") -> EncryptedData:
    """Encrypt plaintext using AES-256-GCM."""

    # Generate random IV
    iv = os.urandom(IV_SIZE)

    # Initialize AES-GCM cipher
    aesgcm = AESGCM(master_key.key_bytes)

    # Encrypt and authenticate
    plaintext_bytes = plaintext.encode("utf-8")
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext_bytes, associated_data=None)

    # Split ciphertext and auth tag
    ciphertext = ciphertext_with_tag[:-TAG_SIZE]
    auth_tag = ciphertext_with_tag[-TAG_SIZE:]

    return EncryptedData(
        ciphertext=base64.b64encode(ciphertext).decode("ascii"),
        iv=base64.b64encode(iv).decode("ascii"),
        auth_tag=base64.b64encode(auth_tag).decode("ascii"),
        version="1",
    )


def decrypt(encrypted: EncryptedData, master_key: "MasterKey") -> str:
    """Decrypt data using AES-256-GCM."""

    try:
        # Decode from base64
        ciphertext = base64.b64decode(encrypted.ciphertext)
        iv = base64.b64decode(encrypted.iv)
        auth_tag = base64.b64decode(encrypted.auth_tag)

        # Validate sizes
        if len(iv) != IV_SIZE:
            raise DecryptionError(f"Invalid IV size: expected {IV_SIZE}, got {len(iv)}")
        if len(auth_tag) != TAG_SIZE:
            raise DecryptionError(
                f"Invalid auth tag size: expected {TAG_SIZE}, got {len(auth_tag)}"
            )

        # Reconstruct ciphertext + tag
        ciphertext_with_tag = ciphertext + auth_tag

        # Initialize AES-GCM cipher
        aesgcm = AESGCM(master_key.key_bytes)

        # Decrypt and verify
        plaintext_bytes = aesgcm.decrypt(iv, ciphertext_with_tag, associated_data=None)

        return plaintext_bytes.decode("utf-8")

    except Exception as e:
        raise DecryptionError(f"Decryption failed: {str(e)}") from e
