"""Tests for Auth API."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from todopro_cli.api.auth import AuthAPI
from todopro_cli.api.client import APIClient


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_login(mock_client):
    """Test login."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "token": "test_token",
        "refresh_token": "test_refresh_token"
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
