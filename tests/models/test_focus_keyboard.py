"""Unit tests for KeyboardHandler and WindowsKeyboardHandler.

All terminal / OS-level calls are mocked so tests run in any CI environment
without requiring a real TTY or Windows.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch


def _make_keyboard_handler(mocker, old_settings=None):
    """Create a KeyboardHandler with all terminal calls patched."""
    mocker.patch("sys.stdin.fileno", return_value=0)
    mocker.patch("termios.tcgetattr", return_value=old_settings or ["saved"])
    mocker.patch("tty.setcbreak")
    from todopro_cli.models.focus.keyboard import KeyboardHandler
    return KeyboardHandler()


# ---------------------------------------------------------------------------
# KeyboardHandler
# ---------------------------------------------------------------------------


class TestKeyboardHandlerSetup:
    def test_init_stores_fd(self, mocker):
        """__init__ stores the stdin file descriptor."""
        handler = _make_keyboard_handler(mocker)
        assert handler.fd == 0  # mocked fileno() returns 0

    def test_init_saves_old_settings(self, mocker):
        """__init__ saves old terminal settings via tcgetattr."""
        sentinel = ["saved_settings"]
        handler = _make_keyboard_handler(mocker, old_settings=sentinel)
        assert handler.old_settings == sentinel

    def test_setup_handles_exception_gracefully(self, mocker):
        """_setup must not propagate exceptions (e.g. on non-TTY environments)."""
        mocker.patch("sys.stdin.fileno", return_value=0)
        mocker.patch("termios.tcgetattr", side_effect=Exception("no tty"))
        mocker.patch("tty.setcbreak")

        from todopro_cli.models.focus.keyboard import KeyboardHandler

        # Should not raise
        handler = KeyboardHandler()
        assert handler.old_settings is None

    def test_setup_calls_setcbreak(self, mocker):
        """_setup calls tty.setcbreak to put terminal in cbreak mode."""
        mocker.patch("sys.stdin.fileno", return_value=0)
        mocker.patch("termios.tcgetattr", return_value=["settings"])
        mock_setcbreak = mocker.patch("tty.setcbreak")

        from todopro_cli.models.focus.keyboard import KeyboardHandler

        KeyboardHandler()
        mock_setcbreak.assert_called_once()


class TestKeyboardHandlerGetKey:
    def test_returns_key_when_input_available(self, mocker):
        handler = _make_keyboard_handler(mocker)

        # select.select reports input ready
        mocker.patch("select.select", return_value=([sys.stdin], [], []))
        mocker.patch.object(sys.stdin, "read", return_value="P")

        key = handler.get_key()
        assert key == "p"  # lowercased

    def test_returns_none_when_no_input(self, mocker):
        handler = _make_keyboard_handler(mocker)

        mocker.patch("select.select", return_value=([], [], []))

        key = handler.get_key()
        assert key is None

    def test_returns_lowercase_key(self, mocker):
        handler = _make_keyboard_handler(mocker)

        mocker.patch("select.select", return_value=([sys.stdin], [], []))
        mocker.patch.object(sys.stdin, "read", return_value="Q")

        assert handler.get_key() == "q"

    def test_returns_none_on_exception(self, mocker):
        """get_key must return None when select raises an exception."""
        handler = _make_keyboard_handler(mocker)

        mocker.patch("select.select", side_effect=Exception("broken pipe"))

        assert handler.get_key() is None


class TestKeyboardHandlerStop:
    def test_stop_restores_settings(self, mocker):
        mock_setattr = mocker.patch("termios.tcsetattr")
        handler = _make_keyboard_handler(mocker)
        handler.stop()
        mock_setattr.assert_called_once()

    def test_stop_does_nothing_when_no_old_settings(self, mocker):
        mock_setattr = mocker.patch("termios.tcsetattr")
        mocker.patch("sys.stdin.fileno", return_value=0)
        mocker.patch("termios.tcgetattr", side_effect=Exception("no tty"))
        mocker.patch("tty.setcbreak")

        from todopro_cli.models.focus.keyboard import KeyboardHandler

        handler = KeyboardHandler()
        assert handler.old_settings is None
        handler.stop()  # must not raise

        mock_setattr.assert_not_called()

    def test_stop_handles_exception_in_tcsetattr(self, mocker):
        mocker.patch("sys.stdin.fileno", return_value=0)
        mocker.patch("termios.tcgetattr", return_value=["saved"])
        mocker.patch("tty.setcbreak")
        mocker.patch("termios.tcsetattr", side_effect=Exception("broken"))

        from todopro_cli.models.focus.keyboard import KeyboardHandler

        handler = KeyboardHandler()
        handler.stop()  # must not raise


# ---------------------------------------------------------------------------
# WindowsKeyboardHandler
# ---------------------------------------------------------------------------


class TestWindowsKeyboardHandler:
    def test_get_key_returns_none_when_no_key_hit(self):
        msvcrt_mock = MagicMock()
        msvcrt_mock.kbhit.return_value = False

        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        handler.msvcrt = msvcrt_mock

        assert handler.get_key() is None

    def test_get_key_returns_lowercase_char(self):
        msvcrt_mock = MagicMock()
        msvcrt_mock.kbhit.return_value = True
        msvcrt_mock.getch.return_value = b"S"

        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        handler.msvcrt = msvcrt_mock

        assert handler.get_key() == "s"

    def test_get_key_handles_str_result(self):
        """getch can return a str on some Windows versions."""
        msvcrt_mock = MagicMock()
        msvcrt_mock.kbhit.return_value = True
        msvcrt_mock.getch.return_value = "A"  # already str, not bytes

        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        handler.msvcrt = msvcrt_mock

        assert handler.get_key() == "a"

    def test_get_key_returns_none_when_msvcrt_unavailable(self):
        """If msvcrt could not be imported, get_key returns None."""
        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        handler.msvcrt = None

        assert handler.get_key() is None

    def test_stop_is_noop(self):
        """stop() should succeed without doing anything."""
        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        handler.stop()  # must not raise

    def test_init_sets_msvcrt_attribute(self):
        """WindowsKeyboardHandler.__init__ tries to import msvcrt."""
        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        # msvcrt is either the real module or None — both are valid
        assert hasattr(handler, "msvcrt")


    def test_get_key_returns_none_when_no_key_pressed(self):
        """get_key returns None when kbhit() reports no key pressed (line 61)."""
        msvcrt_mock = MagicMock()
        msvcrt_mock.kbhit.return_value = False  # no key in buffer

        from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler

        handler = WindowsKeyboardHandler()
        handler.msvcrt = msvcrt_mock

        result = handler.get_key()
        assert result is None


class TestWindowsKeyboardHandlerMsvcrtSuccess:
    def test_init_with_mocked_msvcrt(self):
        """Test that msvcrt is assigned when import succeeds (line 61)."""
        import sys
        from unittest.mock import MagicMock, patch

        fake_msvcrt = MagicMock()

        # Temporarily inject msvcrt into sys.modules so the import succeeds
        with patch.dict(sys.modules, {"msvcrt": fake_msvcrt}):
            from todopro_cli.models.focus.keyboard import WindowsKeyboardHandler
            import importlib
            import todopro_cli.models.focus.keyboard as kb_module
            importlib.reload(kb_module)
            handler = kb_module.WindowsKeyboardHandler()
            assert handler.msvcrt is fake_msvcrt
