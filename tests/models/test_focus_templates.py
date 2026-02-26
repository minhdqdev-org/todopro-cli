"""Unit tests for FocusTemplateManager (models/focus/templates.py)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from todopro_cli.models.config_models import AppConfig
from todopro_cli.models.focus.templates import DEFAULT_TEMPLATES, TemplateManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_config(custom_templates=None) -> AppConfig:
    config = AppConfig()
    config.focus_templates = custom_templates
    return config


def _make_manager(custom_templates=None):
    config = _make_config(custom_templates)
    save_fn = MagicMock()
    return TemplateManager(config=config, save_config=save_fn), config, save_fn


# ---------------------------------------------------------------------------
# get_templates
# ---------------------------------------------------------------------------


class TestGetTemplates:
    def test_returns_defaults_when_no_custom(self):
        manager, _, _ = _make_manager()
        templates = manager.get_templates()
        for key in DEFAULT_TEMPLATES:
            assert key in templates

    def test_custom_templates_merged_with_defaults(self):
        custom = {"sprint": {"duration": 30, "breaks_enabled": False, "description": "Sprint"}}
        manager, _, _ = _make_manager(custom_templates=custom)
        templates = manager.get_templates()
        assert "sprint" in templates
        assert "deep_work" in templates  # default still present

    def test_custom_overrides_default(self):
        """Custom template with same name as default should override it."""
        custom = {"deep_work": {"duration": 60, "breaks_enabled": True, "description": "Modified"}}
        manager, _, _ = _make_manager(custom_templates=custom)
        templates = manager.get_templates()
        assert templates["deep_work"]["duration"] == 60


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------


class TestGetTemplate:
    def test_get_existing_default(self):
        manager, _, _ = _make_manager()
        tmpl = manager.get_template("deep_work")
        assert tmpl is not None
        assert tmpl["duration"] == 90

    def test_get_existing_custom(self):
        custom = {"my_focus": {"duration": 20, "breaks_enabled": False, "description": "My session"}}
        manager, _, _ = _make_manager(custom_templates=custom)
        tmpl = manager.get_template("my_focus")
        assert tmpl is not None
        assert tmpl["duration"] == 20

    def test_get_nonexistent_returns_none(self):
        manager, _, _ = _make_manager()
        tmpl = manager.get_template("nonexistent_template")
        assert tmpl is None

    def test_get_all_defaults(self):
        manager, _, _ = _make_manager()
        for name in DEFAULT_TEMPLATES:
            assert manager.get_template(name) is not None


# ---------------------------------------------------------------------------
# create_template
# ---------------------------------------------------------------------------


class TestCreateTemplate:
    def test_create_when_focus_templates_is_none(self):
        """Creating a template when focus_templates is None initializes the dict."""
        manager, config, save_fn = _make_manager(custom_templates=None)
        assert config.focus_templates is None

        manager.create_template("new_template", duration=20)

        assert config.focus_templates is not None
        assert "new_template" in config.focus_templates
        save_fn.assert_called_once()

    def test_create_with_all_params(self):
        manager, config, save_fn = _make_manager()
        manager.create_template(
            "custom",
            duration=45,
            breaks_enabled=False,
            description="Custom session",
        )
        tmpl = config.focus_templates["custom"]
        assert tmpl["duration"] == 45
        assert tmpl["breaks_enabled"] is False
        assert tmpl["description"] == "Custom session"
        save_fn.assert_called_once()

    def test_create_with_default_description(self):
        """Empty description generates a default description."""
        manager, config, save_fn = _make_manager()
        manager.create_template("auto_desc", duration=35, description="")
        tmpl = config.focus_templates["auto_desc"]
        assert "35" in tmpl["description"]  # should mention duration

    def test_create_template_calls_save(self):
        manager, _, save_fn = _make_manager()
        manager.create_template("save_test", duration=25)
        save_fn.assert_called_once()

    def test_create_adds_to_existing_templates(self):
        manager, config, _ = _make_manager(
            custom_templates={"existing": {"duration": 10, "breaks_enabled": False, "description": "Old"}}
        )
        manager.create_template("new_one", duration=20)
        assert "existing" in config.focus_templates
        assert "new_one" in config.focus_templates


# ---------------------------------------------------------------------------
# delete_template
# ---------------------------------------------------------------------------


class TestDeleteTemplate:
    def test_cannot_delete_default_template(self):
        manager, _, save_fn = _make_manager()
        result = manager.delete_template("deep_work")
        assert result is False
        save_fn.assert_not_called()

    def test_delete_custom_template(self):
        custom = {"my_custom": {"duration": 20, "breaks_enabled": False, "description": "Test"}}
        manager, config, save_fn = _make_manager(custom_templates=custom)
        result = manager.delete_template("my_custom")
        assert result is True
        assert "my_custom" not in (config.focus_templates or {})
        save_fn.assert_called_once()

    def test_delete_nonexistent_returns_false(self):
        manager, _, save_fn = _make_manager()
        result = manager.delete_template("does_not_exist")
        assert result is False
        save_fn.assert_not_called()

    def test_delete_when_focus_templates_is_none(self):
        manager, config, save_fn = _make_manager(custom_templates=None)
        result = manager.delete_template("anything")
        assert result is False
        save_fn.assert_not_called()

    def test_delete_all_defaults_return_false(self):
        manager, _, _ = _make_manager()
        for name in DEFAULT_TEMPLATES:
            assert manager.delete_template(name) is False


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


class TestListTemplates:
    def test_list_returns_all_templates(self):
        manager, _, _ = _make_manager()
        listing = manager.list_templates()
        assert isinstance(listing, list)
        names = [name for name, _ in listing]
        for key in DEFAULT_TEMPLATES:
            assert key in names

    def test_list_includes_custom(self):
        custom = {"custom1": {"duration": 15, "breaks_enabled": True, "description": "c1"}}
        manager, _, _ = _make_manager(custom_templates=custom)
        listing = manager.list_templates()
        names = [name for name, _ in listing]
        assert "custom1" in names
        assert "deep_work" in names

    def test_list_tuples_have_name_and_data(self):
        manager, _, _ = _make_manager()
        listing = manager.list_templates()
        for item in listing:
            assert isinstance(item, tuple)
            assert len(item) == 2
            name, data = item
            assert isinstance(name, str)
            assert isinstance(data, dict)
