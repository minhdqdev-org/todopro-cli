"""Console utilities for TodoPro CLI."""

from functools import lru_cache

from rich.console import Console


@lru_cache(maxsize=2)
def get_console(highlight: bool = True) -> Console:
    """Get a Rich Console instance for consistent output formatting."""
    return Console(highlight=highlight)
