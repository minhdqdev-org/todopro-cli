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

from todopro_cli.api.client import get_client
from todopro_cli.api.labels import LabelsAPI
from todopro_cli.api.projects import ProjectsAPI
from todopro_cli.config import get_config_manager


class TaskCache:
    """Cache for projects and labels."""

    def __init__(self, projects: list[str], labels: list[str]):
        self.projects = projects
        self.labels = labels


class TaskSuggester(Suggester):
    """Suggester for inline autocomplete."""

    def __init__(self, cache: TaskCache | None = None):
        super().__init__(use_cache=False, case_sensitive=False)
        self.task_cache = cache or TaskCache([], [])

    async def get_suggestion(self, value: str) -> str | None:
        """Get inline suggestion."""
        if not self.task_cache:
            return None

        # Check for label completion (@word)
        if "@" in value:
            parts = value.rsplit("@", 1)
            if len(parts) == 2 and parts[1]:
                prefix = parts[1].lower()
                matches = [
                    label
                    for label in self.task_cache.labels
                    if label.lower().startswith(prefix)
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
                    for project in self.task_cache.projects
                    if project.lower().startswith(prefix)
                ]
                if matches:
                    return parts[0] + "#" + matches[0]

        return None


class HighlightedInput(Input):
    """Custom input widget - syntax highlighting applied via CSS styling."""

    def __init__(self, cache: TaskCache | None = None, **kwargs):
        super().__init__(**kwargs)
        self.cache = cache or TaskCache([], [])
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
        if not self.cache:
            return []

        # Label completion
        if "@" in text:
            parts = text.rsplit("@", 1)
            if len(parts) == 2:
                prefix = parts[1].lower()
                if prefix:
                    matches = [
                        f"@{label}"
                        for label in self.cache.labels
                        if label.lower().startswith(prefix)
                    ]
                    return sorted(matches, key=lambda x: x.lower())[:10]
                return sorted([f"@{label}" for label in self.cache.labels])[:10]

        # Project completion
        if "#" in text:
            parts = text.rsplit("#", 1)
            if len(parts) == 2:
                prefix = parts[1].lower()
                if prefix:
                    matches = [
                        f"#{project}"
                        for project in self.cache.projects
                        if project.lower().startswith(prefix)
                    ]
                    return sorted(matches, key=lambda x: x.lower())[:10]
                return sorted([f"#{project}" for project in self.cache.projects])[:10]

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
        cache: TaskCache | None = None,
    ):
        super().__init__()
        self.profile = profile
        self.default_project = default_project
        self.cache = cache
        self.result: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the app layout."""

        width = os.get_terminal_size().columns

        with Vertical():
            yield Static(f" {self.default_project}", id="project-label")
            yield Static("─" * width, id="top-separator")
            yield HighlightedInput(
                placeholder="Enter your task description",
                cache=self.cache,
                suggester=TaskSuggester(self.cache),
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


async def load_cache(profile: str) -> TaskCache:
    """Load projects and labels from API and cache them."""
    config_manager = get_config_manager(profile)
    cache_file = config_manager.data_dir / f"{profile}.quick_add_cache.json"

    # Check if cache exists and is recent (< 5 minutes old)
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            data = json.load(f)
        cache_age = datetime.now().timestamp() - data.get("timestamp", 0)
        if cache_age < 300:  # 5 minutes
            return TaskCache(
                projects=data.get("projects", []),
                labels=data.get("labels", []),
            )

    # Fetch from API
    client = get_client(profile)
    try:
        projects_api = ProjectsAPI(client)
        labels_api = LabelsAPI(client)

        projects_response = await projects_api.list_projects()
        labels_response = await labels_api.list_labels()

        projects = [p.get("name", "") for p in projects_response.get("data", [])]
        # Strip @ prefix from label names if present
        labels = [
            label.get("name", "").lstrip("@")
            for label in labels_response.get("data", [])
        ]

        cache = TaskCache(projects=projects, labels=labels)

        # Save to cache file
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "projects": projects,
                        "labels": labels,
                        "timestamp": datetime.now().timestamp(),
                    },
                    f,
                )
        except Exception:
            pass  # Silently fail cache write

        return cache

    except Exception:
        # Return empty cache instead of None so UI still works
        return TaskCache(projects=[], labels=[])
    finally:
        await client.close()


async def get_interactive_input(
    profile: str = "default", default_project: str = "Inbox"
) -> str | None:
    """Get task input using Textual interactive prompt."""
    # Load cache
    cache = await load_cache(profile)

    # Create and run app
    app = QuickAddApp(profile=profile, default_project=default_project, cache=cache)
    await app.run_async()

    return app.result
