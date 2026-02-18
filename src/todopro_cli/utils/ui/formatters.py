"""Output formatters for different formats."""

import json
from datetime import UTC, datetime
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table
from rich.text import Text

console = Console()


def calculate_unique_suffixes(task_ids: list[str]) -> dict[str, int]:
    """
    Calculate minimum unique suffix length for each task ID.

    Starts from length 1 and grows until unique among all IDs.

    Args:
        task_ids: List of full task IDs

    Returns:
        Dict mapping task_id -> required suffix length
    """
    if not task_ids:
        return {}

    result = {}

    for task_id in task_ids:
        # Start with length 1, grow until unique
        for length in range(1, len(task_id) + 1):
            suffix = task_id[-length:]

            # Check if this suffix is unique
            conflicts = [
                tid for tid in task_ids if tid != task_id and tid.endswith(suffix)
            ]

            if not conflicts:
                result[task_id] = length
                break
        else:
            # Use full ID if no unique suffix found (shouldn't happen with UUIDs)
            result[task_id] = len(task_id)

    return result


def format_output(
    data: Any,
    output_format: str = "pretty",
    compact: bool = False,
    all_task_ids: list[str] | None = None,
) -> None:
    """Format and display output based on format."""
    if output_format == "json":
        print(json.dumps(data, indent=2, default=str))
    elif output_format == "json-pretty":
        print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    elif output_format == "yaml":
        print(yaml.dump(data, default_flow_style=False, sort_keys=False))
    elif output_format in ("table", "wide"):
        format_table(data, wide=output_format == "wide")
    elif output_format == "pretty":
        format_pretty(data, compact=compact, all_task_ids=all_task_ids)
    elif output_format == "quiet":
        format_quiet(data)
    else:
        # Default to pretty
        format_pretty(data, compact=compact, all_task_ids=all_task_ids)


def format_table(data: Any, wide: bool = False) -> None:
    """Format data as a table."""
    if not data:
        console.print("[yellow]No data to display[/yellow]")
        return

    # Handle list of items
    if isinstance(data, list):
        if not data:
            console.print("[yellow]No items found[/yellow]")
            return

        # Create table from list of dictionaries
        if isinstance(data[0], dict):
            format_dict_table(data, wide)
        else:
            # Simple list
            for item in data:
                console.print(item)
    elif isinstance(data, dict):
        # Check if it's a paginated response with items
        if "items" in data or "tasks" in data or "projects" in data:
            items = data.get("items") or data.get("tasks") or data.get("projects") or []
            format_dict_table(items, wide)
        else:
            # Single item
            format_single_item(data)
    else:
        console.print(data)


def format_dict_table(items: list[dict], wide: bool = False) -> None:
    """Format a list of dictionaries as a table."""
    if not items:
        console.print("[yellow]No items found[/yellow]")
        return

    # Determine columns based on first item
    first_item = items[0]
    columns = list(first_item.keys())

    # Create table
    table = Table(show_header=True, header_style="bold magenta")

    # Add columns
    for col in columns:
        table.add_column(col.replace("_", " ").title())

    # Add rows
    for item in items:
        row = []
        for col in columns:
            value = item.get(col, "")
            # Format value
            if isinstance(value, bool):
                value = "✓" if value else "✗"
            elif isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            elif value is None:
                value = "-"
            else:
                value = str(value)
            row.append(value)
        table.add_row(*row)

    console.print(table)


def format_single_item(item: dict) -> None:
    """Format a single item as key-value pairs."""
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in item.items():
        formatted_key = key.replace("_", " ").title()
        if isinstance(value, bool):
            formatted_value = "✓" if value else "✗"
        elif isinstance(value, list):
            formatted_value = ", ".join(str(v) for v in value)
        elif value is None:
            formatted_value = "-"
        else:
            formatted_value = str(value)
        table.add_row(formatted_key, formatted_value)

    console.print(table)


def format_error(message: str) -> None:
    """Format and display an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def format_success(message: str) -> None:
    """Format and display a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def format_warning(message: str) -> None:
    """Format and display a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def format_info(message: str) -> None:
    """Format and display an info message."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")


# ============================================================================
# Pretty Format Implementation
# ============================================================================

# Priority Icons & Colors
PRIORITY_ICONS = {
    4: "🔴",  # URGENT
    3: "🟠",  # HIGH
    2: "🟡",  # MEDIUM
    1: "🟢",  # NORMAL
}

PRIORITY_NAMES = {
    4: "URGENT",
    3: "HIGH PRIORITY",
    2: "MEDIUM PRIORITY",
    1: "NORMAL",
}

PRIORITY_COLORS = {
    4: "bold red",
    3: "bold orange3",
    2: "bold yellow",
    1: "green",
}

# Status Icons
STATUS_ICONS = {
    "open": "⬜",
    "completed": "☑️",
    "recurring": "🔄",
    "paused": "⏸️",
    "skipped": "⏭️",
}

# Metadata Icons
METADATA_ICONS = {
    "due_date": "📅",
    "time": "⏰",
    "assignee": "👤",
    "team": "👥",
    "comments": "💬",
    "reminder": "🔔",
    "label": "🏷️",
    "project": "📁",
    "created": "✨",
    "updated": "🔄",
    "overdue": "⏱️",
}

# Project Icons
PROJECT_ICONS = {
    "favorite": "⭐",
    "work": "💼",
    "personal": "🏠",
    "launch": "🚀",
    "technical": "🔧",
    "mobile": "📱",
    "analytics": "📊",
    "archived": "🗃️",
}


def format_pretty(data: Any, compact: bool = False, all_task_ids: list[str] | None = None) -> None:
    """Format data in pretty format with colors and icons."""
    if not data:
        console.print("[yellow]No data to display[/yellow]")
        return

    # Handle different data structures
    if isinstance(data, list):
        if not data:
            console.print("[yellow]No items found[/yellow]")
            return

        # Detect what type of items we have
        if data and isinstance(data[0], dict):
            first_item = data[0]
            if "content" in first_item or "is_completed" in first_item:
                format_tasks_pretty(data, compact, all_task_ids=all_task_ids)
            elif "name" in first_item and "color" in first_item:
                format_projects_pretty(data, compact)
            else:
                format_generic_list_pretty(data, compact)
    elif isinstance(data, dict):
        # Check for paginated response
        if "items" in data:
            format_pretty(data["items"], compact, all_task_ids=all_task_ids)
        elif "tasks" in data:
            format_tasks_pretty(data["tasks"], compact, all_task_ids=all_task_ids)
        elif "projects" in data:
            format_projects_pretty(data["projects"], compact)
        else:
            # Single item
            format_single_item_pretty(data)
    else:
        console.print(data)


def format_tasks_pretty(tasks: list[dict], compact: bool = False, all_task_ids: list[str] | None = None) -> None:
    """Format tasks in pretty format."""
    # Count tasks by status
    active_tasks = [t for t in tasks if not t.get("is_completed", False)]
    completed_today = [
        t for t in tasks if t.get("is_completed") and is_today(t.get("completed_at"))
    ]

    # Header
    header = Text()
    header.append("📋 Tasks ", style="bold cyan")
    header.append(f"({len(active_tasks)} active", style="dim")
    if completed_today:
        header.append(f", {len(completed_today)} completed today", style="dim green")
    header.append(")", style="dim")
    console.print(header)
    console.print()

    # Calculate unique suffix lengths against all task IDs (globally unique)
    displayed_ids = [task["id"] for task in tasks if task.get("id")]
    suffix_ids = all_task_ids if all_task_ids is not None else displayed_ids
    suffix_map = calculate_unique_suffixes(suffix_ids)

    # Save suffix mapping to cache for later resolution
    from todopro_cli.services.cache_service import save_suffix_mapping

    suffix_to_id = {}
    for task_id, length in suffix_map.items():
        suffix = task_id[-length:] if length > 0 else task_id
        suffix_to_id[suffix] = task_id
    save_suffix_mapping(suffix_to_id)

    # Group tasks by priority and status
    overdue_tasks = []
    tasks_by_priority = {4: [], 3: [], 2: [], 1: []}

    for task in tasks:
        # Check if overdue
        if not task.get("is_completed") and is_overdue(task.get("due_date")):
            overdue_tasks.append(task)
        else:
            priority = task.get("priority", 1)
            tasks_by_priority[priority].append(task)

    # Display by priority (lowest first - reversed order)
    for priority in [1, 2, 3, 4]:
        priority_tasks = tasks_by_priority[priority]
        if not priority_tasks:
            continue

        # Priority header
        icon = PRIORITY_ICONS[priority]
        name = PRIORITY_NAMES[priority]
        color = PRIORITY_COLORS[priority]
        console.print(f"{icon} {name}", style=color)

        # Display tasks
        for task in priority_tasks:
            format_task_item(task, compact, indent="  ", suffix_map=suffix_map)
        console.print()

    # Display overdue tasks separately
    if overdue_tasks:
        console.print(f"⏱️  OVERDUE ({len(overdue_tasks)})", style="bold red")
        for task in overdue_tasks:
            format_task_item(task, compact, indent="  ", suffix_map=suffix_map)
        console.print()


def format_task_item(
    task: dict,
    compact: bool = False,
    indent: str = "",
    suffix_map: dict[str, int] | None = None,
) -> None:
    """Format a single task item."""
    # Status icon
    is_completed = task.get("is_completed", False)
    is_recurring = task.get("is_recurring", False)

    if is_recurring:
        status_icon = STATUS_ICONS["recurring"]
    elif is_completed:
        status_icon = STATUS_ICONS["completed"]
    else:
        status_icon = STATUS_ICONS["open"]

    content = task.get("content", "Untitled")

    # Render Markdown links - convert to Rich markup
    content = render_markdown_links(content)

    if compact:
        # Compact one-line format
        # Build as markup string then convert to Text
        line_str = f"{indent}{status_icon} "

        # Content (dimmed if completed)
        if is_completed:
            line_str += f"[dim]{content}[/dim]"
        else:
            line_str += content

        # Due date
        if task.get("due_date"):
            due_str = format_due_date(task["due_date"])
            if is_overdue(task.get("due_date")) and not is_completed:
                line_str += f" [bold red]• {due_str}[/bold red]"
            else:
                line_str += f" [cyan]• {due_str}[/cyan]"

        # Labels
        labels = task.get("labels", [])
        if labels:
            for label in labels[:3]:  # Show max 3 labels in compact
                # Handle both string labels and dict labels
                label_name = label.get("name", "") if isinstance(label, dict) else label
                line_str += f" [blue]#{label_name}[/blue]"

        console.print(Text.from_markup(line_str))
    else:
        # Full format with metadata
        # Build as markup string then convert to Text
        line_str = f"{indent}{status_icon} "

        # Content
        style = (
            "dim" if is_completed else ("bold" if task.get("priority", 1) >= 3 else "")
        )
        if style:
            line_str += f"[{style}]{content}[/{style}]"
        else:
            line_str += content

        # Labels on same line
        labels = task.get("labels", [])
        if labels:
            line_str += "  "
            for label in labels:
                # Handle both string labels and dict labels
                label_name = label.get("name", "") if isinstance(label, dict) else label
                line_str += f"[blue]#{label_name}[/blue] "

        console.print(Text.from_markup(line_str))

        # Metadata line
        meta = []

        if task.get("due_date"):
            due_str = format_due_date(task["due_date"])
            if is_overdue(task.get("due_date")) and not is_completed:
                meta.append((due_str, "bold red"))
            else:
                meta.append((due_str, "cyan"))
        elif is_completed:
            completed_str = format_relative_time(task.get("completed_at"))
            meta.append((f"Completed {completed_str}", "dim green"))

        if task.get("assigned_to"):
            meta.append((f"Assigned to: @{task['assigned_to']}", "yellow"))

        if task.get("comments_count", 0) > 0:
            meta.append((f"{task['comments_count']} comments", "magenta"))

        if task.get("project_name"):
            meta.append((f"Project: {task['project_name']}", "blue"))

        # Add task ID suffix with dynamic length
        if task.get("id"):
            task_id = task["id"]
            if suffix_map and task_id in suffix_map:
                # Use calculated unique suffix length
                suffix_length = suffix_map[task_id]
                task_id_suffix = task_id[-suffix_length:]
            else:
                # Fallback to last 6 characters if suffix_map not provided
                task_id_suffix = task_id[-6:]
            meta.append((f"#{task_id_suffix}", "dim"))

        if is_recurring and task.get("next_occurrence"):
            next_str = format_due_date(task["next_occurrence"])
            meta.append((f"Next: {next_str}", "cyan"))

        if meta:
            meta_line = Text()
            meta_line.append(f"{indent}   └─ ", style="dim")
            for i, (text, style) in enumerate(meta):
                if i > 0:
                    meta_line.append(" • ", style="dim")
                meta_line.append(text, style=style)
            console.print(meta_line)


def format_projects_pretty(projects: list[dict], compact: bool = False) -> None:
    """Format projects in pretty format."""
    # Count projects
    active_projects = [p for p in projects if not p.get("is_archived", False)]
    archived_projects = [p for p in projects if p.get("is_archived", False)]

    # Header
    header = Text()
    header.append("📁 Projects ", style="bold cyan")
    header.append(f"({len(active_projects)} active", style="dim")
    if archived_projects:
        header.append(f", {len(archived_projects)} archived", style="dim")
    header.append(")", style="dim")
    console.print(header)
    console.print()

    # Group projects
    favorites = [p for p in active_projects if p.get("is_favorite", False)]
    non_favorites = [p for p in active_projects if not p.get("is_favorite", False)]

    # Display favorites
    if favorites:
        console.print("⭐ FAVORITES", style="bold yellow")
        for project in favorites:
            format_project_item(project, compact, indent="  ")
        console.print()

    # Display active projects
    if non_favorites:
        console.print("📂 ACTIVE PROJECTS", style="bold blue")
        for project in non_favorites:
            format_project_item(project, compact, indent="  ")
        console.print()

    # Display archived projects
    if archived_projects:
        console.print(f"🗃️  ARCHIVED ({len(archived_projects)})", style="bold dim")
        for project in archived_projects:
            format_project_item(project, compact, indent="  ")


def format_project_item(project: dict, compact: bool = False, indent: str = "") -> None:
    """Format a single project item."""
    icon = get_project_icon(project.get("name", ""))
    name = project.get("name", "Untitled")
    color = project.get("color", "#808080")

    if compact:
        line = Text()
        line.append(f"{indent}{icon} {name}", style="bold")
        if color and color != "#808080":
            line.append(f" {color}", style=color)
        console.print(line)
    else:
        # Project name with color
        line = Text()
        line.append(f"{indent}{icon} ", style="")
        line.append(name, style="bold")
        if color and color != "#808080":
            line.append(f"  {color}", style="dim")
        console.print(line)

        # Stats line
        meta = []

        # Task stats
        if "task_count" in project or "tasks_active" in project:
            active = project.get("tasks_active", 0)
            done = project.get("tasks_done", 0)
            total = active + done
            if total > 0:
                meta.append((f"{total} tasks ({active} active, {done} done)", ""))

        # Completion percentage
        if "completion_percentage" in project:
            pct = project["completion_percentage"]
            progress = get_progress_bar(pct)
            pct_color = get_completion_color(pct)
            meta.append((f"{progress} {pct}% complete", pct_color))

        # Collaborators
        if project.get("shared_with"):
            count = len(project["shared_with"])
            if count > 0:
                users = ", ".join(f"@{u}" for u in project["shared_with"][:3])
                if count > 3:
                    users += f" +{count - 3} more"
                meta.append((f"👥 Shared with: {users}", "blue"))

        # Due date or last update
        if project.get("due_date"):
            due_str = format_due_date(project["due_date"])
            meta.append((f"Due: {due_str}", "cyan"))
        elif project.get("updated_at"):
            updated_str = format_relative_time(project["updated_at"])
            meta.append((f"Last updated: {updated_str}", "dim"))

        # Overdue tasks warning
        if project.get("overdue_count", 0) > 0:
            meta.append((f"🔔 {project['overdue_count']} overdue tasks", "bold red"))

        if meta:
            for text, style in meta:
                meta_line = Text()
                meta_line.append(f"{indent}   └─ ", style="dim")
                meta_line.append(text, style=style or "")
                console.print(meta_line)


def format_generic_list_pretty(items: list[dict], compact: bool = False) -> None:
    """Format generic list of items."""
    for item in items:
        if "name" in item:
            console.print(f"• {item['name']}", style="bold")
        elif "content" in item:
            console.print(f"• {item['content']}")
        else:
            console.print(f"• {item.get('id', 'Item')}")


def format_single_item_pretty(item: dict) -> None:
    """Format a single item in pretty format."""
    # Try to detect item type
    if "content" in item:
        # Task
        format_task_item(item, compact=False)
    elif "name" in item and "color" in item:
        # Project
        format_project_item(item, compact=False)
    else:
        # Generic item
        for key, value in item.items():
            formatted_key = key.replace("_", " ").title()
            console.print(f"[cyan]{formatted_key}:[/cyan] {value}")


def format_quiet(data: Any) -> None:
    """Format output in quiet mode (IDs only)."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "id" in item:
                print(item["id"])
    elif isinstance(data, dict):
        if "id" in data:
            print(data["id"])
        elif "items" in data:
            format_quiet(data["items"])


# ============================================================================
# Helper Functions
# ============================================================================


def is_today(date_str: str | None) -> bool:
    """Check if date is today (in local timezone)."""
    if not date_str:
        return False
    try:
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if date.tzinfo is not None:
            # Convert aware datetime to local time before comparing
            date = date.astimezone()
        return date.date() == datetime.now().date()
    except Exception:  # pylint: disable=broad-exception-catch
        return False


def is_overdue(due_date: str | None) -> bool:
    """Check if task is overdue."""
    if not due_date:
        return False
    try:
        due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))

        # Make naive datetime timezone-aware if needed
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        return due < now
    except Exception:  # pylint: disable=broad-exception-catch
        return False


def format_due_date(date_str: str | datetime) -> str:
    """Format due date in compact format: HH:MM DD/MM DayOfWeek or HH:MM DD/MM/YYYY DayOfWeek."""
    try:
        # Handle datetime objects directly
        if isinstance(date_str, datetime):
            date = date_str
        else:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return str(date_str) if date_str else ""  # Return original string for invalid dates

    # Make naive datetime timezone-aware if needed
    if date.tzinfo is None:
        date = date.replace(tzinfo=UTC)

    now = datetime.now(UTC)

    # Format: HH:MM DD/MM DayOfWeek
    time_str = date.strftime("%H:%M")
    day_str = date.strftime("%d/%m")
    day_of_week = date.strftime("%a")  # Mon, Tue, etc.

    # Add year if different from current year
    if date.year != now.year:
        day_str = date.strftime("%d/%m/%Y")

    return f"{time_str} {day_str} {day_of_week}"


def format_relative_time(date_str: str | datetime | None) -> str:
    """Format timestamp as relative time."""
    if not date_str:
        return ""

    try:
        # Handle datetime objects directly
        if isinstance(date_str, datetime):
            date = date_str
        else:
            date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return ""  # Return empty string for invalid dates
        
    now = datetime.now()
    # Use timezone-aware now if date is timezone-aware
    if date.tzinfo is not None:
        from datetime import timezone
        now = datetime.now(tz=timezone.utc)
    diff = now - date

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago" if minutes > 1 else "1m ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago" if hours > 1 else "1h ago"
    days = int(seconds / 86400)
    return f"{days}d ago" if days > 1 else "1d ago"


def get_project_icon(name: str) -> str:
    """Get icon for project based on name."""
    name_lower = name.lower()
    if "work" in name_lower or "office" in name_lower:
        return PROJECT_ICONS["work"]
    if "personal" in name_lower or "home" in name_lower:
        return PROJECT_ICONS["personal"]
    if "launch" in name_lower or "sprint" in name_lower:
        return PROJECT_ICONS["launch"]
    if "dev" in name_lower or "tech" in name_lower:
        return PROJECT_ICONS["technical"]
    if "mobile" in name_lower or "app" in name_lower:
        return PROJECT_ICONS["mobile"]
    if "analytics" in name_lower or "data" in name_lower:
        return PROJECT_ICONS["analytics"]
    return "📁"


def get_progress_bar(percentage: float) -> str:
    """Get a progress bar representation."""
    filled = int(percentage / 10)
    empty = 10 - filled
    return "▓" * filled + "░" * empty


def get_completion_color(percentage: float) -> str:
    """Get color based on completion percentage."""
    if percentage >= 80:
        return "green"
    if percentage >= 40:
        return "yellow"
    return "red"


def render_markdown_links(text: str) -> str:
    """Render Markdown links [text](url) as clickable links."""
    import re

    # Pattern: [text](url)
    pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
    # Replace with Rich markup: [link=url]text[/link]
    return re.sub(pattern, r"[link=\2]\1[/link]", text)


# Eisenhower Quadrant Icons
QUADRANT_ICONS = {
    "Q1": "🔴",  # Urgent & Important
    "Q2": "🟠",  # Not Urgent & Important
    "Q3": "🟡",  # Urgent & Not Important
    "Q4": "🟢",  # Not Urgent & Not Important
}


def format_next_task(task: dict) -> None:
    """Format next task in simple format similar to today view."""
    console.print()
    console.print("[bold cyan]Next Task:[/bold cyan]")
    console.print()

    # Status icon
    is_recurring = task.get("is_recurring", False)
    status_icon = STATUS_ICONS["recurring"] if is_recurring else STATUS_ICONS["open"]

    # Content with Markdown rendering
    content = task.get("content", "Untitled")
    content = render_markdown_links(content)

    # Main line - build as markup string
    line_str = f"  {status_icon} [bold]{content}[/bold]"
    console.print(Text.from_markup(line_str))

    # Metadata line
    meta = []

    # Eisenhower Quadrant
    if task.get("eisenhower_quadrant"):
        quadrant = task["eisenhower_quadrant"]
        icon = QUADRANT_ICONS.get(quadrant, "")
        meta.append((icon, ""))

    # Due date
    if task.get("due_date"):
        due_str = format_due_date(task["due_date"])
        meta.append((due_str, "cyan"))

    # Project
    if task.get("project"):
        project_name = task["project"].get("name", "")
        if project_name:
            meta.append((project_name, "blue"))

    # Task ID suffix
    if task.get("id"):
        # For single task, calculate suffix (will be minimal)
        task_id = task["id"]
        suffix_map = calculate_unique_suffixes([task_id])
        suffix_length = suffix_map.get(task_id, 6)
        task_id_suffix = task_id[-suffix_length:]
        meta.append((f"#{task_id_suffix}", "dim"))

    if meta:
        meta_line = Text()
        meta_line.append("     └─ ", style="dim")
        for i, (text, style) in enumerate(meta):
            if i > 0:
                meta_line.append(" • ", style="dim")
            meta_line.append(text, style=style or "")
        console.print(meta_line)

    # Description if exists
    if task.get("description"):
        console.print()
        console.print(f"  [dim]{task['description']}[/dim]")

    console.print()
