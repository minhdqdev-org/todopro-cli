"""Unit tests for ProjectService – focused on previously-uncovered lines.

Covered missing lines
---------------------
* 112-123  update_project when the current project name is 'inbox' raises ValueError
* 134-137  delete_project when project name is 'inbox' raises ValueError
* 150      archive_project when project name is 'inbox' raises ValueError
* 174-175  favorite_project calls repo.update with is_favorite=True
* 186      unarchive_project delegates to repo.unarchive
* 197      get_project_stats delegates to repo.get_stats
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.models import Project, ProjectUpdate
from todopro_cli.services.project_service import ProjectService


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
    repo.archive = AsyncMock()
    repo.unarchive = AsyncMock()
    repo.get_stats = AsyncMock(return_value={})
    return repo


@pytest.fixture()
def service(mock_repo):
    return ProjectService(mock_repo)


def _make_project(name: str, protected: bool = False) -> MagicMock:
    p = MagicMock(spec=Project)
    p.name = name
    p.protected = protected
    return p


# ---------------------------------------------------------------------------
# update_project – inbox guard (lines 112-123)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_project_rename_inbox_raises_value_error(service, mock_repo):
    """Renaming a protected project must raise."""
    mock_repo.get.return_value = _make_project("Inbox", protected=True)

    with pytest.raises(ValueError, match="Cannot rename"):
        await service.update_project("proj-1", name="Work")


@pytest.mark.asyncio
async def test_update_project_rename_inbox_lowercase_raises(service, mock_repo):
    """Guard uses protected field – lowercase 'inbox' with protected=True also raises."""
    mock_repo.get.return_value = _make_project("inbox", protected=True)

    with pytest.raises(ValueError, match="Cannot rename"):
        await service.update_project("proj-1", name="Personal")



@pytest.mark.asyncio
async def test_update_project_non_inbox_succeeds(service, mock_repo):
    """Renaming a normal project should succeed without raising."""
    mock_project = _make_project("Work", protected=False)
    mock_repo.get.return_value = mock_project
    mock_repo.update.return_value = mock_project

    result = await service.update_project("proj-2", name="Home")

    assert result is mock_project
    mock_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_project_no_name_skips_inbox_check(service, mock_repo):
    """Updating fields other than name must NOT call repo.get or raise."""
    mock_project = _make_project("Inbox")
    mock_repo.update.return_value = mock_project

    await service.update_project("proj-1", color="#ff0000")

    mock_repo.get.assert_not_awaited()


# ---------------------------------------------------------------------------
# delete_project – inbox guard (lines 134-137)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_inbox_project_raises_value_error(service, mock_repo):
    """Deleting a protected project must raise ValueError."""
    mock_repo.get.return_value = _make_project("inbox", protected=True)

    with pytest.raises(ValueError, match="Cannot delete"):
        await service.delete_project("proj-inbox")

    mock_repo.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_inbox_project_case_insensitive(service, mock_repo):
    """protected flag drives the check regardless of name casing."""
    mock_repo.get.return_value = _make_project("INBOX", protected=True)

    with pytest.raises(ValueError):
        await service.delete_project("proj-inbox")


@pytest.mark.asyncio
async def test_delete_non_inbox_project_succeeds(service, mock_repo):
    """Deleting a non-protected project should call repo.delete and return True."""
    mock_repo.get.return_value = _make_project("Shopping", protected=False)
    mock_repo.delete.return_value = True

    result = await service.delete_project("proj-shop")

    assert result is True
    mock_repo.delete.assert_awaited_once_with("proj-shop")


# ---------------------------------------------------------------------------
# archive_project – inbox guard (line 150)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_inbox_project_raises_value_error(service, mock_repo):
    """Archiving a protected project must raise ValueError."""
    mock_repo.get.return_value = _make_project("Inbox", protected=True)

    with pytest.raises(ValueError, match="Cannot archive"):
        await service.archive_project("proj-inbox")

    mock_repo.archive.assert_not_awaited()


@pytest.mark.asyncio
async def test_archive_non_inbox_project_succeeds(service, mock_repo):
    """Archiving a regular project should call repo.archive."""
    mock_project = _make_project("Archive me", protected=False)
    mock_repo.get.return_value = mock_project
    mock_repo.archive.return_value = mock_project

    result = await service.archive_project("proj-3")

    assert result is mock_project
    mock_repo.archive.assert_awaited_once_with("proj-3")


# ---------------------------------------------------------------------------
# favorite_project (lines 174-175)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_favorite_project_calls_update_with_is_favorite_true(service, mock_repo):
    """favorite_project should call repo.update with is_favorite=True."""
    mock_project = _make_project("Side project")
    mock_repo.update.return_value = mock_project

    result = await service.favorite_project("proj-4")

    assert result is mock_project
    mock_repo.update.assert_awaited_once()
    proj_id_arg, update_arg = mock_repo.update.call_args[0]
    assert proj_id_arg == "proj-4"
    assert isinstance(update_arg, ProjectUpdate)
    assert update_arg.is_favorite is True


# ---------------------------------------------------------------------------
# unarchive_project (line 186)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unarchive_project_delegates_to_repo(service, mock_repo):
    """unarchive_project should delegate directly to repo.unarchive."""
    mock_project = _make_project("Old project")
    mock_repo.unarchive.return_value = mock_project

    result = await service.unarchive_project("proj-5")

    assert result is mock_project
    mock_repo.unarchive.assert_awaited_once_with("proj-5")


# ---------------------------------------------------------------------------
# get_project_stats (line 197)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_project_stats_delegates_to_repo(service, mock_repo):
    """get_project_stats should delegate to repo.get_stats and return its result."""
    stats = {"total_tasks": 10, "completed_tasks": 4}
    mock_repo.get_stats.return_value = stats

    result = await service.get_project_stats("proj-6")

    assert result == stats
    mock_repo.get_stats.assert_awaited_once_with("proj-6")


# ---------------------------------------------------------------------------
# Basic CRUD – list_projects, get_project, create_project (lines 43-49, 60, 81-87)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_projects_delegates_to_repo(service, mock_repo):
    """list_projects should build ProjectFilters and call repo.list_all."""
    mock_proj = _make_project("Work")
    mock_repo.list_all.return_value = [mock_proj]

    result = await service.list_projects(is_favorite=True, is_archived=False)

    assert result == [mock_proj]
    mock_repo.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_projects_no_filters(service, mock_repo):
    """list_projects with no args should still call repo.list_all."""
    mock_repo.list_all.return_value = []
    result = await service.list_projects()
    assert result == []
    mock_repo.list_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_project_delegates_to_repo(service, mock_repo):
    """get_project should delegate to repo.get."""
    mock_proj = _make_project("My Project")
    mock_repo.get.return_value = mock_proj

    result = await service.get_project("proj-abc")

    assert result is mock_proj
    mock_repo.get.assert_awaited_once_with("proj-abc")


@pytest.mark.asyncio
async def test_create_project_delegates_to_repo(service, mock_repo):
    """create_project should build ProjectCreate and call repo.create."""
    mock_proj = _make_project("New Project")
    mock_repo.create.return_value = mock_proj

    result = await service.create_project("New Project", color="#ff0000", is_favorite=True)

    assert result is mock_proj
    mock_repo.create.assert_awaited_once()
    create_arg = mock_repo.create.call_args[0][0]
    assert create_arg.name == "New Project"
    assert create_arg.color == "#ff0000"
    assert create_arg.is_favorite is True


# ---------------------------------------------------------------------------
# unfavorite_project (lines 174-175)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unfavorite_project_calls_update_with_is_favorite_false(service, mock_repo):
    """unfavorite_project should call repo.update with is_favorite=False."""
    mock_proj = _make_project("Side project")
    mock_repo.update.return_value = mock_proj

    result = await service.unfavorite_project("proj-7")

    assert result is mock_proj
    mock_repo.update.assert_awaited_once()
    proj_id_arg, update_arg = mock_repo.update.call_args[0]
    assert proj_id_arg == "proj-7"
    assert isinstance(update_arg, ProjectUpdate)
    assert update_arg.is_favorite is False


# ---------------------------------------------------------------------------
# get_project_service factory (lines 202-207)
# ---------------------------------------------------------------------------


def test_get_project_service_factory(mocker):
    """get_project_service should return a ProjectService wrapping the repo from context."""
    from todopro_cli.services.project_service import get_project_service

    mock_repo = MagicMock()
    mock_context = MagicMock()
    mock_context.project_repository = mock_repo

    mocker.patch(
        "todopro_cli.services.config_service.get_storage_strategy_context",
        return_value=mock_context,
    )

    service = get_project_service()
    assert isinstance(service, ProjectService)
    assert service.repository is mock_repo
