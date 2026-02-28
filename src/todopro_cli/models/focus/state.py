"""Session state management with persistent storage."""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

SessionStatus = Literal["active", "paused", "completed", "cancelled"]
SessionType = Literal["focus", "short_break", "long_break"]


@dataclass
class SessionState:
    """Represents a focus session state."""

    session_id: str
    task_id: str | None
    task_title: str | None
    start_time: str  # ISO 8601
    end_time: str  # ISO 8601
    duration_minutes: int
    status: SessionStatus
    session_type: SessionType = "focus"
    pause_time: str | None = None
    accumulated_paused_seconds: int = 0
    context: str = "default"

    @property
    def start_datetime(self) -> datetime:
        """Parse start time as datetime."""
        return datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))

    @property
    def end_datetime(self) -> datetime:
        """Parse end time as datetime."""
        return datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))

    @property
    def pause_datetime(self) -> datetime | None:
        """Parse pause time as datetime."""
        if self.pause_time:
            return datetime.fromisoformat(self.pause_time.replace("Z", "+00:00"))
        return None

    def time_remaining(self) -> int:
        """Calculate seconds remaining in session."""
        now = datetime.now().astimezone()
        end = self.end_datetime

        # If paused, return time remaining at pause
        if self.status == "paused" and self.pause_datetime:
            remaining = (end - self.pause_datetime).total_seconds()
        else:
            remaining = (end - now).total_seconds()

        return max(0, int(remaining))

    def time_elapsed(self) -> int:
        """Calculate seconds elapsed in session (excluding paused time)."""
        now = datetime.now().astimezone()
        start = self.start_datetime

        if self.status == "paused" and self.pause_datetime:
            elapsed = (self.pause_datetime - start).total_seconds()
        else:
            elapsed = (now - start).total_seconds()

        # Subtract paused time
        actual_elapsed = elapsed - self.accumulated_paused_seconds
        return max(0, int(actual_elapsed))

    def actual_focus_seconds(self) -> int:
        """Calculate actual focus time (alias for time_elapsed)."""
        return self.time_elapsed()

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return self.time_remaining() == 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Create from dictionary."""
        return cls(**data)


class SessionStateManager:
    """Manages session state persistence."""

    def __init__(self, state_dir: Path | None = None):
        """Initialize state manager."""
        if state_dir is None:
            from platformdirs import user_data_dir

            state_dir = Path(user_data_dir("todopro", "minhdq")) / "state"

        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.state_dir / "current_session.json"

    def save_session(self, session: SessionState) -> None:
        """Save session state to file."""
        with open(self.state_file, "w") as f:
            json.dump(session.to_dict(), f, indent=2)

        # Set secure permissions
        self.state_file.chmod(0o600)

    def load_session(self) -> SessionState | None:
        """Load session state from file. Returns None if file missing or invalid."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file) as f:
                data = json.load(f)
            return SessionState.from_dict(data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def delete_session(self) -> None:
        """Delete session state file."""
        if self.state_file.exists():
            self.state_file.unlink()

    def has_active_session(self) -> bool:
        """Check if an active session exists."""
        try:
            session = self.load_session()
            return session is not None and session.status in ("active", "paused")
        except (FileNotFoundError, ValueError):
            return False

    @staticmethod
    def create_session(
        task_id: str | None,
        task_title: str | None,
        duration_minutes: int,
        session_type: SessionType = "focus",
        context: str = "default",
    ) -> SessionState:
        """Create a new session state."""
        now = datetime.now().astimezone()
        end = now + timedelta(minutes=duration_minutes)

        return SessionState(
            session_id=str(uuid.uuid4()),
            task_id=task_id,
            task_title=task_title,
            start_time=now.isoformat(),
            end_time=end.isoformat(),
            duration_minutes=duration_minutes,
            status="active",
            session_type=session_type,
            context=context,
        )

    def pause_session(self, session: SessionState) -> SessionState:
        """Pause an active session."""
        if session.status != "active":
            raise ValueError("Can only pause active sessions")

        now = datetime.now().astimezone()
        session.status = "paused"
        session.pause_time = now.isoformat()

        self.save_session(session)
        return session

    def resume_session(self, session: SessionState) -> SessionState:
        """Resume a paused session."""
        if session.status != "paused":
            raise ValueError("Can only resume paused sessions")

        if not session.pause_datetime:
            raise ValueError("Pause time not set")

        now = datetime.now().astimezone()

        # Calculate paused duration
        paused_duration = (now - session.pause_datetime).total_seconds()
        session.accumulated_paused_seconds += int(paused_duration)

        # Extend end time by paused duration
        end = session.end_datetime + timedelta(seconds=paused_duration)
        session.end_time = end.isoformat()

        # Update status
        session.status = "active"
        session.pause_time = None

        self.save_session(session)
        return session

    # Convenience aliases for backwards compatibility
    def save(self, session: SessionState) -> None:
        """Alias for save_session."""
        self.save_session(session)

    def load(self) -> SessionState | None:
        """Alias for load_session."""
        return self.load_session()

    def delete(self) -> None:
        """Alias for delete_session."""
        self.delete_session()
