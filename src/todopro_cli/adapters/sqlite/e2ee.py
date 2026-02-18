"""E2EE (End-to-End Encryption) integration for SQLite repositories.

This module provides encryption/decryption wrappers for task content,
integrating the EncryptionService with SQLite storage.
"""

from __future__ import annotations

import json

from todopro_cli.models.crypto.cipher import EncryptedData
from todopro_cli.services.encryption_service import EncryptionService


class E2EEHandler:
    """Handles encryption and decryption of task data using EncryptionService."""

    def __init__(self, encryption_service: EncryptionService | None = None):
        """Initialize E2EE handler.

        Args:
            encryption_service: Optional encryption service. If None, E2EE is disabled.
        """
        self.encryption_service = encryption_service
        self.enabled = encryption_service is not None and encryption_service.is_enabled()

    def encrypt_content(self, plaintext: str) -> str:
        """Encrypt plaintext content.

        Args:
            plaintext: Plain text to encrypt

        Returns:
            JSON string of encrypted data (for storage in content_encrypted field)
        """
        if not self.enabled or not self.encryption_service:
            return ""

        encrypted_dict = self.encryption_service.encrypt(plaintext)
        return json.dumps(encrypted_dict)

    def decrypt_content(self, encrypted_json: str) -> str:
        """Decrypt encrypted content.

        Args:
            encrypted_json: JSON string from content_encrypted field

        Returns:
            Decrypted plaintext

        Raises:
            ValueError: If decryption fails
        """
        if not self.enabled or not self.encryption_service:
            return ""

        try:
            encrypted_dict = json.loads(encrypted_json)
            return self.encryption_service.decrypt(encrypted_dict)
        except Exception as e:
            raise ValueError(f"Failed to decrypt content: {str(e)}") from e

    def prepare_task_for_storage(
        self, content: str, description: str | None = None
    ) -> tuple[str, str, str | None, str | None]:
        """Prepare task content for storage.

        Args:
            content: Task content (plaintext)
            description: Task description (plaintext, optional)

        Returns:
            Tuple of (content, content_encrypted, description, description_encrypted)
            - If E2EE enabled: content is empty, encrypted fields contain data
            - If E2EE disabled: content contains plaintext, encrypted fields are None
        """
        if self.enabled:
            # E2EE mode: encrypt and store in _encrypted fields
            content_encrypted = self.encrypt_content(content)
            description_encrypted = (
                self.encrypt_content(description) if description else None
            )
            return "", content_encrypted, "", description_encrypted
        # Plain mode: store in regular fields
        return content, None, description or "", None

    def extract_task_content(
        self,
        content: str,
        content_encrypted: str | None,
        description: str,
        description_encrypted: str | None,
    ) -> tuple[str, str]:
        """Extract task content from storage.

        Args:
            content: Plain content field
            content_encrypted: Encrypted content field (JSON)
            description: Plain description field
            description_encrypted: Encrypted description field (JSON)

        Returns:
            Tuple of (content, description) in plaintext
        """
        if self.enabled and content_encrypted:
            # E2EE mode: decrypt from encrypted fields
            task_content = self.decrypt_content(content_encrypted)
            task_description = (
                self.decrypt_content(description_encrypted)
                if description_encrypted
                else ""
            )
            return task_content, task_description
        # Plain mode: use regular fields
        return content, description


def get_e2ee_handler() -> E2EEHandler:
    """Get E2EE handler based on configuration.

    Returns:
        E2EEHandler instance (enabled or disabled based on config and key existence)
    """
    from todopro_cli.services.config_service import get_config_service

    try:
        # Check if E2EE is enabled in config
        config_service = get_config_service()
        if not config_service.config.e2ee.enabled:
            return E2EEHandler(encryption_service=None)  # Disabled in config

        # E2EE enabled - try to load encryption service
        encryption_service = EncryptionService()
        if not encryption_service.is_enabled():
            # Key not set up yet
            return E2EEHandler(encryption_service=None)

        return E2EEHandler(encryption_service=encryption_service)

    except Exception:
        # If anything fails, disable E2EE
        return E2EEHandler(encryption_service=None)
