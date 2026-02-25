"""Unit tests for reminder management in set_command and delete_command."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.delete_command import app as delete_app
from todopro_cli.commands.set_command import app as set_app

set_runner = CliRunner()
delete_runner = CliRunner()


class TestSetReminder:
    """Tests for 'todopro set reminder <task-id> <when>'."""

    def test_set_reminder_help(self):
        result = set_runner.invoke(set_app, ["reminder", "--help"])
        assert result.exit_code == 0
        assert "reminder" in result.stdout.lower()
        assert "30min" in result.stdout or "1h" in result.stdout

    def test_set_reminder_30min(self):
        """set reminder with '30min' should call set_reminder with a future ISO datetime."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        reminder_resp = {
            "id": "rem-1",
            "task_id": "task-1",
            "reminder_date": "2025-07-01T10:30:00+00:00",
        }
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock(return_value=reminder_resp)
        with patch(
            "todopro_cli.commands.set_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.set_command.TasksAPI", return_value=mock_api
            ):
                result = set_runner.invoke(set_app, ["reminder", "task-1", "30min"])
        assert result.exit_code == 0
        mock_api.set_reminder.assert_awaited_once()
        call_args = mock_api.set_reminder.call_args
        assert call_args.args[0] == "task-1"
        # The ISO string passed should parse to a future datetime
        from datetime import datetime
        from datetime import timezone as tz

        passed_dt = datetime.fromisoformat(call_args.args[1])
        assert passed_dt > datetime.now(tz=tz.utc)

    def test_set_reminder_1h(self):
        """set reminder with '1h' should work."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock(
            return_value={"id": "rem-2", "task_id": "task-2"}
        )
        with patch(
            "todopro_cli.commands.set_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.set_command.TasksAPI", return_value=mock_api
            ):
                result = set_runner.invoke(set_app, ["reminder", "task-2", "1h"])
        assert result.exit_code == 0

    def test_set_reminder_iso_datetime(self):
        """set reminder with ISO datetime should be accepted."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock(
            return_value={"id": "rem-3", "task_id": "task-3"}
        )
        # Use a far-future datetime to avoid "past" rejection
        future = "2099-12-31T23:59:00"
        with patch(
            "todopro_cli.commands.set_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.set_command.TasksAPI", return_value=mock_api
            ):
                result = set_runner.invoke(set_app, ["reminder", "task-3", future])
        assert result.exit_code == 0

    def test_set_reminder_invalid_format_exits(self):
        """Invalid time format should exit with error."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock()
        with patch(
            "todopro_cli.commands.set_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.set_command.TasksAPI", return_value=mock_api
            ):
                result = set_runner.invoke(
                    set_app, ["reminder", "task-4", "not-a-time"]
                )
        assert result.exit_code != 0

    def test_set_reminder_past_datetime_exits(self):
        """A reminder in the past should exit with an error."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock()
        with patch(
            "todopro_cli.commands.set_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.set_command.TasksAPI", return_value=mock_api
            ):
                result = set_runner.invoke(
                    set_app, ["reminder", "task-5", "2000-01-01T00:00:00"]
                )
        assert result.exit_code != 0

    def test_set_reminder_calls_close_on_success(self):
        """API client should be closed after setting a reminder."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.set_reminder = AsyncMock(return_value={"id": "rem-5", "task_id": "t5"})
        with patch(
            "todopro_cli.commands.set_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.set_command.TasksAPI", return_value=mock_api
            ):
                set_runner.invoke(set_app, ["reminder", "t5", "2h"])
        mock_client.close.assert_awaited_once()


class TestDeleteReminder:
    """Tests for 'todopro delete reminder <task-id> <reminder-id>'."""

    def test_delete_reminder_help(self):
        result = delete_runner.invoke(delete_app, ["reminder", "--help"])
        assert result.exit_code == 0

    def test_delete_reminder_with_force(self):
        """delete reminder --force should skip confirmation."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_reminder = AsyncMock(return_value=None)
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.TasksAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(
                    delete_app, ["reminder", "task-1", "rem-1", "--force"]
                )
        assert result.exit_code == 0
        mock_api.delete_reminder.assert_awaited_once_with("task-1", "rem-1")

    def test_delete_reminder_confirm_yes(self):
        """delete reminder should confirm and proceed."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_reminder = AsyncMock(return_value=None)
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.TasksAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(
                    delete_app, ["reminder", "task-2", "rem-2"], input="y\n"
                )
        assert result.exit_code == 0

    def test_delete_reminder_confirm_no_cancels(self):
        """Declining the confirmation should not delete."""
        mock_client = MagicMock()
        mock_client.close = AsyncMock()
        mock_api = MagicMock()
        mock_api.delete_reminder = AsyncMock(return_value=None)
        with patch(
            "todopro_cli.commands.delete_command.get_client", return_value=mock_client
        ):
            with patch(
                "todopro_cli.commands.delete_command.TasksAPI", return_value=mock_api
            ):
                result = delete_runner.invoke(
                    delete_app, ["reminder", "task-3", "rem-3"], input="n\n"
                )
        mock_api.delete_reminder.assert_not_awaited()
