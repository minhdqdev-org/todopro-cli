"""GitHub integration - import GitHub Issues as tasks."""

import asyncio
import os

import httpx
import typer
from rich.panel import Panel
from rich.table import Table

from todopro_cli.services.api.client import get_client
from todopro_cli.services.api.tasks import TasksAPI
from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(cls=SuggestingGroup, help="GitHub integration commands")
console = get_console()


def _require_remote_context() -> None:
    """Ensure the active context is remote (cloud).

    The server-side PAT commands (connect/status/disconnect) talk to the
    TodoPro backend, so they cannot run against a local SQLite context.
    """
    config_svc = get_config_service()
    try:
        current_context = config_svc.get_current_context()
    except (ValueError, KeyError):
        current_context = None

    if current_context is None or current_context.type != "remote":
        ctx_name = current_context.name if current_context else "local"
        console.print(
            "[red]Error: This command requires a remote (cloud) context.[/red]"
        )
        console.print(
            f"[dim]Active context is '[bold]{ctx_name}[/bold]' (local). "
            "Switch with:[/dim] [cyan]todopro context use cloud[/cyan]"
        )
        raise typer.Exit(1)


def _extract_error_message(response: httpx.Response) -> str:
    """Best-effort extraction of an error message from an API response."""
    try:
        data = response.json()
    except Exception:
        return response.text or f"HTTP {response.status_code}"
    err = data.get("error")
    if isinstance(err, dict):
        return err.get("message") or str(err)
    if isinstance(err, str):
        return err
    return str(data)


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
    _label: str = typer.Option(
        "github", "--label", help="Label to apply to imported tasks"
    ),
    _profile: str = typer.Option(
        "default", "--profile", help="TodoPro profile to use"
    ),
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
        raise typer.Exit(1) from None
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

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
        raise typer.Exit(1) from exc


@app.command("list-issues")
def list_issues(
    repo: str = typer.Option(..., "--repo", help="GitHub repository (owner/repo)"),
    token: str | None = typer.Option(
        None, "--token", help="GitHub personal access token"
    ),
    state: str = typer.Option("open", "--state", help="Issue state (open/closed/all)"),
    limit: int = typer.Option(20, "--limit", help="Max issues to display"),
    output: str = typer.Option(
        "pretty", "--output", "-o", help="Output format (pretty, json, yaml)"
    ),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List GitHub Issues in a repository."""
    if json_opt:
        output = "json"
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
        raise typer.Exit(1) from None
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    issues = [i for i in issues if i.get("pull_request") is None]

    if output != "pretty":
        from todopro_cli.utils.ui.formatters import format_output

        format_output(issues, output)
        return

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


def _render_connection(data: dict) -> None:
    """Render connection details (account, kind, scopes, expiry) as a panel."""
    account = data.get("external_account") or "?"
    kind = data.get("token_kind") or "?"
    scopes = data.get("scopes") or []
    scopes_str = ", ".join(scopes) if scopes else "[dim]none[/dim]"
    expires_at = data.get("expires_at") or "[dim]never[/dim]"

    lines = [
        f"[bold]Account:[/bold] {account}",
        f"[bold]Token kind:[/bold] {kind}",
        f"[bold]Scopes:[/bold] {scopes_str}",
        f"[bold]Expires:[/bold] {expires_at}",
    ]
    token_tail = data.get("token_tail")
    if token_tail:
        lines.insert(2, f"[bold]Token:[/bold] {token_tail}")
    connected_at = data.get("connected_at")
    if connected_at:
        lines.append(f"[bold]Connected at:[/bold] {connected_at}")

    console.print(
        Panel(
            "\n".join(lines),
            title="[green]GitHub connected[/green]",
            border_style="green",
        )
    )


@app.command("connect")
def connect(
    pat: str | None = typer.Option(
        None,
        "--pat",
        help="GitHub Personal Access Token (omit to be prompted securely)",
    ),
) -> None:
    """Connect a GitHub PAT, stored securely on the TodoPro server.

    The token is sent to the TodoPro backend and is NEVER written to local
    config or credentials. Requires a Pro subscription.
    """
    _require_remote_context()

    # Resolve PAT: --pat > env vars > secure prompt. Never persisted locally.
    token = pat or os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PAT")
    if not token:
        token = typer.prompt("GitHub Personal Access Token", hide_input=True)
    token = (token or "").strip()
    if not token:
        console.print("[red]Error: No token provided.[/red]")
        raise typer.Exit(1)

    async def _do_connect() -> dict:
        client = get_client()
        try:
            response = await client.post(
                "/integrations/github/connect/", json={"pat": token}
            )
            return response.json()
        finally:
            await client.close()

    try:
        data = asyncio.run(_do_connect())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 402:
            try:
                err = exc.response.json().get("error", {})
            except Exception:
                err = {}
            message = (
                err.get("message") if isinstance(err, dict) else None
            ) or "A Pro subscription is required to connect GitHub."
            upgrade_url = (
                err.get("details", {}).get("upgrade_url")
                if isinstance(err, dict)
                else None
            )
            console.print(f"[yellow]⚠ Pro subscription required:[/yellow] {message}")
            if upgrade_url:
                console.print(f"[dim]Upgrade:[/dim] [cyan]{upgrade_url}[/cyan]")
            raise typer.Exit(1) from exc
        if status == 400:
            console.print(
                f"[red]Invalid or expired token: "
                f"{_extract_error_message(exc.response)}[/red]"
            )
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: Not authenticated. Run [cyan]todopro login[/cyan] first.[/red]"
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]✓ GitHub PAT connected.[/green]")
    _render_connection(data)


@app.command("status")
def status() -> None:
    """Show the GitHub PAT connection stored on the TodoPro server."""
    _require_remote_context()

    async def _do_status() -> dict:
        client = get_client()
        try:
            response = await client.get("/integrations/github/status/")
            return response.json()
        finally:
            await client.close()

    try:
        data = asyncio.run(_do_status())
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            console.print(
                "[red]Error: Not authenticated. Run [cyan]todopro login[/cyan] first.[/red]"
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    if not data.get("connected"):
        console.print(
            Panel(
                "No GitHub PAT is connected.\n"
                "[dim]Run[/dim] [cyan]todopro github connect[/cyan] [dim]to connect one.[/dim]",
                title="[yellow]Not connected[/yellow]",
                border_style="yellow",
            )
        )
        return

    _render_connection(data)


@app.command("disconnect")
def disconnect() -> None:
    """Remove the GitHub PAT stored on the TodoPro server."""
    _require_remote_context()

    async def _do_disconnect() -> dict:
        client = get_client()
        try:
            response = await client.delete("/integrations/github/disconnect/")
            try:
                return response.json()
            except Exception:
                return {"status": "disconnected"}
        finally:
            await client.close()

    try:
        asyncio.run(_do_disconnect())
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            console.print(
                "[red]Error: Not authenticated. Run [cyan]todopro login[/cyan] first.[/red]"
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print("[green]✓ GitHub PAT disconnected.[/green]")


def _handle_pro_required(response: httpx.Response) -> None:
    """Print a Pro-required (402) message extracted from the API response."""
    try:
        err = response.json().get("error", {})
    except Exception:
        err = {}
    message = (
        err.get("message") if isinstance(err, dict) else None
    ) or "A Pro subscription is required for this feature."
    upgrade_url = (
        err.get("details", {}).get("upgrade_url") if isinstance(err, dict) else None
    )
    console.print(f"[yellow]⚠ Pro subscription required:[/yellow] {message}")
    if upgrade_url:
        console.print(f"[dim]Upgrade:[/dim] [cyan]{upgrade_url}[/cyan]")


@app.command("projects")
def list_projects(
    output: str = typer.Option(
        "pretty", "--output", "-o", help="Output format (pretty, json, yaml)"
    ),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List your GitHub Projects v2 visible to the connected PAT (Pro)."""
    if json_opt:
        output = "json"
    _require_remote_context()

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.get("/integrations/github/projects/")
            return response.json()
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: GitHub is not connected.[/red] "
                "Run [cyan]todopro github connect[/cyan] first."
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    projects = data.get("projects", [])

    if output != "pretty":
        from todopro_cli.utils.ui.formatters import format_output

        format_output(data, output)
        return

    if not projects:
        console.print("No GitHub Projects found.")
        return

    table = Table(title="GitHub Projects")
    table.add_column("#", style="cyan")
    table.add_column("Title")
    table.add_column("Owner", style="magenta")
    table.add_column("ID", style="dim")
    table.add_column("URL", style="blue")

    for proj in projects:
        number = proj.get("number")
        title = proj.get("title", "")
        if proj.get("closed"):
            title = f"{title} [dim](closed)[/dim]"
        table.add_row(
            str(number) if number is not None else "",
            title,
            proj.get("owner", ""),
            proj.get("id", ""),
            proj.get("url", ""),
        )

    console.print(table)
    console.print(
        "[dim]Tip: use the [bold]ID[/bold] (node id) as "
        "[cyan]--github-project[/cyan] when linking.[/dim]"
    )


@app.command("link")
def link_project(
    todopro_project: str = typer.Option(
        ..., "--todopro-project", help="TodoPro project id to link"
    ),
    github_project: str = typer.Option(
        ...,
        "--github-project",
        help="GitHub Project NODE id (the 'ID' from 'github projects', not the number)",
    ),
    name: str | None = typer.Option(
        None, "--name", help="Display name for the linked project"
    ),
    url: str | None = typer.Option(None, "--url", help="URL of the GitHub project"),
    direction: str = typer.Option(
        "pull", "--direction", help="Sync direction: pull, push, or both"
    ),
) -> None:
    """Link a TodoPro project to a GitHub Project v2 (Pro)."""
    _require_remote_context()

    if direction not in ("pull", "push", "both"):
        console.print("[red]Error: --direction must be one of: pull, push, both.[/red]")
        raise typer.Exit(1)

    body = {
        "todopro_project_id": todopro_project,
        "external_id": github_project,
        "external_name": name,
        "external_url": url,
        "sync_direction": direction,
    }

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.post("/integrations/github/links/", json=body)
            try:
                return response.json()
            except Exception:
                return {}
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: GitHub is not connected.[/red] "
                "Run [cyan]todopro github connect[/cyan] first."
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    link_id = data.get("id")
    created = data.get("created")
    verb = "Created" if created else "Updated"
    suffix = f" [dim](link id: {link_id})[/dim]" if link_id is not None else ""
    console.print(f"[green]✓ {verb} link.[/green]{suffix}")


@app.command("unlink")
def unlink_project(
    link: str = typer.Option(..., "--link", help="Link id to remove"),
) -> None:
    """Remove a TodoPro ↔ GitHub Project link (Pro)."""
    _require_remote_context()

    async def _do() -> None:
        client = get_client()
        try:
            await client.delete(f"/integrations/github/links/{link}/")
        finally:
            await client.close()

    try:
        asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            console.print(f"[red]Error: link not found: {link}[/red]")
            raise typer.Exit(1) from exc
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: GitHub is not connected.[/red] "
                "Run [cyan]todopro github connect[/cyan] first."
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(f"[green]✓ Unlinked.[/green] [dim](link id: {link})[/dim]")


@app.command("links")
def list_links(
    output: str = typer.Option(
        "pretty", "--output", "-o", help="Output format (pretty, json, yaml)"
    ),
    json_opt: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --output json)"
    ),
) -> None:
    """List TodoPro ↔ GitHub Project links (Pro)."""
    if json_opt:
        output = "json"
    _require_remote_context()

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.get("/integrations/github/links/")
            return response.json()
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: GitHub is not connected.[/red] "
                "Run [cyan]todopro github connect[/cyan] first."
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    links = data.get("links", [])

    if output != "pretty":
        from todopro_cli.utils.ui.formatters import format_output

        format_output(data, output)
        return

    if not links:
        console.print(
            "No links found. Create one with [cyan]todopro github link[/cyan]."
        )
        return

    table = Table(title="GitHub Project Links")
    table.add_column("Link", style="cyan")
    table.add_column("TodoPro project", style="green")
    table.add_column("GitHub project")
    table.add_column("Direction", style="yellow")
    table.add_column("Last synced", style="dim")
    table.add_column("External id", style="dim")

    for lnk in links:
        table.add_row(
            str(lnk.get("id", "")),
            str(lnk.get("todopro_project_id", "")),
            lnk.get("external_name") or lnk.get("external_id", ""),
            lnk.get("sync_direction", ""),
            lnk.get("last_synced_at") or "[dim]never[/dim]",
            lnk.get("external_id", ""),
        )

    console.print(table)


@app.command("import-project")
def import_project(
    link: str = typer.Option(..., "--link", help="Link id to import from"),
    with_tasks: bool = typer.Option(
        False,
        "--with-tasks",
        help="Also mirror imported items into native TodoPro tasks",
    ),
) -> None:
    """Import items from a linked GitHub Project (Pro)."""
    _require_remote_context()

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.post(
                f"/integrations/github/links/{link}/import/",
                json={"import_tasks": with_tasks},
            )
            try:
                return response.json()
            except Exception:
                return {}
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            console.print(f"[red]Error: link not found: {link}[/red]")
            raise typer.Exit(1) from exc
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: GitHub is not connected.[/red] "
                "Run [cyan]todopro github connect[/cyan] first."
            )
            raise typer.Exit(1) from exc
        if status == 502:
            console.print(
                "[red]Error: GitHub returned an error (upstream). "
                "Try again shortly.[/red]"
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    created = data.get("created", 0)
    updated = data.get("updated", 0)
    skipped = data.get("skipped", 0)
    console.print(
        f"[green]✓ Imported.[/green] "
        f"created [bold]{created}[/bold], "
        f"updated [bold]{updated}[/bold], "
        f"skipped [bold]{skipped}[/bold]"
    )


@app.command("push")
def push_project(
    link: str = typer.Option(..., "--link", help="Link id to push to"),
    create_missing_fields: bool = typer.Option(
        False,
        "--create-missing-fields",
        help=(
            "Auto-create the GitHub Project 'Priority' and 'Due Date' fields "
            "when they are absent before pushing."
        ),
    ),
) -> None:
    """Push TodoPro items to a linked GitHub Project (Pro)."""
    _require_remote_context()

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.post(
                f"/integrations/github/links/{link}/push/",
                json={"create_missing_fields": create_missing_fields},
            )
            try:
                return response.json()
            except Exception:
                return {}
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 404:
            console.print(f"[red]Error: link not found: {link}[/red]")
            raise typer.Exit(1) from exc
        if status == 402:
            _handle_pro_required(exc.response)
            raise typer.Exit(1) from exc
        if status == 401:
            console.print(
                "[red]Error: GitHub is not connected.[/red] "
                "Run [cyan]todopro github connect[/cyan] first."
            )
            raise typer.Exit(1) from exc
        if status == 502:
            console.print(
                "[red]Error: GitHub returned an error (upstream). "
                "Try again shortly.[/red]"
            )
            raise typer.Exit(1) from exc
        console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
        raise typer.Exit(1) from exc
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    created = data.get("created", 0)
    updated = data.get("updated", 0)
    skipped = data.get("skipped", 0)
    console.print(
        f"[green]✓ Pushed.[/green] "
        f"created [bold]{created}[/bold], "
        f"updated [bold]{updated}[/bold], "
        f"skipped [bold]{skipped}[/bold]"
    )


_SYNC_STRATEGIES = ("last-write-wins", "todopro-wins", "github-wins")


async def _sync_one_link(client, link_id: str, strategy: str) -> dict:
    """POST a sync request for a single link and return the parsed result."""
    response = await client.post(
        f"/integrations/github/links/{link_id}/sync/",
        json={"strategy": strategy},
    )
    try:
        return response.json()
    except Exception:
        return {}


def _format_sync_counts(data: dict) -> str:
    """Format the four sync counts as a single Rich-styled line."""
    pulled = data.get("pulled", 0)
    pushed = data.get("pushed", 0)
    skipped = data.get("skipped", 0)
    conflicts = data.get("conflicts", 0)
    return (
        f"pulled [bold]{pulled}[/bold], "
        f"pushed [bold]{pushed}[/bold], "
        f"skipped [bold]{skipped}[/bold], "
        f"conflicts [bold]{conflicts}[/bold]"
    )


def _handle_sync_http_error(exc: httpx.HTTPStatusError, link: str | None) -> None:
    """Map an HTTP error from a sync request to a console message + exit."""
    status = exc.response.status_code
    if status == 400:
        console.print(
            f"[red]Error: invalid strategy: "
            f"{_extract_error_message(exc.response)}[/red]"
        )
        raise typer.Exit(1) from exc
    if status == 404:
        target = f": {link}" if link else ""
        console.print(f"[red]Error: link not found{target}[/red]")
        raise typer.Exit(1) from exc
    if status == 402:
        _handle_pro_required(exc.response)
        raise typer.Exit(1) from exc
    if status == 401:
        console.print(
            "[red]Error: GitHub is not connected.[/red] "
            "Run [cyan]todopro github connect[/cyan] first."
        )
        raise typer.Exit(1) from exc
    if status == 502:
        console.print(
            "[red]Error: GitHub returned an error (upstream). Try again shortly.[/red]"
        )
        raise typer.Exit(1) from exc
    console.print(f"[red]Error: {_extract_error_message(exc.response)}[/red]")
    raise typer.Exit(1) from exc


@app.command("sync")
def sync_link(
    link: str | None = typer.Option(None, "--link", help="Link id to sync"),
    sync_all: bool = typer.Option(
        False, "--all", help="Sync all of your GitHub Project links"
    ),
    strategy: str = typer.Option(
        "last-write-wins",
        "--strategy",
        help="Conflict strategy: last-write-wins, todopro-wins, or github-wins",
    ),
) -> None:
    """Sync a linked GitHub Project bidirectionally (Pro)."""
    _require_remote_context()

    if strategy not in _SYNC_STRATEGIES:
        console.print(
            "[red]Error: --strategy must be one of: "
            f"{', '.join(_SYNC_STRATEGIES)}.[/red]"
        )
        raise typer.Exit(1)

    if bool(link) == sync_all:
        console.print(
            "[red]Error: provide exactly one of [cyan]--link[/cyan] or "
            "[cyan]--all[/cyan].[/red]"
        )
        raise typer.Exit(1)

    if link:
        _sync_single(link, strategy)
    else:
        _sync_all_links(strategy)


def _sync_single(link: str, strategy: str) -> None:
    """Sync a single link by id."""

    async def _do() -> dict:
        client = get_client()
        try:
            return await _sync_one_link(client, link, strategy)
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        _handle_sync_http_error(exc, link)
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    console.print(
        f"[green]✓ Synced.[/green] [dim](link id: {link})[/dim] "
        f"{_format_sync_counts(data)}"
    )


def _sync_all_links(strategy: str) -> None:
    """List all links then sync each one, printing per-link and total summaries."""

    async def _do() -> tuple[list[dict], dict]:
        client = get_client()
        results: list[dict] = []
        totals = {"pulled": 0, "pushed": 0, "skipped": 0, "conflicts": 0}
        try:
            list_resp = await client.get("/integrations/github/links/")
            links = list_resp.json().get("links", [])
            for lnk in links:
                link_id = str(lnk.get("id", ""))
                if not link_id:
                    continue
                data = await _sync_one_link(client, link_id, strategy)
                results.append({"id": link_id, "data": data})
                for key in totals:
                    totals[key] += data.get(key, 0)
        finally:
            await client.close()
        return results, totals

    try:
        results, totals = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        _handle_sync_http_error(exc, None)
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    if not results:
        console.print(
            "No links found. Create one with [cyan]todopro github link[/cyan]."
        )
        return

    for result in results:
        console.print(
            f"[green]✓[/green] link [cyan]{result['id']}[/cyan]: "
            f"{_format_sync_counts(result['data'])}"
        )
    console.print(
        f"[green]Total[/green] across [bold]{len(results)}[/bold] link(s): "
        f"{_format_sync_counts(totals)}"
    )


@app.command("sync-status")
def sync_status(
    link: str = typer.Option(..., "--link", help="Link id to inspect"),
) -> None:
    """Show the last sync time and stats for a linked GitHub Project (Pro)."""
    _require_remote_context()

    async def _do() -> dict:
        client = get_client()
        try:
            response = await client.get(
                f"/integrations/github/links/{link}/sync/status/"
            )
            return response.json()
        finally:
            await client.close()

    try:
        data = asyncio.run(_do())
    except httpx.HTTPStatusError as exc:
        _handle_sync_http_error(exc, link)
    except typer.Exit:
        raise
    except httpx.RequestError as exc:
        console.print(f"[red]Error: Cannot connect to TodoPro API: {exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1) from exc

    last_synced_at = data.get("last_synced_at") or "[dim]never[/dim]"
    stats = data.get("stats") or {}
    lines = [f"[bold]Last synced:[/bold] {last_synced_at}"]
    if stats:
        for key, value in stats.items():
            lines.append(f"[bold]{key}:[/bold] {value}")
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[green]Sync status (link {link})[/green]",
            border_style="green",
        )
    )
