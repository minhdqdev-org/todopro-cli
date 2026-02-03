"""Interactive prompt for task input with autocomplete and syntax highlighting."""

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.styles import Style
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.api.labels import LabelsAPI
from todopro_cli.api.projects import ProjectsAPI
from todopro_cli.config import get_config_manager


@dataclass
class CacheData:
    """Local cache for projects and labels."""

    projects: list[str]
    labels: list[str]
    timestamp: float


class TaskLexer(Lexer):
    """Syntax highlighter for task input."""

    def __init__(self, cache: CacheData | None = None):
        self.cache = cache
        self.date_keywords = [
            "today",
            "tomorrow",
            "tom",  # Abbreviation for tomorrow
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
        # More strict time pattern - only match clear time formats
        # Matches: 8AM, 8 AM, 8:30, 8:30PM, 14:30, etc.
        # Does NOT match: bare "8" or "at"
        self.time_pattern = re.compile(
            r"\b(\d{1,2}):(\d{2})\s?(AM|PM|am|pm)?\b|"  # 8:30 AM or 14:30
            r"\b(\d{1,2})\s?(AM|PM|am|pm)\b"  # 8AM or 8 AM
        )

    def lex_document(self, document: Document):
        """Lex the document and return formatted text."""

        def get_line(lineno):
            if lineno >= len(document.lines):
                return []

            line_text = document.lines[lineno]
            formatted = []
            pos = 0

            # Track processed positions to avoid overlaps
            processed_ranges = []

            # Parse priorities first
            priority_ranges = []
            for match in re.finditer(r"!!(1|2|3|4)", line_text):
                priority = match.group(1)
                style_class = f"class:priority{priority}"
                priority_ranges.append((match.start(), match.end(), style_class, match.group(0)))
                processed_ranges.append((match.start(), match.end()))

            # Parse labels
            label_ranges = []
            for match in re.finditer(r"@(\w+)", line_text):
                label_name = match.group(1)
                if self.cache and label_name in self.cache.labels:
                    label_ranges.append(
                        (match.start(), match.end(), "class:recognized", match.group(0))
                    )
                    processed_ranges.append((match.start(), match.end()))

            # Parse projects
            project_ranges = []
            for match in re.finditer(r"#(\w+)", line_text):
                project_name = match.group(1)
                if self.cache and project_name in self.cache.projects:
                    project_ranges.append(
                        (match.start(), match.end(), "class:recognized", match.group(0))
                    )
                    processed_ranges.append((match.start(), match.end()))

            # Parse dates
            date_ranges = []
            words = line_text.split()
            word_pos = 0
            for word in words:
                word_lower = word.lower().strip(".,!?;:")
                if word_lower in self.date_keywords:
                    start = line_text.find(word, word_pos)
                    if start != -1:
                        date_ranges.append(
                            (start, start + len(word), "class:recognized", word)
                        )
                        processed_ranges.append((start, start + len(word)))
                word_pos += len(word) + 1

            # Parse times
            time_ranges = []
            for match in self.time_pattern.finditer(line_text):
                # Skip if inside priority marker
                if match.start() >= 2 and line_text[match.start() - 2 : match.start()] == "!!":
                    continue
                time_ranges.append(
                    (match.start(), match.end(), "class:recognized", match.group(0))
                )
                processed_ranges.append((match.start(), match.end()))

            # Combine all ranges
            all_ranges = (
                priority_ranges
                + label_ranges
                + project_ranges
                + date_ranges
                + time_ranges
            )
            all_ranges.sort(key=lambda x: x[0])

            # Build formatted output
            pos = 0
            for start, end, style, text in all_ranges:
                if start > pos:
                    formatted.append(("", line_text[pos:start]))
                formatted.append((style, text))
                pos = end

            # Add remaining text
            if pos < len(line_text):
                formatted.append(("", line_text[pos:]))

            return formatted

        return get_line


class TaskCompleter(Completer):
    """Auto-completer for labels and projects."""

    def __init__(self, cache: CacheData | None = None):
        self.cache = cache

    def get_completions(self, document, complete_event):
        """Get completions for current cursor position."""
        if not self.cache:
            return

        text_before_cursor = document.text_before_cursor

        # Check for label completion
        label_match = re.search(r"@(\w*)$", text_before_cursor)
        if label_match:
            prefix = label_match.group(1)
            if prefix:
                # Filter by prefix
                matches = [
                    label
                    for label in self.cache.labels
                    if label.lower().startswith(prefix.lower())
                ]
            else:
                # Show all
                matches = sorted(self.cache.labels)

            for i, label in enumerate(matches[:10]):
                # First item gets special marker
                marker = "▋  " if i == 0 else "   "
                yield Completion(
                    label,
                    start_position=-len(prefix),
                    display=f"{marker}@{label}",
                    style="bold" if i == 0 else "",
                )
            return

        # Check for project completion
        project_match = re.search(r"#(\w*)$", text_before_cursor)
        if project_match:
            prefix = project_match.group(1)
            if prefix:
                # Filter by prefix
                matches = [
                    project
                    for project in self.cache.projects
                    if project.lower().startswith(prefix.lower())
                ]
            else:
                # Show all
                matches = sorted(self.cache.projects)

            for i, project in enumerate(matches[:10]):
                # First item gets special marker
                marker = "▋  " if i == 0 else "   "
                yield Completion(
                    project,
                    start_position=-len(prefix),
                    display=f"{marker}#{project}",
                    style="bold" if i == 0 else "",
                )
            return


async def load_cache(profile: str) -> CacheData | None:
    """Load projects and labels from API and cache them."""
    config_manager = get_config_manager(profile)
    cache_file = config_manager.data_dir / f"{profile}.quick_add_cache.json"

    # Check if cache exists and is recent (< 5 minutes old)
    if cache_file.exists():
        try:
            with open(cache_file) as f:
                data = json.load(f)
            cache_age = datetime.now().timestamp() - data.get("timestamp", 0)
            if cache_age < 300:  # 5 minutes
                return CacheData(
                    projects=data.get("projects", []),
                    labels=data.get("labels", []),
                    timestamp=data.get("timestamp", 0),
                )
        except Exception:
            pass

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

        cache = CacheData(
            projects=projects, labels=labels, timestamp=datetime.now().timestamp()
        )

        # Save to cache file
        try:
            with open(cache_file, "w") as f:
                json.dump(
                    {
                        "projects": projects,
                        "labels": labels,
                        "timestamp": cache.timestamp,
                    },
                    f,
                )
        except Exception:
            pass  # Silently fail cache write

        return cache

    except Exception:
        # Return empty cache instead of None so UI still works
        return CacheData(projects=[], labels=[], timestamp=datetime.now().timestamp())
    finally:
        await client.close()


async def get_interactive_input(
    profile: str = "default", default_project: str = "Inbox"
) -> str:
    """Get task input using interactive prompt."""
    console = Console()

    # Load cache
    cache = await load_cache(profile)

    # Get terminal width
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80

    separator = "─" * width

    # Print header
    console.print(f" {default_project}")
    console.print(f"[dim]{separator}[/dim]")

    # Create style
    style = Style.from_dict(
        {
            "priority1": "#ff0000",  # Red for !!1
            "priority2": "#ff8800",  # Orange for !!2
            "priority3": "#0088ff",  # Blue for !!3
            "priority4": "#888888",  # Light gray for !!4
            "recognized": "bg:#ffcccc",  # Light red background for recognized entities
            # Completion menu styling
            "completion-menu.completion": "#aaaaaa",  # Light gray for suggestions
            "completion-menu.completion.current": "bold",  # Bold for highlighted suggestion
            # Toolbar styling
            "bottom-toolbar": "#888888",
        }
    )

    # Create bottom toolbar with separator
    def bottom_toolbar():
        # Return formatted text as list of (style, text) tuples
        return [
            ("class:bottom-toolbar", separator),
            ("", "\n Press "),
            ("bold", "Enter"),
            ("", " to submit or "),
            ("bold", "Ctrl+C"),
            ("", " to cancel."),
        ]

    # Create session
    session: PromptSession = PromptSession(
        lexer=TaskLexer(cache=cache),
        completer=TaskCompleter(cache=cache),
        style=style,
        complete_while_typing=True,
        mouse_support=False,
        bottom_toolbar=bottom_toolbar,
        complete_in_thread=False,
    )

    try:
        # Get input
        result = await session.prompt_async("❯  ", placeholder="Enter your task description")

        # Clear everything: header + separator + input + completions
        import sys
        # Move up past any completion menu and input lines
        sys.stdout.write("\033[?25h")  # Show cursor
        # Clear from cursor to end of screen
        sys.stdout.write("\033[J")
        # Move up to start of our UI (header line)
        sys.stdout.write("\033[2A")  # Up 2 lines (separator + header)
        sys.stdout.write("\033[2K")  # Clear header line
        sys.stdout.write("\033[1B\033[2K")  # Down 1, clear separator line
        sys.stdout.flush()

        return result.strip()

    except KeyboardInterrupt:
        raise
