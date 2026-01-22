"""Tests for Projects API."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from todopro_cli.api.projects import ProjectsAPI
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
async def test_list_projects(mock_client):
    """Test listing projects."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"projects": []}
    mock_client.get.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    result = await projects_api.list_projects()
    
    assert result == {"projects": []}
    mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_project(mock_client):
    """Test getting a specific project."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "proj-123", "name": "Test Project"}
    mock_client.get.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    result = await projects_api.get_project("proj-123")
    
    assert result["id"] == "proj-123"
    mock_client.get.assert_called_once_with("/v1/projects/proj-123")


@pytest.mark.asyncio
async def test_create_project(mock_client):
    """Test creating a project."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "proj-123", "name": "New Project"}
    mock_client.post.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    result = await projects_api.create_project("New Project")
    
    assert result["name"] == "New Project"
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_update_project(mock_client):
    """Test updating a project."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "proj-123", "name": "Updated Project"}
    mock_client.patch.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    result = await projects_api.update_project("proj-123", name="Updated Project")
    
    assert result["name"] == "Updated Project"
    mock_client.patch.assert_called_once()


@pytest.mark.asyncio
async def test_delete_project(mock_client):
    """Test deleting a project."""
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_client.delete.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    await projects_api.delete_project("proj-123")
    
    mock_client.delete.assert_called_once_with("/v1/projects/proj-123")


@pytest.mark.asyncio
async def test_archive_project(mock_client):
    """Test archiving a project."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "proj-123", "is_archived": True}
    mock_client.post.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    result = await projects_api.archive_project("proj-123")
    
    assert result["is_archived"] is True
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_unarchive_project(mock_client):
    """Test unarchiving a project."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "proj-123", "is_archived": False}
    mock_client.post.return_value = mock_response
    
    projects_api = ProjectsAPI(mock_client)
    result = await projects_api.unarchive_project("proj-123")
    
    assert result["is_archived"] is False
    mock_client.post.assert_called_once()
