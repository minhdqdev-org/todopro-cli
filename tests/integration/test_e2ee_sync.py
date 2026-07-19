"""Integration tests for E2EE sync functionality.

ADR-0024 dropped zero-knowledge E2EE: the CLI no longer encrypts on write —
`prepare_task_for_storage` / `_encrypt_task_fields` are now permanent
plaintext no-ops (see `docs/adr/ADR-0024-drop-e2ee.md`). These tests verify:
1. Local + REST write paths always produce plaintext, even with a legacy
   config/key that still reports encryption as "enabled".
2. The dormant decrypt path (`extract_task_content`/`decrypt_content`) can
   still read back already-encrypted legacy content.
3. The `encryption setup` command no longer flips `config.e2ee.enabled`.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from todopro_cli.adapters.sqlite.e2ee import E2EEHandler
from todopro_cli.models import TaskCreate
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

    def test_prepare_task_for_storage_is_always_plaintext(self, e2ee_handler):
        """ADR-0024: content is never encrypted anymore, even with a valid,
        'enabled' encryption service backing the handler."""
        content = "Secret task content"
        description = "Secret description"

        assert e2ee_handler.enabled is True  # legacy key is present and valid

        result = e2ee_handler.prepare_task_for_storage(content, description)
        plain_content, encrypted_content, plain_desc, encrypted_desc = result

        assert plain_content == content
        assert plain_desc == description
        assert encrypted_content is None
        assert encrypted_desc is None

    def test_extract_task_content_still_decrypts_legacy_ciphertext(self, e2ee_handler):
        """The read/decrypt path stays dormant-but-live: content encrypted
        before this change (or manually crafted) can still be read back."""
        content = "Secret task content"
        description = "Secret description"

        # Build ciphertext directly via the (still-intact) encrypt primitive,
        # simulating rows written before E2EE was dropped.
        legacy_encrypted_content = e2ee_handler.encrypt_content(content)
        legacy_encrypted_desc = e2ee_handler.encrypt_content(description)

        decrypted_content, decrypted_desc = e2ee_handler.extract_task_content(
            "", legacy_encrypted_content, "", legacy_encrypted_desc
        )

        assert decrypted_content == content
        assert decrypted_desc == description

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
    async def test_rest_api_repository_never_encrypts_on_create(self, mock_e2ee_handler):
        """ADR-0024: REST API repository always writes plaintext on create,
        even with a mock e2ee handler that reports `enabled=True` and would
        (per its own logic) have encrypted the payload — because
        `_encrypt_task_fields` is now a hard no-op that never calls into the
        handler at all."""
        from todopro_cli.adapters.rest_api import RestApiTaskRepository

        # Create repository
        repo = RestApiTaskRepository()

        # Replace e2ee handler with our mock (still reports enabled=True)
        repo._e2ee_handler = mock_e2ee_handler

        # Mock the tasks API — server echoes back plaintext, as it always
        # does now that the CLI stopped sending ciphertext.
        mock_tasks_api = Mock()
        mock_tasks_api.create_task = AsyncMock(
            return_value={
                "id": "task-123",
                "content": "Secret task",
                "description": "Secret description",
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

        await repo.add(task_create)

        # Verify API was called with plaintext data — no encrypted fields
        # injected, and the handler's prepare_task_for_storage was never
        # invoked for the write path.
        call_kwargs = mock_tasks_api.create_task.call_args[1]
        assert "content_encrypted" not in call_kwargs
        assert "description_encrypted" not in call_kwargs
        assert call_kwargs["content"] == "Secret task"
        mock_e2ee_handler.prepare_task_for_storage.assert_not_called()

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
    def test_encryption_setup_command_no_longer_enables_e2ee_in_config(
        self, mock_get_config
    ):
        """ADR-0024: the `encryption setup` command is discontinued — it must
        NOT flip `config.e2ee.enabled` or persist config anymore."""
        from typer.testing import CliRunner

        from todopro_cli.commands.encryption_command import app
        from todopro_cli.models.config_models import AppConfig, Context

        mock_config_service = Mock()
        mock_config = AppConfig(
            current_context_name="local",
            contexts=[Context(name="local", type="local", source="/path/to/db")],
        )
        mock_config_service.config = mock_config
        mock_get_config.return_value = mock_config_service

        assert mock_config.e2ee.enabled is False

        result = CliRunner().invoke(app, ["setup"])

        assert result.exit_code == 0
        assert "discontinued" in result.output.lower()
        # Config must be left untouched: no enabling, no save.
        assert mock_config.e2ee.enabled is False
        mock_config_service.save_config.assert_not_called()
