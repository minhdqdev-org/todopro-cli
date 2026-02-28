#!/usr/bin/env python3
"""Generate man page(s) for todopro from the Typer/Click app definition.

Usage:
    uv run scripts/generate_man.py [--output-dir DIR]

The generated file is written to man/man1/todopro.1 by default.
"""

import argparse
import sys
from pathlib import Path

# Allow running from repo root or scripts/ directory
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from click_man.core import write_man_pages
from todopro_cli.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate todopro man page.")
    parser.add_argument(
        "--output-dir",
        default=str(repo_root / "man" / "man1"),
        help="Directory to write generated man page(s) into (default: man/man1/)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Typer's .registered_callback exposes the underlying Click command.
    # app.typer_instance or app() work; the cleanest way is to get the Click
    # Group that Typer builds internally.
    import typer

    click_app = typer.main.get_command(app)

    write_man_pages(
        name="todopro",
        cli=click_app,
        version="1.0.0",
        target_dir=str(output_dir),
    )

    generated = output_dir / "todopro.1"
    if generated.exists():
        print(f"Man page written to: {generated}")
    else:
        print("Warning: expected output file not found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
