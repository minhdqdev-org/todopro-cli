"""Unit tests for SectionService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.models import Section, SectionCreate, SectionUpdate
from todopro_cli.services.section_service import SectionService

PROJECT_ID = "proj-abc"
SECTION_ID = "sec-123"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.get = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    repo.reorder = AsyncMock(return_value=None)
    return repo


@pytest.fixture()
def service(mock_repo):
    return SectionService(mock_repo)


def _make_section(name: str = "Sprint 1") -> MagicMock:
    from datetime import datetime

    s = MagicMock(spec=Section)
    s.name = name
    s.id = SECTION_ID
    s.project_id = PROJECT_ID
    s.display_order = 0
    s.created_at = datetime(2024, 1, 1)
    s.updated_at = datetime(2024, 1, 1)
    return s


# ---------------------------------------------------------------------------
# list_sections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_sections_delegates_to_repo(service, mock_repo):
    mock_repo.list_all.return_value = [_make_section()]
    result = await service.list_sections(PROJECT_ID)
    mock_repo.list_all.assert_called_once_with(PROJECT_ID)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_sections_returns_empty(service, mock_repo):
    mock_repo.list_all.return_value = []
    result = await service.list_sections(PROJECT_ID)
    assert result == []


# ---------------------------------------------------------------------------
# get_section
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_section_delegates_to_repo(service, mock_repo):
    mock_repo.get.return_value = _make_section()
    result = await service.get_section(PROJECT_ID, SECTION_ID)
    mock_repo.get.assert_called_once_with(PROJECT_ID, SECTION_ID)
    assert result.id == SECTION_ID


# ---------------------------------------------------------------------------
# create_section
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_section_builds_correct_payload(service, mock_repo):
    mock_repo.create.return_value = _make_section("New Section")
    await service.create_section(PROJECT_ID, "New Section", display_order=2)
    call_args = mock_repo.create.call_args
    assert call_args[0][0] == PROJECT_ID
    section_data: SectionCreate = call_args[0][1]
    assert section_data.name == "New Section"
    assert section_data.display_order == 2


@pytest.mark.asyncio
async def test_create_section_default_display_order(service, mock_repo):
    mock_repo.create.return_value = _make_section()
    await service.create_section(PROJECT_ID, "Default Order")
    section_data: SectionCreate = mock_repo.create.call_args[0][1]
    assert section_data.display_order == 0


# ---------------------------------------------------------------------------
# update_section
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_section_passes_updates(service, mock_repo):
    updated = _make_section("Updated")
    updated.name = "Updated"
    mock_repo.update.return_value = updated
    await service.update_section(PROJECT_ID, SECTION_ID, name="Updated", display_order=5)
    call_args = mock_repo.update.call_args[0]
    assert call_args[0] == PROJECT_ID
    assert call_args[1] == SECTION_ID
    updates: SectionUpdate = call_args[2]
    assert updates.name == "Updated"
    assert updates.display_order == 5


@pytest.mark.asyncio
async def test_update_section_partial(service, mock_repo):
    mock_repo.update.return_value = _make_section()
    await service.update_section(PROJECT_ID, SECTION_ID, name="Renamed")
    updates: SectionUpdate = mock_repo.update.call_args[0][2]
    assert updates.name == "Renamed"
    assert updates.display_order is None


# ---------------------------------------------------------------------------
# delete_section
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_section_delegates_to_repo(service, mock_repo):
    result = await service.delete_section(PROJECT_ID, SECTION_ID)
    mock_repo.delete.assert_called_once_with(PROJECT_ID, SECTION_ID)
    assert result is True


# ---------------------------------------------------------------------------
# reorder_sections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_sections_delegates_to_repo(service, mock_repo):
    orders = [
        {"section_id": SECTION_ID, "display_order": 0},
        {"section_id": "sec-456", "display_order": 1},
    ]
    await service.reorder_sections(PROJECT_ID, orders)
    mock_repo.reorder.assert_called_once_with(PROJECT_ID, orders)
