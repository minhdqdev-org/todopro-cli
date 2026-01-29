"""Project management commands."""

import asyncio

import typer
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.api.projects import ProjectsAPI
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Project management commands")
console = Console()


def check_auth(profile: str = "default") -> None:
    """Check if user is authenticated."""
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    if not credentials:
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(1)


@app.command("list")
def list_projects(
    archived: bool = typer.Option(False, "--archived", help="Show archived projects"),
    favorites: bool = typer.Option(False, "--favorites", help="Show only favorites"),
    output: str | None = typer.Option(None, "--output", help="Output format"),
    compact: bool = typer.Option(False, "--compact", help="Compact output"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """List projects."""
    check_auth(profile)

    # Get output format from config if not specified
    if output is None:
        config_manager = get_config_manager(profile)
        output = config_manager.get("output.format") or "pretty"
        if not compact:
            compact = config_manager.get("output.compact") or False

    try:

        async def do_list() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                result = await projects_api.list_projects(
                    archived=archived if archived else None,
                    favorites=favorites if favorites else None,
                )
                format_output(result, output, compact=compact)
            finally:
                await client.close()

        asyncio.run(do_list())

    except Exception as e:
        format_error(f"Failed to list projects: {str(e)}")
        raise typer.Exit(1)


@app.command("get")
def get_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get project details."""
    check_auth(profile)

    try:

        async def do_get() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                project = await projects_api.get_project(project_id)
                format_output(project, output)
            finally:
                await client.close()

        asyncio.run(do_get())

    except Exception as e:
        format_error(f"Failed to get project: {str(e)}")
        raise typer.Exit(1)


@app.command("create")
def create_project(
    name: str = typer.Argument(..., help="Project name"),
    color: str | None = typer.Option(None, "--color", help="Project color"),
    favorite: bool = typer.Option(False, "--favorite", help="Mark as favorite"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Create a new project."""
    check_auth(profile)

    try:

        async def do_create() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                project = await projects_api.create_project(
                    name=name,
                    color=color,
                    favorite=favorite,
                )
                format_success(f"Project created: {project.get('id', 'unknown')}")
                format_output(project, output)
            finally:
                await client.close()

        asyncio.run(do_create())

    except Exception as e:
        format_error(f"Failed to create project: {str(e)}")
        raise typer.Exit(1)


@app.command("update")
def update_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    name: str | None = typer.Option(None, "--name", help="Project name"),
    color: str | None = typer.Option(None, "--color", help="Project color"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Update a project."""
    check_auth(profile)

    try:
        # Build updates dictionary
        updates = {}
        if name:
            updates["name"] = name
        if color:
            updates["color"] = color

        if not updates:
            format_error("No updates specified")
            raise typer.Exit(1)

        async def do_update() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                project = await projects_api.update_project(project_id, **updates)
                format_success(f"Project updated: {project_id}")
                format_output(project, output)
            finally:
                await client.close()

        asyncio.run(do_update())

    except Exception as e:
        format_error(f"Failed to update project: {str(e)}")
        raise typer.Exit(1)


@app.command("delete")
def delete_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Delete a project."""
    check_auth(profile)

    try:
        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to delete project {project_id}?"
            )
            if not confirm:
                format_error("Cancelled")
                raise typer.Exit(0)

        async def do_delete() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                await projects_api.delete_project(project_id)
                format_success(f"Project deleted: {project_id}")
            finally:
                await client.close()

        asyncio.run(do_delete())

    except Exception as e:
        format_error(f"Failed to delete project: {str(e)}")
        raise typer.Exit(1)


@app.command("archive")
def archive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Archive a project."""
    check_auth(profile)

    try:

        async def do_archive() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                project = await projects_api.archive_project(project_id)
                format_success(f"Project archived: {project_id}")
                format_output(project, output)
            finally:
                await client.close()

        asyncio.run(do_archive())

    except Exception as e:
        format_error(f"Failed to archive project: {str(e)}")
        raise typer.Exit(1)


@app.command("unarchive")
def unarchive_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Unarchive a project."""
    check_auth(profile)

    try:

        async def do_unarchive() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                project = await projects_api.unarchive_project(project_id)
                format_success(f"Project unarchived: {project_id}")
                format_output(project, output)
            finally:
                await client.close()

        asyncio.run(do_unarchive())

    except Exception as e:
        format_error(f"Failed to unarchive project: {str(e)}")
        raise typer.Exit(1)


@app.command("describe")
def describe_project(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get detailed information about a project."""
    check_auth(profile)

    try:

        async def do_describe() -> None:
            client = get_client(profile)
            projects_api = ProjectsAPI(client)

            try:
                project = await projects_api.get_project(project_id)

                # Display project details
                console.print("\n[bold cyan]Project Details:[/bold cyan]")
                format_output(project, output)

                # Get project stats if available
                try:
                    stats_response = await client.get(
                        f"/v1/projects/{project_id}/stats"
                    )
                    stats = stats_response.json()

                    console.print("\n[bold]Statistics:[/bold]")
                    console.print(f"  Total tasks: {stats.get('total_tasks', 0)}")
                    console.print(f"  Completed: {stats.get('completed_tasks', 0)}")
                    console.print(f"  Pending: {stats.get('pending_tasks', 0)}")
                    console.print(f"  Overdue: {stats.get('overdue_tasks', 0)}")

                    if stats.get("completion_rate") is not None:
                        console.print(
                            f"  Completion rate: {stats.get('completion_rate')}%"
                        )

                except Exception:
                    # Stats endpoint might not exist, ignore
                    pass

            finally:
                await client.close()

        asyncio.run(do_describe())

    except Exception as e:
        format_error(f"Failed to describe project: {str(e)}")
        raise typer.Exit(1)
