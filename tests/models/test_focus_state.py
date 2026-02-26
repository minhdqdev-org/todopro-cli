"""Comprehensive unit tests for todopro_cli.models.focus.state.

Coverage strategy
-----------------
* ``SessionState`` is exercised as a plain dataclass with datetime arithmetic.
* ``SessionStateManager`` is constructed with a *tmp_path* fixture so every
  test is filesystem-isolated and no platform directories are touched.
* State-machine transitions (pause, resume) and edge cases (already-paused,
  expired, corrupted JSON) are all covered.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from todopro_cli.models.focus.state import (
    SessionState,
    SessionStateManager,
    SessionStatus,
    SessionType,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISO_OFFSET = "+00:00"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _future_iso(minutes: int = 25) -> str:
    return (datetime.now().astimezone() + timedelta(minutes=minutes)).isoformat()


def _past_iso(minutes: int = 25) -> str:
    return (datetime.now().astimezone() - timedelta(minutes=minutes)).isoformat()


def _make_state(
    status: SessionStatus = "active",
    duration_minutes: int = 25,
    session_type: SessionType = "focus",
    start_offset: int = 0,
    end_offset: int = 25,
    pause_time: str | None = None,
    accumulated_paused_seconds: int = 0,
    context: str = "default",
) -> SessionState:
    start = datetime.now().astimezone() + timedelta(minutes=start_offset)
    end = datetime.now().astimezone() + timedelta(minutes=end_offset)
    return SessionState(
        session_id="test-session-id",
        task_id="task-1",
        task_title="Test Task",
        start_time=start.isoformat(),
        end_time=end.isoformat(),
        duration_minutes=duration_minutes,
        status=status,
        session_type=session_type,
        pause_time=pause_time,
        accumulated_paused_seconds=accumulated_paused_seconds,
        context=context,
    )


# ---------------------------------------------------------------------------
# SessionState – dataclass behaviour
# ---------------------------------------------------------------------------


class TestSessionStateInit:
    def test_basic_creation(self):
        state = _make_state()
        assert state.session_id == "test-session-id"
        assert state.task_id == "task-1"
        assert state.task_title == "Test Task"
        assert state.status == "active"
        assert state.session_type == "focus"

    def test_default_session_type_is_focus(self):
        now = datetime.now().astimezone()
        s = SessionState(
            session_id="id",
            task_id=None,
            task_title=None,
            start_time=now.isoformat(),
            end_time=(now + timedelta(minutes=5)).isoformat(),
            duration_minutes=5,
            status="active",
        )
        assert s.session_type == "focus"

    def test_pause_time_defaults_to_none(self):
        state = _make_state()
        assert state.pause_time is None

    def test_accumulated_paused_seconds_defaults_to_zero(self):
        state = _make_state()
        assert state.accumulated_paused_seconds == 0

    def test_context_defaults_to_default(self):
        state = _make_state()
        assert state.context == "default"


class TestSessionStateDatetimeProperties:
    def test_start_datetime_parses_correctly(self):
        state = _make_state()
        assert isinstance(state.start_datetime, datetime)

    def test_end_datetime_parses_correctly(self):
        state = _make_state()
        assert isinstance(state.end_datetime, datetime)

    def test_end_datetime_after_start_datetime(self):
        state = _make_state(duration_minutes=25)
        assert state.end_datetime > state.start_datetime

    def test_pause_datetime_none_when_not_paused(self):
        state = _make_state()
        assert state.pause_datetime is None

    def test_pause_datetime_parses_when_set(self):
        pause_time = datetime.now().astimezone().isoformat()
        state = _make_state(status="paused", pause_time=pause_time)
        assert isinstance(state.pause_datetime, datetime)

    def test_start_datetime_handles_z_suffix(self):
        """ISO strings ending with 'Z' are parsed correctly."""
        from datetime import timezone
        now = datetime.now(timezone.utc)
        state = SessionState(
            session_id="id",
            task_id=None,
            task_title=None,
            start_time=now.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            end_time=(now + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            duration_minutes=5,
            status="active",
        )
        assert isinstance(state.start_datetime, datetime)
        assert isinstance(state.end_datetime, datetime)


class TestSessionStateTimeRemaining:
    def test_active_session_has_positive_remaining(self):
        state = _make_state(end_offset=25)
        assert state.time_remaining() > 0

    def test_expired_session_remaining_is_zero(self):
        state = _make_state(start_offset=-30, end_offset=-5)
        assert state.time_remaining() == 0

    def test_paused_session_uses_pause_time(self):
        """Paused sessions report remaining time as of the pause moment."""
        # Session paused 5 minutes ago, ends 20 minutes from now
        pause_at = datetime.now().astimezone() - timedelta(minutes=5)
        state = _make_state(status="paused", end_offset=20, pause_time=pause_at.isoformat())
        remaining = state.time_remaining()
        # Should be ~25 minutes remaining (end - pause = 25min)
        assert remaining > 20 * 60  # at least 20 minutes

    def test_time_remaining_is_non_negative(self):
        state = _make_state(start_offset=-100, end_offset=-50)
        assert state.time_remaining() >= 0


class TestSessionStateTimeElapsed:
    def test_active_session_elapsed_positive(self):
        state = _make_state(start_offset=-10, end_offset=15)
        elapsed = state.time_elapsed()
        assert elapsed > 0

    def test_paused_session_elapsed_uses_pause_time(self):
        pause_at = datetime.now().astimezone() - timedelta(minutes=3)
        state = _make_state(
            status="paused",
            start_offset=-10,
            end_offset=15,
            pause_time=pause_at.isoformat(),
        )
        elapsed = state.time_elapsed()
        # Elapsed = (pause - start) - accumulated ≈ 7 minutes
        assert elapsed > 0

    def test_elapsed_with_accumulated_paused_seconds(self):
        state = _make_state(
            start_offset=-20, end_offset=5, accumulated_paused_seconds=300
        )
        elapsed = state.time_elapsed()
        # ~20 min elapsed minus 5 min paused = ~15 min
        assert elapsed >= 0

    def test_elapsed_is_non_negative(self):
        state = _make_state(start_offset=5, end_offset=30)  # future start
        assert state.time_elapsed() >= 0

    def test_actual_focus_seconds_equals_time_elapsed(self):
        state = _make_state(start_offset=-5, end_offset=20)
        assert state.actual_focus_seconds() == state.time_elapsed()


class TestSessionStateIsExpired:
    def test_not_expired_for_future_end(self):
        state = _make_state(end_offset=25)
        assert state.is_expired() is False

    def test_expired_for_past_end(self):
        state = _make_state(start_offset=-30, end_offset=-1)
        assert state.is_expired() is True


class TestSessionStateSerialization:
    def test_to_dict_returns_dict(self):
        state = _make_state()
        d = state.to_dict()
        assert isinstance(d, dict)

    def test_to_dict_contains_all_fields(self):
        state = _make_state()
        d = state.to_dict()
        expected_keys = {
            "session_id", "task_id", "task_title", "start_time",
            "end_time", "duration_minutes", "status", "session_type",
            "pause_time", "accumulated_paused_seconds", "context",
        }
        assert expected_keys == set(d.keys())

    def test_from_dict_round_trips(self):
        original = _make_state(context="work", accumulated_paused_seconds=60)
        restored = SessionState.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.status == original.status
        assert restored.context == original.context
        assert restored.accumulated_paused_seconds == original.accumulated_paused_seconds

    def test_from_dict_with_none_values(self):
        state = _make_state()
        d = state.to_dict()
        d["task_id"] = None
        d["task_title"] = None
        d["pause_time"] = None
        restored = SessionState.from_dict(d)
        assert restored.task_id is None
        assert restored.pause_time is None


# ---------------------------------------------------------------------------
# SessionStateManager – persistence layer
# ---------------------------------------------------------------------------


class TestSessionStateManagerInit:
    def test_creates_state_dir(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path / "state")
        assert mgr.state_dir.exists()

    def test_state_file_path_inside_state_dir(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path / "state")
        assert mgr.state_file.parent == mgr.state_dir

    def test_custom_state_dir(self, tmp_path):
        custom = tmp_path / "custom_state"
        mgr = SessionStateManager(state_dir=custom)
        assert mgr.state_dir == custom


class TestSessionStateManagerSaveLoad:
    def test_save_and_load_round_trips(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state()
        mgr.save_session(session)
        loaded = mgr.load_session()
        assert loaded is not None
        assert loaded.session_id == session.session_id

    def test_load_returns_none_when_no_file(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        assert mgr.load_session() is None

    def test_save_creates_state_file(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state()
        mgr.save_session(session)
        assert mgr.state_file.exists()

    def test_save_sets_secure_permissions(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state()
        mgr.save_session(session)
        mode = oct(mgr.state_file.stat().st_mode)
        assert mode.endswith("600")

    def test_load_returns_none_on_corrupted_json(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        mgr.state_file.write_text("{ not valid json }")
        assert mgr.load_session() is None

    def test_load_returns_none_on_missing_keys(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        mgr.state_file.write_text('{"session_id": "x"}')
        # Missing required keys → load should return None
        assert mgr.load_session() is None

    def test_overwrite_existing_session(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        s1 = _make_state()
        s1.session_id = "first"
        mgr.save_session(s1)
        s2 = _make_state()
        s2.session_id = "second"
        mgr.save_session(s2)
        loaded = mgr.load_session()
        assert loaded.session_id == "second"


class TestSessionStateManagerDelete:
    def test_delete_removes_file(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        mgr.save_session(_make_state())
        assert mgr.state_file.exists()
        mgr.delete_session()
        assert not mgr.state_file.exists()

    def test_delete_no_file_is_noop(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        mgr.delete_session()  # should not raise


class TestSessionStateManagerHasActiveSession:
    def test_no_session_returns_false(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        assert mgr.has_active_session() is False

    def test_active_session_returns_true(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="active")
        mgr.save_session(session)
        assert mgr.has_active_session() is True

    def test_paused_session_returns_true(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        pause_time = datetime.now().astimezone().isoformat()
        session = _make_state(status="paused", pause_time=pause_time)
        mgr.save_session(session)
        assert mgr.has_active_session() is True

    def test_completed_session_returns_false(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="completed")
        mgr.save_session(session)
        assert mgr.has_active_session() is False

    def test_cancelled_session_returns_false(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="cancelled")
        mgr.save_session(session)
        assert mgr.has_active_session() is False


# ---------------------------------------------------------------------------
# create_session factory
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_create_session_returns_session_state(self):
        session = SessionStateManager.create_session(
            task_id="t1",
            task_title="My Task",
            duration_minutes=25,
        )
        assert isinstance(session, SessionState)

    def test_create_session_status_is_active(self):
        session = SessionStateManager.create_session(
            task_id=None, task_title=None, duration_minutes=5
        )
        assert session.status == "active"

    def test_create_session_generates_unique_ids(self):
        s1 = SessionStateManager.create_session(None, None, 25)
        s2 = SessionStateManager.create_session(None, None, 25)
        assert s1.session_id != s2.session_id

    def test_create_session_end_time_after_start(self):
        session = SessionStateManager.create_session(None, None, 25)
        assert session.end_datetime > session.start_datetime

    def test_create_session_duration_matches(self):
        session = SessionStateManager.create_session(None, None, 30)
        assert session.duration_minutes == 30

    def test_create_session_default_type_is_focus(self):
        session = SessionStateManager.create_session(None, None, 25)
        assert session.session_type == "focus"

    def test_create_session_custom_type(self):
        session = SessionStateManager.create_session(None, None, 5, session_type="short_break")
        assert session.session_type == "short_break"

    def test_create_session_custom_context(self):
        session = SessionStateManager.create_session(None, None, 25, context="work")
        assert session.context == "work"

    def test_create_session_with_task_info(self):
        session = SessionStateManager.create_session("task-99", "Write tests", 45)
        assert session.task_id == "task-99"
        assert session.task_title == "Write tests"

    def test_end_time_offset_matches_duration(self):
        session = SessionStateManager.create_session(None, None, 60)
        delta = (session.end_datetime - session.start_datetime).total_seconds()
        assert abs(delta - 3600) < 5  # within 5 seconds tolerance


# ---------------------------------------------------------------------------
# pause_session
# ---------------------------------------------------------------------------


class TestPauseSession:
    def test_pause_active_session_changes_status(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="active")
        paused = mgr.pause_session(session)
        assert paused.status == "paused"

    def test_pause_sets_pause_time(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="active")
        paused = mgr.pause_session(session)
        assert paused.pause_time is not None

    def test_pause_persists_session(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="active")
        mgr.pause_session(session)
        loaded = mgr.load_session()
        assert loaded is not None
        assert loaded.status == "paused"

    def test_pause_already_paused_raises_value_error(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(
            status="paused",
            pause_time=datetime.now().astimezone().isoformat(),
        )
        with pytest.raises(ValueError, match="pause active"):
            mgr.pause_session(session)

    def test_pause_completed_raises_value_error(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="completed")
        with pytest.raises(ValueError):
            mgr.pause_session(session)


# ---------------------------------------------------------------------------
# resume_session
# ---------------------------------------------------------------------------


class TestResumeSession:
    def test_resume_paused_session_changes_status(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        pause_time = (datetime.now().astimezone() - timedelta(seconds=10)).isoformat()
        session = _make_state(
            status="paused", end_offset=25, pause_time=pause_time
        )
        resumed = mgr.resume_session(session)
        assert resumed.status == "active"

    def test_resume_clears_pause_time(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        pause_time = (datetime.now().astimezone() - timedelta(seconds=5)).isoformat()
        session = _make_state(
            status="paused", end_offset=25, pause_time=pause_time
        )
        resumed = mgr.resume_session(session)
        assert resumed.pause_time is None

    def test_resume_extends_end_time(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        original_end = datetime.now().astimezone() + timedelta(minutes=20)
        pause_at = datetime.now().astimezone() - timedelta(seconds=60)

        # Build session manually
        now_start = datetime.now().astimezone() - timedelta(minutes=5)
        session = SessionState(
            session_id="s",
            task_id=None,
            task_title=None,
            start_time=now_start.isoformat(),
            end_time=original_end.isoformat(),
            duration_minutes=25,
            status="paused",
            pause_time=pause_at.isoformat(),
        )

        resumed = mgr.resume_session(session)
        new_end = resumed.end_datetime
        # End time must be ~60 seconds later than original
        assert new_end > original_end

    def test_resume_accumulates_paused_seconds(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        pause_at = datetime.now().astimezone() - timedelta(seconds=30)
        session = _make_state(
            status="paused",
            end_offset=20,
            pause_time=pause_at.isoformat(),
            accumulated_paused_seconds=100,
        )
        resumed = mgr.resume_session(session)
        assert resumed.accumulated_paused_seconds >= 130  # 100 + 30

    def test_resume_active_raises_value_error(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="active")
        with pytest.raises(ValueError, match="resume paused"):
            mgr.resume_session(session)

    def test_resume_without_pause_time_raises_value_error(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state(status="paused", pause_time=None)
        with pytest.raises(ValueError):
            mgr.resume_session(session)

    def test_resume_persists_session(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        pause_time = (datetime.now().astimezone() - timedelta(seconds=5)).isoformat()
        session = _make_state(
            status="paused", end_offset=25, pause_time=pause_time
        )
        mgr.resume_session(session)
        loaded = mgr.load_session()
        assert loaded is not None
        assert loaded.status == "active"


# ---------------------------------------------------------------------------
# Convenience aliases
# ---------------------------------------------------------------------------


class TestConvenienceAliases:
    def test_save_alias(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state()
        mgr.save(session)
        assert mgr.state_file.exists()

    def test_load_alias(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        session = _make_state()
        mgr.save(session)
        loaded = mgr.load()
        assert loaded is not None
        assert loaded.session_id == session.session_id

    def test_delete_alias(self, tmp_path):
        mgr = SessionStateManager(state_dir=tmp_path)
        mgr.save(_make_state())
        mgr.delete()
        assert not mgr.state_file.exists()


# ---------------------------------------------------------------------------
# SessionStateManager default state_dir (lines 98-100)
# ---------------------------------------------------------------------------


class TestSessionStateManagerDefaultDir:
    def test_init_without_state_dir_uses_platformdirs(self, tmp_path):
        """When state_dir is None, it uses platformdirs to find the data dir."""
        fake_data_dir = str(tmp_path)

        with patch(
            "platformdirs.user_data_dir",
            return_value=fake_data_dir,
        ):
            from todopro_cli.models.focus.state import SessionStateManager

            mgr = SessionStateManager(state_dir=None)
            # State dir should be under the fake data dir
            assert str(tmp_path) in str(mgr.state_dir)
