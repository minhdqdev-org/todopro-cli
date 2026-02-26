"""Tests for API client."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from todopro_cli.services.api.client import APIClient, get_client
from todopro_cli.services.config_service import ConfigService


@pytest.fixture
def mock_config_manager(tmp_path):
    """Create a mock config manager."""
    tmpdir = str(tmp_path)
    with patch(
        "todopro_cli.services.config_service.user_config_dir", return_value=tmpdir
    ):
        with patch(
            "todopro_cli.services.config_service.user_data_dir", return_value=tmpdir
        ):
            config_manager = ConfigService()
            yield config_manager


@pytest.mark.asyncio
async def test_client_initialization(mock_config_manager):
    """Test API client initialization."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        assert client.base_url == "https://todopro.minhdq.dev/api"
        assert client.timeout == 30
        assert client._client is None


@pytest.mark.asyncio
async def test_get_headers_without_auth(mock_config_manager):
    """Test getting headers without authentication."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        headers = client._get_headers(skip_auth=True)

        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers


@pytest.mark.skip(
    reason="Auth header test is complex due to context/config caching. Auth is tested in integration tests."
)
@pytest.mark.asyncio
async def test_get_headers_with_auth(mock_config_manager):
    """Test getting headers with authentication."""
    from todopro_cli.models.config_models import Context

    # Create a mock context
    mock_context = Context(name="test", type="remote", source="https://api.test.com")

    # Mock get_current_context to return a test context
    mock_config_manager.get_current_context = lambda: mock_context

    # Save credentials for the test context
    mock_config_manager.save_credentials(
        "test_token", "test_refresh_token", context_name="test"
    )

    # Patch get_config_service since get_context_manager calls it
    with patch(
        "todopro_cli.services.context_manager.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_get_client_creates_httpx_client(mock_config_manager):
    """Test _get_client creates httpx client."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        httpx_client = await client._get_client()

        assert isinstance(httpx_client, httpx.AsyncClient)
        assert client._client is not None

        await client.close()


@pytest.mark.asyncio
async def test_close_client(mock_config_manager):
    """Test closing the client."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        await client._get_client()

        assert client._client is not None

        await client.close()
        assert client._client is None


@pytest.mark.asyncio
async def test_request_success(mock_config_manager):
    """Test successful request."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await client.request("GET", "/test")
            assert response.status_code == 200

        await client.close()


@pytest.mark.asyncio
async def test_request_with_retry_on_server_error(mock_config_manager):
    """Test request retries on server error."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        # Create a mock response for 500 error
        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_error_response
        )

        with (
            patch.object(
                httpx.AsyncClient,
                "request",
                new_callable=AsyncMock,
                side_effect=mock_error,
            ),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await client.request("GET", "/test", retry=1)

        await client.close()


@pytest.mark.asyncio
async def test_request_no_retry_on_client_error(mock_config_manager):
    """Test request doesn't retry on client error (4xx)."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        # Create a mock response for 404 error
        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_error_response
        )

        with (
            patch.object(
                httpx.AsyncClient,
                "request",
                new_callable=AsyncMock,
                side_effect=mock_error,
            ),
            pytest.raises(httpx.HTTPStatusError),
        ):
            await client.request("GET", "/test")

        await client.close()


@pytest.mark.asyncio
async def test_get_method(mock_config_manager):
    """Test GET request method."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await client.get("/test", params={"key": "value"})
            mock_request.assert_called_once_with(
                "GET", "/test", params={"key": "value"}
            )

        await client.close()


@pytest.mark.asyncio
async def test_post_method(mock_config_manager):
    """Test POST request method."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await client.post("/test", json={"key": "value"})
            mock_request.assert_called_once_with(
                "POST", "/test", json={"key": "value"}, skip_auth=False
            )

        await client.close()


@pytest.mark.asyncio
async def test_put_method(mock_config_manager):
    """Test PUT request method."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await client.put("/test", json={"key": "value"})
            mock_request.assert_called_once_with("PUT", "/test", json={"key": "value"})

        await client.close()


@pytest.mark.asyncio
async def test_patch_method(mock_config_manager):
    """Test PATCH request method."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await client.patch("/test", json={"key": "value"})
            mock_request.assert_called_once_with(
                "PATCH", "/test", json={"key": "value"}
            )

        await client.close()


@pytest.mark.asyncio
async def test_delete_method(mock_config_manager):
    """Test DELETE request method."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            client, "request", new_callable=AsyncMock, return_value=mock_response
        ) as mock_request:
            await client.delete("/test")
            mock_request.assert_called_once_with("DELETE", "/test")

        await client.close()


def test_get_client_factory():
    """Test get_client factory function."""
    client = get_client()
    assert isinstance(client, APIClient)
    assert client.config_manager is not None


# ===========================================================================
# Context manager protocol
# ===========================================================================


@pytest.mark.asyncio
async def test_async_context_manager_enter_returns_client(mock_config_manager):
    """Lines 28: __aenter__ returns self."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        async with client as c:
            assert c is client  # __aenter__ returns self


@pytest.mark.asyncio
async def test_async_context_manager_exit_closes_client(mock_config_manager):
    """Line 32: __aexit__ calls close(), nullifying _client."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        async with client as c:
            # Force an underlying httpx client to exist so close() actually closes it
            await c._get_client()
            assert c._client is not None
        # After __aexit__, _client should be None
        assert client._client is None


# ===========================================================================
# _get_headers – credential fallback paths
# ===========================================================================


@pytest.mark.asyncio
async def test_get_headers_no_current_context_no_auth(mock_config_manager):
    """Line 50: when get_current_context() is None, credentials = None → no Authorization header."""
    mock_config_manager.get_current_context = lambda: None
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        headers = client._get_headers(skip_auth=False)
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_get_headers_with_token_adds_authorization(mock_config_manager):
    """Line 57: when credentials contain 'token', Authorization header is set."""
    from todopro_cli.models.config_models import Context

    mock_ctx = Context(name="test-ctx", type="remote", source="https://api.test.com")
    mock_config_manager.get_current_context = lambda: mock_ctx
    mock_config_manager.load_context_credentials = lambda ctx_name: {
        "token": "my-jwt-token"
    }
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        headers = client._get_headers(skip_auth=False)
    assert headers["Authorization"] == "Bearer my-jwt-token"


@pytest.mark.asyncio
async def test_get_headers_context_creds_missing_falls_back_to_default(
    mock_config_manager,
):
    """Line 50+57: context credentials missing → falls back to load_credentials()."""
    from todopro_cli.models.config_models import Context

    mock_ctx = Context(name="test-ctx", type="remote", source="https://api.test.com")
    mock_config_manager.get_current_context = lambda: mock_ctx
    mock_config_manager.load_context_credentials = (
        lambda ctx_name: None
    )  # no context creds
    # Stub load_credentials to return a token directly (avoids file-system round-trip)
    mock_config_manager.load_credentials = lambda: {"token": "fallback-token"}
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        headers = client._get_headers(skip_auth=False)
    assert "Authorization" in headers
    assert "fallback-token" in headers["Authorization"]


# ===========================================================================
# _try_refresh_token
# ===========================================================================


@pytest.mark.asyncio
async def test_try_refresh_token_no_credentials_returns_false(mock_config_manager):
    """Lines 86-87: no credentials → return False immediately."""
    mock_config_manager.load_credentials = lambda: None
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        result = await client._try_refresh_token()
    assert result is False


@pytest.mark.asyncio
async def test_try_refresh_token_no_refresh_token_returns_false(mock_config_manager):
    """Lines 86-87: credentials exist but no refresh_token → return False."""
    mock_config_manager.load_credentials = lambda: {"token": "access-token"}
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        result = await client._try_refresh_token()
    assert result is False


@pytest.mark.asyncio
async def test_try_refresh_token_success_returns_true(mock_config_manager):
    """Lines 89-109: refresh succeeds → updates credentials, returns True."""
    mock_config_manager.load_credentials = lambda: {
        "token": "old-access",
        "refresh_token": "valid-refresh",
    }
    save_called = []
    mock_config_manager.save_credentials = (
        lambda tok, ref=None, **kw: save_called.append(tok)
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "new-access",
        "refresh_token": "new-refresh",
    }

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            client, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client._try_refresh_token()

    assert result is True
    assert save_called == ["new-access"]


@pytest.mark.asyncio
async def test_try_refresh_token_no_access_token_in_response_returns_false(
    mock_config_manager,
):
    """Lines 99-111: refresh endpoint returns no access_token → return False."""
    mock_config_manager.load_credentials = lambda: {
        "token": "old",
        "refresh_token": "refresh",
    }
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "invalid_grant"}  # no access_token

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            client, "post", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client._try_refresh_token()

    assert result is False


@pytest.mark.asyncio
async def test_try_refresh_token_post_exception_returns_false(mock_config_manager):
    """Lines 112-113: any exception during refresh → return False (not raised)."""
    mock_config_manager.load_credentials = lambda: {
        "token": "old",
        "refresh_token": "refresh",
    }
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            client,
            "post",
            new_callable=AsyncMock,
            side_effect=Exception("network error"),
        ):
            result = await client._try_refresh_token()

    assert result is False


# ===========================================================================
# 401 handling in request()
# ===========================================================================


@pytest.mark.asyncio
async def test_request_401_with_successful_refresh_retries_and_succeeds(
    mock_config_manager,
):
    """Lines 148-156: 401 → refresh succeeds → retry succeeds → response returned."""
    mock_error_response = MagicMock()
    mock_error_response.status_code = 401
    error_401 = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_error_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.raise_for_status = MagicMock()

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        # First call raises 401, second call (after refresh) succeeds
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=[error_401, success_response],
        ):
            with patch.object(
                client,
                "_try_refresh_token",
                new_callable=AsyncMock,
                return_value=True,
            ):
                response = await client.request("GET", "/protected", retry=0)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_401_with_successful_refresh_but_retry_fails(mock_config_manager):
    """Lines 157-159: 401 → refresh succeeds → retry also fails → raises original error."""
    mock_error_response = MagicMock()
    mock_error_response.status_code = 401
    error_401 = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_error_response
    )

    error_after_refresh = httpx.HTTPStatusError(
        "Still 401", request=MagicMock(), response=mock_error_response
    )

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=[error_401, error_after_refresh],
        ):
            with patch.object(
                client,
                "_try_refresh_token",
                new_callable=AsyncMock,
                return_value=True,
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await client.request("GET", "/protected", retry=0)


@pytest.mark.asyncio
async def test_request_401_refresh_fails_no_refresh_token_in_creds(mock_config_manager):
    """Lines 162-176: 401 → refresh fails → no refresh_token in creds → prints message → raises."""
    mock_error_response = MagicMock()
    mock_error_response.status_code = 401
    error_401 = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_error_response
    )

    # load_credentials returns creds without refresh_token
    mock_config_manager.load_credentials = lambda: {"token": "old-token"}

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=error_401,
        ):
            with patch.object(
                client,
                "_try_refresh_token",
                new_callable=AsyncMock,
                return_value=False,
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await client.request("GET", "/secret", retry=0)


@pytest.mark.asyncio
async def test_request_401_refresh_fails_with_refresh_token_still_raises(
    mock_config_manager,
):
    """Lines 162-177: 401 → refresh fails but creds have refresh_token → still raises."""
    mock_error_response = MagicMock()
    mock_error_response.status_code = 401
    error_401 = httpx.HTTPStatusError(
        "Unauthorized", request=MagicMock(), response=mock_error_response
    )

    mock_config_manager.load_credentials = lambda: {
        "token": "old",
        "refresh_token": "r",
    }

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=error_401,
        ):
            with patch.object(
                client,
                "_try_refresh_token",
                new_callable=AsyncMock,
                return_value=False,
            ):
                with pytest.raises(httpx.HTTPStatusError):
                    await client.request("GET", "/secret", retry=0)


# ===========================================================================
# httpx.RequestError and RuntimeError exhausted retries
# ===========================================================================


@pytest.mark.asyncio
async def test_request_request_error_sets_last_exception(mock_config_manager):
    """Lines 183-184: httpx.RequestError is caught, stored in last_exception, then raised."""
    req_error = httpx.ConnectError("Connection refused")

    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=req_error,
        ):
            with pytest.raises(httpx.RequestError):
                await client.request("GET", "/test", retry=0)
        await client.close()


@pytest.mark.asyncio
async def test_request_request_error_with_retries_eventually_raises(mock_config_manager):
    """Lines 183-184: RequestError on all retry attempts → last one re-raised."""
    req_error = httpx.ConnectError("timeout")

    with (
        patch(
            "todopro_cli.services.api.client.get_config_service",
            return_value=mock_config_manager,
        ),
        patch(
            "todopro_cli.services.api.client.asyncio.sleep", new_callable=AsyncMock
        ),
    ):
        client = APIClient()
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=req_error,
        ):
            with pytest.raises(httpx.RequestError):
                await client.request("GET", "/test", retry=2)
        await client.close()


@pytest.mark.asyncio
async def test_request_empty_retry_range_raises_runtime_error(mock_config_manager):
    """Line 194: retry=-1 → loop never runs → last_exception is None → RuntimeError raised."""
    with patch(
        "todopro_cli.services.api.client.get_config_service",
        return_value=mock_config_manager,
    ):
        client = APIClient()
        with pytest.raises(RuntimeError, match="Request failed after all retries"):
            await client.request("GET", "/test", retry=-1)
        await client.close()
