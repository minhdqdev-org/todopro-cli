"""Auto-Pomodoro cycling system."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class PomodoroConfig:
    """Configuration for Pomodoro cycling."""

    focus_duration: int = 25  # minutes
    short_break: int = 5  # minutes
    long_break: int = 15  # minutes
    sessions_before_long_break: int = 4


@dataclass
class CycleState:
    """Current state of the Pomodoro cycle."""

    cycle_number: int = 1
    session_in_cycle: int = 1
    total_sessions_completed: int = 0
    current_phase: Literal["focus", "short_break", "long_break"] = "focus"
    started_at: str | None = None

    def next_phase(
        self, config: PomodoroConfig
    ) -> Literal["focus", "short_break", "long_break"]:
        """Determine the next phase in the cycle."""
        if self.current_phase == "focus":
            # After focus, check if it's time for long break
            if self.session_in_cycle >= config.sessions_before_long_break:
                return "long_break"
            else:
                return "short_break"

        elif self.current_phase == "short_break":
            # After short break, always go to focus
            return "focus"

        elif self.current_phase == "long_break":
            # After long break, start new cycle
            return "focus"

        return "focus"

    def advance(self, config: PomodoroConfig) -> None:
        """Advance to next phase in the cycle."""
        next_phase = self.next_phase(config)

        if self.current_phase == "focus":
            self.total_sessions_completed += 1

        if self.current_phase == "long_break":
            # Starting new cycle
            self.cycle_number += 1
            self.session_in_cycle = 1
        elif next_phase == "focus" and self.current_phase == "short_break":
            # Completed a session, increment
            self.session_in_cycle += 1

        self.current_phase = next_phase
        self.started_at = datetime.now().isoformat()

    def get_duration(self, config: PomodoroConfig) -> int:
        """Get duration in minutes for current phase."""
        if self.current_phase == "focus":
            return config.focus_duration
        elif self.current_phase == "short_break":
            return config.short_break
        else:  # long_break
            return config.long_break

    def get_emoji(self) -> str:
        """Get emoji for current phase."""
        if self.current_phase == "focus":
            return "🍅"
        elif self.current_phase == "short_break":
            return "☕"
        else:
            return "🌴"

    def get_progress_dots(self, config: PomodoroConfig) -> str:
        """Get progress dots showing cycle position."""
        dots = []
        for i in range(1, config.sessions_before_long_break + 1):
            if i < self.session_in_cycle:
                dots.append("⬤")  # Completed
            elif i == self.session_in_cycle and self.current_phase == "focus":
                dots.append("◉")  # Current
            else:
                dots.append("○")  # Upcoming

        return " ".join(dots)

    def to_dict(self) -> dict:
        """Convert to dictionary for persistence."""
        return {
            "cycle_number": self.cycle_number,
            "session_in_cycle": self.session_in_cycle,
            "total_sessions_completed": self.total_sessions_completed,
            "current_phase": self.current_phase,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CycleState":
        """Create from dictionary."""
        return cls(**data)
