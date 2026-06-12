"""Command 'add' of todopro-cli"""

import asyncio
import json
from datetime import datetime

import typer

from todopro_cli.models.core import TaskCreate
from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.services.config_service import (
    get_config_service,
    get_storage_strategy_context,
)
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_success

from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


@app.command("add")
@command_wrapper
def add(
    text: str | None = typer.Argument(None, help="Natural language task description"),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Project name or ID (overrides #project in text)"
    ),
    output: str = typer.Option(
        "pretty", "--output", "-o", help="Output format (pretty/json/table)"
    ),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """
    Quick add a task using natural language.

    Examples:
      todopro add "Review PR tomorrow at 2pm #Work p1 @urgent"
      todopro add "Buy groceries every Friday @Shopping"
      todopro add "Team standup every monday at 9am #Work"

    Syntax:
      #ProjectName - Assign to project
      @label - Add label
      p1-p4 or !!1-!!4 - Set priority (p1/!!1=urgent, p4/!!4=low)
      Natural dates - tomorrow, next monday, at 3pm
      Recurrence - every day/week/monday, etc.

    Note: Natural language parsing requires cloud context.
    For local context, creates a simple task with the text as content.
    """
    import sys  # pylint: disable=import-outside-toplevel

    if json_opt:
        output = "json"

    text = text.strip() if text else None

    # If no text provided, determine how to get it
    if not text:
        # Check if stdin is a TTY (interactive terminal) or has data piped
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            # Interactive terminal, use Textual UI (lazy import)
            try:
                from todopro_cli.utils.ui.textual_prompt import QuickAddApp

                app_ui = QuickAddApp(default_project="Inbox")
                app_ui.run()
                text = app_ui.result
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled.[/yellow]")
                raise typer.Exit(0) from None
            except Exception as e:
                console.print(f"[yellow]Interactive mode failed: {e}[/yellow]")
                console.print("Enter task description:")
                text = input().strip()

        if not text:
            format_error("Task text is required")
            raise typer.Exit(1)

    # Check current context type
    config_svc = get_config_service()
    current_context = config_svc.get_current_context()

    # For local context, use simple task creation
    if current_context.type == "local":
        _create_local_task(text, project_override=project, output=output)
        return

    # For remote context, use NLP parsing
    try:

        async def do_quick_add():
            # Get API client
            client = get_client()
            tasks_api = TasksAPI(client)

            response = await tasks_api.quick_add(text)

            # Check if project not found error
            if "error" in response:
                error_msg = response["error"]
                parsed_err = response.get("parsed", {})
                unrecognized = parsed_err.get("project_name", "")

                # If the error is specifically about a missing project, offer to create it
                if unrecognized and ("project" in error_msg.lower() or "suggestions" in response):
                    import sys

                    from todopro_cli.services.api.projects import ProjectsAPI

                    if sys.stdin.isatty():
                        console.print(
                            f"\n[yellow]Project '[bold]{unrecognized}[/bold]' not found.[/yellow]"
                        )
                        create_it = typer.confirm(
                            f"  Create new project '{unrecognized}'?", default=True
                        )
                    else:
                        create_it = False

                    projects_api = ProjectsAPI(client)
                    if create_it:
                        await projects_api.create_project(unrecognized)
                        console.print(f"[green]  ✓ Created project '{unrecognized}'[/green]")
                        # Retry quick_add — project now exists
                        response2 = await tasks_api.quick_add(text)
                        if "error" not in response2:
                            response.clear()
                            response.update(response2)
                        else:
                            format_error(response2.get("error", "Failed to create task"))
                            raise typer.Exit(1)
                    else:
                        # Retry without project name (strip #Project from text)
                        import re
                        stripped = re.sub(r"#\S+", "", text).strip()
                        response2 = await tasks_api.quick_add(stripped or text)
                        if "error" not in response2:
                            response.clear()
                            response.update(response2)
                        else:
                            format_error(response2.get("error", "Failed to create task"))
                            raise typer.Exit(1)
                else:
                    format_error(error_msg)

                    # Show suggestions if available
                    if "suggestions" in response:
                        suggestions = response["suggestions"]
                        if suggestions.get("available_projects"):
                            console.print("\n[cyan]Available projects:[/cyan]")
                            for proj in suggestions["available_projects"]:
                                console.print(f"  • {proj}")

                    raise typer.Exit(1)

            task = response.get("task", {})
            parsed = response.get("parsed", {})

            # If project_name was parsed but task has no project_id, the project wasn't found
            import sys

            if parsed.get("project_name") and not task.get("project_id") and sys.stdin.isatty():
                unrecognized = parsed["project_name"]
                from todopro_cli.services.api.projects import ProjectsAPI

                console.print(
                    f"\n[yellow]Project '[bold]{unrecognized}[/bold]' not found.[/yellow]"
                )
                create_it = typer.confirm(f"  Create new project '{unrecognized}'?", default=True)
                projects_api = ProjectsAPI(client)
                if create_it:
                    new_proj_resp = await projects_api.create_project(unrecognized)
                    console.print(f"[green]  ✓ Created project '{unrecognized}'[/green]")
                    # Move the newly created task to the new project
                    new_project_id = new_proj_resp.get("id") if isinstance(new_proj_resp, dict) else getattr(new_proj_resp, "id", None)
                    if new_project_id and task.get("id"):
                        updated = await tasks_api.update_task(task["id"], project_id=new_project_id)
                        task.update(updated if isinstance(updated, dict) else updated.model_dump())
                # If declined, task stays in Inbox (already assigned by backend)

            if output == "json":
                import json as _json

                console.print(
                    _json.dumps({"task": task, "parsed": parsed}, indent=2, default=str)
                )
                return

            # Show parsed elements
            console.print("\n[bold green]✓[/bold green] Task created successfully!")
            console.print(f"\n[bold cyan]Task:[/bold cyan] {task.get('content', '')}")

            # Show parsed details — use actual task data, not just parsed metadata
            details = []
            if parsed.get("due_date"):
                due = datetime.fromisoformat(parsed["due_date"].replace("Z", "+00:00"))
                details.append(f"📅 {due.strftime('%b %d, %Y at %I:%M %p')}")

            # Show actual project from task, not the raw parsed project_name
            if task.get("project_name") or task.get("project_id"):
                proj_display = task.get("project_name") or parsed.get("project_name", "")
                if proj_display:
                    details.append(f"[magenta]📁 #{proj_display}[/magenta]")
            elif not parsed.get("project_name"):
                pass  # no project, don't show

            if parsed.get("labels"):
                labels_str = " ".join([f"@{lbl}" for lbl in parsed["labels"]])
                details.append(f"[yellow]🏷️  {labels_str}[/yellow]")

            priority_map = {
                1: "p1 (Urgent)",
                2: "p2 (High)",
                3: "p3 (Medium)",
                4: "p4 (Normal)",
            }
            if parsed.get("priority") and parsed["priority"] < 4:
                priority_display = priority_map.get(
                    parsed["priority"], str(parsed["priority"])
                )
                details.append(f"[red]⚡ {priority_display}[/red]")

            if parsed.get("recurrence_rule"):
                details.append("[green]🔄 Recurring[/green]")

            if details:
                console.print()
                for detail in details:
                    console.print(f"  {detail}")

            console.print(f"\n[dim]Task ID: {task.get('id', '')}[/dim]")

        asyncio.run(do_quick_add())

    except Exception as e:
        format_error(f"Failed to add task: {str(e)}")
        raise typer.Exit(1) from e


def _create_local_task(
    text: str, project_override: str | None = None, output: str = "pretty"
) -> None:
    """Create a task in local context with NLP parsing."""
    import asyncio

    from todopro_cli.utils.nlp_parser import parse_natural_language

    async def _do_create():
        storage_strategy_context = get_storage_strategy_context()
        task_repo = storage_strategy_context.task_repository

        # Parse the text for metadata
        parsed = parse_natural_language(text)

        # Ensure priority is an integer, default to 4 if None
        priority = parsed.get("priority")
        if priority is None or not isinstance(priority, int):
            priority = 4

        # Resolve project_id: --project flag has higher precedence than #project in text
        project_id: str | None = None
        effective_project_name: str | None = None

        from todopro_cli.services.project_service import get_project_service

        if project_override is not None:
            # Resolve project by name/ID (fuzzy)
            from todopro_cli.commands.edit_command import _resolve_project_name

            try:
                project_id = await _resolve_project_name(project_override, storage_strategy_context)
                from todopro_cli.services.project_service import ProjectService
                proj_repo = storage_strategy_context.project_repository
                proj = await ProjectService(proj_repo).get_project(project_id)
                effective_project_name = proj.name
            except ValueError as e:
                from todopro_cli.utils.ui.formatters import format_error

                format_error(str(e))
                raise typer.Exit(1) from e
        elif parsed.get("project_name"):
            # Resolve project name from NLP
            import difflib

            project_service = get_project_service()
            all_projects = await project_service.list_projects()
            names = [p.name for p in all_projects]
            parsed_lower = parsed["project_name"].lower()
            matches = difflib.get_close_matches(
                parsed_lower, [n.lower() for n in names], n=1, cutoff=0.6
            )
            if matches:
                proj = next(p for p in all_projects if p.name.lower() == matches[0])
                project_id = proj.id
                effective_project_name = proj.name
            else:
                # Project not found — prompt the user
                import sys

                unrecognized = parsed["project_name"]
                if sys.stdin.isatty():
                    console.print(
                        f"\n[yellow]Project '[bold]{unrecognized}[/bold]' not found.[/yellow]"
                    )
                    create_it = typer.confirm(f"  Create new project '{unrecognized}'?", default=True)
                else:
                    create_it = False

                if create_it:
                    new_proj = await project_service.create_project(unrecognized)
                    project_id = new_proj.id
                    effective_project_name = new_proj.name
                    console.print(f"[green]  ✓ Created project '{unrecognized}'[/green]")
                else:
                    # Fall back to Inbox
                    inbox = next((p for p in all_projects if p.name.lower() == "inbox"), None)
                    if inbox:
                        project_id = inbox.id
                        effective_project_name = inbox.name
                    # else leave project_id = None (backend default)

        # Create task with parsed metadata
        task_create = TaskCreate(
            content=parsed["content"] or text,
            description="",
            priority=priority,
            due_date=parsed.get("due_date"),
            project_id=project_id,
        )

        task = await task_repo.add(task_create)

        if output == "json":
            console.print(json.dumps(task.model_dump(), indent=2, default=str))
            return

        # Show success message with parsed details
        format_success("Task created successfully!")
        console.print(f"\n[bold cyan]Task:[/bold cyan] {task.content}")

        details = []
        if parsed.get("due_date"):
            due = parsed["due_date"]
            details.append(f"📅 Due: {due.strftime('%b %d, %Y at %H:%M')}")

        if priority < 4:
            priority_map = {
                1: "P1 (Urgent)",
                2: "P2 (High)",
                3: "P3 (Medium)",
                4: "P4 (Normal)",
            }
            details.append(
                f"[red]⚡ {priority_map.get(priority, f'P{priority}')}[/red]"
            )

        if effective_project_name:
            details.append(f"[magenta]📁 #{effective_project_name}[/magenta]")

        if parsed.get("labels"):
            labels_str = " ".join([f"@{label}" for label in parsed["labels"]])
            details.append(f"[yellow]🏷️  {labels_str}[/yellow]")

        if details:
            console.print()
            for detail in details:
                console.print(f"  {detail}")

        console.print(f"\n[dim]Task ID: {task.id}[/dim]")

    try:
        asyncio.run(_do_create())
    except (typer.Exit, SystemExit):
        raise
    except Exception as e:
        format_error(f"Failed to create task: {str(e)}")
        raise typer.Exit(1) from e
