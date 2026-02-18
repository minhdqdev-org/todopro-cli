"""Command 'edit' of todopro-cli — edit a task interactively or via flags."""

from __future__ import annotations

import difflib
import typer
from rich.console import Console
from rich.table import Table

from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.services.project_service import ProjectService
from todopro_cli.services.task_service import TaskService
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.ui.console import get_console

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()

_PRIORITY_NAMES = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}


async def _resolve_project_name(project_input: str, strategy) -> str:
    """Resolve a project name or ID to a project ID using fuzzy matching."""
    from todopro_cli.utils.uuid_utils import is_full_uuid, resolve_project_uuid
    project_repo = strategy.project_repository
    # If it looks like a UUID prefix, resolve directly
    if is_full_uuid(project_input) or len(project_input) >= 8 and "-" in project_input:
        return await resolve_project_uuid(project_input, project_repo)
    # Otherwise, fuzzy-match against project names
    project_service = ProjectService(project_repo)
    all_projects = await project_service.list_projects()
    names = [p.name for p in all_projects]

    # Exact case-insensitive match takes top priority
    exact = [p for p in all_projects if p.name.lower() == project_input.lower()]
    if exact:
        return exact[0].id

    # Prefix matches next
    prefix_matches = [p for p in all_projects if p.name.lower().startswith(project_input.lower())]
    if len(prefix_matches) == 1:
        return prefix_matches[0].id

    # Fall back to fuzzy matches
    fuzzy_names = difflib.get_close_matches(project_input, names, n=5, cutoff=0.4)
    candidates = list(dict.fromkeys([p for p in prefix_matches] + [p for p in all_projects if p.name in fuzzy_names]))

    if not candidates:
        raise ValueError(f"No project matching '{project_input}'. Available: {', '.join(names)}")
    if len(candidates) == 1:
        return candidates[0].id
    # Multiple matches — ask user to pick (only in interactive mode)
    import sys
    if not sys.stdin.isatty():
        # Non-interactive: use first match
        return candidates[0].id
    console.print(f"[yellow]Multiple projects match '{project_input}':[/yellow]")
    for i, p in enumerate(candidates, 1):
        console.print(f"  {i}. {p.name}")
    choice = typer.prompt("Pick a number", default="1")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx].id
    except ValueError:
        pass
    raise ValueError(f"Invalid choice. Please specify an exact project name or ID.")


def _fmt_due(task) -> str:
    """Format due date for display."""
    if task.due_date is None:
        return "(none)"
    try:
        return task.due_date.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(task.due_date)


def _prompt_field(label: str, current: str) -> str | None:
    """Prompt for a field value; return None to keep current, '' to clear."""
    value = typer.prompt(
        f"  {label} [{current}]",
        default="",
        show_default=False,
    )
    return value if value != "" else None


@app.command("edit")
@command_wrapper
async def edit_command(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    content: str | None = typer.Option(None, "--content", "-c", help="New task content"),
    description: str | None = typer.Option(None, "--description", help="New description"),
    due: str | None = typer.Option(None, "--due", "-d", help="New due date (e.g. 'tomorrow', '2026-03-01 14:00')"),
    priority: int | None = typer.Option(None, "--priority", "-p", help="New priority (1=low, 2=medium, 3=high, 4=urgent)"),
    project: str | None = typer.Option(None, "--project", help="New project (name or ID, fuzzy search supported)"),
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json_opt: bool = typer.Option(False, "--json", help="Output as JSON (alias for --output json)"),
) -> None:
    """Edit a task interactively or via flags.

    If no flags are given, launches an interactive prompt showing current
    values so you can edit each field in turn (press Enter to keep).

    Examples:
      tp edit 3f --content "New title" --due tomorrow
      tp edit 3f --priority 3
      tp edit 3f          # interactive
    """
    if json_opt:
        output = "json"

    strategy = get_strategy_context()
    task_repo = strategy.task_repository
    task_service = TaskService(task_repo)

    resolved_id = await resolve_task_id(task_service, task_id)
    task = await task_service.get_task(resolved_id)

    # Determine whether to go interactive (no flags provided)
    flag_mode = any(x is not None for x in [content, description, due, priority, project])

    if flag_mode:
        # Non-interactive: apply provided flags directly
        new_content = content
        new_description = description
        new_due = due
        new_priority = priority
        new_project: str | None = None
        if project is not None:
            new_project = await _resolve_project_name(project, strategy)
    else:
        # Look up current project name for display
        project_repo = strategy.project_repository
        project_service = ProjectService(project_repo)
        current_project_display = task.project_id or "(none)"
        if task.project_id:
            try:
                proj = await project_service.get_project(task.project_id)
                current_project_display = proj.name
            except Exception:
                pass

        # Interactive mode — show current values and prompt for each field
        console.print(f"\n[bold cyan]Editing:[/bold cyan] {task.content}")
        console.print("[dim](Press Enter to keep current value, type a value to change)[/dim]\n")

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_row("[dim]Content[/dim]", task.content)
        table.add_row("[dim]Description[/dim]", task.description or "(none)")
        table.add_row("[dim]Due date[/dim]", _fmt_due(task))
        table.add_row("[dim]Priority[/dim]", f"{task.priority} ({_PRIORITY_NAMES.get(task.priority, '?')})")
        table.add_row("[dim]Project[/dim]", current_project_display)
        console.print(table)
        console.print()

        raw_content = _prompt_field("Content", task.content)
        raw_description = _prompt_field("Description", task.description or "")
        raw_due = _prompt_field("Due date (YYYY-MM-DD / natural)", _fmt_due(task))
        raw_priority = _prompt_field(
            "Priority (1-4)", f"{task.priority} ({_PRIORITY_NAMES.get(task.priority, '?')})"
        )
        raw_project = _prompt_field("Project (name or ID)", current_project_display if current_project_display != "(none)" else "")

        new_content = raw_content
        new_description = raw_description
        new_due = raw_due

        new_project = None
        if raw_project is not None:
            new_project = await _resolve_project_name(raw_project, strategy)

        new_priority: int | None = None
        if raw_priority is not None:
            try:
                new_priority = int(raw_priority)
                if new_priority not in (1, 2, 3, 4):
                    format_error("Priority must be 1-4. Keeping current value.")
                    new_priority = None
            except ValueError:
                format_error(f"Invalid priority '{raw_priority}'. Keeping current value.")

    # Nothing to update
    if not any(x is not None for x in [new_content, new_description, new_due, new_priority, new_project]):
        console.print("[yellow]No changes made.[/yellow]")
        raise typer.Exit(0)

    updated = await task_service.update_task(
        resolved_id,
        content=new_content,
        description=new_description,
        due_date=new_due,
        priority=new_priority,
        project_id=new_project,
    )

    format_success(f"✓ Updated: {updated.content}")
    format_output(updated.model_dump(), output)
