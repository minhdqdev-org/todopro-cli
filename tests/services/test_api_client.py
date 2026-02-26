"""Unit tests for APIClient HTTP client.

All httpx networking is mocked.  Config / credential lookups are patched
so tests are fully isolated from the filesystem.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from todopro_cli.services.api.client import APIClient, get_client


# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def _make_response(status_code: int = 200, json_data: dict | None = None) -> httpx.Response:
    """Build a real httpx.Response with the given status and JSON body."""
    import json as _json

    body = _json.dumps(json_data or {}).encode()
    return httpx.Response(
        status_code=status_code,
        headers={"content-type": "application/json"},
        content=body,
        request=httpx.Request("GET", "https://api.example.com/test"),
    )


def _make_client(
    token: str | None = "test-token",
    refresh_token: str | None = None,
    retry: int = 0,
) -> APIClient:
    """Return an APIClient with mocked config/credentials and no real network."""
    client = APIClient.__new__(APIClient)

    # Mock config manager
    mock_config_manager = MagicMock()
    mock_config_manager.get_current_context.return_value = None
    creds = {}
    if token:
        creds["token"] = token
    if refresh_token:
        creds["refresh_token"] = refresh_token
    mock_config_manager.load_credentials.return_value = creds or None
    mock_config_manager.load_context_credentials.return_value = None
    mock_config_manager.save_credentials = MagicMock()

    # Mock config object
    mock_config = MagicMock()
    mock_config.api.timeout = 30
    mock_config.api.retry = retry
    mock_config_manager.config = mock_config

    client.config_manager = mock_config_manager
    client.config = mock_config
    client.base_url = "https://api.example.com"
    client.timeout = 30
    client._client = None
    return client


# ---------------------------------------------------------------------------
# get_client factory
# ---------------------------------------------------------------------------


class TestGetClientFactory:
    def test_returns_api_client_instance(self, mocker):
        mocker.patch(
            "todopro_cli.services.api.client.get_config_service",
            return_value=MagicMock(config=MagicMock(api=MagicMock(timeout=30, retry=3))),
        )
        mocker.patch("todopro_cli.services.api.client.get_backend_url", return_value="https://x.com")
        c = get_client()
        assert isinstance(c, APIClient)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestAPIClientInit:
    def test_init_sets_base_url(self, mocker):
        mocker.patch(
            "todopro_cli.services.api.client.get_config_service",
            return_value=MagicMock(config=MagicMock(api=MagicMock(timeout=30, retry=3))),
        )
        mocker.patch("todopro_cli.services.api.client.get_backend_url", return_value="https://custom.url")
        client = APIClient()
        assert client.base_url == "https://custom.url"

    def test_init_sets_timeout_from_config(self, mocker):
        mock_cfg = MagicMock(config=MagicMock(api=MagicMock(timeout=99, retry=3)))
        mocker.patch("todopro_cli.services.api.client.get_config_service", return_value=mock_cfg)
        mocker.patch("todopro_cli.services.api.client.get_backend_url", return_value="https://x.com")
        client = APIClient()
        assert client.timeout == 99


# ---------------------------------------------------------------------------
# Async context manager
# ---------------------------------------------------------------------------


class TestAsyncContextManager:
    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        client = _make_client()
        result = await client.__aenter__()
        assert result is client

    @pytest.mark.asyncio
    async def test_aexit_calls_close(self):
        client = _make_client()
        close_called = []
        client.close = AsyncMock(side_effect=lambda: close_called.append(True))
        await client.__aexit__(None, None, None)
        assert close_called


# ---------------------------------------------------------------------------
# _get_headers
# ---------------------------------------------------------------------------


class TestGetHeaders:
    def test_returns_content_type_headers(self):
        client = _make_client(token=None)
        client.config_manager.load_credentials.return_value = None
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_includes_bearer_token_when_credentials_present(self):
        client = _make_client(token="my-jwt")
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer my-jwt"

    def test_no_auth_header_when_skip_auth_true(self):
        client = _make_client(token="my-jwt")
        headers = client._get_headers(skip_auth=True)
        assert "Authorization" not in headers

    def test_no_auth_header_when_no_credentials(self):
        client = _make_client(token=None)
        client.config_manager.load_credentials.return_value = None
        headers = client._get_headers()
        assert "Authorization" not in headers

    def test_uses_context_credentials_when_context_set(self):
        client = _make_client(token="default-token")
        mock_ctx = MagicMock()
        mock_ctx.name = "prod"
        client.config_manager.get_current_context.return_value = mock_ctx
        client.config_manager.load_context_credentials.return_value = {"token": "context-token"}
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer context-token"

    def test_falls_back_to_default_when_context_creds_none(self):
        client = _make_client(token="fallback-token")
        mock_ctx = MagicMock()
        mock_ctx.name = "dev"
        client.config_manager.get_current_context.return_value = mock_ctx
        client.config_manager.load_context_credentials.return_value = None
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer fallback-token"


# ---------------------------------------------------------------------------
# _get_client (lazy httpx.AsyncClient)
# ---------------------------------------------------------------------------


class TestGetHttpClient:
    @pytest.mark.asyncio
    async def test_creates_client_on_first_call(self):
        client = _make_client()
        assert client._client is None
        http_client = await client._get_client()
        assert http_client is not None
        assert client._client is http_client
        await client.close()

    @pytest.mark.asyncio
    async def test_returns_same_client_on_subsequent_calls(self):
        client = _make_client()
        http1 = await client._get_client()
        http2 = await client._get_client()
        assert http1 is http2
        await client.close()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    @pytest.mark.asyncio
    async def test_close_sets_client_to_none(self):
        client = _make_client()
        await client._get_client()  # creates client
        assert client._client is not None
        await client.close()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self):
        client = _make_client()
        await client.close()  # no client created yet
        await client.close()  # should not raise


# ---------------------------------------------------------------------------
# _try_refresh_token
# ---------------------------------------------------------------------------


class TestTryRefreshToken:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_credentials(self):
        client = _make_client(token=None, refresh_token=None)
        client.config_manager.load_credentials.return_value = None
        result = await client._try_refresh_token()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_refresh_token(self):
        client = _make_client(token="t", refresh_token=None)
        result = await client._try_refresh_token()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_and_saves_when_refresh_succeeds(self):
        client = _make_client(token="old-token", refresh_token="refresh-123")
        new_token_response = _make_response(200, {"access_token": "new-token"})
        client.post = AsyncMock(return_value=new_token_response)

        result = await client._try_refresh_token()

        assert result is True
        client.config_manager.save_credentials.assert_called_once()
        saved_args = client.config_manager.save_credentials.call_args[0]
        assert saved_args[0] == "new-token"

    @pytest.mark.asyncio
    async def test_returns_false_when_refresh_response_has_no_access_token(self):
        client = _make_client(token="t", refresh_token="rt")
        client.post = AsyncMock(return_value=_make_response(200, {"error": "invalid_grant"}))
        result = await client._try_refresh_token()
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_request_raises(self):
        client = _make_client(token="t", refresh_token="rt")
        client.post = AsyncMock(side_effect=Exception("network error"))
        result = await client._try_refresh_token()
        assert result is False

    @pytest.mark.asyncio
    async def test_saves_new_refresh_token_when_provided(self):
        client = _make_client(token="old", refresh_token="old-rt")
        resp = _make_response(200, {"access_token": "new-tok", "refresh_token": "new-rt"})
        client.post = AsyncMock(return_value=resp)

        await client._try_refresh_token()

        saved_args = client.config_manager.save_credentials.call_args[0]
        assert saved_args[1] == "new-rt"


# ---------------------------------------------------------------------------
# request (core method)
# ---------------------------------------------------------------------------


class TestRequest:
    @pytest.mark.asyncio
    async def test_successful_get_request(self):
        client = _make_client()
        ok_response = _make_response(200, {"key": "val"})

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(return_value=ok_response)
        mock_http.headers = MagicMock()
        mock_http.headers.update = MagicMock()
        client._client = mock_http

        result = await client.request("GET", "/v1/test")
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_raises_http_error_on_4xx(self):
        client = _make_client(retry=0)

        error_resp = _make_response(404)
        http_err = httpx.HTTPStatusError(
            "Not Found", request=error_resp.request, response=error_resp
        )
        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=http_err)
        mock_http.headers = MagicMock()
        mock_http.headers.update = MagicMock()
        client._client = mock_http

        with pytest.raises(httpx.HTTPStatusError):
            await client.request("GET", "/v1/missing")

    @pytest.mark.asyncio
    async def test_retries_on_5xx(self):
        client = _make_client(retry=2)

        error_resp = _make_response(500)
        http_err = httpx.HTTPStatusError(
            "Server Error", request=error_resp.request, response=error_resp
        )

        call_count = 0

        async def _failing_request(**kwargs):
            nonlocal call_count
            call_count += 1
            raise http_err

        mock_http = AsyncMock()
        mock_http.request = _failing_request
        mock_http.headers = MagicMock()
        mock_http.headers.update = MagicMock()
        client._client = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.HTTPStatusError):
                await client.request("GET", "/v1/error")

        assert call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_retries_on_request_error(self):
        client = _make_client(retry=1)

        req_error = httpx.RequestError("connection failed")

        call_count = 0

        async def _fail(**kwargs):
            nonlocal call_count
            call_count += 1
            raise req_error

        mock_http = AsyncMock()
        mock_http.request = _fail
        mock_http.headers = MagicMock()
        mock_http.headers.update = MagicMock()
        client._client = mock_http

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.RequestError):
                await client.request("POST", "/v1/retry")

        assert call_count == 2

    @pytest.mark.asyncio
    async def test_401_triggers_refresh_and_retries(self):
        client = _make_client(token="expired", refresh_token="rt")

        unauth_resp = _make_response(401)
        http_err = httpx.HTTPStatusError(
            "Unauthorized", request=unauth_resp.request, response=unauth_resp
        )
        ok_resp = _make_response(200, {"ok": True})

        call_count = 0

        async def _request(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise http_err
            return ok_resp

        mock_http = AsyncMock()
        mock_http.request = _request
        mock_http.headers = MagicMock()
        mock_http.headers.update = MagicMock()
        client._client = mock_http

        # Make refresh succeed
        client._try_refresh_token = AsyncMock(return_value=True)

        result = await client.request("GET", "/v1/protected")
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_401_raises_when_refresh_fails(self):
        client = _make_client(token="expired", refresh_token="rt")

        unauth_resp = _make_response(401)
        http_err = httpx.HTTPStatusError(
            "Unauthorized", request=unauth_resp.request, response=unauth_resp
        )

        mock_http = AsyncMock()
        mock_http.request = AsyncMock(side_effect=http_err)
        mock_http.headers = MagicMock()
        mock_http.headers.update = MagicMock()
        client._client = mock_http

        client._try_refresh_token = AsyncMock(return_value=False)
        # No refresh_token to avoid console print branch
        client.config_manager.load_credentials.return_value = {"token": "expired"}

        with patch("todopro_cli.services.api.client.get_console", return_value=MagicMock()):
            with pytest.raises(httpx.HTTPStatusError):
                await client.request("GET", "/v1/protected")


# ---------------------------------------------------------------------------
# HTTP verb helpers
# ---------------------------------------------------------------------------


class TestHttpVerbHelpers:
    @pytest.mark.asyncio
    async def test_get_calls_request_with_get(self):
        client = _make_client()
        client.request = AsyncMock(return_value=_make_response())
        await client.get("/v1/items", params={"q": "foo"})
        client.request.assert_called_once_with("GET", "/v1/items", params={"q": "foo"})

    @pytest.mark.asyncio
    async def test_post_calls_request_with_post(self):
        client = _make_client()
        client.request = AsyncMock(return_value=_make_response())
        await client.post("/v1/items", json={"name": "thing"})
        client.request.assert_called_once_with("POST", "/v1/items", json={"name": "thing"}, skip_auth=False)

    @pytest.mark.asyncio
    async def test_post_skip_auth_forwarded(self):
        client = _make_client()
        client.request = AsyncMock(return_value=_make_response())
        await client.post("/v1/auth", json={}, skip_auth=True)
        client.request.assert_called_once_with("POST", "/v1/auth", json={}, skip_auth=True)

    @pytest.mark.asyncio
    async def test_put_calls_request_with_put(self):
        client = _make_client()
        client.request = AsyncMock(return_value=_make_response())
        await client.put("/v1/items/1", json={"name": "updated"})
        client.request.assert_called_once_with("PUT", "/v1/items/1", json={"name": "updated"})

    @pytest.mark.asyncio
    async def test_patch_calls_request_with_patch(self):
        client = _make_client()
        client.request = AsyncMock(return_value=_make_response())
        await client.patch("/v1/items/1", json={"x": 1})
        client.request.assert_called_once_with("PATCH", "/v1/items/1", json={"x": 1})

    @pytest.mark.asyncio
    async def test_delete_calls_request_with_delete(self):
        client = _make_client()
        client.request = AsyncMock(return_value=_make_response())
        await client.delete("/v1/items/1")
        client.request.assert_called_once_with("DELETE", "/v1/items/1")
