"""Encryption service for TodoPro CLI.

High-level service layer that connects crypto primitives to the rest of the application.
Provides E2EE setup, key management, and encryption/decryption operations.
"""

from dataclasses import dataclass
from pathlib import Path

from todopro_cli.models.crypto.cipher import EncryptedData
from todopro_cli.models.crypto.exceptions import (
    InvalidRecoveryPhraseError,
)
from todopro_cli.models.crypto.manager import EncryptionManager
from todopro_cli.models.crypto.storage import KeyStorage


@dataclass
class EncryptionStatus:
    """Represents current encryption configuration status."""

    enabled: bool
    key_file_exists: bool
    key_file_path: str | None
    key_valid: bool
    error: str | None = None


class EncryptionService:
    """
    High-level encryption service for TodoPro CLI.

    This service provides:
    - E2EE setup and initialization
    - Key management (rotate, recover, backup)
    - Encryption/decryption operations
    - Status checking

    Integrates with:
    - ConfigService for E2EE enabled/disabled state
    - KeyStorage for secure key persistence
    - EncryptionManager for crypto operations
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize encryption service.

        Args:
            config_dir: Directory for key storage. If None, uses default platform directory.
        """
        if config_dir is None:
            from platformdirs import user_config_dir

            config_dir = Path(user_config_dir("todopro-cli"))

        self.config_dir = config_dir
        self.storage = KeyStorage(config_dir)
        self._manager: EncryptionManager | None = None

    def _get_manager(self) -> EncryptionManager:
        """
        Get or load encryption manager.

        Returns:
            EncryptionManager instance

        Raises:
            FileNotFoundError: If no key is set up
        """
        if self._manager is None:
            key_b64 = self.storage.load_key()
            self._manager = EncryptionManager.from_base64_key(key_b64)
        return self._manager

    def is_enabled(self) -> bool:
        """
        Check if encryption is enabled.

        Returns:
            True if encryption key exists and is valid
        """
        if not self.storage.has_key():
            return False

        try:
            self._get_manager()
            return True
        except Exception:
            return False

    def get_status(self) -> EncryptionStatus:
        """
        Get detailed encryption status.

        Returns:
            EncryptionStatus with detailed information
        """
        key_exists = self.storage.has_key()
        key_path = str(self.storage.get_key_path()) if key_exists else None
        key_valid = False
        error = None

        if key_exists:
            try:
                self._get_manager()
                key_valid = True
            except Exception as e:
                error = str(e)

        return EncryptionStatus(
            enabled=key_valid,
            key_file_exists=key_exists,
            key_file_path=key_path,
            key_valid=key_valid,
            error=error,
        )

    def setup(self) -> tuple[EncryptionManager, str]:
        """
        Set up E2EE for the first time.

        Generates a new master encryption key and recovery phrase.
        Does NOT save the key - caller must save after user confirms.

        Returns:
            Tuple of (EncryptionManager, recovery_phrase_string)

        Example:
            >>> service = EncryptionService()
            >>> manager, phrase = service.setup()
            >>> # Display phrase to user, get confirmation
            >>> service.save_manager(manager)
        """
        manager = EncryptionManager.generate()
        recovery_phrase = manager.get_recovery_phrase()
        return manager, recovery_phrase

    def save_manager(self, manager: EncryptionManager) -> None:
        """
        Save encryption manager's key to storage.

        Args:
            manager: EncryptionManager to save
        """
        self.storage.save_key(manager.export_key())
        self._manager = manager

    def get_recovery_phrase(self) -> str:
        """
        Get recovery phrase for current encryption key.

        Returns:
            12-word recovery phrase

        Raises:
            FileNotFoundError: If no key is set up
        """
        manager = self._get_manager()
        return manager.get_recovery_phrase()

    def verify_recovery_phrase(self, phrase: str) -> bool:
        """
        Verify that a recovery phrase matches the current key.

        Args:
            phrase: Recovery phrase to verify

        Returns:
            True if phrase matches current key
        """
        try:
            manager = self._get_manager()
            return manager.verify_recovery_phrase(phrase)
        except Exception:
            return False

    def recover(self, recovery_phrase: str) -> EncryptionManager:
        """
        Recover encryption key from recovery phrase.

        Args:
            recovery_phrase: 12-word recovery phrase

        Returns:
            EncryptionManager restored from phrase

        Raises:
            InvalidRecoveryPhraseError: If phrase is invalid
        """
        try:
            manager = EncryptionManager.from_recovery_phrase(recovery_phrase)
            return manager
        except Exception as e:
            raise InvalidRecoveryPhraseError(
                f"Failed to recover key from phrase: {str(e)}"
            ) from e

    def encrypt(self, plaintext: str) -> dict[str, str]:
        """
        Encrypt plaintext data.

        Args:
            plaintext: Text to encrypt

        Returns:
            Dictionary with 'ciphertext', 'iv', 'authTag', 'version'

        Raises:
            FileNotFoundError: If no key is set up
        """
        manager = self._get_manager()
        encrypted = manager.encrypt(plaintext)
        return encrypted.to_dict()

    def decrypt(self, encrypted_dict: dict[str, str]) -> str:
        """
        Decrypt encrypted data.

        Args:
            encrypted_dict: Dictionary with 'ciphertext', 'iv', 'authTag'

        Returns:
            Decrypted plaintext

        Raises:
            FileNotFoundError: If no key is set up
            DecryptionError: If decryption fails
        """
        manager = self._get_manager()
        encrypted = EncryptedData.from_dict(encrypted_dict)
        return manager.decrypt(encrypted)

    def encrypt_dict(self, data: dict[str, str]) -> dict[str, dict[str, str]]:
        """
        Encrypt multiple fields in a dictionary.

        Args:
            data: Dictionary of plaintext fields

        Returns:
            Dictionary of encrypted fields

        Example:
            >>> encrypted = service.encrypt_dict({
            ...     "content": "Buy groceries",
            ...     "description": "Milk, eggs, bread"
            ... })
        """
        manager = self._get_manager()
        return manager.encrypt_dict(data)

    def decrypt_dict(self, encrypted_data: dict[str, dict[str, str]]) -> dict[str, str]:
        """
        Decrypt multiple fields from a dictionary.

        Args:
            encrypted_data: Dictionary of encrypted fields

        Returns:
            Dictionary of decrypted plaintext fields
        """
        manager = self._get_manager()
        return manager.decrypt_dict(encrypted_data)

    def rotate_key(
        self, old_password: str | None = None
    ) -> tuple[EncryptionManager, str]:
        """
        Rotate encryption key (generate new key).

        Note: This only generates a new key. The caller is responsible for:
        1. Re-encrypting all existing data with the new key
        2. Uploading re-encrypted data to server
        3. Saving the new key

        Args:
            old_password: Optional password for verification (not yet implemented)

        Returns:
            Tuple of (new_manager, new_recovery_phrase)
        """
        # Generate new key
        new_manager = EncryptionManager.generate()
        new_recovery_phrase = new_manager.get_recovery_phrase()

        return new_manager, new_recovery_phrase

    def delete_key(self) -> None:
        """
        Delete stored encryption key.

        WARNING: This will make all encrypted data inaccessible unless
        you have the recovery phrase backed up!
        """
        self.storage.delete_key()
        self._manager = None

    def backup_to_server(self) -> None:
        """
        Backup encrypted master key to server.

        TODO: Implement server API integration
        - POST /api/auth/setup-encryption with encrypted backup
        - Store recovery phrase encrypted with user's auth token
        """
        raise NotImplementedError("Server backup not yet implemented")

    def restore_from_server(self) -> EncryptionManager:
        """
        Restore encryption key from server backup.

        TODO: Implement server API integration
        - GET /api/auth/backup-master-key
        - Decrypt backup with user's auth token
        - Return restored EncryptionManager
        """
        raise NotImplementedError("Server restore not yet implemented")


def get_encryption_service() -> EncryptionService:
    """Factory function to get EncryptionService instance."""
    return EncryptionService()
