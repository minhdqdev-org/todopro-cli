"""Comprehensive unit tests for todopro_cli.commands.focus.

Covers all commands: start, resume, stop, status, cycle, templates, template.
Goal: maximise line/branch coverage across all paths.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.focus import app
from todopro_cli.models import Task
from todopro_cli.models.config_models import AppConfig, Context
from todopro_cli.models.focus.state import SessionState

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_ansi(text: str) -> str:
    ansi = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi.sub("", text)


def _make_task(task_id="task-abc12345", content="Test Task", priority=2):
    now = datetime(2024, 1, 1, 12, 0, 0)
    return Task(
        id=task_id,
        content=content,
        priority=priority,
        is_completed=False,
        labels=[],
        created_at=now,
        updated_at=now,
    )


def _make_session(
    task_id="task-abc12345",
    task_title="Test Task",
    status="active",
    duration=25,
    session_type="focus",
    pause_time=None,
) -> SessionState:
    now = datetime.now(tz=timezone.utc)
    end = now + timedelta(minutes=duration)
    return SessionState(
        session_id="sess-0001",
        task_id=task_id,
        task_title=task_title,
        start_time=now.isoformat(),
        end_time=end.isoformat(),
        duration_minutes=duration,
        status=status,
        session_type=session_type,
        pause_time=pause_time,
    )


# ---------------------------------------------------------------------------
# Shared patch helpers
# ---------------------------------------------------------------------------

def _patch_task_service(task=None, tasks=None):
    """Return a context manager that patches get_task_service."""
    mock_svc = MagicMock()
    mock_svc.get_task = AsyncMock(return_value=task or _make_task())
    mock_svc.complete_task = AsyncMock(return_value=None)
    mock_svc.list_tasks = AsyncMock(return_value=tasks or [])
    return patch("todopro_cli.commands.focus.get_task_service", return_value=mock_svc), mock_svc


def _patch_config_service(context_type="local"):
    ctx = Context(name="default", type=context_type, source="/tmp/test.db")
    mock_cfg = MagicMock()
    mock_cfg.config.current_context_name = "default"
    mock_cfg.get_current_context.return_value = ctx
    return patch("todopro_cli.commands.focus.get_config_service", return_value=mock_cfg), mock_cfg


def _patch_state_manager(session=None, load_return=None):
    mock_sm = MagicMock()
    mock_sm.load.return_value = load_return
    mock_sm.save = MagicMock()
    mock_sm.delete = MagicMock()
    return patch("todopro_cli.commands.focus.SessionStateManager", return_value=mock_sm), mock_sm


def _patch_timer_display(result="completed"):
    mock_display = MagicMock()
    mock_display.run_timer.return_value = result
    return patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display), mock_display


def _patch_template_manager(template_data=None, templates_list=None):
    mock_tm = MagicMock()
    mock_tm.get_template.return_value = template_data
    mock_tm.list_templates.return_value = templates_list or [
        ("standard", {"duration": 25, "breaks_enabled": True, "description": "Classic Pomodoro"}),
        ("deep_work", {"duration": 90, "breaks_enabled": False, "description": "Deep focus"}),
    ]
    mock_tm.create_template = MagicMock()
    mock_tm.delete_template = MagicMock(return_value=True)
    return patch("todopro_cli.commands.focus._get_template_manager", return_value=mock_tm), mock_tm


def _patch_suggestion_engine(suggestions=None):
    mock_engine = MagicMock()
    mock_engine.suggest_tasks.return_value = suggestions or []
    return patch("todopro_cli.commands.focus._get_suggestion_engine", return_value=mock_engine), mock_engine


# ===========================================================================
# Tests: start_focus
# ===========================================================================

class TestStartFocus:
    """Tests for the `focus start` command."""

    def test_help(self):
        result = runner.invoke(app, ["start", "--help"])
        assert result.exit_code == 0
        assert "Start a focus session" in result.stdout

    def test_missing_task_id_exits_nonzero(self):
        result = runner.invoke(app, ["start"])
        assert result.exit_code != 0

    def test_start_success_no_template(self):
        """Happy path: start a focus session, timer completes, user says task not done."""
        p_ts, mock_svc = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)
        p_td, mock_td = _patch_timer_display("completed")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch("todopro_cli.commands.focus.HistoryLogger") as mock_hist:
                    result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        assert "Focus session started" in strip_ansi(result.stdout)
        mock_sm.save.assert_called()
        mock_sm.delete.assert_called_once()

    def test_start_success_user_completes_task(self):
        """Timer completes, user confirms task is done."""
        p_ts, mock_svc = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=True):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        mock_svc.complete_task.assert_awaited_once()

    def test_start_complete_task_api_error(self):
        """Timer completes, user confirms, but complete_task raises — graceful warning."""
        p_ts, mock_svc = _patch_task_service()
        mock_svc.complete_task = AsyncMock(side_effect=Exception("API error"))
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=True):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        assert "Warning" in strip_ansi(result.stdout)

    def test_start_history_log_error(self):
        """Timer completes, history log raises — should print Note and continue."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch(
                    "todopro_cli.commands.focus.HistoryLogger",
                    side_effect=Exception("disk error"),
                ):
                    result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        assert "Could not log to history" in strip_ansi(result.stdout)

    def test_start_timer_stopped(self):
        """Timer is stopped by user — show stopped message."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("stopped")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.HistoryLogger"):
                with patch("todopro_cli.commands.focus.show_stopped_message") as mock_stop_msg:
                    result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        mock_stop_msg.assert_called_once()
        mock_sm.delete.assert_called_once()

    def test_start_timer_stopped_history_error(self):
        """Timer stopped, history log raises — graceful note."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("stopped")

        with p_ts, p_cfg, p_sm, p_td:
            with patch(
                "todopro_cli.commands.focus.HistoryLogger",
                side_effect=Exception("err"),
            ):
                result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        assert "Could not log to history" in strip_ansi(result.stdout)

    def test_start_timer_interrupted(self):
        """Timer interrupted — state saved, resume message shown."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("interrupted")

        with p_ts, p_cfg, p_sm, p_td:
            result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        assert "interrupted" in strip_ansi(result.stdout).lower()
        mock_sm.delete.assert_not_called()

    def test_start_existing_active_session(self):
        """Existing active session should block starting a new one."""
        existing = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=existing)
        p_cfg, _ = _patch_config_service()

        with p_sm, p_cfg:
            result = runner.invoke(app, ["start", "new-task-id"])

        assert result.exit_code == 1
        assert "already active" in strip_ansi(result.stdout)

    def test_start_existing_paused_session(self):
        """Existing paused session should also block."""
        existing = _make_session(status="paused")
        p_sm, _ = _patch_state_manager(load_return=existing)
        p_cfg, _ = _patch_config_service()

        with p_sm, p_cfg:
            result = runner.invoke(app, ["start", "new-task-id"])

        assert result.exit_code == 1

    def test_start_task_fetch_error(self):
        """Task fetch error exits 1 with error message."""
        p_ts, mock_svc = _patch_task_service()
        mock_svc.get_task = AsyncMock(side_effect=Exception("not found"))
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)

        with p_ts, p_cfg, p_sm:
            result = runner.invoke(app, ["start", "bad-id"])

        assert result.exit_code == 1
        assert "Error fetching task" in strip_ansi(result.stdout)

    def test_start_with_valid_template(self):
        """--template flag with an existing template applies its duration."""
        template_data = {"duration": 90, "breaks_enabled": False, "description": "Deep focus"}
        p_tm, mock_tm = _patch_template_manager(template_data=template_data)
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        with p_tm, p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["start", "task-abc12345", "--template", "deep_work"])

        assert result.exit_code == 0
        assert "deep_work" in strip_ansi(result.stdout)
        mock_tm.get_template.assert_called_once_with("deep_work")

    def test_start_with_invalid_template(self):
        """--template flag with a missing template falls back to default duration."""
        p_tm, mock_tm = _patch_template_manager(template_data=None)
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        with p_tm, p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["start", "task-abc12345", "--template", "nonexistent"])

        assert result.exit_code == 0
        assert "not found" in strip_ansi(result.stdout)

    def test_start_with_custom_duration(self):
        """--duration flag should override default 25 minutes."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["start", "task-abc12345", "--duration", "45"])

        assert result.exit_code == 0
        assert "45 minutes" in strip_ansi(result.stdout)


# ===========================================================================
# Tests: resume_focus
# ===========================================================================

class TestResumeFocus:
    """Tests for `focus resume` command."""

    def test_no_active_session(self):
        """No session found exits 0."""
        p_sm, _ = _patch_state_manager(load_return=None)
        with p_sm:
            result = runner.invoke(app, ["resume"])
        assert result.exit_code == 0
        assert "No active focus session" in strip_ansi(result.stdout)

    def test_session_expired_user_declines_completion(self):
        """Expired session — user declines task completion."""
        past_end = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).isoformat()
        session = _make_session(status="active")
        session.end_time = past_end  # force expired

        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()

        with p_sm, p_cfg:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "expired" in strip_ansi(result.stdout).lower()
        mock_sm.delete.assert_called_once()

    def test_session_expired_user_confirms_completion(self):
        """Expired session — user confirms task completion."""
        past_end = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).isoformat()
        session = _make_session(status="active")
        session.end_time = past_end

        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_ts, mock_svc = _patch_task_service()
        p_cfg, _ = _patch_config_service()

        with p_sm, p_ts, p_cfg:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=True):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        mock_svc.complete_task.assert_awaited_once()

    def test_session_expired_complete_task_error(self):
        """Expired session — complete_task raises, silently ignored."""
        past_end = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).isoformat()
        session = _make_session(status="active")
        session.end_time = past_end

        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_ts, mock_svc = _patch_task_service()
        mock_svc.complete_task = AsyncMock(side_effect=Exception("err"))
        p_cfg, _ = _patch_config_service()

        with p_sm, p_ts, p_cfg:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=True):
                result = runner.invoke(app, ["resume"])

        # Should still exit cleanly (error is silently swallowed)
        assert result.exit_code == 0

    def test_resume_paused_session_timer_completes_no_task(self):
        """Paused session: resume, timer completes, user says task not done."""
        pause_time = (datetime.now(tz=timezone.utc) - timedelta(minutes=2)).isoformat()
        session = _make_session(status="paused", pause_time=pause_time)

        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("completed")

        with p_sm, p_cfg, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "Resuming focus session" in strip_ansi(result.stdout)
        mock_sm.delete.assert_called_once()

    def test_resume_paused_session_timer_completes_with_task(self):
        """Paused session: timer completes, user confirms task done."""
        pause_time = (datetime.now(tz=timezone.utc) - timedelta(minutes=2)).isoformat()
        session = _make_session(status="paused", pause_time=pause_time)

        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("completed")
        p_ts, mock_svc = _patch_task_service()

        with p_sm, p_cfg, p_td, p_ts:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=True):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        mock_svc.complete_task.assert_awaited_once()

    def test_resume_history_log_error(self):
        """Resume timer completes, history log raises — note printed."""
        session = _make_session(status="active")

        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("completed")

        with p_sm, p_cfg, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch(
                    "todopro_cli.commands.focus.HistoryLogger",
                    side_effect=Exception("disk error"),
                ):
                    result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "Could not log to history" in strip_ansi(result.stdout)

    def test_resume_timer_stopped(self):
        """Resumed timer is stopped — show stopped message."""
        session = _make_session(status="active")
        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("stopped")

        with p_sm, p_cfg, p_td:
            with patch("todopro_cli.commands.focus.HistoryLogger"):
                with patch("todopro_cli.commands.focus.show_stopped_message") as mock_msg:
                    result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        mock_msg.assert_called_once()
        mock_sm.delete.assert_called_once()

    def test_resume_timer_stopped_history_error(self):
        """Resume, timer stopped, history log fails."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("stopped")

        with p_sm, p_cfg, p_td:
            with patch(
                "todopro_cli.commands.focus.HistoryLogger",
                side_effect=Exception("err"),
            ):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "Could not log to history" in strip_ansi(result.stdout)

    def test_resume_timer_interrupted(self):
        """Resumed timer gets interrupted — paused state saved."""
        session = _make_session(status="active")
        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("interrupted")

        with p_sm, p_cfg, p_td:
            result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "paused" in strip_ansi(result.stdout).lower()
        mock_sm.delete.assert_not_called()

    def test_resume_active_session_no_pause_time(self):
        """Active session without pause_time skips pause calc."""
        session = _make_session(status="active", pause_time=None)
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_td, _ = _patch_timer_display("completed")

        with p_sm, p_cfg, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=False):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0


# ===========================================================================
# Tests: stop_focus
# ===========================================================================

class TestStopFocus:
    """Tests for `focus stop` command."""

    def test_no_active_session(self):
        """No session found exits 0."""
        p_sm, _ = _patch_state_manager(load_return=None)
        with p_sm:
            result = runner.invoke(app, ["stop"])
        assert result.exit_code == 0
        assert "No active focus session" in strip_ansi(result.stdout)

    def test_stop_active_session(self):
        """Active session is cancelled and deleted."""
        session = _make_session(status="active")
        p_sm, mock_sm = _patch_state_manager(load_return=session)

        with p_sm:
            with patch("todopro_cli.commands.focus.HistoryLogger"):
                result = runner.invoke(app, ["stop"])

        assert result.exit_code == 0
        assert "Stopping focus session" in strip_ansi(result.stdout)
        assert session.status == "cancelled"
        mock_sm.delete.assert_called_once()

    def test_stop_history_log_error(self):
        """Stop session: history log raises — note printed."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)

        with p_sm:
            with patch(
                "todopro_cli.commands.focus.HistoryLogger",
                side_effect=Exception("disk error"),
            ):
                result = runner.invoke(app, ["stop"])

        assert result.exit_code == 0
        assert "Could not log to history" in strip_ansi(result.stdout)


# ===========================================================================
# Tests: focus_status
# ===========================================================================

class TestFocusStatus:
    """Tests for `focus status` command."""

    def test_no_active_session(self):
        """No session found."""
        p_sm, _ = _patch_state_manager(load_return=None)
        with p_sm:
            result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "No active focus session" in strip_ansi(result.stdout)

    def test_active_session_with_time_remaining(self):
        """Active session with time remaining shows countdown."""
        session = _make_session(status="active", duration=25)
        p_sm, _ = _patch_state_manager(load_return=session)

        with p_sm:
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "Current Focus Session" in strip_ansi(result.stdout)
        assert "Time remaining" in strip_ansi(result.stdout)

    def test_expired_session_shows_expired(self):
        """Session with no time remaining shows expired."""
        session = _make_session(status="active")
        session.end_time = (datetime.now(tz=timezone.utc) - timedelta(minutes=1)).isoformat()
        p_sm, _ = _patch_state_manager(load_return=session)

        with p_sm:
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "expired" in strip_ansi(result.stdout).lower()


# ===========================================================================
# Tests: list_templates
# ===========================================================================

class TestListTemplates:
    """Tests for `focus templates` command."""

    def test_list_templates_success(self):
        """Templates listed in a table."""
        p_tm, mock_tm = _patch_template_manager()

        with p_tm:
            result = runner.invoke(app, ["templates"])

        assert result.exit_code == 0
        assert "Focus Session Templates" in strip_ansi(result.stdout)
        mock_tm.list_templates.assert_called_once()

    def test_list_templates_empty(self):
        """No templates — empty table rendered."""
        p_tm, _ = _patch_template_manager(templates_list=[])

        with p_tm:
            result = runner.invoke(app, ["templates"])

        assert result.exit_code == 0

    def test_list_templates_no_breaks_indicator(self):
        """Template with breaks_enabled=False shows ✗."""
        templates = [
            ("no_break_tpl", {"duration": 60, "breaks_enabled": False, "description": "No break"}),
        ]
        p_tm, _ = _patch_template_manager(templates_list=templates)

        with p_tm:
            result = runner.invoke(app, ["templates"])

        assert result.exit_code == 0
        assert "✗" in result.stdout


# ===========================================================================
# Tests: manage_template
# ===========================================================================

class TestManageTemplate:
    """Tests for `focus template` command."""

    def test_create_template(self):
        """Create action creates a template."""
        p_tm, mock_tm = _patch_template_manager()

        with p_tm:
            result = runner.invoke(app, ["template", "create", "sprint", "--duration", "50"])

        assert result.exit_code == 0
        assert "created" in strip_ansi(result.stdout).lower()
        mock_tm.create_template.assert_called_once()

    def test_create_template_with_no_breaks(self):
        """Create with --no-breaks flag passes breaks_enabled=False."""
        p_tm, mock_tm = _patch_template_manager()

        with p_tm:
            result = runner.invoke(app, ["template", "create", "deep", "--no-breaks", "--description", "Deep work"])

        assert result.exit_code == 0
        call_kwargs = mock_tm.create_template.call_args
        assert call_kwargs.kwargs.get("breaks_enabled") is False or \
               (call_kwargs.args and call_kwargs.args[2] is False) or \
               call_kwargs[1].get("breaks_enabled") is False or \
               not call_kwargs[1].get("breaks_enabled", True)

    def test_delete_template_found(self):
        """Delete action deletes existing template."""
        p_tm, mock_tm = _patch_template_manager()
        mock_tm.delete_template.return_value = True

        with p_tm:
            result = runner.invoke(app, ["template", "delete", "sprint"])

        assert result.exit_code == 0
        assert "deleted" in strip_ansi(result.stdout).lower()

    def test_delete_template_not_found(self):
        """Delete action on missing / default template shows warning."""
        p_tm, mock_tm = _patch_template_manager()
        mock_tm.delete_template.return_value = False

        with p_tm:
            result = runner.invoke(app, ["template", "delete", "standard"])

        assert result.exit_code == 0
        assert "Cannot delete" in strip_ansi(result.stdout)

    def test_unknown_action(self):
        """Unknown action exits 1."""
        p_tm, _ = _patch_template_manager()

        with p_tm:
            result = runner.invoke(app, ["template", "bad_action", "sprint"])

        assert result.exit_code == 1
        assert "Unknown action" in strip_ansi(result.stdout)


# ===========================================================================
# Tests: auto_cycle
# ===========================================================================

class TestAutoCycle:
    """Tests for `focus cycle` command."""

    def test_cycle_with_task_id_timer_stopped(self):
        """Provide task_id directly, timer immediately stops."""
        p_ts, mock_svc = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("stopped")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.HistoryLogger"):
                result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
        assert "stopped" in strip_ansi(result.stdout).lower()

    def test_cycle_with_task_id_timer_interrupted(self):
        """Provide task_id, timer gets interrupted."""
        p_ts, mock_svc = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("interrupted")

        with p_ts, p_cfg, p_sm, p_td:
            result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
        assert "interrupted" in strip_ansi(result.stdout).lower()

    def test_cycle_task_fetch_error(self):
        """Task fetch fails — exits 1."""
        p_ts, mock_svc = _patch_task_service()
        mock_svc.get_task = AsyncMock(side_effect=Exception("not found"))
        p_cfg, _ = _patch_config_service()

        with p_ts, p_cfg:
            result = runner.invoke(app, ["cycle", "bad-task-id"])

        assert result.exit_code == 1
        assert "Error fetching task" in strip_ansi(result.stdout)

    def test_cycle_completed_then_continue_no(self):
        """Timer completes; user declines to continue — loop breaks."""
        task = _make_task()
        p_ts, mock_svc = _patch_task_service(task=task)
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        answers = iter([False, False])  # "Did you complete task?" → No; "Continue?" → No

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=answers):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
        assert "stopped" in strip_ansi(result.stdout).lower()

    def test_cycle_completed_user_completes_task_then_stops(self):
        """Timer completes; user completes task and gets next suggestion; declines continue."""
        task = _make_task()
        next_task = _make_task(task_id="next-task-0001", content="Next Task")
        p_ts, mock_svc = _patch_task_service(task=task, tasks=[next_task])
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        p_se, mock_engine = _patch_suggestion_engine(
            suggestions=[{"task": {"id": "next-task-0001", "title": "Next Task"}, "score": 5.0}]
        )

        # "Did you complete task?" → Yes; "Continue?" → No
        answers = iter([True, False])

        with p_ts, p_cfg, p_sm, p_td, p_se:
            with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=answers):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
        mock_svc.complete_task.assert_awaited_once()

    def test_cycle_completed_no_next_suggestion(self):
        """Timer completes; user completes task but no suggestions available."""
        task = _make_task()
        p_ts, mock_svc = _patch_task_service(task=task, tasks=[])
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")
        p_se, _ = _patch_suggestion_engine(suggestions=[])

        answers = iter([True, False])

        with p_ts, p_cfg, p_sm, p_td, p_se:
            with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=answers):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0

    def test_cycle_without_task_id_no_suggestions(self):
        """No task_id; no suggestions available — exit 0."""
        p_ts, mock_svc = _patch_task_service()
        mock_svc.list_tasks = AsyncMock(return_value=[])
        p_cfg, _ = _patch_config_service()
        p_se, _ = _patch_suggestion_engine(suggestions=[])

        with p_ts, p_cfg, p_se:
            result = runner.invoke(app, ["cycle"])

        assert result.exit_code == 0
        assert "No tasks available" in strip_ansi(result.stdout)

    def test_cycle_without_task_id_with_suggestions_valid_choice(self):
        """No task_id; suggestions shown; user picks task 1."""
        suggestions = [
            {"task": {"id": "sugg-0001", "title": "Suggested Task", "priority": 2,
                      "due_date": None, "labels": [], "estimated_minutes": 25}, "score": 8.0},
        ]
        task = _make_task(task_id="sugg-0001", content="Suggested Task")
        p_ts, mock_svc = _patch_task_service(task=task)
        mock_svc.list_tasks = AsyncMock(return_value=[task])
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("stopped")
        p_se, _ = _patch_suggestion_engine(suggestions=suggestions)

        with p_ts, p_cfg, p_sm, p_td, p_se:
            with patch("todopro_cli.commands.focus.Prompt.ask", return_value="1"):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["cycle"])

        assert result.exit_code == 0

    def test_cycle_without_task_id_invalid_choice(self):
        """No task_id; user picks invalid index — exit 1."""
        suggestions = [
            {"task": {"id": "sugg-0001", "title": "Suggested Task", "priority": 2,
                      "due_date": None, "labels": [], "estimated_minutes": 25}, "score": 8.0},
        ]
        task = _make_task(task_id="sugg-0001", content="Suggested Task")
        p_ts, mock_svc = _patch_task_service(task=task)
        mock_svc.list_tasks = AsyncMock(return_value=[task])
        p_cfg, _ = _patch_config_service()
        p_se, _ = _patch_suggestion_engine(suggestions=suggestions)

        with p_ts, p_cfg, p_se:
            with patch("todopro_cli.commands.focus.Prompt.ask", return_value="999"):
                result = runner.invoke(app, ["cycle"])

        assert result.exit_code == 1
        assert "Invalid selection" in strip_ansi(result.stdout)

    def test_cycle_without_task_id_nonnumeric_choice(self):
        """No task_id; user enters non-numeric choice — exit 1."""
        suggestions = [
            {"task": {"id": "sugg-0001", "title": "Suggested Task", "priority": 2,
                      "due_date": None, "labels": [], "estimated_minutes": 25}, "score": 8.0},
        ]
        task = _make_task(task_id="sugg-0001", content="Suggested Task")
        p_ts, mock_svc = _patch_task_service(task=task)
        mock_svc.list_tasks = AsyncMock(return_value=[task])
        p_cfg, _ = _patch_config_service()
        p_se, _ = _patch_suggestion_engine(suggestions=suggestions)

        with p_ts, p_cfg, p_se:
            with patch("todopro_cli.commands.focus.Prompt.ask", return_value="abc"):
                result = runner.invoke(app, ["cycle"])

        assert result.exit_code == 1

    def test_cycle_without_task_id_list_tasks_error(self):
        """list_tasks raises → tasks_dicts falls back to empty list."""
        p_ts, mock_svc = _patch_task_service()
        mock_svc.list_tasks = AsyncMock(side_effect=Exception("API error"))
        p_cfg, _ = _patch_config_service()
        p_se, _ = _patch_suggestion_engine(suggestions=[])

        with p_ts, p_cfg, p_se:
            result = runner.invoke(app, ["cycle"])

        assert result.exit_code == 0
        assert "No tasks available" in strip_ansi(result.stdout)

    def test_cycle_custom_options(self):
        """Custom work/break/long-break/cycles options are accepted."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("stopped")

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.HistoryLogger"):
                result = runner.invoke(
                    app,
                    ["cycle", "task-abc12345", "--work", "30", "--short-break", "10",
                     "--long-break", "20", "--cycles", "3"],
                )

        assert result.exit_code == 0

    def test_cycle_complete_task_api_error(self):
        """complete_task raises during cycle — silently caught."""
        task = _make_task()
        p_ts, mock_svc = _patch_task_service(task=task)
        mock_svc.complete_task = AsyncMock(side_effect=Exception("API err"))
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_td, _ = _patch_timer_display("completed")

        answers = iter([True, False])

        with p_ts, p_cfg, p_sm, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=answers):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["cycle", "task-abc12345"])

        # Error is caught; loop should still stop when user says no
        assert result.exit_code == 0


# ===========================================================================
# Tests: inner callbacks (on_pause, on_resume, on_stop, on_complete)
# Invoked by capturing from run_timer mock call_args
# ===========================================================================

def _make_callback_invoking_display(phase_callbacks_to_invoke):
    """Create a mock TimerDisplay whose run_timer invokes the specified callbacks."""
    mock_display = MagicMock()

    def fake_run_timer(session, on_pause, on_resume, on_stop, on_complete):
        for cb_name in phase_callbacks_to_invoke:
            if cb_name == "on_pause":
                on_pause()
            elif cb_name == "on_resume_with_pause":
                # Simulate pause was set before resume
                session.pause_time = (datetime.now(tz=timezone.utc) - timedelta(seconds=30)).isoformat()
                on_pause()
                on_resume()
            elif cb_name == "on_resume_no_pause":
                on_resume()
            elif cb_name == "on_stop":
                on_stop()
            elif cb_name == "on_complete":
                on_complete()
        return "interrupted"

    mock_display.run_timer.side_effect = fake_run_timer
    return mock_display


class TestStartFocusCallbacks:
    """Test the callback closures defined inside start_focus."""

    def test_on_pause_callback(self):
        """on_pause sets session status=paused and saves state."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)

        mock_display = _make_callback_invoking_display(["on_pause"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0
        # save was called at least once (initial save) + once for on_pause
        assert mock_sm.save.call_count >= 2

    def test_on_resume_with_pause_time(self):
        """on_resume with a pause_time extends end_time and resets pause."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)

        mock_display = _make_callback_invoking_display(["on_resume_with_pause"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0

    def test_on_resume_without_pause_time(self):
        """on_resume with no pause_time just sets status=active."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)

        mock_display = _make_callback_invoking_display(["on_resume_no_pause"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0

    def test_on_stop_callback(self):
        """on_stop sets session status=cancelled."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)

        mock_display = _make_callback_invoking_display(["on_stop"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0

    def test_on_complete_callback(self):
        """on_complete sets session status=completed."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)

        mock_display = _make_callback_invoking_display(["on_complete"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["start", "task-abc12345"])

        assert result.exit_code == 0


class TestResumeFocusCallbacks:
    """Test the callback closures defined inside resume_focus."""

    def test_resume_on_pause_callback(self):
        """on_pause callback in resume_focus saves paused state."""
        session = _make_session(status="active")
        p_sm, mock_sm = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()

        mock_display = _make_callback_invoking_display(["on_pause"])
        with p_sm, p_cfg:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0

    def test_resume_on_resume_with_pause_time(self):
        """on_resume callback in resume_focus updates end time."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()

        mock_display = _make_callback_invoking_display(["on_resume_with_pause"])
        with p_sm, p_cfg:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0

    def test_resume_on_resume_without_pause_time(self):
        """on_resume callback without pause_time just activates."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()

        mock_display = _make_callback_invoking_display(["on_resume_no_pause"])
        with p_sm, p_cfg:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0

    def test_resume_on_stop_callback(self):
        """on_stop callback in resume_focus cancels session."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()

        mock_display = _make_callback_invoking_display(["on_stop"])
        with p_sm, p_cfg:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0

    def test_resume_on_complete_callback(self):
        """on_complete callback in resume_focus marks session completed."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()

        mock_display = _make_callback_invoking_display(["on_complete"])
        with p_sm, p_cfg:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0

    def test_resume_complete_task_error_silently_ignored(self):
        """When complete_task fails in resume_focus after Confirm, error is silently ignored."""
        session = _make_session(status="active")
        p_sm, _ = _patch_state_manager(load_return=session)
        p_cfg, _ = _patch_config_service()
        p_ts, mock_svc = _patch_task_service()
        mock_svc.complete_task = AsyncMock(side_effect=Exception("API error"))
        p_td, _ = _patch_timer_display("completed")

        with p_sm, p_cfg, p_ts, p_td:
            with patch("todopro_cli.commands.focus.Confirm.ask", return_value=True):
                with patch("todopro_cli.commands.focus.HistoryLogger"):
                    result = runner.invoke(app, ["resume"])

        # Error silently swallowed — still exits 0
        assert result.exit_code == 0


class TestAutoCycleCallbacks:
    """Test callbacks inside auto_cycle's main loop and multi-phase cycling."""

    def _make_cycle_callback_display(self, phase_callbacks_to_invoke, result="interrupted"):
        """Display that invokes callbacks then returns result."""
        mock_display = MagicMock()
        call_count = [0]

        def fake_run_timer(session, on_pause, on_resume, on_stop, on_complete):
            for cb_name in phase_callbacks_to_invoke:
                if cb_name == "on_pause":
                    on_pause()
                elif cb_name == "on_resume_with_pause":
                    session.pause_time = (
                        datetime.now(tz=timezone.utc) - timedelta(seconds=30)
                    ).isoformat()
                    on_pause()
                    on_resume()
                elif cb_name == "on_resume_no_pause":
                    on_resume()
                elif cb_name == "on_stop":
                    on_stop()
                elif cb_name == "on_complete":
                    on_complete()
            call_count[0] += 1
            return result

        mock_display.run_timer.side_effect = fake_run_timer
        return mock_display

    def test_cycle_callbacks_on_pause(self):
        """on_pause callback inside auto_cycle saves paused state."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, mock_sm = _patch_state_manager(load_return=None)

        mock_display = self._make_cycle_callback_display(["on_pause"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0

    def test_cycle_callbacks_on_resume_with_pause(self):
        """on_resume with pause_time inside auto_cycle."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)

        mock_display = self._make_cycle_callback_display(["on_resume_with_pause"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0

    def test_cycle_callbacks_on_resume_no_pause(self):
        """on_resume without pause_time inside auto_cycle."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)

        mock_display = self._make_cycle_callback_display(["on_resume_no_pause"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0

    def test_cycle_callbacks_on_stop(self):
        """on_stop callback inside auto_cycle."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)

        mock_display = self._make_cycle_callback_display(["on_stop"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0

    def test_cycle_callbacks_on_complete(self):
        """on_complete callback inside auto_cycle."""
        p_ts, _ = _patch_task_service()
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)

        mock_display = self._make_cycle_callback_display(["on_complete"])
        with p_ts, p_cfg, p_sm:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0

    def test_cycle_short_break_phase(self):
        """auto_cycle runs through focus→short_break phases."""
        task = _make_task()
        p_ts, mock_svc = _patch_task_service(task=task)
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_se, _ = _patch_suggestion_engine(suggestions=[])

        # Timer returns "completed" on first call (focus), then "stopped" on second (short_break)
        timer_results = iter(["completed", "stopped"])
        mock_display = MagicMock()
        mock_display.run_timer.side_effect = lambda *a, **kw: next(timer_results)

        # First Confirm: "Did you complete task?" → No
        # Second Confirm: "Continue to Short Break?" → Yes
        # (then stopped on short_break, so 3rd Confirm.ask not needed)
        confirm_answers = iter([False, True])

        with p_ts, p_cfg, p_sm, p_se:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=confirm_answers):
                    with patch("todopro_cli.commands.focus.HistoryLogger"):
                        result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
        # run_timer should have been called twice (focus + short_break)
        assert mock_display.run_timer.call_count == 2

    def test_cycle_long_break_phase(self):
        """auto_cycle runs through 4 focus sessions → long_break phase."""
        task = _make_task()
        p_ts, mock_svc = _patch_task_service(task=task)
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_se, _ = _patch_suggestion_engine(suggestions=[])

        # Simulate: focus→completed, short_break→completed, focus→completed,
        #           short_break→completed, focus→completed, short_break→completed,
        #           focus→completed (4th) → long_break → stopped
        # Actually with cycles=4, it takes 4 focus sessions before long break.
        # To simplify: use cycles=1 so first focus → long_break
        timer_results = iter(["completed", "stopped"])
        mock_display = MagicMock()
        mock_display.run_timer.side_effect = lambda *a, **kw: next(timer_results)

        # "Did you complete task?" → No; "Continue to Long Break?" → Yes
        confirm_answers = iter([False, True])

        with p_ts, p_cfg, p_sm, p_se:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=confirm_answers):
                    with patch("todopro_cli.commands.focus.HistoryLogger"):
                        result = runner.invoke(
                            app,
                            ["cycle", "task-abc12345", "--cycles", "1"],
                        )

        assert result.exit_code == 0
        assert mock_display.run_timer.call_count == 2

    def test_cycle_complete_task_success_lines(self):
        """Successful complete_task in auto_cycle increments stats (line 613-614)."""
        task = _make_task()
        next_task = _make_task(task_id="next-001", content="Next")
        p_ts, mock_svc = _patch_task_service(task=task, tasks=[next_task])
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)

        suggestions = [
            {"task": {"id": "next-001", "title": "Next", "priority": 2,
                      "due_date": None, "labels": [], "estimated_minutes": 25},
             "score": 7.0}
        ]
        p_se, _ = _patch_suggestion_engine(suggestions=suggestions)

        timer_results = iter(["completed", "stopped"])
        mock_display = MagicMock()
        mock_display.run_timer.side_effect = lambda *a, **kw: next(timer_results)

        # "Did you complete task?" → Yes; "Continue?" → Yes; (2nd timer stopped)
        confirm_answers = iter([True, True])

        with p_ts, p_cfg, p_sm, p_se:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=confirm_answers):
                    with patch("todopro_cli.commands.focus.HistoryLogger"):
                        result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
        mock_svc.complete_task.assert_awaited_once()


# ===========================================================================
# Tests: factory functions (get_task_service, _get_template_manager, _get_suggestion_engine)
# ===========================================================================

class TestFactoryFunctions:
    """Tests for factory functions to cover lines 56, 61-62, 67-68."""

    def test_get_task_service_returns_task_service(self):
        """get_task_service() returns a TaskService instance."""
        from todopro_cli.commands.focus import get_task_service
        from todopro_cli.services.task_service import TaskService

        mock_repo = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.task_repository = mock_repo

        with patch("todopro_cli.commands.focus.get_storage_strategy_context", return_value=mock_ctx):
            svc = get_task_service()

        assert isinstance(svc, TaskService)

    def test_get_template_manager_returns_template_manager(self):
        """_get_template_manager() returns a TemplateManager instance."""
        from todopro_cli.commands.focus import _get_template_manager
        from todopro_cli.models.focus.templates import TemplateManager

        mock_cfg_svc = MagicMock()
        mock_cfg_svc.load_config.return_value = MagicMock()
        mock_cfg_svc.save_config = MagicMock()

        with patch("todopro_cli.commands.focus.get_config_service", return_value=mock_cfg_svc):
            tm = _get_template_manager()

        assert isinstance(tm, TemplateManager)

    def test_get_suggestion_engine_returns_engine(self):
        """_get_suggestion_engine() returns a TaskSuggestionEngine instance."""
        from todopro_cli.commands.focus import _get_suggestion_engine
        from todopro_cli.models.focus.suggestions import TaskSuggestionEngine

        mock_cfg_svc = MagicMock()
        mock_cfg_svc.load_config.return_value = MagicMock()

        with patch("todopro_cli.commands.focus.get_config_service", return_value=mock_cfg_svc):
            engine = _get_suggestion_engine()

        assert isinstance(engine, TaskSuggestionEngine)

    def test_cycle_list_tasks_raises_during_completion(self):
        """list_tasks raises inside cycle completion path — falls back to empty (lines 613-614)."""
        task = _make_task()
        p_ts, mock_svc = _patch_task_service(task=task)
        mock_svc.list_tasks = AsyncMock(side_effect=Exception("API unavailable"))
        p_cfg, _ = _patch_config_service()
        p_sm, _ = _patch_state_manager(load_return=None)
        p_se, _ = _patch_suggestion_engine(suggestions=[])

        timer_results = iter(["completed", "stopped"])
        mock_display = MagicMock()
        mock_display.run_timer.side_effect = lambda *a, **kw: next(timer_results)

        # "Did you complete task?" → Yes; "Continue?" → Yes
        confirm_answers = iter([True, True])

        with p_ts, p_cfg, p_sm, p_se:
            with patch("todopro_cli.commands.focus.TimerDisplay", return_value=mock_display):
                with patch("todopro_cli.commands.focus.Confirm.ask", side_effect=confirm_answers):
                    with patch("todopro_cli.commands.focus.HistoryLogger"):
                        result = runner.invoke(app, ["cycle", "task-abc12345"])

        assert result.exit_code == 0
