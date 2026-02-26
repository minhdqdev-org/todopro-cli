"""Unit tests for E2EE handler (e2ee.py)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.adapters.sqlite.e2ee import E2EEHandler, get_e2ee_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_disabled_handler() -> E2EEHandler:
    """E2EE disabled (no encryption service)."""
    return E2EEHandler(encryption_service=None)


def _make_enabled_handler() -> E2EEHandler:
    """E2EE enabled with a mock EncryptionService."""
    svc = MagicMock()
    svc.is_enabled.return_value = True
    svc.encrypt.side_effect = lambda text: {"ciphertext": text[::-1], "nonce": "aaa"}
    svc.decrypt.side_effect = lambda d: d["ciphertext"][::-1]
    handler = E2EEHandler(encryption_service=svc)
    return handler


# ---------------------------------------------------------------------------
# E2EEHandler.__init__ and .enabled
# ---------------------------------------------------------------------------


class TestE2EEHandlerInit:
    def test_disabled_when_no_service(self):
        h = E2EEHandler(encryption_service=None)
        assert h.enabled is False

    def test_disabled_when_service_not_enabled(self):
        svc = MagicMock()
        svc.is_enabled.return_value = False
        h = E2EEHandler(encryption_service=svc)
        assert h.enabled is False

    def test_enabled_when_service_enabled(self):
        svc = MagicMock()
        svc.is_enabled.return_value = True
        h = E2EEHandler(encryption_service=svc)
        assert h.enabled is True


# ---------------------------------------------------------------------------
# encrypt_content
# ---------------------------------------------------------------------------


class TestEncryptContent:
    def test_returns_empty_when_disabled(self):
        h = _make_disabled_handler()
        result = h.encrypt_content("hello")
        assert result == ""

    def test_returns_json_when_enabled(self):
        h = _make_enabled_handler()
        result = h.encrypt_content("hello")
        parsed = json.loads(result)
        assert "ciphertext" in parsed

    def test_encrypted_is_reversible(self):
        h = _make_enabled_handler()
        plaintext = "secret task content"
        encrypted = h.encrypt_content(plaintext)
        decrypted = h.decrypt_content(encrypted)
        assert decrypted == plaintext


# ---------------------------------------------------------------------------
# decrypt_content
# ---------------------------------------------------------------------------


class TestDecryptContent:
    def test_returns_empty_when_disabled(self):
        h = _make_disabled_handler()
        result = h.decrypt_content('{"ciphertext": "abc"}')
        assert result == ""

    def test_decrypts_valid_json(self):
        h = _make_enabled_handler()
        encrypted_json = h.encrypt_content("my task")
        result = h.decrypt_content(encrypted_json)
        assert result == "my task"

    def test_raises_value_error_on_bad_data(self):
        svc = MagicMock()
        svc.is_enabled.return_value = True
        svc.decrypt.side_effect = Exception("bad key")
        h = E2EEHandler(encryption_service=svc)
        with pytest.raises(ValueError, match="Failed to decrypt"):
            h.decrypt_content('{"bad": "json"}')

    def test_raises_value_error_on_invalid_json(self):
        h = _make_enabled_handler()
        with pytest.raises((ValueError, json.JSONDecodeError)):
            h.decrypt_content("not-valid-json")


# ---------------------------------------------------------------------------
# prepare_task_for_storage
# ---------------------------------------------------------------------------


class TestPrepareTaskForStorage:
    def test_plain_mode_returns_content_as_is(self):
        h = _make_disabled_handler()
        content, content_enc, desc, desc_enc = h.prepare_task_for_storage(
            "my task", "my description"
        )
        assert content == "my task"
        assert content_enc is None
        assert desc == "my description"
        assert desc_enc is None

    def test_plain_mode_none_description_defaults_empty(self):
        h = _make_disabled_handler()
        content, content_enc, desc, desc_enc = h.prepare_task_for_storage(
            "my task", None
        )
        assert content == "my task"
        assert desc == ""
        assert content_enc is None
        assert desc_enc is None

    def test_e2ee_mode_content_is_empty_string(self):
        h = _make_enabled_handler()
        content, content_enc, desc, desc_enc = h.prepare_task_for_storage(
            "secret", "notes"
        )
        assert content == ""
        assert content_enc is not None
        assert content_enc != ""

    def test_e2ee_mode_description_encrypted_when_provided(self):
        h = _make_enabled_handler()
        _, _, _, desc_enc = h.prepare_task_for_storage("task", "desc text")
        assert desc_enc is not None

    def test_e2ee_mode_no_description_gives_none_desc_enc(self):
        h = _make_enabled_handler()
        _, _, _, desc_enc = h.prepare_task_for_storage("task", None)
        assert desc_enc is None


# ---------------------------------------------------------------------------
# extract_task_content
# ---------------------------------------------------------------------------


class TestExtractTaskContent:
    def test_plain_mode_returns_fields_as_is(self):
        h = _make_disabled_handler()
        content, desc = h.extract_task_content(
            "task text", None, "task desc", None
        )
        assert content == "task text"
        assert desc == "task desc"

    def test_plain_mode_ignores_encrypted_fields(self):
        h = _make_disabled_handler()
        content, desc = h.extract_task_content(
            "plain", '{"ciphertext": "xyz"}', "plain desc", None
        )
        assert content == "plain"

    def test_e2ee_mode_decrypts_content(self):
        h = _make_enabled_handler()
        enc_content = h.encrypt_content("real content")
        content, desc = h.extract_task_content("", enc_content, "", None)
        assert content == "real content"

    def test_e2ee_mode_decrypts_description(self):
        h = _make_enabled_handler()
        enc_desc = h.encrypt_content("real desc")
        _, desc = h.extract_task_content("", h.encrypt_content("x"), "", enc_desc)
        assert desc == "real desc"

    def test_e2ee_mode_empty_description_encrypted_gives_empty(self):
        h = _make_enabled_handler()
        enc_content = h.encrypt_content("task")
        _, desc = h.extract_task_content("", enc_content, "", None)
        assert desc == ""

    def test_plain_mode_when_no_encrypted_field(self):
        h = _make_enabled_handler()
        # content_encrypted is None/empty → falls back to plain mode
        content, desc = h.extract_task_content("plain text", None, "plain desc", None)
        assert content == "plain text"


# ---------------------------------------------------------------------------
# get_e2ee_handler
# ---------------------------------------------------------------------------


class TestGetE2eeHandler:
    def test_returns_disabled_handler_when_e2ee_disabled_in_config(self):
        mock_config = MagicMock()
        mock_config.config.e2ee.enabled = False

        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=mock_config,
        ):
            handler = get_e2ee_handler()

        assert isinstance(handler, E2EEHandler)
        assert handler.enabled is False

    def test_returns_disabled_handler_when_key_not_set_up(self):
        mock_config = MagicMock()
        mock_config.config.e2ee.enabled = True

        mock_enc_svc = MagicMock()
        mock_enc_svc.is_enabled.return_value = False

        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=mock_config,
        ), patch(
            "todopro_cli.adapters.sqlite.e2ee.EncryptionService",
            return_value=mock_enc_svc,
        ):
            handler = get_e2ee_handler()

        assert handler.enabled is False

    def test_returns_enabled_handler_when_key_ready(self):
        mock_config = MagicMock()
        mock_config.config.e2ee.enabled = True

        mock_enc_svc = MagicMock()
        mock_enc_svc.is_enabled.return_value = True

        with patch(
            "todopro_cli.services.config_service.get_config_service",
            return_value=mock_config,
        ), patch(
            "todopro_cli.adapters.sqlite.e2ee.EncryptionService",
            return_value=mock_enc_svc,
        ):
            handler = get_e2ee_handler()

        assert handler.enabled is True

    def test_returns_disabled_on_any_exception(self):
        with patch(
            "todopro_cli.services.config_service.get_config_service",
            side_effect=RuntimeError("config error"),
        ):
            handler = get_e2ee_handler()

        assert isinstance(handler, E2EEHandler)
        assert handler.enabled is False
