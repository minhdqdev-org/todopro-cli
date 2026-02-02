"""Task management commands."""

import asyncio

import typer
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.api.tasks import TasksAPI
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import (
    format_error,
    format_info,
    format_output,
    format_success,
)
from todopro_cli.utils.task_helpers import resolve_task_id
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Task management commands")
console = Console()


def check_auth(profile: str = "default") -> None:
    """Check if user is authenticated."""
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    if not credentials:
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(1)


@app.command("list")
def list_tasks(
    status: str | None = typer.Option(None, "--status", help="Filter by status"),
    project: str | None = typer.Option(None, "--project", help="Filter by project ID"),
    priority: int | None = typer.Option(None, "--priority", help="Filter by priority"),
    search: str | None = typer.Option(None, "--search", help="Search tasks"),
    limit: int = typer.Option(30, "--limit", help="Limit results"),
    offset: int = typer.Option(0, "--offset", help="Pagination offset"),
    output: str | None = typer.Option(None, "--output", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """List tasks."""
    check_auth(profile)

    # Get output format from config if not specified
    if output is None:
        config_manager = get_config_manager(profile)
        output = config_manager.get("output.format") or "pretty"
        if not compact:
            compact = config_manager.get("output.compact") or False

    try:
        assert output is not None  # for mypy

        async def do_list() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                result = await tasks_api.list_tasks(
                    status=status,
                    project_id=project,
                    priority=priority,
                    search=search,
                    limit=limit,
                    offset=offset,
                )

                # Filter out tasks being completed in background
                from todopro_cli.utils.task_cache import get_background_cache

                cache = get_background_cache()
                completing_tasks = set(cache.get_completing_tasks())

                if completing_tasks and isinstance(result, dict):
                    tasks_list = result.get("tasks", result.get("items", []))
                    if tasks_list:
                        original_count = len(tasks_list)
                        filtered_tasks = [
                            task
                            for task in tasks_list
                            if not any(task.get("id", "").endswith(short_id) for short_id in completing_tasks)
                        ]
                        if len(filtered_tasks) < original_count:
                            if "tasks" in result:
                                result["tasks"] = filtered_tasks
                            elif "items" in result:
                                result["items"] = filtered_tasks

                format_output(result, output, compact=compact)
            finally:
                await client.close()

        asyncio.run(do_list())

    except Exception as e:
        format_error(f"Failed to list tasks: {str(e)}")
        raise typer.Exit(1) from e


@app.command("get")
def get_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get task details."""
    check_auth(profile)

    try:

        async def do_get() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                resolved_id = await resolve_task_id(tasks_api, task_id)
                task = await tasks_api.get_task(resolved_id)
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_get())

    except Exception as e:
        format_error(f"Failed to get task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("create")
def create_task(
    content: str = typer.Argument(..., help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    labels: str | None = typer.Option(None, "--labels", help="Comma-separated labels"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Create a new task."""
    check_auth(profile)

    try:
        # Parse labels
        label_list = None
        if labels:
            label_list = [l.strip() for l in labels.split(",")]

        async def do_create() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                task = await tasks_api.create_task(
                    content=content,
                    description=description,
                    project_id=project,
                    due_date=due,
                    priority=priority,
                    labels=label_list,
                )
                format_success(f"Task created: {task.get('id', 'unknown')}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_create())

    except Exception as e:
        format_error(f"Failed to create task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("update")
def update_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    content: str | None = typer.Option(None, "--content", help="Task content"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    project: str | None = typer.Option(None, "--project", help="Project ID"),
    due: str | None = typer.Option(None, "--due", help="Due date"),
    priority: int | None = typer.Option(None, "--priority", help="Priority (1-4)"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Update a task."""
    check_auth(profile)

    try:
        # Build updates dictionary
        updates = {}
        if content:
            updates["content"] = content
        if description:
            updates["description"] = description
        if project:
            updates["project_id"] = project
        if due:
            updates["due_date"] = due
        if priority is not None:
            updates["priority"] = priority

        if not updates:
            format_error("No updates specified")
            raise typer.Exit(1)

        async def do_update() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                resolved_id = await resolve_task_id(tasks_api, task_id)
                task = await tasks_api.update_task(resolved_id, **updates)
                format_success(f"Task updated: {resolved_id}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_update())

    except Exception as e:
        format_error(f"Failed to update task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("delete")
def delete_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Delete a task."""
    check_auth(profile)

    try:
        if not yes:
            confirm = typer.confirm(f"Are you sure you want to delete task {task_id}?")
            if not confirm:
                format_error("Cancelled")
                raise typer.Exit(0)

        async def do_delete() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                resolved_id = await resolve_task_id(tasks_api, task_id)
                await tasks_api.delete_task(resolved_id)
                format_success(f"Task deleted: {resolved_id}")
            finally:
                await client.close()

        asyncio.run(do_delete())

    except Exception as e:
        format_error(f"Failed to delete task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("complete")
def complete_task(
    task_ids: list[str] = typer.Argument(
        ..., help="Task ID(s) or suffix - can specify multiple"
    ),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
    sync: bool = typer.Option(
        False, "--sync", help="Wait for completion (synchronous mode)"
    ),
) -> None:
    """Mark one or more tasks as completed."""
    check_auth(profile)

    # Single task - use original logic
    if len(task_ids) == 1:
        task_id = task_ids[0]
        try:
            if sync:
                # Synchronous mode - wait for completion
                async def do_complete() -> None:
                    client = get_client(profile)
                    tasks_api = TasksAPI(client)

                    try:
                        resolved_id = await resolve_task_id(tasks_api, task_id)
                        response = await tasks_api.complete_task(resolved_id)

                        # Extract task from response (API may wrap it)
                        task = response.get(
                            "completed_task", response.get("task", response)
                        )

                        # Show concise success message
                        content = task.get("content", "")
                        if not content or not content.strip():
                            content = "[No title]"
                        # Truncate long content
                        if len(content) > 60:
                            content = content[:57] + "..."

                        format_success(f"✓ Completed: {content}")
                        console.print(f"[dim]To undo: tp tasks reopen {task_id}[/dim]")

                        # Only show full output if explicitly requested
                        if output not in ["table", "pretty"]:
                            format_output(task, output)
                    finally:
                        await client.close()

                asyncio.run(do_complete())
            else:
                # Background mode - don't wait, start immediately
                from todopro_cli.utils.background import run_in_background
                from todopro_cli.utils.task_cache import get_background_cache

                # Add to cache for optimistic UI update
                cache = get_background_cache()
                cache.add_completing_task(task_id)

                # Start background task immediately
                run_in_background(
                    task_type="complete",
                    command="complete",
                    context={
                        "task_id": task_id,
                        "profile": profile,
                    },
                    max_retries=3,
                )

                # Show immediate feedback without waiting
                format_success(f"✓ Marking task as complete: {task_id}")
                console.print(f"[dim]Check status: tp tasks get {task_id}[/dim]")

        except Exception as e:
            format_error(f"Failed to complete task: {str(e)}")
            raise typer.Exit(1) from e

    # Multiple tasks - use batch API
    else:
        try:
            if sync:
                # Synchronous batch mode
                async def do_batch_complete() -> None:
                    client = get_client(profile)
                    tasks_api = TasksAPI(client)

                    try:
                        # Resolve all IDs first
                        resolved_ids = []
                        for task_id in task_ids:
                            resolved_id = await resolve_task_id(tasks_api, task_id)
                            resolved_ids.append(resolved_id)

                        # Batch complete
                        response = await tasks_api.batch_complete_tasks(resolved_ids)

                        # Show results
                        completed = response.get("completed", [])
                        failed = response.get("failed", [])
                        summary = response.get("summary", {})

                        if completed:
                            format_success(f"✓ Completed {len(completed)} task(s)")
                            for task in completed:
                                content = task.get("content", "")[:50]
                                console.print(f"  • {content}")

                        if failed:
                            format_error(f"Failed to complete {len(failed)} task(s)")
                            for fail_info in failed:
                                console.print(
                                    f"  • {fail_info.get('task_id')}: {fail_info.get('error')}"
                                )

                        # Show summary
                        console.print(
                            f"\n[dim]Summary: {summary.get('completed', 0)}/{summary.get('total', 0)} completed[/dim]"
                        )

                    finally:
                        await client.close()

                asyncio.run(do_batch_complete())
            else:
                # Background batch mode
                from todopro_cli.utils.background import run_in_background
                from todopro_cli.utils.task_cache import get_background_cache

                # Add all tasks to cache for optimistic UI update
                cache = get_background_cache()
                cache.add_completing_tasks(task_ids)

                run_in_background(
                    task_type="batch_complete",
                    command="complete",
                    context={
                        "task_ids": task_ids,
                        "profile": profile,
                    },
                    max_retries=3,
                )

                # Show immediate feedback
                format_success(
                    f"✓ Marking {len(task_ids)} task(s) as complete in background"
                )
                console.print(f"[dim]Tasks: {', '.join(task_ids)}[/dim]")

        except Exception as e:
            format_error(f"Failed to batch complete tasks: {str(e)}")
            raise typer.Exit(1) from e


@app.command("reopen")
def reopen_task(
    task_id: str = typer.Argument(..., help="Task ID or suffix"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Reopen a completed task."""
    check_auth(profile)

    try:

        async def do_reopen() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                resolved_id = await resolve_task_id(tasks_api, task_id)
                task = await tasks_api.reopen_task(resolved_id)
                format_success(f"Task reopened: {resolved_id}")
                format_output(task, output)
            finally:
                await client.close()

        asyncio.run(do_reopen())

    except Exception as e:
        format_error(f"Failed to reopen task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("today")
def today(
    output: str = typer.Option("pretty", "--output", "-o", help="Output format"),
    json: bool = typer.Option(False, "--json", help="Output as JSON (alias for --output json)"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show tasks for today (overdue + today's tasks)."""
    check_auth(profile)
    
    # Handle --json flag as alias for --output json
    if json:
        output = "json"

    # Show error banner if there are unread errors
    from rich.panel import Panel

    from todopro_cli.utils.error_logger import get_unread_errors, mark_errors_as_read

    unread_errors = get_unread_errors()
    if unread_errors:
        error_count = len(unread_errors)
        latest_error = unread_errors[0]

        # Show banner
        error_msg = latest_error.get("error", "Unknown error")
        command = latest_error.get("command", "unknown")

        # Truncate long error messages
        if len(error_msg) > 100:
            error_msg = error_msg[:97] + "..."

        banner_text = (
            f"[yellow]⚠️  {error_count} background task(s) failed[/yellow]\n"
            f"[dim]Latest: '{command}' - {error_msg}[/dim]\n\n"
            f"[dim]View details: [cyan]todopro errors[/cyan][/dim]"
        )

        console.print(Panel(banner_text, border_style="yellow", padding=(0, 1)))
        console.print()

        # Mark errors as read
        mark_errors_as_read()

    try:

        async def do_today() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                result = await tasks_api.today_tasks()

                # Combine overdue and today tasks for pretty output
                all_tasks = result.get("overdue", []) + result.get("today", [])

                # Filter out tasks being completed in background
                from todopro_cli.utils.task_cache import get_background_cache

                cache = get_background_cache()
                completing_tasks = set(cache.get_completing_tasks())

                if completing_tasks:
                    # Filter tasks and adjust counts
                    original_count = len(all_tasks)
                    all_tasks = [
                        task
                        for task in all_tasks
                        if not any(task.get("id", "").endswith(short_id) for short_id in completing_tasks)
                    ]
                    filtered_count = original_count - len(all_tasks)

                    if filtered_count > 0:
                        console.print(
                            f"[dim]Hiding {filtered_count} task(s) being completed in background...[/dim]"
                        )
                        console.print()

                if all_tasks:
                    # Display with pretty format by default
                    format_output(all_tasks, output, compact=compact)

                    # Summary (skip for JSON output)
                    if output not in ["json", "yaml"]:
                        console.print()
                        console.print(
                            f"[bold]Summary:[/bold] {result.get('overdue_count', 0)} overdue, "
                            f"{result.get('today_count', 0)} due today"
                        )
                else:
                    # Handle empty result based on output format
                    if output == "json":
                        import json
                        print(json.dumps({
                            "tasks": [],
                            "overdue_count": 0,
                            "today_count": 0,
                            "message": "No tasks due today"
                        }))
                    elif output == "yaml":
                        print("tasks: []\noverdue_count: 0\ntoday_count: 0\nmessage: No tasks due today")
                    else:
                        console.print("[green]No tasks due today! 🎉[/green]")

            finally:
                await client.close()

        asyncio.run(do_today())

    except Exception as e:
        format_error(f"Failed to get today's tasks: {str(e)}")
        raise typer.Exit(1) from e


@app.command("next")
def next_task(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
    json: bool = typer.Option(False, "--json", help="Output as JSON (alias for --output json)"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show the next task to do right now."""
    check_auth(profile)
    
    # Handle --json flag as alias for --output json
    if json:
        output = "json"

    try:

        async def do_next() -> None:
            client = get_client(profile)
            tasks_api = TasksAPI(client)

            try:
                result = await tasks_api.next_task()

                if "message" in result:
                    # No tasks found
                    if output == "json":
                        import json
                        print(json.dumps({
                            "task": None,
                            "message": result["message"]
                        }))
                    elif output == "yaml":
                        print(f"task: null\nmessage: {result['message']}")
                    else:
                        console.print(f"[green]{result['message']}[/green]")
                else:
                    # Task found - format based on output type
                    if output in ["json", "yaml"]:
                        format_output(result, output)
                    else:
                        # Custom simple format for next task
                        from todopro_cli.ui.formatters import format_next_task
                        format_next_task(result)

            finally:
                await client.close()

        asyncio.run(do_next())

    except Exception as e:
        format_error(f"Failed to get next task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("reschedule")
def reschedule(
    target: str | None = typer.Argument(
        None, help="Task ID/suffix (omit to reschedule all overdue tasks)"
    ),
    date: str | None = typer.Option(
        None, "--date", "-d", help="New due date (today/tomorrow/YYYY-MM-DD)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Reschedule a task or all overdue tasks."""
    check_auth(profile)

    # Check if target is None or "overdue" for bulk reschedule
    if target is None or target == "overdue":
        try:

            async def do_reschedule_overdue() -> None:
                client = get_client(profile)
                tasks_api = TasksAPI(client)

                try:
                    # Get overdue count first
                    result = await tasks_api.today_tasks()
                    overdue_count = result.get("overdue_count", 0)

                    if overdue_count == 0:
                        console.print(
                            "[green]No overdue tasks to reschedule! 🎉[/green]"
                        )
                        return

                    # Confirm
                    if not yes:
                        # Format the prompt as requested: "Do you want to reschedule 35 overdue tasks to today? <Y/n>:"
                        task_word = "task" if overdue_count == 1 else "tasks"
                        confirm = typer.confirm(
                            f"Do you want to reschedule {overdue_count} overdue {task_word} to today?",
                            default=True,
                        )
                        if not confirm:
                            format_info("Cancelled")
                            return

                    # Reschedule
                    response = await tasks_api.reschedule_overdue()

                    count = response.get("rescheduled_count", 0)
                    task_word = "task" if count == 1 else "tasks"
                    format_success(f"Rescheduled {count} overdue {task_word} to today")

                    # Suggest undo command instead of showing full list
                    console.print(
                        "[dim]💡 Tip: You can undo this later if needed[/dim]"
                    )

                finally:
                    await client.close()

            asyncio.run(do_reschedule_overdue())

        except Exception as e:
            format_error(f"Failed to reschedule tasks: {str(e)}")
            raise typer.Exit(1) from e
    else:
        # Reschedule a specific task
        task_id = target

        # Default to today if no date specified
        if not date:
            date = "today"

        try:

            async def do_reschedule_task() -> None:
                client = get_client(profile)
                tasks_api = TasksAPI(client)

                try:
                    # Resolve task ID
                    resolved_id = await resolve_task_id(tasks_api, task_id)

                    # Reschedule the task
                    response = await tasks_api.reschedule_task(resolved_id, date)

                    task = response.get("task", {})
                    content = task.get("content", "")
                    if not content or not content.strip():
                        content = "[No title]"
                    if len(content) > 60:
                        content = content[:57] + "..."

                    message = response.get("message", "Task rescheduled")
                    format_success(f"✓ {content}")
                    console.print(f"[dim]{message}[/dim]")

                finally:
                    await client.close()

            asyncio.run(do_reschedule_task())

        except Exception as e:
            format_error(f"Failed to reschedule task: {str(e)}")
            raise typer.Exit(1) from e


@app.command("add")
def quick_add(
    text: str | None = typer.Argument(None, help="Task text in natural language"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
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
    """
    check_auth(profile)

    # If no text provided, use interactive prompt
    if not text:
        try:
            from todopro_cli.ui.interactive_prompt import get_interactive_input

            text = asyncio.run(get_interactive_input(profile=profile))
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0) from None

        if not text:
            format_error("Task text is required")
            raise typer.Exit(1)

    try:

        async def do_quick_add():
            client = get_client(profile)
            try:
                tasks_api = TasksAPI(client)

                # Show parsing preview
                # console.print(f"\n[cyan]Parsing:[/cyan] {text}")

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

                # Show parsed elements
                console.print("\n[bold green]✓[/bold green] Task created successfully!")
                console.print(
                    f"\n[bold cyan]Task:[/bold cyan] {task.get('content', '')}"
                )

                # Show parsed details
                details = []
                if parsed.get("due_date"):
                    from datetime import datetime

                    due = datetime.fromisoformat(
                        parsed["due_date"].replace("Z", "+00:00")
                    )
                    details.append(
                        f"[blue]📅 {due.strftime('%b %d, %Y at %I:%M %p')}[/blue]"
                    )

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

            finally:
                await client.close()

        asyncio.run(do_quick_add())

    except Exception as e:
        format_error(f"Failed to add task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("matrix")
def eisenhower_matrix(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """
    View tasks organized by Eisenhower Matrix (Urgent-Important).

    Quadrants:
      Q1 (Do First)    - Urgent & Important
      Q2 (Schedule)    - Important, Not Urgent
      Q3 (Delegate)    - Urgent, Not Important
      Q4 (Eliminate)   - Neither
    """
    check_auth(profile)

    try:

        async def get_matrix():
            client = get_client(profile)
            try:
                tasks_api = TasksAPI(client)
                matrix_data = await tasks_api.eisenhower_matrix()

                matrix = matrix_data.get("matrix", {})
                insights = matrix_data.get("insights", {})

                # Display matrix
                console.print()
                console.print("[bold cyan]═" * 60 + "[/bold cyan]")
                console.print(f"[bold cyan]{'Eisenhower Matrix':^60}[/bold cyan]")
                console.print("[bold cyan]═" * 60 + "[/bold cyan]")
                console.print()

                # Display quadrants in 2x2 grid
                _display_quadrant_pair(matrix, "Q1", "Q2")
                console.print()
                _display_quadrant_pair(matrix, "Q3", "Q4")

                # Display insights
                console.print()
                console.print("[bold cyan]" + "─" * 60 + "[/bold cyan]")
                console.print("[bold]📊 Insights:[/bold]")
                console.print(f"  • Total tasks: {insights.get('total_tasks', 0)}")
                console.print(
                    f"  • Q2 (Strategic work): {insights.get('q2_percentage', 0)}%"
                )

                score = insights.get("health_score", 0)
                score_color = (
                    "green" if score >= 70 else "yellow" if score >= 50 else "red"
                )
                stars = "⭐" * (score // 20)
                console.print(
                    f"  • Health Score: [{score_color}]{score}/100 {stars}[/{score_color}]"
                )
                console.print(f"  • {insights.get('message', '')}")
                console.print()

            finally:
                await client.close()

        asyncio.run(get_matrix())

    except Exception as e:
        format_error(f"Failed to get matrix: {str(e)}")
        raise typer.Exit(1) from e


def _display_quadrant_pair(matrix, q1_key, q2_key):
    """Display two quadrants side by side."""
    q1 = matrix.get(q1_key, {})
    q2 = matrix.get(q2_key, {})

    # Header
    console.print("[bold]╔" + "═" * 58 + "╗[/bold]")
    console.print(
        f"[bold]║ {q1_key}: {q1.get('label', '')} ({q1.get('count', 0)})".ljust(58)
        + " ║ "
        + f"{q2_key}: {q2.get('label', '')} ({q2.get('count', 0)})".ljust(58)
        + " ║[/bold]"
    )
    console.print(
        f"[dim]║ {q1.get('description', '')}".ljust(58)
        + " ║ "
        + f"{q2.get('description', '')}".ljust(58)
        + " ║[/dim]"
    )
    console.print("[bold]╠" + "═" * 58 + "╬" + "═" * 58 + "╣[/bold]")

    # Tasks
    q1_tasks = q1.get("tasks", [])[:5]  # Show max 5 per quadrant
    q2_tasks = q2.get("tasks", [])[:5]

    max_rows = max(len(q1_tasks), len(q2_tasks), 3)

    for i in range(max_rows):
        left_content = ""
        right_content = ""

        if i < len(q1_tasks):
            task = q1_tasks[i]
            icon = _get_quadrant_icon(q1_key)
            left_content = f"{icon} {task.get('content', '')[:50]}"
            if task.get("due_date"):
                from datetime import datetime

                due = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00"))
                left_content += f" [dim]({due.strftime('%m/%d')})[/dim]"

        if i < len(q2_tasks):
            task = q2_tasks[i]
            icon = _get_quadrant_icon(q2_key)
            right_content = f"{icon} {task.get('content', '')[:50]}"
            if task.get("due_date"):
                from datetime import datetime

                due = datetime.fromisoformat(task["due_date"].replace("Z", "+00:00"))
                right_content += f" [dim]({due.strftime('%m/%d')})[/dim]"

        console.print(
            f"║ {left_content}".ljust(66) + "║ " + f"{right_content}".ljust(66) + "║"
        )

    # Show recommendation for top row
    if q1_key in ["Q1", "Q3"]:
        console.print("[bold]╠" + "═" * 58 + "╬" + "═" * 58 + "╣[/bold]")
        q1_rec = q1.get("recommendation", "")[:55]
        q2_rec = q2.get("recommendation", "")[:55]
        console.print(
            f"[dim]║ {q1_rec}".ljust(66) + "║ " + f"{q2_rec}".ljust(66) + "║[/dim]"
        )

    console.print("[bold]╚" + "═" * 58 + "╩" + "═" * 58 + "╝[/bold]")


def _get_quadrant_icon(quadrant):
    """Get emoji icon for quadrant."""
    icons = {
        "Q1": "🔴",  # Red - Urgent & Important
        "Q2": "🟢",  # Green - Important
        "Q3": "🟡",  # Yellow - Urgent
        "Q4": "🔵",  # Blue - Neither
    }
    return icons.get(quadrant, "•")


@app.command("classify")
def classify_task_cmd(
    task_id: str = typer.Argument(..., help="Task ID or suffix to classify"),
    urgent: bool = typer.Option(None, "--urgent/--not-urgent", help="Mark as urgent"),
    important: bool = typer.Option(
        None, "--important/--not-important", help="Mark as important"
    ),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Classify a task in the Eisenhower Matrix."""
    check_auth(profile)

    # Interactive mode if no flags provided
    if urgent is None and important is None:
        try:
            urgent_input = (
                console.input("[cyan]Is this task urgent? (y/n):[/cyan] ")
                .strip()
                .lower()
            )
            urgent = urgent_input == "y"

            important_input = (
                console.input("[cyan]Is this task important? (y/n):[/cyan] ")
                .strip()
                .lower()
            )
            important = important_input == "y"
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            raise typer.Exit(0)

    try:

        async def do_classify():
            client = get_client(profile)
            try:
                tasks_api = TasksAPI(client)
                resolved_id = await resolve_task_id(tasks_api, task_id)
                result = await tasks_api.classify_task(resolved_id, urgent, important)

                task = result.get("task", {})
                quadrant = result.get("quadrant", "")

                icon = _get_quadrant_icon(quadrant)
                console.print(
                    f"\n[bold green]✓[/bold green] Task classified as {icon} {quadrant}"
                )
                console.print(f"  {task.get('content', '')}")
                console.print(f"  [dim]Urgent: {urgent}, Important: {important}[/dim]")

            finally:
                await client.close()

        asyncio.run(do_classify())

    except Exception as e:
        format_error(f"Failed to classify task: {str(e)}")
        raise typer.Exit(1) from e


@app.command("focus")
def focus_on_q2(
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Show Q2 tasks (Important but Not Urgent) - Strategic work."""
    check_auth(profile)

    try:

        async def get_focus_tasks():
            client = get_client(profile)
            try:
                tasks_api = TasksAPI(client)
                matrix_data = await tasks_api.eisenhower_matrix()

                q2 = matrix_data.get("matrix", {}).get("Q2", {})
                tasks = q2.get("tasks", [])

                console.print()
                console.print(
                    f"[bold green]🟢 Q2: {q2.get('label', '')} ({len(tasks)} tasks)[/bold green]"
                )
                console.print(f"[dim]{q2.get('description', '')}[/dim]")
                console.print()

                if tasks:
                    format_output(tasks, "pretty", compact=False)
                    console.print()
                    console.print(
                        f"[cyan]💡 Tip: {q2.get('recommendation', '')}[/cyan]"
                    )
                else:
                    console.print(
                        "[yellow]No Q2 tasks found. Add some strategic, long-term work![/yellow]"
                    )
                console.print()

            finally:
                await client.close()

        asyncio.run(get_focus_tasks())

    except Exception as e:
        format_error(f"Failed to get focus tasks: {str(e)}")
        raise typer.Exit(1) from e
