"""Unit tests for ScratchpadService and the Scratchpad model alias mapping."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.models import Scratchpad, ScratchpadCreate, ScratchpadUpdate
from todopro_cli.services.scratchpad_service import ScratchpadService

PROJECT_ID = "proj-abc"
SCRATCHPAD_ID = "scr-123"


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
    return repo


@pytest.fixture()
def service(mock_repo):
    return ScratchpadService(mock_repo)


def _make_scratchpad(title: str = "Notes") -> MagicMock:
    s = MagicMock(spec=Scratchpad)
    s.id = SCRATCHPAD_ID
    s.project_id = PROJECT_ID
    s.title = title
    s.content = "<p>body</p>"
    s.display_order = 0
    s.version = 1
    s.created_at = datetime(2024, 1, 1)
    s.updated_at = datetime(2024, 1, 1)
    return s


# ---------------------------------------------------------------------------
# Scratchpad model — API returns ``project``, the model exposes ``project_id``
# ---------------------------------------------------------------------------


def test_scratchpad_model_maps_project_alias():
    api_payload = {
        "id": SCRATCHPAD_ID,
        "project": PROJECT_ID,
        "title": "Notes",
        "content": "<p>hi</p>",
        "display_order": 1,
        "version": 2,
        "created_at": datetime(2024, 1, 1),
        "updated_at": datetime(2024, 1, 2),
    }
    s = Scratchpad(**api_payload)
    assert s.project_id == PROJECT_ID
    # model_dump uses the field name, not the API alias
    assert s.model_dump()["project_id"] == PROJECT_ID


# ---------------------------------------------------------------------------
# list_scratchpads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_scratchpads_delegates_to_repo(service, mock_repo):
    mock_repo.list_all.return_value = [_make_scratchpad()]
    result = await service.list_scratchpads(PROJECT_ID)
    mock_repo.list_all.assert_called_once_with(PROJECT_ID)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# get_scratchpad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_scratchpad_delegates_to_repo(service, mock_repo):
    mock_repo.get.return_value = _make_scratchpad()
    result = await service.get_scratchpad(SCRATCHPAD_ID)
    mock_repo.get.assert_called_once_with(SCRATCHPAD_ID)
    assert result.id == SCRATCHPAD_ID


# ---------------------------------------------------------------------------
# create_scratchpad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_scratchpad_builds_correct_payload(service, mock_repo):
    mock_repo.create.return_value = _make_scratchpad("New")
    await service.create_scratchpad(PROJECT_ID, title="New", content="<p>x</p>")
    call_args = mock_repo.create.call_args
    assert call_args[0][0] == PROJECT_ID
    data: ScratchpadCreate = call_args[0][1]
    assert data.title == "New"
    assert data.content == "<p>x</p>"


@pytest.mark.asyncio
async def test_create_scratchpad_defaults_empty(service, mock_repo):
    mock_repo.create.return_value = _make_scratchpad()
    await service.create_scratchpad(PROJECT_ID)
    data: ScratchpadCreate = mock_repo.create.call_args[0][1]
    assert data.title == ""
    assert data.content == ""


# ---------------------------------------------------------------------------
# update_scratchpad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_scratchpad_passes_updates(service, mock_repo):
    mock_repo.update.return_value = _make_scratchpad("Updated")
    await service.update_scratchpad(SCRATCHPAD_ID, title="Updated", content="<p>y</p>")
    call_args = mock_repo.update.call_args[0]
    assert call_args[0] == SCRATCHPAD_ID
    updates: ScratchpadUpdate = call_args[1]
    assert updates.title == "Updated"
    assert updates.content == "<p>y</p>"


@pytest.mark.asyncio
async def test_update_scratchpad_partial(service, mock_repo):
    mock_repo.update.return_value = _make_scratchpad()
    await service.update_scratchpad(SCRATCHPAD_ID, title="Renamed")
    updates: ScratchpadUpdate = mock_repo.update.call_args[0][1]
    assert updates.title == "Renamed"
    assert updates.content is None


# ---------------------------------------------------------------------------
# delete_scratchpad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_scratchpad_delegates_to_repo(service, mock_repo):
    result = await service.delete_scratchpad(SCRATCHPAD_ID)
    mock_repo.delete.assert_called_once_with(SCRATCHPAD_ID)
    assert result is True
