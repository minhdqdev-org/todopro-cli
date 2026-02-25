"""Cross-platform keyboard input handler for timer controls."""

import sys
import termios
import tty
from typing import Optional


class KeyboardHandler:
    """Non-blocking keyboard input handler."""

    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = None
        self._setup()

    def _setup(self):
        """Setup terminal for non-blocking input."""
        try:
            self.old_settings = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        except Exception:
            # Windows or other platform
            pass

    def get_key(self) -> Optional[str]:
        """
        Get a single keypress without blocking.

        Returns the key character or None if no key pressed.
        """
        try:
            import select

            # Check if input is available (non-blocking)
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                return key.lower()
            return None
        except Exception:
            # Fallback for platforms without select
            return None

    def stop(self):
        """Restore terminal settings."""
        if self.old_settings:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass


# Windows alternative (if needed)
class WindowsKeyboardHandler:
    """Keyboard handler for Windows using msvcrt."""

    def __init__(self):
        try:
            import msvcrt

            self.msvcrt = msvcrt
        except ImportError:
            self.msvcrt = None

    def get_key(self) -> Optional[str]:
        """Get key on Windows."""
        if not self.msvcrt:
            return None

        if self.msvcrt.kbhit():
            key = self.msvcrt.getch()
            if isinstance(key, bytes):
                key = key.decode("utf-8", errors="ignore")
            return key.lower()
        return None

    def stop(self):
        """No cleanup needed on Windows."""
        pass
