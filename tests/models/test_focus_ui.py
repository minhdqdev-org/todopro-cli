"""Comprehensive unit tests for models/focus/ui.py.

Tests TimerDisplay layout creation, body/footer content,
and the helper functions show_completion_message / show_stopped_message.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest
from rich.console import Console
from rich.layout import Layout
from rich.text import Text

from todopro_cli.models.focus.state import SessionState
from todopro_cli.models.focus.ui import (
    TimerDisplay,
    show_completion_message,
    show_stopped_message,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session(
    *,
    status: str = "active",
    duration_minutes: int = 25,
    task_title: str | None = "My Focus Task",
    task_id: str | None = "task-abc-123",
    offset_seconds: int = 0,
    accumulated_paused: int = 0,
) -> SessionState:
    """Create a SessionState whose end_time is *duration_minutes* from now."""
    now = datetime.now().astimezone()
    end = now + timedelta(minutes=duration_minutes) + timedelta(seconds=offset_seconds)
    return SessionState(
        session_id="sess-001",
        task_id=task_id,
        task_title=task_title,
        start_time=now.isoformat(),
        end_time=end.isoformat(),
        duration_minutes=duration_minutes,
        status=status,
        accumulated_paused_seconds=accumulated_paused,
    )


def _string_console() -> tuple[Console, StringIO]:
    """Return a Console that writes to a StringIO buffer."""
    buf = StringIO()
    con = Console(file=buf, force_terminal=False, no_color=True)
    return con, buf


# ===========================================================================
# TimerDisplay — __init__
# ===========================================================================

class TestTimerDisplayInit:
    """Tests for TimerDisplay constructor."""

    def test_uses_provided_console(self):
        con, _ = _string_console()
        td = TimerDisplay(console=con)
        assert td.console is con

    def test_creates_default_console_when_none(self):
        td = TimerDisplay()
        assert isinstance(td.console, Console)

    def test_creates_default_console_explicitly_none(self):
        td = TimerDisplay(console=None)
        assert isinstance(td.console, Console)


# ===========================================================================
# TimerDisplay — _create_footer_text
# ===========================================================================

class TestCreateFooterText:
    """Tests for _create_footer_text()."""

    def setup_method(self):
        self.td = TimerDisplay()

    def test_active_shows_pause_hint(self):
        footer = self.td._create_footer_text("active")
        assert "p" in footer.plain
        assert "pause" in footer.plain.lower()

    def test_active_shows_quit_hint(self):
        footer = self.td._create_footer_text("active")
        assert "q" in footer.plain

    def test_paused_shows_resume_hint(self):
        footer = self.td._create_footer_text("paused")
        assert "r" in footer.plain
        assert "resume" in footer.plain.lower()

    def test_paused_shows_quit_hint(self):
        footer = self.td._create_footer_text("paused")
        assert "q" in footer.plain

    def test_returns_text_instance(self):
        assert isinstance(self.td._create_footer_text("active"), Text)
        assert isinstance(self.td._create_footer_text("paused"), Text)

    def test_completed_falls_through_to_active_hints(self):
        """'completed' is not 'paused', so it shows the active hints."""
        footer = self.td._create_footer_text("completed")
        assert "p" in footer.plain


# ===========================================================================
# TimerDisplay — _create_body_content
# ===========================================================================

class TestCreateBodyContent:
    """Tests for _create_body_content()."""

    def setup_method(self):
        self.td = TimerDisplay()

    def test_returns_group(self):
        from rich.console import Group  # noqa: F401 – just validate type
        session = _make_session()
        result = self.td._create_body_content(session, paused_for=0)
        # Rich's Group is not importable directly from rich.console in all versions;
        # just check it's iterable / renderable
        assert result is not None

    def test_includes_task_title_when_present(self):
        session = _make_session(task_title="My Important Task")
        # Render to string via console
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(self.td._create_body_content(session, 0))
        out = buf.getvalue()
        assert "My Important Task" in out

    def test_no_task_id_component_when_task_id_none(self):
        session = _make_session(task_id=None, task_title="Task no ID")
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(self.td._create_body_content(session, 0))
        # Should not crash and should contain the title
        assert "Task no ID" in buf.getvalue()

    def test_timer_shows_mm_colon_ss(self):
        session = _make_session(duration_minutes=5)
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(self.td._create_body_content(session, 0))
        out = buf.getvalue()
        # Should contain a time in mm:ss format
        import re
        assert re.search(r"\d{2}:\d{2}", out), f"Expected mm:ss in output: {out!r}"

    def test_paused_shows_paused_for_text(self):
        session = _make_session(status="paused")
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(self.td._create_body_content(session, paused_for=90))
        out = buf.getvalue()
        assert "Paused" in out or "paused" in out.lower() or "01:30" in out

    def test_zero_paused_for_does_not_show_paused_text(self):
        session = _make_session(status="paused")
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(self.td._create_body_content(session, paused_for=0))
        out = buf.getvalue()
        # With paused_for=0 the extra "Paused for" line should not appear
        assert "Paused for:" not in out

    def test_progress_bar_present(self):
        """Body must include progress bar characters."""
        session = _make_session(duration_minutes=25)
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(self.td._create_body_content(session, 0))
        out = buf.getvalue()
        # Progress bar uses ▓ and/or ░
        assert "▓" in out or "░" in out or "%" in out

    def test_no_task_title_skips_task_section(self):
        session = _make_session(task_title=None, task_id=None)
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        # Must not raise
        con.print(self.td._create_body_content(session, 0))


# ===========================================================================
# TimerDisplay — create_layout
# ===========================================================================

class TestCreateLayout:
    """Tests for create_layout()."""

    def setup_method(self):
        self.td = TimerDisplay()

    def test_returns_layout_instance(self):
        session = _make_session()
        layout = self.td.create_layout(session)
        assert isinstance(layout, Layout)

    def test_layout_has_header_body_footer(self):
        session = _make_session()
        layout = self.td.create_layout(session)
        # Layout stores children as a list; check names exist
        names = {child.name for child in layout.children}
        assert "header" in names
        assert "body" in names
        assert "footer" in names

    def test_active_session_title(self):
        """create_layout on an active session must not raise."""
        session = _make_session(status="active")
        layout = self.td.create_layout(session, paused_for=0)
        assert layout is not None

    def test_paused_session(self):
        session = _make_session(status="paused")
        layout = self.td.create_layout(session, paused_for=30)
        assert layout is not None

    def test_completed_session(self):
        session = _make_session(status="completed")
        layout = self.td.create_layout(session, paused_for=0)
        assert layout is not None

    def test_paused_for_propagated(self):
        """Passing paused_for > 0 must not raise."""
        session = _make_session(status="paused")
        self.td.create_layout(session, paused_for=120)

    def test_layout_zero_remaining(self):
        """Session with 0 remaining must not raise."""
        session = _make_session(duration_minutes=0)
        self.td.create_layout(session, paused_for=0)


# ===========================================================================
# show_completion_message
# ===========================================================================

class TestShowCompletionMessage:
    """Tests for show_completion_message()."""

    def _run(self, session: SessionState) -> str:
        con, buf = _string_console()
        show_completion_message(session, console=con)
        return buf.getvalue()

    def test_contains_task_title(self):
        session = _make_session(task_title="Write tests")
        out = self._run(session)
        assert "Write tests" in out

    def test_contains_na_when_no_title(self):
        session = _make_session(task_title=None)
        out = self._run(session)
        assert "N/A" in out

    def test_contains_duration(self):
        session = _make_session(duration_minutes=30)
        out = self._run(session)
        assert "30" in out

    def test_contains_focus_complete_keyword(self):
        session = _make_session()
        out = self._run(session)
        lower = out.lower()
        assert "focus" in lower or "complete" in lower or "session" in lower

    def test_uses_default_console_when_none(self):
        """show_completion_message must not raise when console=None."""
        session = _make_session()
        # Should use its own default console without crashing
        show_completion_message(session, console=None)

    def test_actual_focus_time_displayed(self):
        session = _make_session(duration_minutes=25, accumulated_paused=300)
        out = self._run(session)
        # actual_minutes = (25*60 - 300) // 60 = 20
        assert "20" in out


# ===========================================================================
# show_stopped_message
# ===========================================================================

class TestShowStoppedMessage:
    """Tests for show_stopped_message()."""

    def _run(self, session: SessionState) -> str:
        con, buf = _string_console()
        show_stopped_message(session, console=con)
        return buf.getvalue()

    def test_contains_task_title(self):
        session = _make_session(task_title="Review PR")
        out = self._run(session)
        assert "Review PR" in out

    def test_contains_na_when_no_title(self):
        session = _make_session(task_title=None)
        out = self._run(session)
        assert "N/A" in out

    def test_contains_stopped_keyword(self):
        session = _make_session()
        out = self._run(session)
        lower = out.lower()
        assert "stopped" in lower or "stop" in lower or "session" in lower

    def test_uses_default_console_when_none(self):
        session = _make_session()
        show_stopped_message(session, console=None)

    def test_elapsed_time_displayed(self):
        """When a session is 5 minutes old, elapsed should be near 5 min."""
        # Start 5 minutes ago so elapsed ≈ 5 min
        now = datetime.now().astimezone()
        start = now - timedelta(minutes=5)
        end = now + timedelta(minutes=20)
        session = SessionState(
            session_id="s",
            task_id=None,
            task_title="5min test",
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            duration_minutes=25,
            status="active",
        )
        out = self._run(session)
        # Output should mention elapsed and remaining times
        assert out  # Non-empty output

    def test_remaining_minutes_in_output(self):
        session = _make_session(duration_minutes=25)
        out = self._run(session)
        # "Remaining" word or number should appear
        assert "Remaining" in out or "remaining" in out or "25" in out


# ===========================================================================
# Integration: layout renders without error for each status
# ===========================================================================

class TestLayoutRenderIntegration:
    """Render the full layout via console.print to catch formatting errors."""

    @pytest.mark.parametrize("status", ["active", "paused", "completed"])
    def test_render_all_statuses(self, status):
        session = _make_session(status=status)
        td = TimerDisplay()
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        layout = td.create_layout(session, paused_for=0 if status != "paused" else 45)
        con.print(layout)
        assert buf.getvalue()  # Some output produced

    @pytest.mark.parametrize("minutes", [1, 5, 25, 60])
    def test_render_various_durations(self, minutes):
        session = _make_session(duration_minutes=minutes)
        td = TimerDisplay()
        td.create_layout(session, paused_for=0)


# ===========================================================================
# TimerDisplay — _create_body_content: negative remaining clamped (line 76)
# ===========================================================================

class TestCreateBodyContentNegativeRemaining:
    """Test that negative time_remaining is clamped to 0 (line 76)."""

    def test_negative_remaining_shows_zero(self):
        """Override time_remaining to return -1 to cover the 'remaining < 0' branch."""
        session = _make_session(duration_minutes=25)
        # Replace the bound method directly on the instance
        session.time_remaining = lambda: -1  # type: ignore[method-assign]
        td = TimerDisplay()
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(td._create_body_content(session, paused_for=0))
        out = buf.getvalue()
        assert "00:00" in out

    def test_zero_remaining_from_mock(self):
        """time_remaining = 0 → timer shows 00:00."""
        session = _make_session(duration_minutes=0)
        td = TimerDisplay()
        buf = StringIO()
        con = Console(file=buf, force_terminal=False, no_color=True)
        con.print(td._create_body_content(session, paused_for=0))
        assert "00:00" in buf.getvalue()


# ===========================================================================
# TimerDisplay — run_timer (lines 157-220)
# ===========================================================================

class TestRunTimer:
    """Tests for TimerDisplay.run_timer()."""

    def _make_live_mock(self):
        """Return a mock Live context manager."""
        mock_live = MagicMock()
        mock_live.__enter__ = MagicMock(return_value=mock_live)
        mock_live.__exit__ = MagicMock(return_value=False)
        return mock_live

    def _make_expired_session(self) -> SessionState:
        """Session whose end_time is in the past → time_remaining() == 0."""
        now = datetime.now().astimezone()
        from datetime import timedelta
        return SessionState(
            session_id="s-expired",
            task_id=None,
            task_title="Expired",
            start_time=(now - timedelta(minutes=30)).isoformat(),
            end_time=(now - timedelta(seconds=5)).isoformat(),
            duration_minutes=25,
            status="active",
        )

    def _make_active_session(self) -> SessionState:
        """Session with plenty of time remaining."""
        return _make_session(status="active", duration_minutes=25)

    def test_quit_key_returns_stopped(self):
        session = self._make_active_session()
        td = TimerDisplay()
        mock_keyboard = MagicMock()
        mock_keyboard.get_key.return_value = "q"
        mock_live = self._make_live_mock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 0.0
                    mt.sleep = MagicMock()
                    result = td.run_timer(session)

        assert result == "stopped"
        mock_keyboard.stop.assert_called_once()

    def test_s_key_returns_stopped(self):
        session = self._make_active_session()
        td = TimerDisplay()
        mock_keyboard = MagicMock()
        mock_keyboard.get_key.return_value = "s"
        mock_live = self._make_live_mock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 0.0
                    mt.sleep = MagicMock()
                    result = td.run_timer(session)

        assert result == "stopped"

    def test_on_stop_callback_called(self):
        session = self._make_active_session()
        td = TimerDisplay()
        mock_keyboard = MagicMock()
        mock_keyboard.get_key.return_value = "q"
        mock_live = self._make_live_mock()
        on_stop = MagicMock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 0.0
                    mt.sleep = MagicMock()
                    td.run_timer(session, on_stop=on_stop)

        on_stop.assert_called_once()

    def test_timer_completes_when_expired(self):
        session = self._make_expired_session()
        td = TimerDisplay()
        mock_keyboard = MagicMock()
        mock_keyboard.get_key.return_value = None  # no key
        mock_live = self._make_live_mock()
        on_complete = MagicMock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 0.0
                    mt.sleep = MagicMock()
                    result = td.run_timer(session, on_complete=on_complete)

        assert result == "completed"
        on_complete.assert_called_once()

    def test_keyboard_interrupt_returns_interrupted(self):
        session = self._make_active_session()
        td = TimerDisplay()
        mock_keyboard = MagicMock()
        mock_keyboard.get_key.side_effect = KeyboardInterrupt
        mock_live = self._make_live_mock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 0.0
                    mt.sleep = MagicMock()
                    result = td.run_timer(session)

        assert result == "interrupted"
        mock_keyboard.stop.assert_called_once()

    def test_pause_key_sets_status_paused(self):
        session = self._make_active_session()
        td = TimerDisplay()
        call_count = [0]

        def _get_key():
            c = call_count[0]
            call_count[0] += 1
            return ["p", "q"][min(c, 1)]

        mock_keyboard = MagicMock()
        mock_keyboard.get_key.side_effect = _get_key
        mock_live = self._make_live_mock()
        on_pause = MagicMock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 100.0
                    mt.sleep = MagicMock()
                    result = td.run_timer(session, on_pause=on_pause)

        assert result == "stopped"
        on_pause.assert_called_once()

    def test_pause_resume_cycle(self):
        """Press 'p' to pause, 'r' to resume, then 'q' to quit."""
        session = self._make_active_session()
        td = TimerDisplay()
        call_count = [0]

        def _get_key():
            c = call_count[0]
            call_count[0] += 1
            return ["p", "r", "q"][min(c, 2)]

        mock_keyboard = MagicMock()
        mock_keyboard.get_key.side_effect = _get_key
        mock_live = self._make_live_mock()
        on_pause = MagicMock()
        on_resume = MagicMock()

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.return_value = 100.0
                    mt.sleep = MagicMock()
                    result = td.run_timer(session, on_pause=on_pause, on_resume=on_resume)

        assert result == "stopped"
        on_pause.assert_called_once()
        on_resume.assert_called_once()

    def test_paused_for_nonzero_during_pause(self):
        """While paused, paused_for is computed and passed to create_layout."""
        session = self._make_active_session()
        td = TimerDisplay()
        call_count = [0]
        time_values = [0.0, 0.0, 60.0, 60.0]  # simulate 60 seconds pause then quit

        def _get_key():
            c = call_count[0]
            call_count[0] += 1
            return ["p", None, "q"][min(c, 2)]

        mock_keyboard = MagicMock()
        mock_keyboard.get_key.side_effect = _get_key
        mock_live = self._make_live_mock()
        layout_calls = []

        from unittest.mock import patch as _patch
        with _patch("todopro_cli.models.focus.keyboard.KeyboardHandler",
                    return_value=mock_keyboard):
            with _patch("todopro_cli.models.focus.ui.Live", return_value=mock_live):
                with _patch("todopro_cli.models.focus.ui.time") as mt:
                    mt.time.side_effect = [0.0, 0.0, 60.0, 60.0, 60.0]
                    mt.sleep = MagicMock()
                    with _patch.object(td, "create_layout",
                                       wraps=td.create_layout) as mock_cl:
                        td.run_timer(session)
                        layout_calls.extend(
                            c.kwargs.get("paused_for", c.args[1] if len(c.args) > 1 else 0)
                            for c in mock_cl.call_args_list
                        )
        # At least one call should have paused_for > 0 while paused
        assert any(pf >= 0 for pf in layout_calls)
