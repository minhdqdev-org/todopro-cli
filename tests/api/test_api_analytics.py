"""Tests for Analytics API."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.api.client import APIClient
from todopro_cli.services.api.analytics import AnalyticsAPI


@pytest.fixture
def mock_client():
    """Create a mock API client."""
    client = MagicMock(spec=APIClient)
    client.get = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# get_productivity_score
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_productivity_score(mock_client):
    """Test getting productivity score returns response.json()."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "score": 87,
        "trend": "up",
        "breakdown": {"completed": 20, "overdue": 2},
    }
    mock_client.get.return_value = mock_response

    api = AnalyticsAPI(mock_client)
    result = await api.get_productivity_score()

    assert result["score"] == 87
    assert result["trend"] == "up"
    mock_client.get.assert_called_once_with("/v1/analytics/productivity-score")
    mock_response.json.assert_called_once()


# ---------------------------------------------------------------------------
# get_streaks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_streaks(mock_client):
    """Test getting task completion streaks returns response.json()."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "current_streak": 5,
        "longest_streak": 14,
        "streak_history": [],
    }
    mock_client.get.return_value = mock_response

    api = AnalyticsAPI(mock_client)
    result = await api.get_streaks()

    assert result["current_streak"] == 5
    assert result["longest_streak"] == 14
    mock_client.get.assert_called_once_with("/v1/analytics/streaks")
    mock_response.json.assert_called_once()


# ---------------------------------------------------------------------------
# get_completion_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_completion_stats(mock_client):
    """Test getting completion statistics returns response.json()."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "total_completed": 150,
        "completion_rate": 0.82,
    }
    mock_client.get.return_value = mock_response

    api = AnalyticsAPI(mock_client)
    result = await api.get_completion_stats()

    assert result["total_completed"] == 150
    assert result["completion_rate"] == 0.82
    mock_client.get.assert_called_once_with("/v1/analytics/completion-stats")
    mock_response.json.assert_called_once()


# ---------------------------------------------------------------------------
# export_data — returns response.content (bytes), NOT .json()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_data_csv(mock_client):
    """Test exporting data as CSV returns raw bytes (response.content)."""
    csv_bytes = b"id,content,status\ntask-1,Buy milk,open\n"
    mock_response = MagicMock()
    mock_response.content = csv_bytes
    mock_client.get.return_value = mock_response

    api = AnalyticsAPI(mock_client)
    result = await api.export_data(format="csv")

    assert result == csv_bytes
    assert isinstance(result, bytes)
    mock_client.get.assert_called_once_with("/v1/analytics/export?format=csv")
    # Critically: .json() must NOT have been called
    mock_response.json.assert_not_called()


@pytest.mark.asyncio
async def test_export_data_json_format(mock_client):
    """Test exporting data as JSON format also returns raw bytes."""
    json_bytes = b'[{"id": "task-1", "content": "Buy milk"}]'
    mock_response = MagicMock()
    mock_response.content = json_bytes
    mock_client.get.return_value = mock_response

    api = AnalyticsAPI(mock_client)
    result = await api.export_data(format="json")

    assert result == json_bytes
    assert isinstance(result, bytes)
    mock_client.get.assert_called_once_with("/v1/analytics/export?format=json")
    mock_response.json.assert_not_called()


@pytest.mark.asyncio
async def test_export_data_default_format_is_csv(mock_client):
    """Test that the default export format is 'csv'."""
    mock_response = MagicMock()
    mock_response.content = b""
    mock_client.get.return_value = mock_response

    api = AnalyticsAPI(mock_client)
    await api.export_data()

    mock_client.get.assert_called_once_with("/v1/analytics/export?format=csv")
