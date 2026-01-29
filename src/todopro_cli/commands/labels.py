"""Label management commands."""

import asyncio

import typer
from rich.console import Console

from todopro_cli.api.client import get_client
from todopro_cli.api.labels import LabelsAPI
from todopro_cli.config import get_config_manager
from todopro_cli.ui.formatters import format_error, format_output, format_success
from todopro_cli.utils.typer_helpers import SuggestingGroup

app = typer.Typer(cls=SuggestingGroup, help="Label management commands")
console = Console()


def check_auth(profile: str = "default") -> None:
    """Check if user is authenticated."""
    config_manager = get_config_manager(profile)
    credentials = config_manager.load_credentials()
    if not credentials:
        format_error("Not logged in. Use 'todopro login' to authenticate.")
        raise typer.Exit(1)


@app.command("list")
def list_labels(
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """List all labels."""
    check_auth(profile)

    try:

        async def do_list() -> None:
            client = get_client(profile)
            labels_api = LabelsAPI(client)

            try:
                result = await labels_api.list_labels()
                format_output(result, output)
            finally:
                await client.close()

        asyncio.run(do_list())

    except Exception as e:
        format_error(f"Failed to list labels: {str(e)}")
        raise typer.Exit(1)


@app.command("get")
def get_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Get label details."""
    check_auth(profile)

    try:

        async def do_get() -> None:
            client = get_client(profile)
            labels_api = LabelsAPI(client)

            try:
                label = await labels_api.get_label(label_id)
                format_output(label, output)
            finally:
                await client.close()

        asyncio.run(do_get())

    except Exception as e:
        format_error(f"Failed to get label: {str(e)}")
        raise typer.Exit(1)


@app.command("create")
def create_label(
    name: str = typer.Argument(..., help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Create a new label."""
    check_auth(profile)

    try:

        async def do_create() -> None:
            client = get_client(profile)
            labels_api = LabelsAPI(client)

            try:
                label = await labels_api.create_label(name=name, color=color)
                format_success(f"Label created: {label.get('id', 'unknown')}")
                format_output(label, output)
            finally:
                await client.close()

        asyncio.run(do_create())

    except Exception as e:
        format_error(f"Failed to create label: {str(e)}")
        raise typer.Exit(1)


@app.command("update")
def update_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    name: str | None = typer.Option(None, "--name", help="Label name"),
    color: str | None = typer.Option(None, "--color", help="Label color"),
    output: str = typer.Option("table", "--output", help="Output format"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Update a label."""
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
            labels_api = LabelsAPI(client)

            try:
                label = await labels_api.update_label(label_id, **updates)
                format_success(f"Label updated: {label_id}")
                format_output(label, output)
            finally:
                await client.close()

        asyncio.run(do_update())

    except Exception as e:
        format_error(f"Failed to update label: {str(e)}")
        raise typer.Exit(1)


@app.command("delete")
def delete_label(
    label_id: str = typer.Argument(..., help="Label ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    profile: str = typer.Option("default", "--profile", help="Profile name"),
) -> None:
    """Delete a label."""
    check_auth(profile)

    try:
        if not yes:
            confirm = typer.confirm(
                f"Are you sure you want to delete label {label_id}?"
            )
            if not confirm:
                format_error("Cancelled")
                raise typer.Exit(0)

        async def do_delete() -> None:
            client = get_client(profile)
            labels_api = LabelsAPI(client)

            try:
                await labels_api.delete_label(label_id)
                format_success(f"Label deleted: {label_id}")
            finally:
                await client.close()

        asyncio.run(do_delete())

    except Exception as e:
        format_error(f"Failed to delete label: {str(e)}")
        raise typer.Exit(1)
