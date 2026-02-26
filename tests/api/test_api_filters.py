"""Tests for Filters API."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.api.client import APIClient
from todopro_cli.services.api.filters import FiltersAPI


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.delete = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# list_filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_filters(mock_client):
    """Test listing all saved filters."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "f1", "name": "Work", "color": "#FF0000"},
    ]
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.list_filters()

    assert result == [{"id": "f1", "name": "Work", "color": "#FF0000"}]
    mock_client.get.assert_called_once_with("/v1/filters/")


# ---------------------------------------------------------------------------
# create_filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_filter_no_criteria(mock_client):
    """Test creating a filter with name and color only (no criteria)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "f1", "name": "Work", "color": "#FF5733"}
    mock_client.post.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.create_filter("Work", "#FF5733")

    assert result["id"] == "f1"
    mock_client.post.assert_called_once_with(
        "/v1/filters/",
        json={"name": "Work", "color": "#FF5733", "criteria": {}},
    )


@pytest.mark.asyncio
async def test_create_filter_with_all_criteria(mock_client):
    """Test creating a filter with all criteria fields populated."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "f2", "name": "Urgent Work"}
    mock_client.post.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.create_filter(
        "Urgent Work",
        "#FF0000",
        priority=[1],
        project_ids=["p1"],
        label_ids=["l1"],
        due_within_days=7,
    )

    assert result["id"] == "f2"
    mock_client.post.assert_called_once_with(
        "/v1/filters/",
        json={
            "name": "Urgent Work",
            "color": "#FF0000",
            "criteria": {
                "priority": [1],
                "project_ids": ["p1"],
                "label_ids": ["l1"],
                "due_within_days": 7,
            },
        },
    )


@pytest.mark.asyncio
async def test_create_filter_with_priority_only(mock_client):
    """Test creating a filter with only the priority criterion."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "f3", "name": "High Priority"}
    mock_client.post.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.create_filter("High Priority", "#0000FF", priority=[1, 2])

    assert result["id"] == "f3"
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["criteria"] == {"priority": [1, 2]}


@pytest.mark.asyncio
async def test_create_filter_due_within_days_zero(mock_client):
    """Test that due_within_days=0 is included (falsy value but not None)."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "f4"}
    mock_client.post.return_value = mock_response

    api = FiltersAPI(mock_client)
    await api.create_filter("Today Only", "#00FF00", due_within_days=0)

    call_kwargs = mock_client.post.call_args
    assert call_kwargs[1]["json"]["criteria"]["due_within_days"] == 0


# ---------------------------------------------------------------------------
# get_filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_filter(mock_client):
    """Test getting a specific filter by ID."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "f1", "name": "Work", "color": "#FF5733"}
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.get_filter("f1")

    assert result["id"] == "f1"
    mock_client.get.assert_called_once_with("/v1/filters/f1")


# ---------------------------------------------------------------------------
# delete_filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_filter(mock_client):
    """Test deleting a filter."""
    mock_client.delete.return_value = MagicMock(status_code=204)

    api = FiltersAPI(mock_client)
    await api.delete_filter("f1")

    mock_client.delete.assert_called_once_with("/v1/filters/f1")


# ---------------------------------------------------------------------------
# apply_filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_filter(mock_client):
    """Test applying a filter to retrieve matching tasks."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "task-1", "content": "Buy milk"},
        {"id": "task-2", "content": "Write tests"},
    ]
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.apply_filter("f1")

    assert len(result) == 2
    assert result[0]["id"] == "task-1"
    mock_client.get.assert_called_once_with("/v1/filters/f1/tasks")


# ---------------------------------------------------------------------------
# find_filter_by_name
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_filter_by_name_found(mock_client):
    """Test finding a filter by name when it exists (case-insensitive)."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "f1", "name": "Work"},
        {"id": "f2", "name": "Personal"},
    ]
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.find_filter_by_name("WORK")

    assert result == {"id": "f1", "name": "Work"}


@pytest.mark.asyncio
async def test_find_filter_by_name_not_found(mock_client):
    """Test finding a filter by name when it does not exist."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "f1", "name": "Work"},
    ]
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.find_filter_by_name("NonExistent")

    assert result is None


@pytest.mark.asyncio
async def test_find_filter_by_name_case_insensitive(mock_client):
    """Test that find_filter_by_name is truly case-insensitive."""
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": "f1", "name": "My Filter"},
    ]
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)

    assert await api.find_filter_by_name("my filter") == {"id": "f1", "name": "My Filter"}
    assert await api.find_filter_by_name("MY FILTER") == {"id": "f1", "name": "My Filter"}
    assert await api.find_filter_by_name("My Filter") == {"id": "f1", "name": "My Filter"}


@pytest.mark.asyncio
async def test_find_filter_by_name_empty_list(mock_client):
    """Test finding a filter by name when the filter list is empty."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_client.get.return_value = mock_response

    api = FiltersAPI(mock_client)
    result = await api.find_filter_by_name("Work")

    assert result is None
