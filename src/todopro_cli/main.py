"""Main entry point for TodoPro CLI."""

import typer

from .commands.achievements_command import (
    app as achievements_app,  # Gamification achievements
)
from .commands.add_command import app as add_command_app
from .commands.analytics import app as analytics_app  # Analytics stats/streaks/export
from .commands.apply_command import app as apply_app  # Apply saved filters
from .commands.archive_command import app as archive_app
from .commands.calendar_command import (
    app as calendar_app,  # Google Calendar integration
)
from .commands.collaborate_command import app as collaborate_app
from .commands.comment_command import app as comment_app

# from .commands.check_command import app as check_app  # DISABLED: Gamification/location - deferred
from .commands.complete_command import app as complete_command_app
from .commands.create_command import app as create_app
from .commands.data_command import app as data_app  # Working export/import commands
from .commands.delete_command import app as delete_app
from .commands.describe_command import app as describe_command_app
from .commands.edit_command import app as edit_command_app
from .commands.encryption_command import (
    app as encryption_app,
)  # E2EE commands (setup, status, recover, rotate, show-recovery)

# from .commands.export_command import app as export_app  # DISABLED: Duplicate of data.py export, references undefined factory
from .commands.focus import app as focus_app  # Focus mode with Pomodoro timer
from .commands.get_command import app as get_app
from .commands.github_command import app as github_app  # GitHub Issues integration
from .commands.goals import app as goals_app  # Focus goals management
from .commands.link_command import app as link_app  # Task dependency management

# from .commands.import_command import app as import_app  # DISABLED: Duplicate of data.py import, references undefined factory
from .commands.list_command import app as list_app
from .commands.login_command import app as login_command_app
from .commands.logout_command import app as logout_command_app
from .commands.ramble_command import app as ramble_app

# from .commands.pull_command import app as pull_app  # DISABLED: Duplicate of sync.py pull, references undefined factory
# from .commands.purge_command import app as purge_app  # DISABLED: References undefined factory
# from .commands.push_command import app as push_app  # DISABLED: Duplicate of sync.py push, references undefined factory
# from .commands.recover_command import app as recover_app  # DISABLED: Replaced by encryption.py
from .commands.rename_command import app as rename_app
from .commands.reopen_command import app as reopen_app
from .commands.reschedule_command import app as reschedule_command_app
from .commands.reset_command import app as reset_app  # Reset config and goals
from .commands.resume_command import app as resume_app  # Resume focus sessions

# from .commands.rotate_command import app as rotate_app  # DISABLED: Replaced by encryption.py
from .commands.set_command import app as set_app  # Set config and goals

# from .commands.setup_command import app as setup_app  # DISABLED: Replaced by encryption.py
from .commands.signup_command import app as signup_app
from .commands.skip_command import app as skip_app  # Skip recurring task instances
from .commands.start_command import app as start_app  # Start focus sessions
from .commands.stats import app as stats_app  # Focus stats (today/week/month/streak)
from .commands.status_command import app as status_app  # Focus session status
from .commands.stop_command import app as stop_app  # Stop focus sessions
from .commands.sync import app as sync_app  # Working sync commands (push, pull, status)
from .commands.task_command import app as task_command_app
from .commands.template_command import app as template_app  # Task templates

# from .commands.sync_status_command import app as sync_status_app  # DISABLED: Duplicate of sync.py status, references undefined factory
from .commands.today_command import app as today_command_app
from .commands.unarchive_command import app as unarchive_app
from .commands.update_command import app as update_command_app
from .commands.update_resource_command import app as update_resource_app
from .commands.use_command import app as use_app
from .commands.version_command import app as version_command_app
from .commands.view_command import app as view_command_app
from .utils.typer_helpers import SuggestingGroup

# Create main app with custom group class
app = typer.Typer(
    name="todopro",
    cls=SuggestingGroup,
    help="A professional CLI for TodoPro task management",
    no_args_is_help=True,
)

# Add top-level commands
app.add_typer(version_command_app, name="", help="Show version information")
app.add_typer(update_command_app, name="", help="Update TodoPro CLI to latest version")
app.add_typer(logout_command_app, name="", help="Logout from TodoPro")
app.add_typer(login_command_app, name="", help="Login to TodoPro")
app.add_typer(complete_command_app, name="", help="Complete a task by ID or suffix")
app.add_typer(reschedule_command_app, name="", help="Reschedule tasks to today")
app.add_typer(add_command_app, name="", help="Quick add a task using natural language")
app.add_typer(edit_command_app, name="", help="Edit a task interactively or via flags")
app.add_typer(view_command_app, name="", help="View project in interactive board mode")
app.add_typer(describe_command_app, name="", help="Describe a resource (e.g., project)")
app.add_typer(today_command_app, name="", help="View today's tasks in interactive mode")

# Add sub-level commands
app.add_typer(
    list_app, name="list", help="List resources (tasks, projects, labels, etc.)"
)
app.add_typer(task_command_app, name="", help="Get task details by ID or suffix")
app.add_typer(get_app, name="get", help="Get resource details")
app.add_typer(create_app, name="create", help="Create new resources")
app.add_typer(update_resource_app, name="update", help="Update existing resources")
app.add_typer(delete_app, name="delete", help="Delete resources")
app.add_typer(
    stats_app, name="show", help="Show focus stats (today, week, month, streak)"
)
app.add_typer(use_app, name="use", help="Switch/use contexts")
app.add_typer(set_app, name="set", help="Set configuration and goals")
app.add_typer(start_app, name="start", help="Start focus sessions")
app.add_typer(stop_app, name="stop", help="Stop focus sessions")
app.add_typer(resume_app, name="resume", help="Resume paused focus sessions")
# app.add_typer(export_app, name="export", help="Export data and analytics")  # DISABLED: Duplicate + broken factory
# app.add_typer(import_app, name="import", help="Import data")  # DISABLED: Duplicate + broken factory
app.add_typer(archive_app, name="archive", help="Archive projects")
app.add_typer(unarchive_app, name="unarchive", help="Unarchive projects")
app.add_typer(reopen_app, name="", help="Reopen completed tasks")
app.add_typer(rename_app, name="rename", help="Rename contexts")
# app.add_typer(check_app, name="check", help="Check achievements and location")  # DISABLED: Gamification/location - deferred
app.add_typer(reset_app, name="reset", help="Reset configuration and goals")
# app.add_typer(purge_app, name="purge", help="Delete all data")  # DISABLED: Broken factory
# app.add_typer(pull_app, name="pull", help="Pull data from remote")  # DISABLED: Duplicate + broken factory (use sync.py)
# app.add_typer(push_app, name="push", help="Push data to remote")  # DISABLED: Duplicate + broken factory (use sync.py)
# app.add_typer(sync_status_app, name="sync-status", help="Show sync status")  # DISABLED: Duplicate + broken factory (use sync.py)
app.add_typer(
    sync_app, name="sync", help="Sync data between local and remote"
)  # Working sync commands
app.add_typer(
    data_app, name="data", help="Export/import data"
)  # Working export/import commands
app.add_typer(
    encryption_app, name="encryption", help="Manage end-to-end encryption"
)  # E2EE commands
# app.add_typer(setup_app, name="setup", help="Setup encryption")  # DISABLED: Replaced by encryption.py
app.add_typer(status_app, name="status", help="Show status (focus session)")
# app.add_typer(recover_app, name="recover", help="Recover encryption")  # DISABLED: Replaced by encryption.py
# app.add_typer(rotate_app, name="rotate", help="Rotate encryption key")  # DISABLED: Replaced by encryption.py
app.add_typer(signup_app, name="signup", help="Register new user")
app.add_typer(focus_app, name="focus", help="Focus mode with Pomodoro timer")
app.add_typer(
    analytics_app, name="analytics", help="Analytics stats, streaks, and export"
)
app.add_typer(goals_app, name="goals", help="Focus goals and progress tracking")
app.add_typer(
    achievements_app, name="achievements", help="Focus achievements and gamification"
)
app.add_typer(skip_app, name="", help="Skip the current instance of a recurring task")
app.add_typer(
    apply_app, name="apply", help="Apply saved filters to list matching tasks"
)
app.add_typer(template_app, name="template", help="Manage task templates")
app.add_typer(link_app, name="link", help="Manage task dependencies")
app.add_typer(
    collaborate_app, name="share", help="Manage project collaboration and sharing"
)
app.add_typer(comment_app, name="comment", help="Manage task comments")
app.add_typer(
    github_app, name="github", help="GitHub integration - import issues as tasks"
)
app.add_typer(calendar_app, name="calendar", help="Google Calendar integration")
app.add_typer(ramble_app, name="ramble", help="Ramble — voice-to-tasks")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
