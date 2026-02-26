"""Unit tests for AchievementService and get_achievement_service factory.

Covered missing lines
---------------------
* All methods in AchievementService:
  - __init__
  - check_achievement(latitude, longitude) → bool
* get_achievement_service factory function
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.services.achievement_service import AchievementService, get_achievement_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_context_repo():
    repo = MagicMock()
    repo.get_available = AsyncMock(return_value=[])
    return repo


@pytest.fixture()
def service(mock_context_repo):
    return AchievementService(mock_context_repo)


# ---------------------------------------------------------------------------
# AchievementService.__init__
# ---------------------------------------------------------------------------


def test_achievement_service_stores_repository(mock_context_repo):
    """AchievementService should store the repository on self.context_repository."""
    svc = AchievementService(mock_context_repo)
    assert svc.context_repository is mock_context_repo


# ---------------------------------------------------------------------------
# check_achievement – False branch (no available contexts)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_achievement_returns_false_when_no_contexts(service, mock_context_repo):
    """check_achievement must return False when get_available returns an empty list."""
    mock_context_repo.get_available.return_value = []

    result = await service.check_achievement(37.7749, -122.4194)

    assert result is False
    mock_context_repo.get_available.assert_awaited_once_with(37.7749, -122.4194)


# ---------------------------------------------------------------------------
# check_achievement – True branch (contexts available)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_achievement_returns_true_when_contexts_available(
    service, mock_context_repo
):
    """check_achievement must return True when get_available returns non-empty list."""
    mock_context_repo.get_available.return_value = [MagicMock(), MagicMock()]

    result = await service.check_achievement(37.7749, -122.4194)

    assert result is True


@pytest.mark.asyncio
async def test_check_achievement_returns_true_for_single_context(
    service, mock_context_repo
):
    """A single available context is enough to return True."""
    mock_context_repo.get_available.return_value = [MagicMock()]

    result = await service.check_achievement(51.5074, -0.1278)

    assert result is True


# ---------------------------------------------------------------------------
# check_achievement – coordinates are forwarded to the repository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_achievement_passes_coordinates_to_repo(service, mock_context_repo):
    """check_achievement must forward latitude and longitude to get_available."""
    lat, lon = 48.8566, 2.3522  # Paris
    mock_context_repo.get_available.return_value = []

    await service.check_achievement(lat, lon)

    mock_context_repo.get_available.assert_awaited_once_with(lat, lon)


# ---------------------------------------------------------------------------
# get_achievement_service factory
# ---------------------------------------------------------------------------


def test_get_achievement_service_returns_achievement_service_instance():
    """get_achievement_service() must return an AchievementService instance."""
    mock_repo = MagicMock()
    mock_storage_ctx = MagicMock()
    mock_storage_ctx.achievement_repository = mock_repo

    with patch(
        "todopro_cli.services.config_service.get_storage_strategy_context",
        return_value=mock_storage_ctx,
    ):
        svc = get_achievement_service()

    assert isinstance(svc, AchievementService)
    assert svc.context_repository is mock_repo
