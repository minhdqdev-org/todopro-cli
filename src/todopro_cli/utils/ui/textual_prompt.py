"""Textual-based interactive prompt for task input with autocomplete.

This module provides a modern TUI for task input matching the design spec
from docs/CLI_UI_UX_IMPROVE.md with full syntax highlighting support.
"""

import json
import os
from datetime import datetime

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.suggester import Suggester
from textual.widgets import Input, Static

from todopro_cli.services.config_service import get_config_service


class TaskSuggester(Suggester):
    """Suggester for inline autocomplete."""

    def __init__(self):
        super().__init__(use_cache=False, case_sensitive=False)
        self.projects = []
        self.labels = []

    async def get_suggestion(self, value: str) -> str | None:
        """Get inline suggestion."""
        if not self.projects and not self.labels:
            return None

        # Check for label completion (@word)
        if "@" in value:
            parts = value.rsplit("@", 1)
            if len(parts) == 2 and parts[1]:
                prefix = parts[1].lower()
                matches = [
                    label for label in self.labels if label.lower().startswith(prefix)
                ]
                if matches:
                    return parts[0] + "@" + matches[0]

        # Check for project completion (#word)
        if "#" in value:
            parts = value.rsplit("#", 1)
            if len(parts) == 2 and parts[1]:
                prefix = parts[1].lower()
                matches = [
                    project
                    for project in self.projects
                    if project.lower().startswith(prefix)
                ]
                if matches:
                    return parts[0] + "#" + matches[0]

        return None


class HighlightedInput(Input):
    """Custom input widget - syntax highlighting applied via CSS styling."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.projects = []
        self.labels = []
        self.date_keywords = [
            "today",
            "tomorrow",
            "tom",
            "yesterday",
            "monday",
            "mon",
            "tuesday",
            "tue",
            "wednesday",
            "wed",
            "thursday",
            "thu",
            "friday",
            "fri",
            "saturday",
            "sat",
            "sunday",
            "sun",
        ]
        self.keyword_unhighlighted = set()

    def get_suggestions(self, text: str) -> list[str]:
        """Get suggestions list for display."""
        if not self.projects and not self.labels:
            return []

        # Label completion
        if "@" in text:
            parts = text.rsplit("@", 1)
            if len(parts) == 2:
                prefix = parts[1].lower()
                if prefix:
                    matches = [
                        f"@{label}"
                        for label in self.labels
                        if label.lower().startswith(prefix)
                    ]
                    return sorted(matches, key=lambda x: x.lower())[:10]
                return sorted([f"@{label}" for label in self.labels])[:10]

        # Project completion
        if "#" in text:
            parts = text.rsplit("#", 1)
            if len(parts) == 2:
                prefix = parts[1].lower()
                if prefix:
                    matches = [
                        f"#{project}"
                        for project in self.projects
                        if project.lower().startswith(prefix)
                    ]
                    return sorted(matches, key=lambda x: x.lower())[:10]
                return sorted([f"#{project}" for project in self.projects])[:10]

        return []


class QuickAddApp(App):
    """Textual app for task input matching the UI spec with syntax highlighting."""

    CSS = """
    Screen {
        background: $background;
        padding: 0;
    }

    #project-label {
        width: 100%;
        height: 1;
        content-align: left middle;
        padding: 0 1;
    }

    #top-separator {
        width: 100%;
        height: 1;
        color: $text-muted;
    }

    #task-input {
        width: 100%;
        height: 1;
        border: none;
        padding: 0 1;
        background: $background;
    }

    #bottom-separator {
        width: 100%;
        height: 1;
        color: $text-muted;
    }

    #suggestions {
        width: 100%;
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }

    #help-text {
        width: 100%;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        profile: str = "default",
        default_project: str = "Inbox",
    ):
        super().__init__()
        self.profile = profile
        self.default_project = default_project
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the app layout."""

        width = os.get_terminal_size().columns

        with Vertical():
            yield Static(f" {self.default_project}", id="project-label")
            yield Static("─" * width, id="top-separator")
            yield HighlightedInput(
                placeholder="Enter your task description",
                suggester=TaskSuggester(),
                id="task-input",
            )
            yield Static("─" * width, id="bottom-separator")
            yield Static("", id="suggestions")
            yield Static(
                " Press [bold]Enter[/bold] to submit or [bold]Ctrl+C[/bold] to cancel.",
                id="help-text",
                markup=True,
            )

    def on_mount(self) -> None:
        """Focus the input when app starts."""
        self.query_one("#task-input", HighlightedInput).focus()

    @on(Input.Changed)
    def handle_input_change(self, event: Input.Changed) -> None:
        """Update suggestions when input changes."""
        task_input = self.query_one("#task-input", HighlightedInput)
        suggestions_widget = self.query_one("#suggestions", Static)

        suggestions = task_input.get_suggestions(event.value)

        # Update suggestions display
        if suggestions:
            lines = []
            for i, suggestion in enumerate(suggestions):
                marker = "▋  " if i == 0 else "   "
                if i == 0:
                    lines.append(f"{marker}[bold]{suggestion}[/bold]")
                else:
                    lines.append(f"{marker}{suggestion}")
            suggestions_widget.update("\n".join(lines))
        else:
            suggestions_widget.update("")

    @on(Input.Submitted)
    def handle_submit(self, event: Input.Submitted) -> None:
        """Handle task submission."""
        value = event.value.strip()
        if value:
            self.result = value
            self.exit()

    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key in ("ctrl+c", "escape"):
            self.result = None
            self.exit()


def load_cache() -> tuple[list[str], list[str]]:
    """Load projects and labels from API and cache them."""

    config_service = get_config_service()

    cache_file = config_service.data_dir / "quick_add_cache.json"

    # Check if cache exists and is recent (< 5 minutes old)
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        cache_age = datetime.now().timestamp() - data.get("timestamp", 0)
        if cache_age < 300:  # 5 minutes
            return (
                data.get("projects", []),
                data.get("labels", []),
            )

    # Fetch from API

    projects = project_service.list_projects()
    labels = label_service.list_labels()

    projects = [p.get("name", "") for p in projects.get("data", [])]
    # Strip @ prefix from label names if present
    labels = [label.get("name", "").lstrip("@") for label in labels.get("data", [])]

    # Save to cache file
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "projects": projects,
                "labels": labels,
                "timestamp": datetime.now().timestamp(),
            },
            f,
        )

    return projects, labels


def get_interactive_input(default_project: str = "Inbox") -> str | None:
    """Get task input using Textual interactive prompt."""
    # Load cache
    projects, labels = load_cache()

    # Create and run app
    app = QuickAddApp(default_project=default_project)
    app.run()
