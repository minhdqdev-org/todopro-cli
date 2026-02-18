"""Command 'add' of todopro-cli"""

import asyncio
from datetime import datetime

import typer

from todopro_cli.models.core import TaskCreate
from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.services.config_service import get_config_service
from todopro_cli.services.context_manager import get_strategy_context
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_error, format_success

# Lazy import QuickAddApp to avoid Textual initialization issues
# from todopro_cli.utils.ui.textual_prompt import QuickAddApp
from .decorators import command_wrapper

app = typer.Typer()
console = get_console()


@app.command("add")
@command_wrapper
def add(
    text: str | None = typer.Argument(None, help="Natural language task description"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
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
    import sys

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
                format_error(error_msg)

                # Show suggestions if available
                if "suggestions" in response:
                    suggestions = response["suggestions"]
                    if suggestions.get("create_project"):
                        project_name = response.get("parsed", {}).get(
                            "project_name", ""
                        )
                        console.print(
                            "\n[yellow]Tip:[/yellow] Create the project first:"
                        )
                        console.print(f'  todopro projects add "{project_name}"')

                    if suggestions.get("available_projects"):
                        console.print("\n[cyan]Available projects:[/cyan]")
                        for proj in suggestions["available_projects"]:
                            console.print(f"  • {proj}")

                raise typer.Exit(1)

            task = response.get("task", {})
            parsed = response.get("parsed", {})

            if output == "json":
                import json as _json

                console.print(
                    _json.dumps({"task": task, "parsed": parsed}, indent=2, default=str)
                )
                return

            # Show parsed elements
            console.print("\n[bold green]✓[/bold green] Task created successfully!")
            console.print(f"\n[bold cyan]Task:[/bold cyan] {task.get('content', '')}")

            # Show parsed details
            details = []
            if parsed.get("due_date"):
                due = datetime.fromisoformat(parsed["due_date"].replace("Z", "+00:00"))
                details.append(f"📅 {due.strftime('%b %d, %Y at %I:%M %p')}")

            if parsed.get("project_name"):
                details.append(f"[magenta]📁 #{parsed['project_name']}[/magenta]")

            if parsed.get("labels"):
                labels_str = " ".join([f"@{l}" for l in parsed["labels"]])
                details.append(f"[yellow]🏷️  {labels_str}[/yellow]")

            priority_map = {
                4: "p1 (Urgent)",
                3: "p2 (High)",
                2: "p3 (Medium)",
                1: "p4 (Low)",
            }
            if parsed.get("priority") and parsed["priority"] > 1:
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
        strategy = get_strategy_context()
        task_repo = strategy.task_repository

        # Parse the text for metadata
        parsed = parse_natural_language(text)

        # Ensure priority is an integer, default to 1 if None
        priority = parsed.get("priority")
        if priority is None or not isinstance(priority, int):
            priority = 1

        # Resolve project_id: --project flag has higher precedence than #project in text
        project_id: str | None = None
        effective_project_name: str | None = None

        if project_override is not None:
            # Resolve project by name/ID (fuzzy)
            from todopro_cli.commands.edit_command import _resolve_project_name
            from todopro_cli.services.project_service import ProjectService

            project_repo = strategy.project_repository
            try:
                project_id = await _resolve_project_name(project_override, strategy)
                proj = await ProjectService(project_repo).get_project(project_id)
                effective_project_name = proj.name
            except ValueError as e:
                from todopro_cli.utils.ui.formatters import format_error

                format_error(str(e))
                raise typer.Exit(1) from e
        elif parsed.get("project_name"):
            # Resolve project name from NLP
            import difflib

            from todopro_cli.services.project_service import ProjectService

            project_repo = strategy.project_repository
            project_service = ProjectService(project_repo)
            all_projects = await project_service.list_projects()
            names = [p.name for p in all_projects]
            matches = difflib.get_close_matches(
                parsed["project_name"], names, n=1, cutoff=0.6
            )
            if matches:
                proj = next(p for p in all_projects if p.name == matches[0])
                project_id = proj.id
                effective_project_name = proj.name
            else:
                effective_project_name = parsed[
                    "project_name"
                ]  # will note it wasn't found

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
            import json as _json

            console.print(_json.dumps(task.model_dump(), indent=2, default=str))
            return

        # Show success message with parsed details
        format_success("Task created successfully!")
        console.print(f"\n[bold cyan]Task:[/bold cyan] {task.content}")

        details = []
        if parsed.get("due_date"):
            due = parsed["due_date"]
            details.append(f"📅 Due: {due.strftime('%b %d, %Y at %H:%M')}")

        if priority > 1:
            priority_map = {
                4: "P1 (Urgent)",
                3: "P2 (High)",
                2: "P3 (Medium)",
                1: "P4 (Low)",
            }
            details.append(
                f"[red]⚡ {priority_map.get(priority, f'P{priority}')}[/red]"
            )

        if effective_project_name:
            details.append(f"[magenta]📁 #{effective_project_name}[/magenta]")

        if parsed.get("labels"):
            labels_str = " ".join([f"@{l}" for l in parsed["labels"]])
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
        from todopro_cli.utils.ui.formatters import format_error as _fe

        _fe(f"Failed to create task: {str(e)}")
        raise typer.Exit(1) from e
