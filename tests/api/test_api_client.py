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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")
        assert client.base_url == "https://todopro.minhdq.dev/api"
        assert client.timeout == 30
        assert client._client is None


@pytest.mark.asyncio
async def test_get_headers_without_auth(mock_config_manager):
    """Test getting headers without authentication."""
    with patch(
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")
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
        client = APIClient(profile="test")
        headers = client._get_headers()

        assert headers["Authorization"] == "Bearer test_token"


@pytest.mark.asyncio
async def test_get_client_creates_httpx_client(mock_config_manager):
    """Test _get_client creates httpx client."""
    with patch(
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")
        httpx_client = await client._get_client()

        assert isinstance(httpx_client, httpx.AsyncClient)
        assert client._client is not None

        await client.close()


@pytest.mark.asyncio
async def test_close_client(mock_config_manager):
    """Test closing the client."""
    with patch(
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")
        await client._get_client()

        assert client._client is not None

        await client.close()
        assert client._client is None


@pytest.mark.asyncio
async def test_request_success(mock_config_manager):
    """Test successful request."""
    with patch(
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
        "todopro_cli.services.context_manager.get_context_manager",
        return_value=mock_config_manager,
    ):
        client = APIClient(profile="test")

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
    client = get_client(profile="test")
    assert isinstance(client, APIClient)
    assert client.config_manager is not None
