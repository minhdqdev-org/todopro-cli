"""Unit tests for calendar_command."""
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.calendar_command import app

runner = CliRunner()


def _mock_api(method: str, return_value: dict):
    """Patch one of the internal async API helpers."""
    return patch(
        f"todopro_cli.commands.calendar_command.{method}",
        new=AsyncMock(return_value=return_value),
    )


# ---------------------------------------------------------------------------
# --help smoke tests
# ---------------------------------------------------------------------------


def test_connect_help():
    result = runner.invoke(app, ["connect", "--help"])
    assert result.exit_code == 0


def test_disconnect_help():
    result = runner.invoke(app, ["disconnect", "--help"])
    assert result.exit_code == 0


def test_status_help():
    result = runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0


def test_list_help():
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0


def test_push_help():
    result = runner.invoke(app, ["push", "--help"])
    assert result.exit_code == 0


def test_pull_help():
    result = runner.invoke(app, ["pull", "--help"])
    assert result.exit_code == 0


def test_sync_help():
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0


def test_configure_help():
    result = runner.invoke(app, ["configure", "--help"])
    assert result.exit_code == 0


def test_describe_help():
    result = runner.invoke(app, ["describe", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


def test_status_not_connected():
    with _mock_api("_api_get", {"connected": False}):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "not connected" in result.output.lower() or "Not connected" in result.output


def test_status_connected():
    with _mock_api(
        "_api_get",
        {
            "connected": True,
            "email": "user@example.com",
            "connected_at": "2027-01-01T00:00:00Z",
        },
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Connected" in result.output


def test_status_error():
    with _mock_api("_api_get", {"error": "Unauthorised"}):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# disconnect
# ---------------------------------------------------------------------------


def test_disconnect_success():
    with _mock_api("_api_delete", {"status": "disconnected"}):
        result = runner.invoke(app, ["disconnect"])
    assert result.exit_code == 0
    assert "disconnected" in result.output.lower()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_list_calendars_success():
    calendars = [{"id": "cal1", "summary": "My Calendar", "timeZone": "UTC"}]
    with _mock_api("_api_get", {"calendars": calendars}):
        result = runner.invoke(app, ["list", "calendars"])
    assert result.exit_code == 0
    assert "My Calendar" in result.output


def test_list_calendars_empty():
    with _mock_api("_api_get", {"calendars": []}):
        result = runner.invoke(app, ["list", "calendars"])
    assert result.exit_code == 0
    assert "No calendars" in result.output


def test_list_calendars_error():
    with _mock_api("_api_get", {"error": "Google Calendar not connected"}):
        result = runner.invoke(app, ["list", "calendars"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_list_unknown_resource():
    result = runner.invoke(app, ["list", "events"])
    assert result.exit_code == 1
    assert "Unknown resource" in result.output


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


def test_push_success():
    with _mock_api(
        "_api_post", {"status": "pushed", "created": 5, "updated": 2, "skipped": 1}
    ):
        result = runner.invoke(app, ["push"])
    assert result.exit_code == 0
    assert "5" in result.output


def test_push_with_project():
    with _mock_api("_api_post", {"created": 3, "updated": 0, "skipped": 0}):
        result = runner.invoke(app, ["push", "--project", "proj-123"])
    assert result.exit_code == 0


def test_push_error():
    with _mock_api("_api_post", {"error": "Google Calendar not connected"}):
        result = runner.invoke(app, ["push"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


def test_pull_success():
    with _mock_api("_api_post", {"status": "pulled", "created": 4, "skipped": 0}):
        result = runner.invoke(app, ["pull"])
    assert result.exit_code == 0
    assert "4" in result.output


def test_pull_with_calendar_id():
    with _mock_api("_api_post", {"created": 2, "skipped": 0}):
        result = runner.invoke(app, ["pull", "--calendar-id", "cal1"])
    assert result.exit_code == 0


def test_pull_error():
    with _mock_api("_api_post", {"error": "Google Calendar not connected"}):
        result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


def test_sync_success():
    with _mock_api("_api_post", {"status": "synced", "created": 0, "updated": 1, "skipped": 0}):
        result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    assert "Sync complete" in result.output


def test_sync_status():
    with _mock_api(
        "_api_get",
        {"last_synced_at": "2027-01-01T00:00:00Z", "stats": {"created": 5}},
    ):
        result = runner.invoke(app, ["sync", "--status"])
    assert result.exit_code == 0
    assert "2027" in result.output


def test_sync_error():
    with _mock_api("_api_post", {"error": "Google Calendar not connected"}):
        result = runner.invoke(app, ["sync"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------


def test_configure_success():
    with _mock_api("_api_post", {"status": "saved"}):
        result = runner.invoke(app, ["configure", "--push-on-create"])
    assert result.exit_code == 0
    assert "saved" in result.output.lower() or "Configuration" in result.output


def test_configure_no_push_on_complete():
    with _mock_api("_api_post", {"status": "saved"}):
        result = runner.invoke(app, ["configure", "--no-push-on-complete"])
    assert result.exit_code == 0


def test_configure_error():
    with _mock_api("_api_post", {"error": "Unauthorised"}):
        result = runner.invoke(app, ["configure", "--push-on-create"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# describe
# ---------------------------------------------------------------------------


def test_describe_config_empty():
    with _mock_api("_api_get", {"config": {}}):
        result = runner.invoke(app, ["describe", "config"])
    assert result.exit_code == 0
    assert "No configuration" in result.output


def test_describe_config_with_data():
    with _mock_api("_api_get", {"config": {"push_on_create": True}}):
        result = runner.invoke(app, ["describe", "config"])
    assert result.exit_code == 0
    assert "push_on_create" in result.output


def test_describe_invalid_resource():
    result = runner.invoke(app, ["describe", "invalid"])
    assert result.exit_code == 1
    assert "Unknown resource" in result.output


def test_describe_error():
    with _mock_api("_api_get", {"error": "Unauthorised"}):
        result = runner.invoke(app, ["describe", "config"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------


def test_set_default_calendar():
    with _mock_api(
        "_api_post",
        {"status": "saved", "config": {"default_calendar_id": "cal1"}},
    ):
        result = runner.invoke(app, ["set", "default", "cal1"])
    assert result.exit_code == 0
    assert "Default calendar" in result.output or "cal1" in result.output


def test_set_unknown_resource():
    result = runner.invoke(app, ["set", "unknown-resource", "val"])
    assert result.exit_code == 1


def test_set_error():
    with _mock_api("_api_post", {"error": "Unauthorised"}):
        result = runner.invoke(app, ["set", "default", "cal1"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# connect (error path only – success requires interactive prompt)
# ---------------------------------------------------------------------------


def test_connect_server_error():
    with _mock_api("_api_post", {"error": "Google Calendar integration not configured"}):
        result = runner.invoke(app, ["connect"], input="\n")
    assert result.exit_code == 1 or "Error" in result.output
