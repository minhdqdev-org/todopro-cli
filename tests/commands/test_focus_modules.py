"""Unit tests for todopro_cli.focus package.

Covers:
  - focus/__init__.py  (re-exports from models.focus)
  - focus/ui.py        (re-exports from models.focus.ui)
"""


class TestFocusPackageReExports:
    """focus/__init__.py re-exports from todopro_cli.models.focus."""

    def test_import_focus_package(self):
        import todopro_cli.focus  # noqa: F401

    def test_session_state_exported(self):
        from todopro_cli.focus import SessionState

        assert SessionState is not None

    def test_session_state_manager_exported(self):
        from todopro_cli.focus import SessionStateManager

        assert SessionStateManager is not None

    def test_timer_display_exported(self):
        from todopro_cli.focus import TimerDisplay

        assert TimerDisplay is not None

    def test_keyboard_handler_exported(self):
        from todopro_cli.focus import KeyboardHandler

        assert KeyboardHandler is not None

    def test_history_logger_exported(self):
        from todopro_cli.focus import HistoryLogger

        assert HistoryLogger is not None

    def test_show_completion_message_exported(self):
        from todopro_cli.focus import show_completion_message

        assert callable(show_completion_message)

    def test_show_stopped_message_exported(self):
        from todopro_cli.focus import show_stopped_message

        assert callable(show_stopped_message)

    def test_all_contains_expected_names(self):
        import todopro_cli.focus as focus_pkg

        expected = {
            "SessionState",
            "SessionStateManager",
            "TimerDisplay",
            "KeyboardHandler",
            "HistoryLogger",
            "show_completion_message",
            "show_stopped_message",
        }
        assert expected.issubset(set(focus_pkg.__all__))

    def test_re_exported_classes_are_same_as_source(self):
        """Re-exports should be the same objects as the originals."""
        from todopro_cli.focus import SessionState as FocusSessionState
        from todopro_cli.models.focus import SessionState as ModelSessionState

        assert FocusSessionState is ModelSessionState


class TestFocusUiReExports:
    """focus/ui.py re-exports from todopro_cli.models.focus.ui."""

    def test_import_focus_ui(self):
        import todopro_cli.focus.ui  # noqa: F401

    def test_timer_display_exported(self):
        from todopro_cli.focus.ui import TimerDisplay

        assert TimerDisplay is not None

    def test_show_completion_message_exported(self):
        from todopro_cli.focus.ui import show_completion_message

        assert callable(show_completion_message)

    def test_show_stopped_message_exported(self):
        from todopro_cli.focus.ui import show_stopped_message

        assert callable(show_stopped_message)

    def test_all_contains_expected_names(self):
        import todopro_cli.focus.ui as ui_pkg

        expected = {"TimerDisplay", "show_completion_message", "show_stopped_message"}
        assert expected.issubset(set(ui_pkg.__all__))

    def test_ui_timer_display_is_same_as_source(self):
        """focus.ui.TimerDisplay should be the same as models.focus.ui.TimerDisplay."""
        from todopro_cli.focus.ui import TimerDisplay as UiTimerDisplay
        from todopro_cli.models.focus.ui import TimerDisplay as ModelTimerDisplay

        assert UiTimerDisplay is ModelTimerDisplay

    def test_focus_and_ui_timer_display_are_same(self):
        """focus.TimerDisplay and focus.ui.TimerDisplay are the same class."""
        from todopro_cli.focus import TimerDisplay as FocusTimerDisplay
        from todopro_cli.focus.ui import TimerDisplay as UiTimerDisplay

        assert FocusTimerDisplay is UiTimerDisplay
