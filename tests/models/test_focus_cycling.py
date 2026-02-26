"""Comprehensive unit tests for the Pomodoro cycling module.

Covers PomodoroConfig defaults/custom values and all CycleState
methods: next_phase, advance, get_duration, get_emoji,
get_progress_dots, to_dict/from_dict round-trip.
"""

from __future__ import annotations

import pytest

from todopro_cli.models.focus.cycling import CycleState, PomodoroConfig


# ---------------------------------------------------------------------------
# PomodoroConfig
# ---------------------------------------------------------------------------


class TestPomodoroConfig:
    """Tests for PomodoroConfig dataclass."""

    def test_default_values(self) -> None:
        """Default configuration should match standard Pomodoro timings."""
        config = PomodoroConfig()

        assert config.focus_duration == 25
        assert config.short_break == 5
        assert config.long_break == 15
        assert config.sessions_before_long_break == 4

    def test_custom_values(self) -> None:
        """Custom values override the defaults."""
        config = PomodoroConfig(
            focus_duration=50,
            short_break=10,
            long_break=30,
            sessions_before_long_break=2,
        )

        assert config.focus_duration == 50
        assert config.short_break == 10
        assert config.long_break == 30
        assert config.sessions_before_long_break == 2

    def test_partial_override(self) -> None:
        """Partially overriding keeps the remaining defaults intact."""
        config = PomodoroConfig(focus_duration=45)

        assert config.focus_duration == 45
        assert config.short_break == 5  # unchanged default
        assert config.long_break == 15  # unchanged default


# ---------------------------------------------------------------------------
# CycleState defaults
# ---------------------------------------------------------------------------


class TestCycleStateDefaults:
    """Tests for CycleState initial values."""

    def test_default_values(self) -> None:
        """A freshly created CycleState starts at cycle 1, session 1, focus phase."""
        state = CycleState()

        assert state.cycle_number == 1
        assert state.session_in_cycle == 1
        assert state.total_sessions_completed == 0
        assert state.current_phase == "focus"
        assert state.started_at is None


# ---------------------------------------------------------------------------
# CycleState.next_phase
# ---------------------------------------------------------------------------


class TestCycleStateNextPhase:
    """Tests for CycleState.next_phase()."""

    def test_focus_before_long_break_threshold_gives_short_break(self) -> None:
        """During focus, if session_in_cycle < sessions_before_long_break → short_break."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=1)

        assert state.next_phase(config) == "short_break"

    def test_focus_at_long_break_threshold_gives_long_break(self) -> None:
        """At the last session in a cycle, focus should transition to long_break."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=4)

        assert state.next_phase(config) == "long_break"

    def test_short_break_always_gives_focus(self) -> None:
        """After a short break, the next phase is always focus."""
        config = PomodoroConfig()
        state = CycleState(current_phase="short_break")

        assert state.next_phase(config) == "focus"

    def test_long_break_always_gives_focus(self) -> None:
        """After a long break, the next phase is always focus (new cycle)."""
        config = PomodoroConfig()
        state = CycleState(current_phase="long_break")

        assert state.next_phase(config) == "focus"

    def test_focus_session_2_of_4_gives_short_break(self) -> None:
        """Any session before the threshold results in a short break."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=2)

        assert state.next_phase(config) == "short_break"

    def test_focus_session_3_of_4_gives_short_break(self) -> None:
        """Session 3 out of 4 still results in a short break."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=3)

        assert state.next_phase(config) == "short_break"

    def test_custom_sessions_before_long_break(self) -> None:
        """Custom threshold (e.g. 2) triggers long_break at session 2."""
        config = PomodoroConfig(sessions_before_long_break=2)
        state_early = CycleState(current_phase="focus", session_in_cycle=1)
        state_at_threshold = CycleState(current_phase="focus", session_in_cycle=2)

        assert state_early.next_phase(config) == "short_break"
        assert state_at_threshold.next_phase(config) == "long_break"


# ---------------------------------------------------------------------------
# CycleState.advance
# ---------------------------------------------------------------------------


class TestCycleStateAdvance:
    """Tests for CycleState.advance()."""

    def test_advance_from_focus_increments_total_sessions(self) -> None:
        """Advancing from focus increments total_sessions_completed."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=1)

        state.advance(config)

        assert state.total_sessions_completed == 1

    def test_advance_from_focus_to_short_break(self) -> None:
        """Advancing from focus (session<threshold) moves to short_break."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=1)

        state.advance(config)

        assert state.current_phase == "short_break"

    def test_advance_from_focus_to_long_break_at_threshold(self) -> None:
        """Advancing from the final focus session moves to long_break."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=4)

        state.advance(config)

        assert state.current_phase == "long_break"
        assert state.total_sessions_completed == 1

    def test_advance_from_short_break_increments_session_in_cycle(self) -> None:
        """After a short break, session_in_cycle should increment."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="short_break", session_in_cycle=1)

        state.advance(config)

        assert state.current_phase == "focus"
        assert state.session_in_cycle == 2

    def test_advance_from_long_break_starts_new_cycle(self) -> None:
        """After a long break, cycle_number increments and session_in_cycle resets."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(
            current_phase="long_break",
            cycle_number=1,
            session_in_cycle=4,
        )

        state.advance(config)

        assert state.current_phase == "focus"
        assert state.cycle_number == 2
        assert state.session_in_cycle == 1

    def test_advance_sets_started_at(self) -> None:
        """After advancing, started_at is set to a non-None ISO string."""
        config = PomodoroConfig()
        state = CycleState(current_phase="focus", session_in_cycle=1)

        state.advance(config)

        assert state.started_at is not None
        # Should be parseable as ISO datetime
        from datetime import datetime

        dt = datetime.fromisoformat(state.started_at)
        assert isinstance(dt, datetime)

    def test_full_cycle_of_4_increments_correctly(self) -> None:
        """Walk through a full pomodoro cycle and verify all counters."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState()

        # Session 1: focus → short_break
        state.advance(config)
        assert state.current_phase == "short_break"
        assert state.total_sessions_completed == 1

        # Short break → focus (session 2)
        state.advance(config)
        assert state.current_phase == "focus"
        assert state.session_in_cycle == 2

        # Session 2: focus → short_break
        state.advance(config)
        assert state.current_phase == "short_break"
        assert state.total_sessions_completed == 2

        # Short break → focus (session 3)
        state.advance(config)
        assert state.current_phase == "focus"
        assert state.session_in_cycle == 3

        # Session 3: focus → short_break
        state.advance(config)
        assert state.current_phase == "short_break"
        assert state.total_sessions_completed == 3

        # Short break → focus (session 4)
        state.advance(config)
        assert state.current_phase == "focus"
        assert state.session_in_cycle == 4

        # Session 4: focus → long_break
        state.advance(config)
        assert state.current_phase == "long_break"
        assert state.total_sessions_completed == 4

        # Long break → focus (new cycle 2)
        state.advance(config)
        assert state.current_phase == "focus"
        assert state.cycle_number == 2
        assert state.session_in_cycle == 1
        assert state.total_sessions_completed == 4  # unchanged after long break


# ---------------------------------------------------------------------------
# CycleState.get_duration
# ---------------------------------------------------------------------------


class TestCycleStateGetDuration:
    """Tests for CycleState.get_duration()."""

    def test_focus_duration(self) -> None:
        """Returns config.focus_duration during focus phase."""
        config = PomodoroConfig(focus_duration=25)
        state = CycleState(current_phase="focus")

        assert state.get_duration(config) == 25

    def test_short_break_duration(self) -> None:
        """Returns config.short_break during short_break phase."""
        config = PomodoroConfig(short_break=5)
        state = CycleState(current_phase="short_break")

        assert state.get_duration(config) == 5

    def test_long_break_duration(self) -> None:
        """Returns config.long_break during long_break phase."""
        config = PomodoroConfig(long_break=15)
        state = CycleState(current_phase="long_break")

        assert state.get_duration(config) == 15

    def test_custom_durations(self) -> None:
        """Custom durations are correctly reflected for each phase."""
        config = PomodoroConfig(focus_duration=50, short_break=10, long_break=30)

        assert CycleState(current_phase="focus").get_duration(config) == 50
        assert CycleState(current_phase="short_break").get_duration(config) == 10
        assert CycleState(current_phase="long_break").get_duration(config) == 30


# ---------------------------------------------------------------------------
# CycleState.get_emoji
# ---------------------------------------------------------------------------


class TestCycleStateGetEmoji:
    """Tests for CycleState.get_emoji()."""

    def test_focus_emoji(self) -> None:
        """Focus phase emoji is a tomato 🍅."""
        state = CycleState(current_phase="focus")
        assert state.get_emoji() == "🍅"

    def test_short_break_emoji(self) -> None:
        """Short break phase emoji is a coffee ☕."""
        state = CycleState(current_phase="short_break")
        assert state.get_emoji() == "☕"

    def test_long_break_emoji(self) -> None:
        """Long break phase emoji is a palm tree 🌴."""
        state = CycleState(current_phase="long_break")
        assert state.get_emoji() == "🌴"


# ---------------------------------------------------------------------------
# CycleState.get_progress_dots
# ---------------------------------------------------------------------------


class TestCycleStateGetProgressDots:
    """Tests for CycleState.get_progress_dots()."""

    def test_first_session_in_focus_shows_current_dot(self) -> None:
        """Session 1, focus phase: first dot is ◉, rest are ○."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=1)

        dots = state.get_progress_dots(config)
        dot_list = dots.split(" ")

        assert dot_list[0] == "◉"
        assert all(d == "○" for d in dot_list[1:])

    def test_later_session_shows_completed_dots(self) -> None:
        """By session 3, two previous dots are ⬤ and the current is ◉."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=3)

        dots = state.get_progress_dots(config)
        dot_list = dots.split(" ")

        assert dot_list[0] == "⬤"  # session 1 done
        assert dot_list[1] == "⬤"  # session 2 done
        assert dot_list[2] == "◉"  # session 3 current
        assert dot_list[3] == "○"  # session 4 upcoming

    def test_short_break_shows_all_upcoming_for_current_position(self) -> None:
        """During a short break session_in_cycle=1, current is not focus → all ○."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="short_break", session_in_cycle=1)

        dots = state.get_progress_dots(config)
        dot_list = dots.split(" ")

        # session_in_cycle=1, current_phase != focus → no ◉ for session 1
        # but sessions 0 (< 1) → ⬤, i=1 not (current and focus) → ○
        # Actually: for i in range(1, 5):
        #   i=1: not (i < 1), not (i==1 and focus) → ○
        #   i=2..4: ○
        assert all(d == "○" for d in dot_list)

    def test_number_of_dots_equals_sessions_before_long_break(self) -> None:
        """The total number of dots always equals sessions_before_long_break."""
        for n in [2, 3, 4, 6]:
            config = PomodoroConfig(sessions_before_long_break=n)
            state = CycleState(current_phase="focus", session_in_cycle=1)
            dots = state.get_progress_dots(config)
            assert len(dots.split(" ")) == n

    def test_last_session_shows_all_but_last_completed(self) -> None:
        """At session_in_cycle == sessions_before_long_break, n-1 ⬤ then ◉."""
        config = PomodoroConfig(sessions_before_long_break=4)
        state = CycleState(current_phase="focus", session_in_cycle=4)

        dots = state.get_progress_dots(config)
        dot_list = dots.split(" ")

        assert dot_list[0] == "⬤"
        assert dot_list[1] == "⬤"
        assert dot_list[2] == "⬤"
        assert dot_list[3] == "◉"


# ---------------------------------------------------------------------------
# CycleState serialisation
# ---------------------------------------------------------------------------


class TestCycleStateSerialization:
    """Tests for CycleState.to_dict() and CycleState.from_dict()."""

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict returns a dict with the five expected keys."""
        state = CycleState(
            cycle_number=2,
            session_in_cycle=3,
            total_sessions_completed=7,
            current_phase="short_break",
            started_at="2024-06-15T10:30:00",
        )

        d = state.to_dict()

        assert d == {
            "cycle_number": 2,
            "session_in_cycle": 3,
            "total_sessions_completed": 7,
            "current_phase": "short_break",
            "started_at": "2024-06-15T10:30:00",
        }

    def test_from_dict_creates_equivalent_state(self) -> None:
        """from_dict reconstructs a CycleState identical to the original."""
        original = CycleState(
            cycle_number=3,
            session_in_cycle=2,
            total_sessions_completed=10,
            current_phase="long_break",
            started_at="2024-06-15T14:00:00",
        )

        restored = CycleState.from_dict(original.to_dict())

        assert restored.cycle_number == original.cycle_number
        assert restored.session_in_cycle == original.session_in_cycle
        assert restored.total_sessions_completed == original.total_sessions_completed
        assert restored.current_phase == original.current_phase
        assert restored.started_at == original.started_at

    def test_round_trip_with_defaults(self) -> None:
        """A default-constructed CycleState survives a to_dict/from_dict round-trip."""
        state = CycleState()
        restored = CycleState.from_dict(state.to_dict())

        assert restored.cycle_number == 1
        assert restored.session_in_cycle == 1
        assert restored.total_sessions_completed == 0
        assert restored.current_phase == "focus"
        assert restored.started_at is None

    def test_to_dict_returns_plain_dict(self) -> None:
        """to_dict output is a plain Python dict (not a dataclass instance)."""
        state = CycleState()
        assert isinstance(state.to_dict(), dict)


# ---------------------------------------------------------------------------
# CycleState.next_phase – fallback branch (line 47)
# ---------------------------------------------------------------------------


class TestCycleStateNextPhaseFallback:
    """Test the final fallback 'return focus' in next_phase."""

    def test_unknown_phase_returns_focus(self) -> None:
        """An unexpected current_phase value triggers the fallback to 'focus'."""
        config = PomodoroConfig()
        # Bypass type-checking by injecting an invalid phase directly
        state = CycleState(current_phase="focus")
        object.__setattr__(state, "current_phase", "unknown_phase")  # type: ignore[arg-type]

        result = state.next_phase(config)
        assert result == "focus"
