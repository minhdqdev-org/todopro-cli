"""Interactive prompt for task input with autocomplete and syntax highlighting."""

import os
import re
import sys
import termios
import tty
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.text import Text

from todopro_cli.api.client import get_client
from todopro_cli.api.labels import LabelsAPI
from todopro_cli.api.projects import ProjectsAPI
from todopro_cli.config import get_config_manager


@dataclass
class Entity:
    """Represents a recognized entity in the input."""

    type: str  # "priority", "label", "project", "date", "time"
    value: str
    start: int
    end: int
    raw: str  # The original text including markers (@, #, !!)
    recognized: bool
    background_removed: bool = False  # Track if user removed background


@dataclass
class CacheData:
    """Local cache for projects and labels."""

    projects: list[str]
    labels: list[str]
    timestamp: float


class InteractivePrompt:
    """Enhanced interactive prompt for task input."""

    def __init__(self, profile: str = "default", default_project: str = "Inbox"):
        self.profile = profile
        self.default_project = default_project
        self.console = Console()
        self.input_text = ""
        self.cursor_pos = 0
        self.cache: CacheData | None = None
        self.suggestions: list[str] = []
        self.suggestion_type: str | None = None  # "label" or "project"
        self.suggestion_prefix: str = ""
        self.entities: list[Entity] = []

        # Date/time keywords
        self.date_keywords = [
            "today",
            "tomorrow",
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

        # Time patterns: 8AM, 7:30PM, 14:45, etc.
        self.time_pattern = re.compile(
            r"\b(\d{1,2})(?::(\d{2}))?\s?(AM|PM|am|pm)?\b|\b(\d{2}):(\d{2})\b"
        )

    async def load_cache(self) -> None:
        """Load projects and labels from API and cache them."""
        config_manager = get_config_manager(self.profile)
        cache_file = config_manager.data_dir / f"{self.profile}.quick_add_cache.json"

        # Check if cache exists and is recent (< 5 minutes old)
        if cache_file.exists():
            import json

            try:
                with open(cache_file) as f:
                    data = json.load(f)
                cache_age = datetime.now().timestamp() - data.get("timestamp", 0)
                if cache_age < 300:  # 5 minutes
                    self.cache = CacheData(
                        projects=data.get("projects", []),
                        labels=data.get("labels", []),
                        timestamp=data.get("timestamp", 0),
                    )
                    return
            except Exception:
                pass

        # Fetch from API
        client = get_client(self.profile)
        try:
            projects_api = ProjectsAPI(client)
            labels_api = LabelsAPI(client)

            projects_response = await projects_api.list_projects()
            labels_response = await labels_api.list_labels()

            projects = [p.get("name", "") for p in projects_response.get("data", [])]
            labels = [
                label.get("name", "") for label in labels_response.get("data", [])
            ]

            self.cache = CacheData(
                projects=projects, labels=labels, timestamp=datetime.now().timestamp()
            )

            # Save to cache file
            import json

            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "projects": projects,
                        "labels": labels,
                        "timestamp": self.cache.timestamp,
                    },
                    f,
                )

        finally:
            await client.close()

    def get_terminal_width(self) -> int:
        """Get terminal width."""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 80

    def parse_entities(self) -> None:
        """Parse input text to find all entities (priorities, labels, projects, dates, times)."""
        self.entities = []
        text = self.input_text

        # Parse priorities (!!1, !!2, !!3, !!4)
        for match in re.finditer(r"!!(1|2|3|4)", text):
            self.entities.append(
                Entity(
                    type="priority",
                    value=match.group(1),
                    start=match.start(),
                    end=match.end(),
                    raw=match.group(0),
                    recognized=True,
                )
            )

        # Parse labels (@label)
        for match in re.finditer(r"@(\w+)", text):
            label_name = match.group(1)
            recognized = (
                self.cache is not None and label_name in self.cache.labels
            ) or self._is_partial_match(label_name, self.cache.labels if self.cache else [])

            self.entities.append(
                Entity(
                    type="label",
                    value=label_name,
                    start=match.start(),
                    end=match.end(),
                    raw=match.group(0),
                    recognized=recognized,
                )
            )

        # Parse projects (#project)
        for match in re.finditer(r"#(\w+)", text):
            project_name = match.group(1)
            recognized = (
                self.cache is not None and project_name in self.cache.projects
            ) or self._is_partial_match(project_name, self.cache.projects if self.cache else [])

            self.entities.append(
                Entity(
                    type="project",
                    value=project_name,
                    start=match.start(),
                    end=match.end(),
                    raw=match.group(0),
                    recognized=recognized,
                )
            )

        # Parse date keywords
        words = text.split()
        pos = 0
        for word in words:
            word_lower = word.lower().strip(".,!?;:")
            if word_lower in self.date_keywords:
                start = text.find(word, pos)
                if start != -1:
                    entity = Entity(
                        type="date",
                        value=word,
                        start=start,
                        end=start + len(word),
                        raw=word,
                        recognized=True,
                    )
                    # Check if background was manually removed
                    for e in self.entities:
                        if (
                            e.type == "date"
                            and e.start == start
                            and e.background_removed
                        ):
                            entity.background_removed = True
                    self.entities.append(entity)
            pos += len(word) + 1

        # Parse time patterns
        for match in self.time_pattern.finditer(text):
            # Skip if this time match is inside a priority marker (!!1, !!2, etc.)
            if match.start() >= 2 and text[match.start() - 2 : match.start()] == "!!":
                continue

            entity = Entity(
                type="time",
                value=match.group(0),
                start=match.start(),
                end=match.end(),
                raw=match.group(0),
                recognized=True,
            )
            # Check if background was manually removed
            for e in self.entities:
                if e.type == "time" and e.start == match.start() and e.background_removed:
                    entity.background_removed = True
            self.entities.append(entity)

    def _is_partial_match(self, partial: str, items: list[str]) -> bool:
        """Check if partial string matches any item in the list."""
        partial_lower = partial.lower()
        return any(item.lower().startswith(partial_lower) for item in items)

    def update_suggestions(self) -> None:
        """Update autocomplete suggestions based on cursor position."""
        self.suggestions = []
        self.suggestion_type = None
        self.suggestion_prefix = ""

        if not self.cache:
            return

        # Find if cursor is after @ or #
        text_before_cursor = self.input_text[: self.cursor_pos]

        # Check for label autocomplete (@)
        label_match = re.search(r"@(\w*)$", text_before_cursor)
        if label_match:
            prefix = label_match.group(1)
            self.suggestion_prefix = prefix
            self.suggestion_type = "label"

            if prefix:
                # Filter by prefix
                self.suggestions = [
                    label
                    for label in self.cache.labels
                    if label.lower().startswith(prefix.lower())
                ][:10]
            else:
                # Show all labels alphabetically
                self.suggestions = sorted(self.cache.labels)[:10]
            return

        # Check for project autocomplete (#)
        project_match = re.search(r"#(\w*)$", text_before_cursor)
        if project_match:
            prefix = project_match.group(1)
            self.suggestion_prefix = prefix
            self.suggestion_type = "project"

            if prefix:
                # Filter by prefix
                self.suggestions = [
                    project
                    for project in self.cache.projects
                    if project.lower().startswith(prefix.lower())
                ][:10]
            else:
                # Show all projects alphabetically
                self.suggestions = sorted(self.cache.projects)[:10]
            return

    def render(self) -> None:
        """Render the prompt UI."""
        width = self.get_terminal_width()
        separator = "─" * width

        # Clear screen and move cursor to top
        self.console.print("\033[2J\033[H", end="")

        # Header with project name
        self.console.print(f" {self.default_project}")

        # Top separator
        self.console.print(f"[dim]{separator}[/dim]")

        # Input field with syntax highlighting
        input_line = Text("❯  ")
        if self.input_text:
            input_line.append(self.render_highlighted_input())
        else:
            input_line.append("Enter your task description", style="dim")

        self.console.print(input_line)

        # Bottom separator
        self.console.print(f"[dim]{separator}[/dim]")

        # Show suggestions if any
        if self.suggestions:
            for i, suggestion in enumerate(self.suggestions):
                prefix = "▋  "
                full_suggestion = f"@{suggestion}" if self.suggestion_type == "label" else f"#{suggestion}"

                if i == 0 and self.suggestion_prefix:
                    # Highlight first suggestion
                    self.console.print(f"[dim]{prefix}[/dim][bold]{full_suggestion}[/bold]")
                else:
                    self.console.print(f"[dim]{prefix}{full_suggestion}[/dim]")
        else:
            # Footer with instructions
            footer = Text(" Press ")
            footer.append("Enter", style="bold")
            footer.append(" to submit or ")
            footer.append("Ctrl+C", style="bold")
            footer.append(" to cancel.")
            self.console.print(footer)

    def render_highlighted_input(self) -> Text:
        """Render input text with syntax highlighting."""
        self.parse_entities()

        result = Text()
        pos = 0

        # Sort entities by start position
        sorted_entities = sorted(self.entities, key=lambda e: e.start)

        for entity in sorted_entities:
            # Add text before entity
            if entity.start > pos:
                result.append(self.input_text[pos : entity.start])

            # Add entity with appropriate styling
            entity_text = self.input_text[entity.start : entity.end]

            if entity.type == "priority":
                # Priority colors
                if entity.value == "1":
                    result.append(entity_text, style="red")
                elif entity.value == "2":
                    result.append(entity_text, style="yellow")
                elif entity.value == "3":
                    result.append(entity_text, style="blue")
                else:  # 4
                    result.append(entity_text, style="dim")

            elif entity.type in ("label", "project") and entity.recognized and not entity.background_removed:
                # Recognized labels/projects with background
                result.append(entity_text, style="on red")

            elif entity.type in ("date", "time") and not entity.background_removed:
                # Recognized dates/times with background
                result.append(entity_text, style="on red")

            else:
                # Unrecognized or background removed
                result.append(entity_text)

            pos = entity.end

        # Add remaining text
        if pos < len(self.input_text):
            result.append(self.input_text[pos:])

        # Add autocomplete preview for labels/projects
        if self.suggestion_type and self.suggestions and self.suggestion_prefix:
            first_suggestion = self.suggestions[0]
            if first_suggestion.lower().startswith(self.suggestion_prefix.lower()):
                # Add the remaining part of the suggestion in dim
                remaining = first_suggestion[len(self.suggestion_prefix) :]
                result.append(remaining, style="dim")

        return result

    def handle_backspace(self) -> None:
        """Handle backspace key with entity background removal logic."""
        if self.cursor_pos > 0:
            # Check if we're at the end of a recognized entity
            for entity in self.entities:
                if (
                    entity.end == self.cursor_pos
                    and entity.recognized
                    and entity.type in ("label", "project", "date", "time")
                    and not entity.background_removed
                ):
                    # First backspace: remove background, keep text
                    entity.background_removed = True
                    self.render()
                    return

            # Normal backspace: delete character
            self.input_text = (
                self.input_text[: self.cursor_pos - 1] + self.input_text[self.cursor_pos :]
            )
            self.cursor_pos -= 1

    def insert_char(self, char: str) -> None:
        """Insert character at cursor position."""
        self.input_text = (
            self.input_text[: self.cursor_pos] + char + self.input_text[self.cursor_pos :]
        )
        self.cursor_pos += 1

    async def prompt(self) -> str:
        """Show interactive prompt and get input."""
        # Load cache
        await self.load_cache()

        # Save terminal settings
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            # Set terminal to raw mode
            tty.setraw(fd)

            self.render()

            while True:
                # Read single character
                char = sys.stdin.read(1)

                # Handle Ctrl+C
                if char == "\x03":
                    raise KeyboardInterrupt

                # Handle Enter
                if char in ("\r", "\n"):
                    break

                # Handle backspace
                if char in ("\x7f", "\x08"):
                    self.handle_backspace()

                # Handle regular characters
                elif char.isprintable():
                    self.insert_char(char)

                # Update suggestions and re-render
                self.update_suggestions()
                self.render()

        finally:
            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            self.console.print()  # New line after input

        return self.input_text.strip()


async def get_interactive_input(
    profile: str = "default", default_project: str = "Inbox"
) -> str:
    """Get task input using interactive prompt."""
    prompt = InteractivePrompt(profile=profile, default_project=default_project)
    return await prompt.prompt()
