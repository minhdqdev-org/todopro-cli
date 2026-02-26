"""Tests for Collaboration API."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.api.client import APIClient
from todopro_cli.services.api.collaboration import CollaborationAPI


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Project sharing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_share_project(mock_client):
    """Test sharing a project with a user by email."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "project_id": "p1",
        "email": "alice@example.com",
        "permission": "editor",
    }
    mock_client.post.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.share_project("p1", "alice@example.com", "editor")

    assert result["email"] == "alice@example.com"
    assert result["permission"] == "editor"
    mock_client.post.assert_called_once_with(
        "/v1/projects/p1/share",
        json={"email": "alice@example.com", "permission": "editor"},
    )


@pytest.mark.asyncio
async def test_share_project_default_permission(mock_client):
    """Test sharing a project uses 'editor' as the default permission."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"permission": "editor"}
    mock_client.post.return_value = mock_response

    api = CollaborationAPI(mock_client)
    await api.share_project("p1", "bob@example.com")

    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["permission"] == "editor"


@pytest.mark.asyncio
async def test_get_collaborators(mock_client):
    """Test getting all collaborators for a project."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"user_id": "u1", "email": "alice@example.com", "permission": "editor"},
        {"user_id": "u2", "email": "bob@example.com", "permission": "viewer"},
    ]
    mock_client.get.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.get_collaborators("p1")

    assert len(result) == 2
    assert result[0]["email"] == "alice@example.com"
    mock_client.get.assert_called_once_with("/v1/projects/p1/collaborators")


@pytest.mark.asyncio
async def test_update_collaborator_permission(mock_client):
    """Test updating a collaborator's permission on a project."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"user_id": "u1", "permission": "viewer"}
    mock_client.patch.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.update_collaborator_permission("p1", "u1", "viewer")

    assert result["permission"] == "viewer"
    mock_client.patch.assert_called_once_with(
        "/v1/projects/p1/collaborators/u1",
        json={"permission": "viewer"},
    )


@pytest.mark.asyncio
async def test_remove_collaborator(mock_client):
    """Test removing a collaborator from a project."""
    mock_client.delete.return_value = MagicMock(status_code=204)

    api = CollaborationAPI(mock_client)
    await api.remove_collaborator("p1", "u1")

    mock_client.delete.assert_called_once_with("/v1/projects/p1/collaborators/u1")


@pytest.mark.asyncio
async def test_leave_project(mock_client):
    """Test leaving a project (removing self as collaborator)."""
    mock_client.delete.return_value = MagicMock(status_code=204)

    api = CollaborationAPI(mock_client)
    await api.leave_project("p1")

    mock_client.delete.assert_called_once_with("/v1/projects/p1/leave")


# ---------------------------------------------------------------------------
# Task assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_task(mock_client):
    """Test assigning a task to a user by email."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "task_id": "t1",
        "assignee": "alice@example.com",
    }
    mock_client.patch.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.assign_task("t1", "alice@example.com")

    assert result["assignee"] == "alice@example.com"
    mock_client.patch.assert_called_once_with(
        "/v1/tasks/t1/assign",
        json={"email": "alice@example.com"},
    )


@pytest.mark.asyncio
async def test_unassign_task(mock_client):
    """Test unassigning a task - returns response.json()."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"task_id": "t1", "assignee": None}
    mock_client.delete.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.unassign_task("t1")

    assert result["assignee"] is None
    mock_client.delete.assert_called_once_with("/v1/tasks/t1/assign")
    # Ensure we called .json() on the response (not .content or similar)
    mock_response.json.assert_called_once()


# ---------------------------------------------------------------------------
# Task comments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_comments(mock_client):
    """Test getting all comments for a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "c1", "content": "First comment"},
        {"id": "c2", "content": "Second comment"},
    ]
    mock_client.get.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.get_comments("t1")

    assert len(result) == 2
    assert result[0]["id"] == "c1"
    mock_client.get.assert_called_once_with("/v1/tasks/t1/comments")


@pytest.mark.asyncio
async def test_add_comment(mock_client):
    """Test adding a comment to a task."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "c1", "content": "Nice work!"}
    mock_client.post.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.add_comment("t1", "Nice work!")

    assert result["content"] == "Nice work!"
    mock_client.post.assert_called_once_with(
        "/v1/tasks/t1/comments",
        json={"content": "Nice work!"},
    )


@pytest.mark.asyncio
async def test_update_comment(mock_client):
    """Test updating an existing comment."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "c1", "content": "Updated comment"}
    mock_client.patch.return_value = mock_response

    api = CollaborationAPI(mock_client)
    result = await api.update_comment("t1", "c1", "Updated comment")

    assert result["content"] == "Updated comment"
    mock_client.patch.assert_called_once_with(
        "/v1/tasks/t1/comments/c1",
        json={"content": "Updated comment"},
    )


@pytest.mark.asyncio
async def test_delete_comment(mock_client):
    """Test deleting a comment from a task."""
    mock_client.delete.return_value = MagicMock(status_code=204)

    api = CollaborationAPI(mock_client)
    await api.delete_comment("t1", "c1")

    mock_client.delete.assert_called_once_with("/v1/tasks/t1/comments/c1")
