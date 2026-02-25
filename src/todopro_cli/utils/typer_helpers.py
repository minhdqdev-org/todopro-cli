"""Typer helper utilities."""

from difflib import get_close_matches

import typer
from typer.core import TyperGroup


class SuggestingGroup(TyperGroup):
    """Custom Typer group that suggests commands on typos.

    Similar to kubectl's "Did you mean this?" functionality.
    """

    def resolve_command(self, ctx, args):
        """Override to provide command suggestions on errors."""
        try:
            return super().resolve_command(ctx, args)
        except Exception as e:
            # Get the attempted command
            if args:
                attempted = args[0]
                # Get all available commands
                available_commands = list(self.commands.keys())

                # Find close matches (max 3 suggestions, cutoff 0.6 for similarity)
                suggestions = get_close_matches(
                    attempted, available_commands, n=3, cutoff=0.6
                )

                if suggestions:
                    console = get_console()
                    console.print(
                        f'[red]Error:[/red] unknown command "{attempted}" for "{ctx.info_name}"'
                    )
                    console.print()
                    if len(suggestions) == 1:
                        console.print("[yellow]Did you mean this?[/yellow]")
                    else:
                        console.print("[yellow]Did you mean one of these?[/yellow]")
                    for suggestion in suggestions:
                        console.print(f"        {suggestion}")
                    raise typer.Exit(1) from e
            raise
