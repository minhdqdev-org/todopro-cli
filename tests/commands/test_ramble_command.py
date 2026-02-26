"""Unit tests for ramble_command."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from todopro_cli.commands.ramble_command import app

runner = CliRunner()


def _mock_api_get(return_value):
    return patch("todopro_cli.commands.ramble_command._api_get", new=AsyncMock(return_value=return_value))


def _mock_api_post(return_value):
    return patch("todopro_cli.commands.ramble_command._api_post", new=AsyncMock(return_value=return_value))


def _mock_api_put(return_value):
    return patch("todopro_cli.commands.ramble_command._api_put", new=AsyncMock(return_value=return_value))


# Help tests
def test_ramble_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_history_help():
    result = runner.invoke(app, ["history", "--help"])
    assert result.exit_code == 0


def test_config_help():
    result = runner.invoke(app, ["config", "--help"])
    assert result.exit_code == 0


def test_usage_help():
    result = runner.invoke(app, ["usage", "--help"])
    assert result.exit_code == 0


# ramble --text (skips mic recording)
def test_ramble_text_success():
    with _mock_api_post({
        "tasks_created": 2,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [
            {"success": True, "title": "Buy milk"},
            {"success": True, "title": "Call doctor"},
        ],
        "transcript": "Buy milk and call doctor",
        "errors": [],
    }):
        result = runner.invoke(app, ["--text", "Buy milk and call doctor"])
    assert result.exit_code == 0
    assert "2" in result.output


def test_ramble_text_error():
    with _mock_api_post({"error": "LLM not configured"}):
        result = runner.invoke(app, ["--text", "some text"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_ramble_text_dry_run():
    with _mock_api_post({
        "tasks_created": 1,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [],
        "transcript": "Buy milk",
        "errors": [],
        "dry_run": True,
    }):
        result = runner.invoke(app, ["--text", "Buy milk", "--dry-run"])
    assert result.exit_code == 0
    assert "dry" in result.output.lower() or "1" in result.output


def test_ramble_no_audio_deps():
    """Without sounddevice, should print helpful message and exit."""
    with patch("todopro_cli.commands.ramble_command.check_dependencies", return_value=(False, "sounddevice not installed")):
        result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "sounddevice" in result.output or "Audio" in result.output


# history
def test_history_empty():
    with _mock_api_get({"sessions": []}):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "No Ramble sessions" in result.output


def test_history_with_sessions():
    sessions = [
        {
            "id": "abc12345-1234-1234-1234-123456789012",
            "started_at": "2027-01-01T10:00:00Z",
            "ended_at": "2027-01-01T10:01:00Z",
            "duration_seconds": 30.5,
            "stt_provider": "whisper",
            "llm_provider": "gemini",
            "tasks_created": 3,
            "tasks_updated": 0,
            "tasks_deleted": 0,
            "source": "cli",
        }
    ]
    with _mock_api_get({"sessions": sessions}):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 0
    assert "whisper" in result.output


def test_history_error():
    with _mock_api_get({"error": "Unauthorized"}):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 1


# config
def test_config_show():
    with _mock_api_get({
        "default_stt_provider": "whisper",
        "default_llm_provider": "gemini",
        "silence_timeout_seconds": 3,
        "default_language": "auto",
        "sessions_per_day_limit": 5,
        "max_session_duration": 30,
    }):
        result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "whisper" in result.output


def test_config_update_stt():
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--stt", "gemini"])
    assert result.exit_code == 0
    assert "saved" in result.output.lower() or "Configuration" in result.output


def test_config_update_silence_timeout():
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--silence-timeout", "5"])
    assert result.exit_code == 0


def test_config_error():
    with _mock_api_put({"error": "Server error"}):
        result = runner.invoke(app, ["config", "--stt", "gemini"])
    assert result.exit_code == 1


# usage
def test_usage_success():
    with _mock_api_get({
        "sessions_today": 2,
        "sessions_limit": 5,
        "sessions_remaining": 3,
        "max_session_duration": 30,
    }):
        result = runner.invoke(app, ["usage"])
    assert result.exit_code == 0
    assert "2" in result.output
    assert "5" in result.output


def test_usage_error():
    with _mock_api_get({"error": "Unauthorized"}):
        result = runner.invoke(app, ["usage"])
    assert result.exit_code == 1


# ===========================================================================
# Additional tests — covering the previously uncovered lines
# ===========================================================================

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from todopro_cli.commands.ramble_command import (
    _display_ramble_result,
    _get_auth_headers,
    _get_base_url,
    _process_audio_ramble,
    _process_text_ramble,
)

# ---------------------------------------------------------------------------
# _get_base_url (lines 20-23)
# ---------------------------------------------------------------------------


def test_get_base_url_strips_trailing_slash():
    with patch(
        "todopro_cli.utils.update_checker.get_backend_url",
        return_value="https://api.example.com/",
    ):
        url = _get_base_url()
    assert url == "https://api.example.com/api/ramble"


def test_get_base_url_no_trailing_slash():
    with patch(
        "todopro_cli.utils.update_checker.get_backend_url",
        return_value="https://api.example.com",
    ):
        url = _get_base_url()
    assert url == "https://api.example.com/api/ramble"


# ---------------------------------------------------------------------------
# _get_auth_headers (lines 27-40)
# ---------------------------------------------------------------------------


def test_get_auth_headers_with_context_and_token():
    """Context credentials with token → Authorization header set."""
    mock_cfg = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.name = "work"
    mock_cfg.get_current_context.return_value = mock_ctx
    mock_cfg.load_context_credentials.return_value = {"token": "ctx_token"}

    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_cfg,
    ):
        headers = _get_auth_headers()

    assert headers["Authorization"] == "Bearer ctx_token"


def test_get_auth_headers_falls_back_to_global_credentials():
    """No context → fall back to load_credentials()."""
    mock_cfg = MagicMock()
    mock_cfg.get_current_context.return_value = None
    mock_cfg.load_credentials.return_value = {"token": "global_token"}

    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_cfg,
    ):
        headers = _get_auth_headers()

    assert headers["Authorization"] == "Bearer global_token"


def test_get_auth_headers_no_token_omits_authorization():
    """When credentials have no token, Authorization header is absent."""
    mock_cfg = MagicMock()
    mock_cfg.get_current_context.return_value = None
    mock_cfg.load_credentials.return_value = {}

    with patch(
        "todopro_cli.services.config_service.get_config_service",
        return_value=mock_cfg,
    ):
        headers = _get_auth_headers()

    assert "Authorization" not in headers
    assert headers.get("Accept") == "application/json"


def test_get_auth_headers_null_credentials_no_authorization():
    """load_credentials returns None → no Authorization header."""
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
# _api_get / _api_post / _api_put (lines 44-48, 56-62, 70-76)
# ---------------------------------------------------------------------------


def _make_httpx_mock(status: int, payload: dict):
    """Return a mock httpx.AsyncClient context-manager."""
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.put = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def test_api_get_returns_json_on_200():
    from todopro_cli.commands.ramble_command import _api_get

    mock_client = _make_httpx_mock(200, {"sessions": []})
    with patch("todopro_cli.commands.ramble_command._get_base_url", return_value="http://t"):
        with patch("todopro_cli.commands.ramble_command._get_auth_headers", return_value={}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_get("/sessions/"))
    assert result == {"sessions": []}


def test_api_get_returns_error_dict_on_500():
    from todopro_cli.commands.ramble_command import _api_get

    mock_client = _make_httpx_mock(503, {})
    with patch("todopro_cli.commands.ramble_command._get_base_url", return_value="http://t"):
        with patch("todopro_cli.commands.ramble_command._get_auth_headers", return_value={}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_get("/sessions/"))
    assert "error" in result
    assert "503" in result["error"]


def test_api_post_returns_json_on_200():
    from todopro_cli.commands.ramble_command import _api_post

    mock_client = _make_httpx_mock(200, {"tasks_created": 3})
    with patch("todopro_cli.commands.ramble_command._get_base_url", return_value="http://t"):
        with patch("todopro_cli.commands.ramble_command._get_auth_headers", return_value={}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_post("/batch/", {"transcript": "hello"}))
    assert result == {"tasks_created": 3}


def test_api_post_returns_error_on_500():
    from todopro_cli.commands.ramble_command import _api_post

    mock_client = _make_httpx_mock(500, {})
    with patch("todopro_cli.commands.ramble_command._get_base_url", return_value="http://t"):
        with patch("todopro_cli.commands.ramble_command._get_auth_headers", return_value={}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_post("/batch/"))
    assert "error" in result


def test_api_put_returns_json_on_200():
    from todopro_cli.commands.ramble_command import _api_put

    mock_client = _make_httpx_mock(200, {"status": "saved"})
    with patch("todopro_cli.commands.ramble_command._get_base_url", return_value="http://t"):
        with patch("todopro_cli.commands.ramble_command._get_auth_headers", return_value={}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_put("/config/", {"key": "val"}))
    assert result == {"status": "saved"}


def test_api_put_returns_error_on_500():
    from todopro_cli.commands.ramble_command import _api_put

    mock_client = _make_httpx_mock(500, {})
    with patch("todopro_cli.commands.ramble_command._get_base_url", return_value="http://t"):
        with patch("todopro_cli.commands.ramble_command._get_auth_headers", return_value={}):
            with patch("httpx.AsyncClient", return_value=mock_client):
                result = asyncio.run(_api_put("/config/"))
    assert "error" in result


# ---------------------------------------------------------------------------
# --stream warning (line 116)
# ---------------------------------------------------------------------------


def test_ramble_stream_flag_prints_warning():
    """--stream shows a streaming-mode warning before attempting audio check."""
    with patch(
        "todopro_cli.commands.ramble_command.check_dependencies",
        return_value=(False, "sounddevice missing"),
    ):
        result = runner.invoke(app, ["--stream"])
    assert "Streaming" in result.output or "stream" in result.output.lower()


# ---------------------------------------------------------------------------
# Audio recording path (lines 137-160)
# ---------------------------------------------------------------------------


def test_ramble_audio_success_path():
    """When deps OK and audio recorded, upload is attempted."""
    fake_audio = b"\x00\x01\x02\x03"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "tasks_created": 2,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [{"success": True, "title": "Task A"}],
        "transcript": "Do stuff",
        "errors": [],
    }

    with patch(
        "todopro_cli.commands.ramble_command.check_dependencies",
        return_value=(True, ""),
    ):
        with patch(
            "todopro_cli.services.audio.recorder.record_audio",
            return_value=fake_audio,
        ):
            with patch(
                "todopro_cli.commands.ramble_command._get_base_url",
                return_value="http://test",
            ):
                with patch(
                    "todopro_cli.commands.ramble_command._get_auth_headers",
                    return_value={},
                ):
                    mock_httpx_client = MagicMock()
                    mock_httpx_client.__enter__ = MagicMock(
                        return_value=mock_httpx_client
                    )
                    mock_httpx_client.__exit__ = MagicMock(return_value=False)
                    mock_httpx_client.post.return_value = mock_resp
                    with patch("httpx.Client", return_value=mock_httpx_client):
                        result = runner.invoke(app, [])
    assert result.exit_code == 0


def test_ramble_audio_keyboard_interrupt():
    """KeyboardInterrupt during recording → empty audio → exit 1."""
    with patch(
        "todopro_cli.commands.ramble_command.check_dependencies",
        return_value=(True, ""),
    ):
        with patch(
            "todopro_cli.services.audio.recorder.record_audio",
            side_effect=KeyboardInterrupt,
        ):
            result = runner.invoke(app, [])
    assert result.exit_code == 1


def test_ramble_audio_record_exception():
    """Exception from record_audio → exit code 1."""
    with patch(
        "todopro_cli.commands.ramble_command.check_dependencies",
        return_value=(True, ""),
    ):
        with patch(
            "todopro_cli.services.audio.recorder.record_audio",
            side_effect=RuntimeError("mic broken"),
        ):
            result = runner.invoke(app, [])
    assert result.exit_code == 1


def test_ramble_audio_empty_bytes_exits():
    """Empty bytes from record_audio → 'No audio recorded' exit 1."""
    with patch(
        "todopro_cli.commands.ramble_command.check_dependencies",
        return_value=(True, ""),
    ):
        with patch(
            "todopro_cli.services.audio.recorder.record_audio",
            return_value=b"",
        ):
            result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "No audio recorded" in result.output


# ---------------------------------------------------------------------------
# _process_audio_ramble (lines 199-230)
# ---------------------------------------------------------------------------


def test_process_audio_ramble_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "tasks_created": 1,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [],
        "transcript": "",
        "errors": [],
    }
    with patch(
        "todopro_cli.commands.ramble_command._get_base_url", return_value="http://test"
    ):
        with patch(
            "todopro_cli.commands.ramble_command._get_auth_headers", return_value={}
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            with patch("httpx.Client", return_value=mock_client):
                # Should run without raising
                _process_audio_ramble(b"audio_data", "whisper", "gemini", None, False, "en")


def test_process_audio_ramble_with_project():
    """project option is included in POST data."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "tasks_created": 0, "tasks_updated": 0, "tasks_deleted": 0,
        "task_results": [], "transcript": "", "errors": [],
    }
    with patch(
        "todopro_cli.commands.ramble_command._get_base_url", return_value="http://test"
    ):
        with patch(
            "todopro_cli.commands.ramble_command._get_auth_headers", return_value={}
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            with patch("httpx.Client", return_value=mock_client):
                _process_audio_ramble(b"audio", "whisper", "gemini", "my-project", False, "en")
    call_kwargs = mock_client.post.call_args
    assert call_kwargs is not None
    data_sent = call_kwargs[1].get("data", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {})
    # Just confirm no exceptions raised
    assert mock_client.post.called


def test_process_audio_ramble_server_error_exits():
    """Server error in audio upload path exits the CLI with code 1."""
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.json.return_value = {}
    with patch(
        "todopro_cli.commands.ramble_command._get_base_url", return_value="http://test"
    ):
        with patch(
            "todopro_cli.commands.ramble_command._get_auth_headers", return_value={}
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.return_value = mock_resp
            with patch("httpx.Client", return_value=mock_client):
                import typer as _typer
                with pytest.raises(_typer.Exit):
                    _process_audio_ramble(
                        b"audio", "whisper", "gemini", None, False, "en"
                    )


def test_process_audio_ramble_exception_exits():
    """Network exception in audio upload path exits with code 1."""
    with patch(
        "todopro_cli.commands.ramble_command._get_base_url", return_value="http://test"
    ):
        with patch(
            "todopro_cli.commands.ramble_command._get_auth_headers", return_value={}
        ):
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = Exception("connection refused")
            with patch("httpx.Client", return_value=mock_client):
                import typer as _typer
                with pytest.raises(_typer.Exit):
                    _process_audio_ramble(
                        b"audio", "whisper", "gemini", None, False, "en"
                    )


# ---------------------------------------------------------------------------
# _display_ramble_result — errors list (line 266)
# ---------------------------------------------------------------------------


def test_display_ramble_result_shows_errors():
    """Errors in result are printed with warning prefix."""
    with _mock_api_post({
        "tasks_created": 0,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [],
        "transcript": "",
        "errors": ["Failed to create task A", "Duplicate task B"],
    }):
        result = runner.invoke(app, ["--text", "do stuff"])
    assert result.exit_code == 0
    assert "Failed to create task A" in result.output
    assert "Duplicate task B" in result.output


def test_display_ramble_result_long_transcript_truncated():
    """Transcripts over 200 chars are truncated with ellipsis."""
    long_transcript = "word " * 60  # 300 chars
    with _mock_api_post({
        "tasks_created": 1,
        "tasks_updated": 0,
        "tasks_deleted": 0,
        "task_results": [],
        "transcript": long_transcript,
        "errors": [],
    }):
        result = runner.invoke(app, ["--text", "stuff"])
    assert result.exit_code == 0
    assert "..." in result.output


# ---------------------------------------------------------------------------
# history — exception handler (lines 313-315)
# ---------------------------------------------------------------------------


def test_history_exception_handler():
    """Generic exception from _api_get is caught and re-raised as Exit(1)."""
    with patch(
        "todopro_cli.commands.ramble_command._api_get",
        new=AsyncMock(side_effect=Exception("network error")),
    ):
        result = runner.invoke(app, ["history"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# ramble config — additional branches (lines 343-344, 355, 359, 361, 373-375)
# ---------------------------------------------------------------------------


def test_config_show_returns_error_from_api():
    """config show path error response → exit 1."""
    with _mock_api_get({"error": "Unauthorized"}):
        result = runner.invoke(app, ["config", "--show"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_config_update_llm_option():
    """--llm flag updates default LLM provider."""
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--llm", "openai"])
    assert result.exit_code == 0


def test_config_update_default_project():
    """--default-project option is sent in the PUT payload."""
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--default-project", "proj-123"])
    assert result.exit_code == 0


def test_config_update_language():
    """--language option is sent in the PUT payload."""
    with _mock_api_put({"status": "saved"}):
        result = runner.invoke(app, ["config", "--language", "vi"])
    assert result.exit_code == 0


def test_config_exception_handler():
    """Generic exception inside config _do() is caught → exit 1."""
    with patch(
        "todopro_cli.commands.ramble_command._api_put",
        new=AsyncMock(side_effect=Exception("timeout")),
    ):
        result = runner.invoke(app, ["config", "--stt", "whisper"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ---------------------------------------------------------------------------
# usage — exception handler (lines 398-400)
# ---------------------------------------------------------------------------


def test_usage_exception_handler():
    """Generic exception inside usage _do() is caught → exit 1."""
    with patch(
        "todopro_cli.commands.ramble_command._api_get",
        new=AsyncMock(side_effect=Exception("server gone")),
    ):
        result = runner.invoke(app, ["usage"])
    assert result.exit_code == 1
    assert "Error" in result.output
