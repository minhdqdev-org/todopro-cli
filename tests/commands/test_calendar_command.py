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


# ===========================================================================
# Additional tests — covering the previously uncovered lines
# ===========================================================================

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from todopro_cli.commands.calendar_command import (
    _get_auth_headers,
    _get_base_url,
)


# ---------------------------------------------------------------------------
# _get_base_url (lines 19-21)
# ---------------------------------------------------------------------------


def test_calendar_get_base_url_strips_trailing_slash():
    with patch(
        "todopro_cli.utils.update_checker.get_backend_url",
        return_value="https://api.example.com/",
    ):
        url = _get_base_url()
    assert url == "https://api.example.com"


def test_calendar_get_base_url_no_slash():
    with patch(
        "todopro_cli.utils.update_checker.get_backend_url",
        return_value="https://api.example.com",
    ):
        assert _get_base_url() == "https://api.example.com"


# ---------------------------------------------------------------------------
# _get_auth_headers (lines 25-39)
# ---------------------------------------------------------------------------


def test_calendar_get_auth_headers_with_context_token():
    mock_cfg = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.name = "default"
    mock_cfg.get_current_context.return_value = mock_ctx
    mock_cfg.load_context_credentials.return_value = {"token": "ctx_tok"}

    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_cfg,
    ):
        headers = _get_auth_headers()

    assert headers["Authorization"] == "Bearer ctx_tok"
    assert headers["Content-Type"] == "application/json"


def test_calendar_get_auth_headers_no_context_fallback():
    mock_cfg = MagicMock()
    mock_cfg.get_current_context.return_value = None
    mock_cfg.load_credentials.return_value = {"token": "global_tok"}

    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_cfg,
    ):
        headers = _get_auth_headers()

    assert headers["Authorization"] == "Bearer global_tok"


def test_calendar_get_auth_headers_no_credentials():
    mock_cfg = MagicMock()
    mock_cfg.get_current_context.return_value = None
    mock_cfg.load_credentials.return_value = None

    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_cfg,
    ):
        headers = _get_auth_headers()

    assert "Authorization" not in headers


# ---------------------------------------------------------------------------
# _api_get / _api_post / _api_delete (lines 43-80)
# ---------------------------------------------------------------------------


def _make_async_httpx_mock(status: int, payload: dict):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.delete = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def test_calendar_api_get_returns_json_on_200():
    from todopro_cli.commands.calendar_command import _api_get

    mock_client = _make_async_httpx_mock(200, {"connected": True})
    with patch(
        "todopro_cli.commands.calendar_command._get_base_url", return_value="http://t"
    ):
        with patch(
            "todopro_cli.commands.calendar_command._get_auth_headers", return_value={}
        ):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_get("/status/"))
    assert result == {"connected": True}


def test_calendar_api_get_returns_error_on_500():
    from todopro_cli.commands.calendar_command import _api_get

    mock_client = _make_async_httpx_mock(503, {})
    with patch(
        "todopro_cli.commands.calendar_command._get_base_url", return_value="http://t"
    ):
        with patch(
            "todopro_cli.commands.calendar_command._get_auth_headers", return_value={}
        ):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_get("/status/"))
    assert "error" in result


def test_calendar_api_post_returns_json_on_200():
    from todopro_cli.commands.calendar_command import _api_post

    mock_client = _make_async_httpx_mock(200, {"auth_url": "https://google.com"})
    with patch(
        "todopro_cli.commands.calendar_command._get_base_url", return_value="http://t"
    ):
        with patch(
            "todopro_cli.commands.calendar_command._get_auth_headers", return_value={}
        ):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_post("/auth-url/"))
    assert result == {"auth_url": "https://google.com"}


def test_calendar_api_post_returns_error_on_500():
    from todopro_cli.commands.calendar_command import _api_post

    mock_client = _make_async_httpx_mock(500, {})
    with patch(
        "todopro_cli.commands.calendar_command._get_base_url", return_value="http://t"
    ):
        with patch(
            "todopro_cli.commands.calendar_command._get_auth_headers", return_value={}
        ):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_post("/push/"))
    assert "error" in result


def test_calendar_api_delete_returns_json():
    from todopro_cli.commands.calendar_command import _api_delete

    mock_client = _make_async_httpx_mock(200, {"status": "disconnected"})
    with patch(
        "todopro_cli.commands.calendar_command._get_base_url", return_value="http://t"
    ):
        with patch(
            "todopro_cli.commands.calendar_command._get_auth_headers", return_value={}
        ):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_delete("/disconnect/"))
    assert result == {"status": "disconnected"}


def test_calendar_api_delete_handles_non_json_response():
    """If response body is not JSON, _api_delete returns {'status': 'ok'}."""
    from todopro_cli.commands.calendar_command import _api_delete

    mock_resp = MagicMock()
    mock_resp.status_code = 204
    mock_resp.json.side_effect = Exception("no body")

    mock_client = AsyncMock()
    mock_client.delete = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "todopro_cli.commands.calendar_command._get_base_url", return_value="http://t"
    ):
        with patch(
            "todopro_cli.commands.calendar_command._get_auth_headers", return_value={}
        ):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_delete("/disconnect/"))
    assert result == {"status": "ok"}


# ---------------------------------------------------------------------------
# calendar connect — success path (lines 92-105) and error paths
# ---------------------------------------------------------------------------


def test_connect_full_success():
    """Full OAuth flow: auth-url → user enters code → connected."""
    mock_post = AsyncMock(
        side_effect=[
            {"auth_url": "https://accounts.google.com/o/oauth2/auth?..."},
            {"email": "user@example.com"},
        ]
    )
    with patch("todopro_cli.commands.calendar_command._api_post", new=mock_post):
        result = runner.invoke(app, ["connect"], input="myauthcode\n")
    assert result.exit_code == 0
    assert "Connected" in result.output


def test_connect_full_success_no_email():
    """Full OAuth flow without email in response."""
    mock_post = AsyncMock(
        side_effect=[
            {"auth_url": "https://accounts.google.com/o/oauth2/auth?..."},
            {},
        ]
    )
    with patch("todopro_cli.commands.calendar_command._api_post", new=mock_post):
        result = runner.invoke(app, ["connect"], input="myauthcode\n")
    assert result.exit_code == 0
    assert "Connected" in result.output


def test_connect_callback_error():
    """Auth callback returns error → exit 1."""
    mock_post = AsyncMock(
        side_effect=[
            {"auth_url": "https://accounts.google.com/o/oauth2/auth?..."},
            {"error": "Invalid authorisation code"},
        ]
    )
    with patch("todopro_cli.commands.calendar_command._api_post", new=mock_post):
        result = runner.invoke(app, ["connect"], input="badcode\n")
    assert result.exit_code == 1
    assert "Error" in result.output


def test_connect_exception_handler():
    """Network exception inside connect _do() → exit 1."""
    with patch(
        "todopro_cli.commands.calendar_command._api_post",
        new=AsyncMock(side_effect=Exception("network error")),
    ):
        result = runner.invoke(app, ["connect"], input="\n")
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# Exception handlers for each command (lines 126-130, 158-160, 195-197 ...)
# ---------------------------------------------------------------------------


def test_disconnect_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_delete",
        new=AsyncMock(side_effect=Exception("gone")),
    ):
        result = runner.invoke(app, ["disconnect"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_status_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_get",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_list_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_get",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["list", "calendars"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_set_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_post",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["set", "default", "cal1"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_push_with_label():
    """--label option is sent in the push payload."""
    with _mock_api("_api_post", {"created": 2, "updated": 0, "skipped": 0}):
        result = runner.invoke(app, ["push", "--label", "work"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_push_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_post",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["push"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_pull_with_date_range():
    """--from and --to options are forwarded to the API."""
    with _mock_api("_api_post", {"created": 3, "skipped": 1}):
        result = runner.invoke(
            app, ["pull", "--from", "2027-01-01", "--to", "2027-01-31"]
        )
    assert result.exit_code == 0
    assert "3" in result.output


def test_pull_with_date_from_only():
    with _mock_api("_api_post", {"created": 1, "skipped": 0}):
        result = runner.invoke(app, ["pull", "--from", "2027-01-01"])
    assert result.exit_code == 0


def test_pull_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_post",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_sync_status_error():
    """sync --status with error response → exit 1."""
    with _mock_api("_api_get", {"error": "Not connected"}):
        result = runner.invoke(app, ["sync", "--status"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_sync_status_never_synced():
    """sync --status with no last_synced_at shows 'Never'."""
    with _mock_api("_api_get", {"last_synced_at": None, "stats": {}}):
        result = runner.invoke(app, ["sync", "--status"])
    assert result.exit_code == 0
    assert "Never" in result.output


def test_sync_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_post",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["sync"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_configure_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_post",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["configure", "--push-on-create"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_describe_exception_handler():
    with patch(
        "todopro_cli.commands.calendar_command._api_get",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["describe", "config"])
    assert result.exit_code == 1
    assert "Error" in result.output
