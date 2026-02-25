"""GitHub integration - import GitHub Issues as tasks."""

import asyncio
import os

import httpx
import typer
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
app = typer.Typer(cls=SuggestingGroup, help="GitHub integration commands")
console = get_console()


def _get_priority_from_labels(labels: list[dict]) -> int:
    """Map GitHub issue labels to TodoPro priority (1-4)."""
    label_names = {lbl.get("name", "").lower() for lbl in labels}
    if "bug" in label_names:
        return 4
    if "enhancement" in label_names or "feature" in label_names:
        return 2
    if "docs" in label_names or "documentation" in label_names:
        return 1
    return 1


async def _fetch_issues(
    repo: str,
    token: str,
    state: str,
    limit: int,
) -> list[dict]:
    """Fetch issues from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "todopro-cli",
    }
    params = {"state": state, "per_page": limit}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code == 401:
            console.print("[red]Error: Invalid GitHub token[/red]")
            raise typer.Exit(1)
        if response.status_code == 404:
            console.print(f"[red]Error: Repository not found: {repo}[/red]")
            raise typer.Exit(1)
        response.raise_for_status()
        return response.json()


@app.command("import")
def import_issues(
    repo: str = typer.Option(..., "--repo", help="GitHub repository (owner/repo)"),
    token: str | None = typer.Option(
        None, "--token", help="GitHub personal access token"
    ),
    state: str = typer.Option("open", "--state", help="Issue state (open/closed/all)"),
    limit: int = typer.Option(20, "--limit", help="Max issues to import"),
    label: str = typer.Option(
        "github", "--label", help="Label to apply to imported tasks"
    ),
    profile: str = typer.Option("default", "--profile", help="TodoPro profile to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview without importing"),
) -> None:
    """Import GitHub Issues as TodoPro tasks."""
    # Resolve token
    gh_token = token or os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        console.print(
            "[red]Error: GitHub token required. Use --token or set GITHUB_TOKEN env var.[/red]"
        )
        raise typer.Exit(1)

    try:
        issues = asyncio.run(_fetch_issues(repo, gh_token, state, limit))
    except typer.Exit:
        raise
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to GitHub API[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)

    # Filter out pull requests
    issues = [i for i in issues if i.get("pull_request") is None]

    if not issues:
        console.print(f"No {state} issues found in {repo}")
        return

    if dry_run:
        table = Table(title=f"Issues to import from {repo} (dry run)")
        table.add_column("#", style="cyan")
        table.add_column("Title")
        table.add_column("Priority", style="yellow")
        for issue in issues:
            priority = _get_priority_from_labels(issue.get("labels", []))
            table.add_row(str(issue["number"]), issue["title"], str(priority))
        console.print(table)
        return

    async def _do_import():
        client = get_client()
        tasks_api = TasksAPI(client)
        count = 0
        try:
            for issue in issues:
                priority = _get_priority_from_labels(issue.get("labels", []))
                content = f"[GitHub #{issue['number']}] {issue['title']}"
                description = (issue.get("body") or "")[:500]
                await tasks_api.create_task(
                    content,
                    description=description,
                    priority=priority,
                )
                count += 1
        finally:
            await client.close()
        return count

    try:
        count = asyncio.run(_do_import())
        console.print(f"[green]✓ Imported {count} tasks from {repo}[/green]")
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("list-issues")
def list_issues(
    repo: str = typer.Option(..., "--repo", help="GitHub repository (owner/repo)"),
    token: str | None = typer.Option(
        None, "--token", help="GitHub personal access token"
    ),
    state: str = typer.Option("open", "--state", help="Issue state (open/closed/all)"),
    limit: int = typer.Option(20, "--limit", help="Max issues to display"),
) -> None:
    """List GitHub Issues in a repository."""
    gh_token = token or os.environ.get("GITHUB_TOKEN")
    if not gh_token:
        console.print(
            "[red]Error: GitHub token required. Use --token or set GITHUB_TOKEN env var.[/red]"
        )
        raise typer.Exit(1)

    try:
        issues = asyncio.run(_fetch_issues(repo, gh_token, state, limit))
    except typer.Exit:
        raise
    except httpx.ConnectError:
        console.print("[red]Error: Cannot connect to GitHub API[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)

    issues = [i for i in issues if i.get("pull_request") is None]

    if not issues:
        console.print(f"No {state} issues found in {repo}")
        return

    table = Table(title=f"Issues in {repo}")
    table.add_column("#", style="cyan")
    table.add_column("Title")
    table.add_column("Labels", style="magenta")
    table.add_column("State", style="green")
    table.add_column("URL", style="blue")

    for issue in issues:
        labels_str = ", ".join(lbl.get("name", "") for lbl in issue.get("labels", []))
        table.add_row(
            str(issue["number"]),
            issue["title"],
            labels_str,
            issue.get("state", ""),
            issue.get("html_url", ""),
        )

    console.print(table)
