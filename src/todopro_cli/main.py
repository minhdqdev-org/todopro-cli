"""Main entry point for TodoPro CLI."""

import typer

# ── Convenience task commands (kept at top-level for UX) ──────────────────────
from .commands.add_command import app as add_command_app
from .commands.complete_command import app as complete_command_app
from .commands.edit_command import app as edit_command_app
from .commands.ramble_command import app as ramble_app
from .commands.reopen_command import app as reopen_app
from .commands.reschedule_command import app as reschedule_command_app
from .commands.today_command import app as today_command_app

# ── General commands ──────────────────────────────────────────────────────────
from .commands.update_command import app as update_command_app
from .commands.version_command import app as version_command_app

# ── Resource command groups ───────────────────────────────────────────────────
from .commands.achievements_command import app as achievements_app
from .commands.analytics import app as analytics_app
from .commands.auth_app import app as auth_app
from .commands.calendar_command import app as calendar_app
from .commands.config_command import app as config_app
from .commands.context import app as context_app
from .commands.data_command import app as data_app
from .commands.encryption_command import app as encryption_app
from .commands.focus import app as focus_app
from .commands.github_command import app as github_app
from .commands.goals import app as goals_app
from .commands.labels import app as labels_app
from .commands.projects import app as projects_app
from .commands.stats import app as stats_app
from .commands.sync import app as sync_app
from .commands.tasks_command import app as tasks_app
from .commands.template_command import app as template_app
from .utils.typer_helpers import SuggestingGroup

# Create main app
app = typer.Typer(
    name="todopro",
    cls=SuggestingGroup,
    help="A professional CLI for TodoPro task management",
    no_args_is_help=True,
)

# ── General commands ──────────────────────────────────────────────────────────
app.add_typer(version_command_app, name="", help="Show version information")
app.add_typer(update_command_app, name="", help="Update TodoPro CLI to latest version")

# ── Convenience task commands ─────────────────────────────────────────────────
app.add_typer(add_command_app, name="", help="Quick-add a task using natural language")
app.add_typer(complete_command_app, name="", help="Mark task(s) as completed")
app.add_typer(reschedule_command_app, name="", help="Reschedule tasks to today")
app.add_typer(edit_command_app, name="", help="Edit a task interactively or via flags")
app.add_typer(today_command_app, name="", help="View today's tasks in interactive mode")
app.add_typer(reopen_app, name="", help="Reopen a completed task")
app.add_typer(ramble_app, name="ramble", help="Ramble — voice-to-tasks")

# ── Resource groups ───────────────────────────────────────────────────────────
app.add_typer(auth_app, name="auth", help="Authentication — login, logout, signup")
app.add_typer(tasks_app, name="task", help="Task operations — list, get, create, …")
app.add_typer(projects_app, name="project", help="Project operations — list, create, …")
app.add_typer(labels_app, name="label", help="Label operations — list, create, …")
app.add_typer(context_app, name="context", help="Context operations — list, use, …")
app.add_typer(config_app, name="config", help="Configuration — view, get, set, reset")
app.add_typer(focus_app, name="focus", help="Focus mode — Pomodoro timer")
app.add_typer(goals_app, name="goals", help="Focus goals and progress tracking")
app.add_typer(stats_app, name="stats", help="Focus stats — today, week, month, …")
app.add_typer(analytics_app, name="analytics", help="Analytics — stats, streaks, export")
app.add_typer(achievements_app, name="achievements", help="Achievements and gamification")
app.add_typer(sync_app, name="sync", help="Sync — push, pull, status")
app.add_typer(data_app, name="data", help="Data — export and import")
app.add_typer(encryption_app, name="encryption", help="End-to-end encryption")
app.add_typer(template_app, name="template", help="Task templates")
app.add_typer(github_app, name="github", help="GitHub Issues integration")
app.add_typer(calendar_app, name="calendar", help="Google Calendar integration")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()

