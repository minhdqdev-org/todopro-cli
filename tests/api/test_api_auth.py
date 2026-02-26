"""Tests for Auth API."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.api.auth import AuthAPI
from todopro_cli.services.api.client import APIClient


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_login(mock_client):
    """Test login."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
    }
    mock_client.post.return_value = mock_response

    auth_api = AuthAPI(mock_client)
    result = await auth_api.login("test@example.com", "password")

    assert result["token"] == "test_token"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_token(mock_client):
    """Test refreshing token."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"token": "new_token"}
    mock_client.post.return_value = mock_response

    auth_api = AuthAPI(mock_client)
    result = await auth_api.refresh_token("old_refresh_token")

    assert result["token"] == "new_token"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_get_profile(mock_client):
    """Test getting current user profile."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "user-123", "email": "test@example.com"}
    mock_client.get.return_value = mock_response

    auth_api = AuthAPI(mock_client)
    result = await auth_api.get_profile()

    assert result["email"] == "test@example.com"
    mock_client.get.assert_called_once_with("/v1/auth/profile")


@pytest.mark.asyncio
async def test_logout(mock_client):
    """Test logout."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.post.return_value = mock_response

    auth_api = AuthAPI(mock_client)
    await auth_api.logout()

    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_update_profile(mock_client):
    """Test updating user profile."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "user-123", "name": "New Name"}
    mock_client.patch.return_value = mock_response

    auth_api = AuthAPI(mock_client)
    result = await auth_api.update_profile(name="New Name")

    assert result["name"] == "New Name"
    mock_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_logout_exception_is_silenced(mock_client):
    """Test that logout silences exceptions when the token is already invalid."""
    mock_client.post.side_effect = Exception("Token already invalid")

    auth_api = AuthAPI(mock_client)
    # Should NOT raise — the except block swallows the error
    await auth_api.logout()

    mock_client.post.assert_called_once_with("/v1/auth/logout")


@pytest.mark.asyncio
async def test_signup(mock_client):
    """Test creating a new account via signup."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": "user-456",
        "email": "newuser@example.com",
        "token": "signup_token",
    }
    mock_client.post.return_value = mock_response

    auth_api = AuthAPI(mock_client)
    result = await auth_api.signup("newuser@example.com", "securepass123")

    assert result["email"] == "newuser@example.com"
    assert result["token"] == "signup_token"
    mock_client.post.assert_called_once_with(
        "/v1/auth/register",
        json={"email": "newuser@example.com", "password": "securepass123"},
        skip_auth=True,
    )
