"""Tests for EncryptionService."""

import shutil
import tempfile
from pathlib import Path

import pytest

from todopro_cli.models.crypto.exceptions import InvalidRecoveryPhraseError
from todopro_cli.services.encryption_service import EncryptionService, EncryptionStatus


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for tests."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def encryption_service(temp_config_dir):
    """Create EncryptionService with temporary config directory."""
    return EncryptionService(config_dir=temp_config_dir)


class TestEncryptionSetup:
    """Tests for encryption setup."""

    def test_setup_generates_manager_and_phrase(self, encryption_service):
        """Test that setup generates encryption manager and recovery phrase."""
        manager, phrase = encryption_service.setup()

        assert manager is not None
        assert isinstance(phrase, str)
        # Recovery phrase should have words (24 for 256-bit keys)
        words = phrase.split()
        assert len(words) >= 12  # At least 12 words

    def test_setup_generates_unique_keys(self, encryption_service):
        """Test that multiple setups generate different keys."""
        manager1, phrase1 = encryption_service.setup()
        manager2, phrase2 = encryption_service.setup()

        assert phrase1 != phrase2
        assert manager1.export_key() != manager2.export_key()

    def test_save_manager_persists_key(self, encryption_service):
        """Test that save_manager persists key to storage."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        # Verify key file was created
        assert encryption_service.storage.has_key()

        # Verify we can load it back
        loaded_key = encryption_service.storage.load_key()
        assert loaded_key == manager.export_key()


class TestEncryptionStatus:
    """Tests for encryption status checking."""

    def test_is_enabled_returns_false_when_no_key(self, encryption_service):
        """Test is_enabled returns False when no key exists."""
        assert encryption_service.is_enabled() is False

    def test_is_enabled_returns_true_after_setup(self, encryption_service):
        """Test is_enabled returns True after setup."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        assert encryption_service.is_enabled() is True

    def test_get_status_when_not_set_up(self, encryption_service):
        """Test get_status returns correct info when not set up."""
        status = encryption_service.get_status()

        assert isinstance(status, EncryptionStatus)
        assert status.enabled is False
        assert status.key_file_exists is False
        assert status.key_file_path is None
        assert status.key_valid is False

    def test_get_status_when_set_up(self, encryption_service):
        """Test get_status returns correct info when set up."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        status = encryption_service.get_status()

        assert status.enabled is True
        assert status.key_file_exists is True
        assert status.key_file_path is not None
        assert status.key_valid is True
        assert status.error is None


class TestRecoveryPhrase:
    """Tests for recovery phrase operations."""

    def test_get_recovery_phrase_returns_phrase(self, encryption_service):
        """Test get_recovery_phrase returns recovery phrase."""
        manager, original_phrase = encryption_service.setup()
        encryption_service.save_manager(manager)

        phrase = encryption_service.get_recovery_phrase()

        assert phrase == original_phrase
        assert len(phrase.split()) >= 12  # At least 12 words

    def test_verify_recovery_phrase_correct(self, encryption_service):
        """Test verify_recovery_phrase returns True for correct phrase."""
        manager, phrase = encryption_service.setup()
        encryption_service.save_manager(manager)

        assert encryption_service.verify_recovery_phrase(phrase) is True

    def test_verify_recovery_phrase_incorrect(self, encryption_service):
        """Test verify_recovery_phrase returns False for incorrect phrase."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        wrong_phrase = (
            "wrong wrong wrong wrong wrong wrong wrong wrong wrong wrong wrong wrong"
        )
        assert encryption_service.verify_recovery_phrase(wrong_phrase) is False

    def test_recover_from_phrase(self, encryption_service):
        """Test recovering encryption manager from recovery phrase."""
        manager, phrase = encryption_service.setup()
        original_key = manager.export_key()

        # Recover from phrase
        recovered_manager = encryption_service.recover(phrase)

        # Should produce same key
        assert recovered_manager.export_key() == original_key

    def test_recover_with_invalid_phrase_raises(self, encryption_service):
        """Test recover raises with invalid phrase."""
        invalid_phrase = "not a valid recovery phrase at all"

        with pytest.raises(InvalidRecoveryPhraseError):
            encryption_service.recover(invalid_phrase)


class TestEncryptionDecryption:
    """Tests for encryption and decryption operations."""

    def test_encrypt_returns_dict_with_required_fields(self, encryption_service):
        """Test encrypt returns dictionary with required encryption fields."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        plaintext = "Hello, World!"
        encrypted = encryption_service.encrypt(plaintext)

        assert isinstance(encrypted, dict)
        assert "ciphertext" in encrypted
        assert "iv" in encrypted
        assert "authTag" in encrypted
        assert "version" in encrypted

    def test_encrypt_decrypt_roundtrip(self, encryption_service):
        """Test encrypting then decrypting returns original plaintext."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        original = "Sensitive data that needs encryption!"
        encrypted = encryption_service.encrypt(original)
        decrypted = encryption_service.decrypt(encrypted)

        assert decrypted == original

    def test_encrypt_produces_different_ciphertexts(self, encryption_service):
        """Test encrypting same plaintext twice produces different ciphertexts (due to random IV)."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        plaintext = "Same text"
        encrypted1 = encryption_service.encrypt(plaintext)
        encrypted2 = encryption_service.encrypt(plaintext)

        # Should have different IVs and ciphertexts
        assert encrypted1["iv"] != encrypted2["iv"]
        assert encrypted1["ciphertext"] != encrypted2["ciphertext"]

        # But both should decrypt to same plaintext
        assert encryption_service.decrypt(encrypted1) == plaintext
        assert encryption_service.decrypt(encrypted2) == plaintext

    def test_encrypt_dict_encrypts_multiple_fields(self, encryption_service):
        """Test encrypt_dict encrypts all fields in dictionary."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        data = {
            "content": "Task content",
            "description": "Task description",
        }

        encrypted = encryption_service.encrypt_dict(data)

        assert isinstance(encrypted, dict)
        assert "content" in encrypted
        assert "description" in encrypted
        assert isinstance(encrypted["content"], dict)
        assert "ciphertext" in encrypted["content"]

    def test_encrypt_decrypt_dict_roundtrip(self, encryption_service):
        """Test encrypting then decrypting dictionary returns original data."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        original = {
            "field1": "Value 1",
            "field2": "Value 2",
            "field3": "Value 3",
        }

        encrypted = encryption_service.encrypt_dict(original)
        decrypted = encryption_service.decrypt_dict(encrypted)

        assert decrypted == original


class TestKeyManagement:
    """Tests for key management operations."""

    def test_rotate_key_generates_new_key(self, encryption_service):
        """Test rotate_key generates a new manager and phrase."""
        manager1, phrase1 = encryption_service.setup()
        encryption_service.save_manager(manager1)

        manager2, phrase2 = encryption_service.rotate_key()

        # Should be different
        assert phrase1 != phrase2
        assert manager1.export_key() != manager2.export_key()

    def test_delete_key_removes_storage(self, encryption_service):
        """Test delete_key removes key from storage."""
        manager, _ = encryption_service.setup()
        encryption_service.save_manager(manager)

        assert encryption_service.storage.has_key()

        encryption_service.delete_key()

        assert not encryption_service.storage.has_key()
        assert encryption_service.is_enabled() is False

    def test_backup_to_server_not_implemented(self, encryption_service):
        """Test backup_to_server raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            encryption_service.backup_to_server()

    def test_restore_from_server_not_implemented(self, encryption_service):
        """Test restore_from_server raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            encryption_service.restore_from_server()
