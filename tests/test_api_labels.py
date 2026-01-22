"""Tests for Labels API."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from todopro_cli.api.labels import LabelsAPI
from todopro_cli.api.client import APIClient


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_list_labels(mock_client):
    """Test listing labels."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"labels": []}
    mock_client.get.return_value = mock_response
    
    labels_api = LabelsAPI(mock_client)
    result = await labels_api.list_labels()
    
    assert result == {"labels": []}
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_create_label(mock_client):
    """Test creating a label."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "label-123", "name": "urgent"}
    mock_client.post.return_value = mock_response
    
    labels_api = LabelsAPI(mock_client)
    result = await labels_api.create_label("urgent")
    
    assert result["name"] == "urgent"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_update_label(mock_client):
    """Test updating a label."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "label-123", "name": "critical"}
    mock_client.patch.return_value = mock_response
    
    labels_api = LabelsAPI(mock_client)
    result = await labels_api.update_label("label-123", name="critical")
    
    assert result["name"] == "critical"
    mock_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_delete_label(mock_client):
    """Test deleting a label."""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_client.delete.return_value = mock_response
    
    labels_api = LabelsAPI(mock_client)
    await labels_api.delete_label("label-123")
    
    mock_client.delete.assert_called_once_with("/v1/labels/label-123")


@pytest.mark.asyncio
async def test_get_label(mock_client):
    """Test getting a specific label."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "label-123", "name": "urgent"}
    mock_client.get.return_value = mock_response
    
    labels_api = LabelsAPI(mock_client)
    result = await labels_api.get_label("label-123")
    
    assert result["name"] == "urgent"
    mock_client.get.assert_called_once()
