"""Show command - Show information (stats, goals, analytics, etc.)."""

import typer

from todopro_cli.utils.typer_helpers import SuggestingGroup
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.ui.formatters import format_output

from .decorators import command_wrapper

app = typer.Typer(cls=SuggestingGroup, help="Show information")
console = get_console()


@app.command("stats-today")
@command_wrapper
async def show_stats_today(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show today's focus statistics."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    stats = await service.get_today_stats()
    format_output(stats.model_dump(), output)


@app.command("stats-week")
@command_wrapper
async def show_stats_week(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show this week's focus statistics."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    stats = await service.get_week_stats()
    format_output(stats.model_dump(), output)


@app.command("stats-month")
@command_wrapper
async def show_stats_month(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show this month's focus statistics."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    stats = await service.get_month_stats()
    format_output(stats.model_dump(), output)


@app.command("streak")
@command_wrapper
async def show_streak(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show current focus streak."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    streak = await service.get_streak()
    format_output({"streak": streak}, output)


@app.command("score")
@command_wrapper
async def show_score(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show productivity score."""
    from todopro_cli.services.analytics_service import AnalyticsService

    storage_strategy_context = get_storage_strategy_context()
    task_repo = strategy_context.task_repository
    service = AnalyticsService(task_repo)

    score = await service.get_score()
    format_output({"score": score}, output)


@app.command("goals")
@command_wrapper
async def show_goals(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show focus goals."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    goals = await service.get_goals()
    format_output(goals.model_dump(), output)


@app.command("analytics")
@command_wrapper
async def show_analytics(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show productivity analytics."""
    from todopro_cli.services.analytics_service import AnalyticsService

    storage_strategy_context = get_storage_strategy_context()
    task_repo = strategy_context.task_repository
    service = AnalyticsService(task_repo)

    analytics = await service.get_analytics()
    format_output(analytics.model_dump(), output)


@app.command("streaks")
@command_wrapper
async def show_streaks(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show productivity streaks."""
    from todopro_cli.services.analytics_service import AnalyticsService

    storage_strategy_context = get_storage_strategy_context()
    task_repo = strategy_context.task_repository
    service = AnalyticsService(task_repo)

    streaks = await service.get_streaks()
    format_output(streaks.model_dump(), output)


@app.command("heatmap")
@command_wrapper
async def show_heatmap(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show activity heatmap."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    heatmap = await service.get_heatmap()
    format_output(heatmap, output)


@app.command("quality")
@command_wrapper
async def show_quality(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show focus session quality metrics."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    quality = await service.get_quality_metrics()
    format_output(quality.model_dump(), output)


@app.command("recovery-key")
@command_wrapper
async def show_recovery_key(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show encryption recovery key."""
    from todopro_cli.services.encryption_service import EncryptionService

    service = EncryptionService()
    recovery_key = service.show_recovery_key()
    format_output({"recovery_key": recovery_key}, output)


@app.command("config")
@command_wrapper
async def show_config(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show current configuration."""
    from todopro_cli.services.config_service import get_config_service

    config_service = get_config_service()
    config = config_service.get_all()
    format_output(config, output)


@app.command("timer-history")
@command_wrapper
async def show_timer_history(
    limit: int = typer.Option(10, "--limit", help="Number of sessions to show"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show timer session history."""
    from todopro_cli.services.timer_service import TimerService

    storage_strategy_context = get_storage_strategy_context()
    timer_repo = factory.get_timer_repository()
    service = TimerService(timer_repo)

    history = await service.get_history(limit=limit)
    format_output({"sessions": [s.model_dump() for s in history]}, output)


@app.command("timer-stats")
@command_wrapper
async def show_timer_stats(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show timer statistics."""
    from todopro_cli.services.timer_service import TimerService

    storage_strategy_context = get_storage_strategy_context()
    timer_repo = factory.get_timer_repository()
    service = TimerService(timer_repo)

    stats = await service.get_stats()
    format_output(stats.model_dump(), output)


@app.command("project-stats")
@command_wrapper
async def show_project_stats(
    project_id: str = typer.Argument(..., help="Project ID"),
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show statistics for a specific project."""
    from todopro_cli.services.focus_service import FocusService

    storage_strategy_context = get_storage_strategy_context()
    focus_repo = factory.get_focus_session_repository()
    service = FocusService(focus_repo)

    stats = await service.get_project_stats(project_id)
    format_output(stats.model_dump(), output)


@app.command("achievement-stats")
@command_wrapper
async def show_achievement_stats(
    output: str = typer.Option("table", "--output", "-o", help="Output format"),
) -> None:
    """Show achievement statistics."""
    from todopro_cli.services.achievement_service import AchievementService

    storage_strategy_context = get_storage_strategy_context()
    repo = factory.get_achievement_repository()
    service = AchievementService(repo)

    stats = await service.get_stats()
    format_output(stats.model_dump(), output)
