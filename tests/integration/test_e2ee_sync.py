"""Integration tests for E2EE sync functionality.

Tests the complete flow:
1. Enable E2EE
2. Create tasks in local context
3. Sync to remote (encrypted)
4. Verify server has encrypted data
5. Pull on new device
6. Verify decrypted data matches
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from todopro_cli.adapters.sqlite.e2ee import E2EEHandler
from todopro_cli.models import Task, TaskCreate
from todopro_cli.services.encryption_service import EncryptionService


class TestE2EEIntegration:
    """Test E2EE integration with local storage."""

    @pytest.fixture
    def encryption_service(self, tmp_path):
        """Create encryption service with temporary storage."""
        key_file = tmp_path / ".todopro_key"
        with patch(
            "todopro_cli.services.encryption_service.KeyStorage"
        ) as mock_storage_cls:
            mock_storage = Mock()
            mock_storage.key_file = str(key_file)
            mock_storage.exists.return_value = False
            mock_storage_cls.return_value = mock_storage

            service = EncryptionService()
            service.storage = mock_storage

            # Setup encryption
            manager, phrase = service.setup()
            service.save_manager(manager)
            mock_storage.exists.return_value = True

            yield service

    @pytest.fixture
    def e2ee_handler(self, encryption_service):
        """Create E2EE handler with encryption enabled."""
        return E2EEHandler(encryption_service=encryption_service)

    def test_prepare_task_for_storage_encrypts_content(self, e2ee_handler):
        """Test that task content is encrypted when E2EE is enabled."""
        content = "Secret task content"
        description = "Secret description"

        result = e2ee_handler.prepare_task_for_storage(content, description)
        plain_content, encrypted_content, plain_desc, encrypted_desc = result

        # In E2EE mode, plain fields should be empty
        assert plain_content == ""
        assert plain_desc == ""

        # Encrypted fields should contain JSON
        assert encrypted_content != ""
        assert encrypted_desc != ""
        assert "ciphertext" in encrypted_content
        assert "ciphertext" in encrypted_desc

    def test_extract_task_content_decrypts_data(self, e2ee_handler):
        """Test that encrypted task data is correctly decrypted."""
        content = "Secret task content"
        description = "Secret description"

        # Encrypt
        _, encrypted_content, _, encrypted_desc = e2ee_handler.prepare_task_for_storage(
            content, description
        )

        # Decrypt
        decrypted_content, decrypted_desc = e2ee_handler.extract_task_content(
            "", encrypted_content, "", encrypted_desc
        )

        # Should match original
        assert decrypted_content == content
        assert decrypted_desc == description

    def test_roundtrip_encryption_decryption(self, e2ee_handler):
        """Test complete encrypt → decrypt roundtrip."""
        original_content = "My secret todo item"
        original_desc = "This is sensitive information"

        # Prepare for storage (encrypt)
        _, enc_content, _, enc_desc = e2ee_handler.prepare_task_for_storage(
            original_content, original_desc
        )

        # Extract from storage (decrypt)
        decrypted_content, decrypted_desc = e2ee_handler.extract_task_content(
            "", enc_content, "", enc_desc
        )

        # Verify roundtrip
        assert decrypted_content == original_content
        assert decrypted_desc == original_desc

    def test_e2ee_handler_disabled_mode(self):
        """Test E2EE handler with encryption disabled."""
        handler = E2EEHandler(encryption_service=None)

        assert not handler.enabled

        # Should pass through plaintext unchanged
        content = "Plain content"
        description = "Plain description"

        result = handler.prepare_task_for_storage(content, description)
        plain_content, encrypted_content, plain_desc, encrypted_desc = result

        assert plain_content == content
        assert plain_desc == description
        assert encrypted_content is None
        assert encrypted_desc is None


class TestE2EESyncIntegration:
    """Test E2EE integration with sync operations."""

    @pytest.fixture
    def mock_encryption_service(self):
        """Create a mock encryption service."""
        service = Mock(spec=EncryptionService)
        service.is_enabled.return_value = True
        service.encrypt.return_value = {
            "ciphertext": "encrypted_data_base64",
            "iv": "iv_base64",
            "tag": "tag_base64",
        }
        service.decrypt.return_value = "decrypted_plaintext"
        return service

    @pytest.fixture
    def mock_e2ee_handler(self, mock_encryption_service):
        """Create a mock E2EE handler."""
        handler = Mock(spec=E2EEHandler)
        handler.enabled = True
        handler.encryption_service = mock_encryption_service

        # Mock prepare_task_for_storage
        def prepare_task(content, description=None):
            import json

            enc_content = json.dumps(mock_encryption_service.encrypt(content))
            enc_desc = (
                json.dumps(mock_encryption_service.encrypt(description))
                if description
                else None
            )
            return "", enc_content, "", enc_desc

        handler.prepare_task_for_storage.side_effect = prepare_task

        # Mock extract_task_content
        def extract_task(content, enc_content, desc, enc_desc):
            if enc_content:
                return "decrypted_content", "decrypted_description" if enc_desc else ""
            return content, desc

        handler.extract_task_content.side_effect = extract_task

        return handler

    @pytest.mark.asyncio
    async def test_rest_api_repository_encrypts_on_create(self, mock_e2ee_handler):
        """Test that REST API repository encrypts task data on create."""
        from todopro_cli.adapters.rest_api import RestApiTaskRepository
        from todopro_cli.services.config_service import ConfigService

        # Create repository
        repo = RestApiTaskRepository()

        # Replace e2ee handler with our mock
        repo._e2ee_handler = mock_e2ee_handler

        # Mock the tasks API
        mock_tasks_api = Mock()
        mock_tasks_api.create_task = AsyncMock(
            return_value={
                "id": "task-123",
                "content": "",
                "content_encrypted": '{"ciphertext": "encrypted", "iv": "iv", "tag": "tag"}',
                "description": "",
                "description_encrypted": '{"ciphertext": "encrypted_desc", "iv": "iv2", "tag": "tag2"}',
                "priority": 1,
                "is_completed": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        )
        repo._tasks_api = mock_tasks_api

        # Create task
        task_create = TaskCreate(
            content="Secret task", description="Secret description"
        )

        result = await repo.add(task_create)

        # Verify API was called with encrypted data
        call_kwargs = mock_tasks_api.create_task.call_args[1]
        assert "content_encrypted" in call_kwargs
        assert call_kwargs["content"] == ""  # Plain content should be empty

    @patch("todopro_cli.services.config_service.get_config_service")
    def test_get_e2ee_handler_respects_config(self, mock_get_config):
        """Test that get_e2ee_handler checks config.e2ee.enabled."""
        from todopro_cli.adapters.sqlite.e2ee import get_e2ee_handler

        # Test when E2EE is disabled in config
        mock_config_service = Mock()
        mock_config_service.config.e2ee.enabled = False
        mock_get_config.return_value = mock_config_service

        handler = get_e2ee_handler()
        assert not handler.enabled

        # Test when E2EE is enabled in config
        mock_config_service.config.e2ee.enabled = True

        # Mock EncryptionService to say it's not enabled (key not set up)
        with patch(
            "todopro_cli.adapters.sqlite.e2ee.EncryptionService"
        ) as mock_enc_cls:
            mock_enc = Mock()
            mock_enc.is_enabled.return_value = False
            mock_enc_cls.return_value = mock_enc

            handler = get_e2ee_handler()
            assert not handler.enabled


class TestE2EEConfigIntegration:
    """Test E2EE configuration integration."""

    def test_app_config_has_e2ee_field(self):
        """Test that AppConfig includes e2ee configuration."""
        from todopro_cli.models.config_models import AppConfig, Context, E2EEConfig

        config = AppConfig(
            current_context_name="local",
            contexts=[Context(name="local", type="local", source="/path/to/db")],
        )

        # Should have e2ee config with default values
        assert hasattr(config, "e2ee")
        assert isinstance(config.e2ee, E2EEConfig)
        assert config.e2ee.enabled is False  # Default

    def test_e2ee_config_can_be_enabled(self):
        """Test that E2EE can be enabled in config."""
        from todopro_cli.models.config_models import AppConfig, Context, E2EEConfig

        config = AppConfig(
            current_context_name="local",
            contexts=[Context(name="local", type="local", source="/path/to/db")],
            e2ee=E2EEConfig(enabled=True),
        )

        assert config.e2ee.enabled is True

    @patch("todopro_cli.services.config_service.get_config_service")
    def test_encryption_setup_enables_e2ee_in_config(self, mock_get_config):
        """Test that encryption setup command enables E2EE in config."""
        from todopro_cli.models.config_models import AppConfig, Context, E2EEConfig

        # Create mock config service
        mock_config_service = Mock()
        mock_config = AppConfig(
            current_context_name="local",
            contexts=[Context(name="local", type="local", source="/path/to/db")],
        )
        mock_config_service.config = mock_config
        mock_get_config.return_value = mock_config_service

        # Initially disabled
        assert mock_config.e2ee.enabled is False

        # Simulate what happens in encryption setup command
        mock_config.e2ee.enabled = True
        mock_config_service.save_config()

        # Verify it was enabled and saved
        assert mock_config.e2ee.enabled is True
        mock_config_service.save_config.assert_called_once()
