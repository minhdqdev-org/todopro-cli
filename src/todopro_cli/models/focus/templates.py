"""Focus mode templates for different work types."""

from collections.abc import Callable
from typing import Any

from todopro_cli.models.config_models import AppConfig

DEFAULT_TEMPLATES = {
    "deep_work": {
        "duration": 90,
        "breaks_enabled": False,
        "description": "Uninterrupted deep focus",
    },
    "standard": {
        "duration": 25,
        "breaks_enabled": True,
        "description": "Classic Pomodoro",
    },
    "quick_task": {
        "duration": 15,
        "breaks_enabled": False,
        "description": "Short focused burst",
    },
    "long_session": {
        "duration": 45,
        "breaks_enabled": True,
        "description": "Extended focus with breaks",
    },
}


class TemplateManager:
    """Manage focus session templates."""

    def __init__(self, config: AppConfig, save_config: Callable[[], None]):
        """Initialize template manager.

        Args:
            config: Current application configuration.
            save_config: Callable that persists the configuration.
        """
        self.config = config
        self.save_config = save_config

    def get_templates(self) -> dict[str, dict[str, Any]]:
        """Get all templates (default + custom)."""
        custom_templates = self.config.focus_templates or {}
        return {**DEFAULT_TEMPLATES, **custom_templates}

    def get_template(self, name: str) -> dict[str, Any] | None:
        """Get a specific template by name."""
        templates = self.get_templates()
        return templates.get(name)

    def create_template(
        self,
        name: str,
        duration: int,
        breaks_enabled: bool = True,
        description: str = "",
    ) -> None:
        """Create a new custom template."""
        if self.config.focus_templates is None:
            self.config.focus_templates = {}

        self.config.focus_templates[name] = {
            "duration": duration,
            "breaks_enabled": breaks_enabled,
            "description": description or f"Custom {duration}-minute session",
        }

        self.save_config()

    def delete_template(self, name: str) -> bool:
        """Delete a custom template (can't delete defaults)."""
        if name in DEFAULT_TEMPLATES:
            return False

        if self.config.focus_templates and name in self.config.focus_templates:
            del self.config.focus_templates[name]
            self.save_config()
            return True

        return False

    def list_templates(self) -> list[tuple[str, dict[str, Any]]]:
        """List all templates with metadata."""
        templates = self.get_templates()
        return [(name, data) for name, data in templates.items()]
