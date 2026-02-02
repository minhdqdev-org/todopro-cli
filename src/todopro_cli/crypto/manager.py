"""High-level encryption manager for TodoPro."""

from typing import Dict

from todopro_cli.crypto.cipher import EncryptedData, decrypt, encrypt
from todopro_cli.crypto.keys import MasterKey
from todopro_cli.crypto.mnemonic import RecoveryPhrase


class EncryptionManager:
    """High-level interface for TodoPro encryption."""

    def __init__(self, master_key: MasterKey):
        """Initialize with a master key."""
        self.master_key = master_key

    @classmethod
    def generate(cls) -> "EncryptionManager":
        """Create new manager with random master key."""
        master_key = MasterKey.generate()
        return cls(master_key)

    @classmethod
    def from_master_key(cls, master_key: MasterKey) -> "EncryptionManager":
        """Create manager from existing master key."""
        return cls(master_key)

    @classmethod
    def from_recovery_phrase(cls, phrase_str: str) -> "EncryptionManager":
        """Restore manager from recovery phrase."""
        recovery_phrase = RecoveryPhrase.from_words(phrase_str)
        master_key = recovery_phrase.to_master_key()
        return cls(master_key)

    @classmethod
    def from_base64_key(cls, key_b64: str) -> "EncryptionManager":
        """Create manager from base64-encoded master key."""
        master_key = MasterKey.from_base64(key_b64)
        return cls(master_key)

    def encrypt(self, plaintext: str) -> EncryptedData:
        """Encrypt plaintext data."""
        return encrypt(plaintext, self.master_key)

    def decrypt(self, encrypted: EncryptedData) -> str:
        """Decrypt encrypted data."""
        return decrypt(encrypted, self.master_key)

    def encrypt_dict(self, data: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Encrypt multiple fields in a dictionary."""
        encrypted_data = {}
        for key, value in data.items():
            if value:  # Only encrypt non-empty values
                encrypted = self.encrypt(value)
                encrypted_data[key] = encrypted.to_dict()
        return encrypted_data

    def decrypt_dict(self, encrypted_data: Dict[str, Dict[str, str]]) -> Dict[str, str]:
        """Decrypt multiple fields from a dictionary."""
        plaintext_data = {}
        for key, value in encrypted_data.items():
            encrypted = EncryptedData.from_dict(value)
            plaintext_data[key] = self.decrypt(encrypted)
        return plaintext_data

    def get_recovery_phrase(self) -> str:
        """Get 12-word recovery phrase for this manager's key."""
        recovery_phrase = RecoveryPhrase.from_master_key(self.master_key)
        return recovery_phrase.to_string()

    def export_key(self) -> str:
        """Export master key as base64 string."""
        return self.master_key.to_base64()

    def verify_recovery_phrase(self, phrase_str: str) -> bool:
        """Verify that a recovery phrase matches this manager's key."""
        try:
            test_manager = EncryptionManager.from_recovery_phrase(phrase_str)
            return self.master_key == test_manager.master_key
        except Exception:
            return False
