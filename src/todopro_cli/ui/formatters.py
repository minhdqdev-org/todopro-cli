"""Output formatters for different formats."""

import json
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()


def format_output(data: Any, output_format: str = "table") -> None:
    """Format and display output based on format."""
    if output_format == "json":
        print(json.dumps(data, indent=2, default=str))
    elif output_format == "yaml":
        print(yaml.dump(data, default_flow_style=False, sort_keys=False))
    elif output_format in ("table", "wide"):
        format_table(data, wide=output_format == "wide")
    else:
        # Default to table
        format_table(data)


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
