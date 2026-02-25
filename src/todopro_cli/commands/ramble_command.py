"""Ramble — Voice-to-tasks command."""

import asyncio

import httpx
import typer
from rich.table import Table

from todopro_cli.services.audio.recorder import check_dependencies
from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console

app = typer.Typer(
    cls=SuggestingGroup, help="Ramble — voice-to-tasks", invoke_without_command=True
)
console = get_console()


def _get_base_url() -> str:
    from todopro_cli.utils.update_checker import get_backend_url

    base = get_backend_url().rstrip("/")
    return f"{base}/api/ramble"


def _get_auth_headers() -> dict:
    from todopro_cli.services.config_service import get_config_service

    config_manager = get_config_service()
    headers = {"Accept": "application/json"}
    current_context = config_manager.get_current_context()
    if current_context:
        credentials = config_manager.load_context_credentials(current_context.name)
    else:
        credentials = None
    if not credentials:
        credentials = config_manager.load_credentials()
    if credentials and "token" in credentials:
        headers["Authorization"] = f"Bearer {credentials['token']}"
    return headers


async def _api_get(path: str) -> dict:
    base = _get_base_url()
    headers = _get_auth_headers()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base}{path}", headers=headers, timeout=30)
        return (
            resp.json()
            if resp.status_code < 500
            else {"error": f"Server error {resp.status_code}"}
        )


async def _api_post(path: str, data: dict | None = None) -> dict:
    base = _get_base_url()
    headers = {**_get_auth_headers(), "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}{path}", json=data or {}, headers=headers, timeout=60
        )
        return (
            resp.json()
            if resp.status_code < 500
            else {"error": f"Server error {resp.status_code}"}
        )


async def _api_put(path: str, data: dict | None = None) -> dict:
    base = _get_base_url()
    headers = {**_get_auth_headers(), "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{base}{path}", json=data or {}, headers=headers, timeout=30
        )
        return (
            resp.json()
            if resp.status_code < 500
            else {"error": f"Server error {resp.status_code}"}
        )


@app.callback(invoke_without_command=True)
def ramble(
    ctx: typer.Context,
    duration: int = typer.Option(
        30, "--duration", "-d", help="Recording duration in seconds"
    ),
    stt: str = typer.Option(
        "whisper", "--stt", help="STT provider (whisper/gemini/deepgram)"
    ),
    llm: str = typer.Option("gemini", "--llm", help="LLM provider (gemini/openai)"),
    project: str | None = typer.Option(
        None, "--project", help="Default project for tasks"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show parsed tasks without creating"
    ),
    language: str = typer.Option(
        "auto", "--language", "-l", help="Language code (auto/en/vi/...)"
    ),
    stream: bool = typer.Option(
        False, "--stream", help="Streaming mode (premium, cloud context required)"
    ),
    text: str | None = typer.Option(
        None,
        "--text",
        help="Use text transcript instead of microphone (no mic required)",
    ),
) -> None:
    """Start a Ramble voice-to-tasks session."""
    if ctx.invoked_subcommand is not None:
        return

    if stream:
        console.print(
            "[yellow]⚠ Streaming mode requires cloud context and premium plan.[/yellow]"
        )

    # If --text provided, skip audio capture and use text directly
    if text:
        _process_text_ramble(text, stt, llm, project, dry_run, language)
        return

    # Check audio dependencies
    ok, msg = check_dependencies()
    if not ok:
        console.print("[yellow]⚠ Audio capture requires additional packages.[/yellow]")
        console.print(f"  {msg}")
        console.print()
        console.print(
            "[dim]Tip: Use --text 'your transcript here' to skip mic and use text instead.[/dim]"
        )
        raise typer.Exit(1)

    # Record audio
    console.print(
        f"[bold green]🎙️ Ramble — Recording ({duration}s, batch mode)[/bold green]"
    )
    console.print(f"[dim]STT: {stt} | LLM: {llm}[/dim]")
    console.print("[dim]Speak naturally. Press Ctrl+C to stop early.[/dim]")
    console.print()

    try:
        from todopro_cli.services.audio.recorder import record_audio

        audio_data = record_audio(duration_seconds=duration)
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording stopped.[/yellow]")
        audio_data = b""
    except Exception as exc:
        console.print(f"[red]Error recording audio: {exc}[/red]")
        raise typer.Exit(1)

    if not audio_data:
        console.print("[yellow]No audio recorded.[/yellow]")
        raise typer.Exit(1)

    # Upload to backend for processing
    _process_audio_ramble(audio_data, stt, llm, project, dry_run, language)


def _process_text_ramble(
    text: str, stt: str, llm: str, project: str | None, dry_run: bool, language: str
) -> None:
    """Process text transcript directly (no mic)."""

    async def _do():
        console.print("[bold]Processing text transcript...[/bold]")
        result = await _api_post(
            "/batch/",
            {
                "transcript": text,
                "stt_provider": stt,
                "llm_provider": llm,
                "language": language,
                "dry_run": str(dry_run).lower(),
                "project": project or "",
            },
        )
        _display_ramble_result(result, dry_run)

    try:
        asyncio.run(_do())
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def _process_audio_ramble(
    audio_data: bytes,
    stt: str,
    llm: str,
    project: str | None,
    dry_run: bool,
    language: str,
) -> None:
    """Upload audio to backend and display results."""
    import httpx

    console.print("[dim]Transcribing...[/dim]")

    base = _get_base_url()
    headers = _get_auth_headers()

    try:
        with httpx.Client() as client:
            files = {"audio": ("recording.wav", audio_data, "audio/wav")}
            data = {
                "stt_provider": stt,
                "llm_provider": llm,
                "language": language,
                "dry_run": str(dry_run).lower(),
            }
            if project:
                data["project"] = project

            resp = client.post(
                f"{base}/batch/", files=files, data=data, headers=headers, timeout=120
            )
            result = (
                resp.json()
                if resp.status_code < 500
                else {"error": f"Server error {resp.status_code}"}
            )

        _display_ramble_result(result, dry_run)
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


def _display_ramble_result(result: dict, dry_run: bool) -> None:
    """Display the Ramble processing result."""
    if result.get("error"):
        console.print(f"[red]Error: {result['error']}[/red]")
        raise typer.Exit(1)

    transcript = result.get("transcript", "")
    if transcript:
        console.print(
            f"[dim]Transcript: {transcript[:200]}{'...' if len(transcript) > 200 else ''}[/dim]"
        )
        console.print()

    tasks = result.get("task_results", [])
    created = result.get("tasks_created", 0)
    updated = result.get("tasks_updated", 0)
    deleted = result.get("tasks_deleted", 0)

    if dry_run:
        console.print(f"[yellow]Dry run — would create {created} tasks[/yellow]")
    else:
        for task_result in tasks:
            if task_result.get("success"):
                console.print(
                    f"  [green]✓ Created:[/green] {task_result.get('title', '')}"
                )
        console.print()
        console.print(
            f"[green]✓ {created} tasks created, {updated} updated, {deleted} deleted[/green]"
        )

    errors = result.get("errors", [])
    for err in errors:
        console.print(f"  [red]⚠ {err}[/red]")


@app.command()
def history() -> None:
    """Show Ramble session history."""

    async def _do():
        data = await _api_get("/sessions/")
        if data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
            raise typer.Exit(1)
        sessions = data.get("sessions", [])
        if not sessions:
            console.print("No Ramble sessions found.")
            return
        table = Table(title="Ramble Session History")
        table.add_column("ID", style="cyan", no_wrap=True, max_width=8)
        table.add_column("Started", style="white")
        table.add_column("Duration", style="yellow")
        table.add_column("STT")
        table.add_column("Created", style="green")
        table.add_column("Updated", style="blue")
        table.add_column("Source")
        for s in sessions:
            sid = str(s.get("id", ""))[:8]
            started = str(s.get("started_at", ""))[:19]
            dur = (
                f"{s.get('duration_seconds', 0):.1f}s"
                if s.get("duration_seconds")
                else "-"
            )
            table.add_row(
                sid,
                started,
                dur,
                s.get("stt_provider", ""),
                str(s.get("tasks_created", 0)),
                str(s.get("tasks_updated", 0)),
                s.get("source", ""),
            )
        console.print(table)

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command("config")
def ramble_config(
    stt: str | None = typer.Option(None, "--stt", help="Default STT provider"),
    llm: str | None = typer.Option(None, "--llm", help="Default LLM provider"),
    silence_timeout: int | None = typer.Option(
        None, "--silence-timeout", help="Silence timeout (seconds)"
    ),
    default_project: str | None = typer.Option(
        None, "--default-project", help="Default project name/ID"
    ),
    language: str | None = typer.Option(None, "--language", help="Default language"),
    show: bool = typer.Option(False, "--show", help="Show current config"),
) -> None:
    """Show or update Ramble configuration."""

    async def _do():
        if show or (
            not stt
            and not llm
            and not silence_timeout
            and not default_project
            and not language
        ):
            data = await _api_get("/config/")
            if data.get("error"):
                console.print(f"[red]Error: {data['error']}[/red]")
                raise typer.Exit(1)
            console.print("[bold]Ramble Configuration:[/bold]")
            for key, value in data.items():
                if key != "error":
                    console.print(f"  {key}: {value}")
            return

        updates: dict = {}
        if stt:
            updates["default_stt_provider"] = stt
        if llm:
            updates["default_llm_provider"] = llm
        if silence_timeout is not None:
            updates["silence_timeout_seconds"] = silence_timeout
        if default_project:
            updates["default_project_id"] = default_project
        if language:
            updates["default_language"] = language

        result = await _api_put("/config/", updates)
        if result.get("error"):
            console.print(f"[red]Error: {result['error']}[/red]")
            raise typer.Exit(1)
        console.print("[green]✓ Ramble configuration saved[/green]")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)


@app.command()
def usage() -> None:
    """Show Ramble usage stats for today."""

    async def _do():
        data = await _api_get("/usage/")
        if data.get("error"):
            console.print(f"[red]Error: {data['error']}[/red]")
            raise typer.Exit(1)
        today = data.get("sessions_today", 0)
        limit = data.get("sessions_limit", 5)
        remaining = data.get("sessions_remaining", 0)
        console.print(f"Sessions today:     {today} / {limit}")
        console.print(f"Sessions remaining: {remaining}")
        console.print(f"Max duration:       {data.get('max_session_duration', 30)}s")

    try:
        asyncio.run(_do())
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/red]")
        raise typer.Exit(1)
