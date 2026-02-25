"""Enhanced configuration models for context system.

This module defines the new context-aware configuration models
that support multiple storage backends (local/remote).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class APIConfig(BaseModel):
    """API configuration."""

    endpoint: str = Field(default="https://todopro.minhdq.dev/api")
    timeout: int = Field(default=30)
    retry: int = Field(default=3)


class AuthConfig(BaseModel):
    """Authentication configuration."""

    auto_refresh: bool = Field(default=True)


class OutputConfig(BaseModel):
    """Output configuration."""

    format: str = Field(default="pretty")
    color: bool = Field(default=True)
    icons: bool = Field(default=True)
    icon_style: str = Field(default="emoji")  # emoji, nerd-font, ascii
    compact: bool = Field(default=False)


class UIConfig(BaseModel):
    """UI configuration."""

    interactive: bool = Field(default=False)
    page_size: int = Field(default=30)
    language: str = Field(default="en")
    timezone: str = Field(default="UTC")


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True)
    ttl: int = Field(default=300)


class SyncConfig(BaseModel):
    """Sync configuration."""

    auto: bool = Field(default=False)
    interval: int = Field(default=300)


class E2EEConfig(BaseModel):
    """End-to-end encryption configuration."""

    model_config = {"extra": "allow"}  # Allow future fields like key_backup_url, etc.

    enabled: bool = Field(default=False, description="Whether E2EE is enabled")


class Context(BaseModel):
    """Context configuration for a storage backend.

    Represents either a local SQLite vault or remote API endpoint.
    """

    name: str = Field(..., description="Unique context name")
    type: Literal["local", "remote"] = Field(..., description="Context type")
    source: str = Field(..., description="Database path or API URL")
    user: str | None = Field(default=None, description="User email (remote only)")
    user_id: str | None = Field(default=None, description="User ID (local contexts)")
    workspace_id: str | None = Field(default=None, description="Workspace ID")
    master_key_backup: str | None = None  # Encrypted with recovery phrase
    description: str = Field(default="", description="Human-readable description")

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str, _) -> str:
        """Validate source format based on context type."""
        # Basic validation - just ensure it's not empty
        if not v or not v.strip():
            raise ValueError("source cannot be empty")
        return v.strip()


class AppConfig(BaseModel):
    """Main TodoPro configuration"""

    current_context_name: str = Field(
        default="default", description="Active context name"
    )
    contexts: list[Context] = Field(
        default_factory=list, description="Available contexts"
    )

    api: APIConfig = Field(default_factory=APIConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    sync: SyncConfig = Field(default_factory=SyncConfig)
    e2ee: E2EEConfig = Field(default_factory=E2EEConfig)

    # Focus-related settings
    focus_templates: dict[str, dict] | None = None
    focus_suggestions: dict[str, dict] | None = None
    focus_goals: dict[str, dict] | None = None
    achievements: dict[str, dict] | None = None

    def get_context(self, name: str) -> Context:
        """Get context by name."""
        for ctx in self.contexts:
            if ctx.name == name:
                return ctx
        raise ValueError(f"Context '{name}' not found")

    def get_current_context(self) -> Context:
        """Get the currently active context."""
        return self.get_context(self.current_context_name)

    def add_context(self, context: Context):
        """Add a new context.

        Raises:
            ValueError: If context with the same name already exists
        """
        # Check for existing context with same name
        existing = [ctx for ctx in self.contexts if ctx.name == context.name]
        if existing:
            raise ValueError(
                f"Context '{context.name}' already exists."
                " Use a different name or remove the existing context first."
            )
        self.contexts.append(context)

    def remove_context(self, name: str):
        """Remove a context by name."""
        original_len = len(self.contexts)
        self.contexts = [ctx for ctx in self.contexts if ctx.name != name]
        if len(self.contexts) == original_len:
            raise ValueError(f"Context '{name}' not found")
        return True

    def rename_context(self, old_name: str, new_name: str):
        """Rename a context."""
        for ctx in self.contexts:
            if ctx.name == old_name:
                ctx.name = new_name
                if self.current_context_name == old_name:
                    self.current_context_name = new_name
                return True
        raise ValueError(f"Context '{old_name}' not found")
