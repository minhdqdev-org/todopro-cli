"""Unit tests for LabelService – focused on previously-uncovered lines.

Covered missing lines
---------------------
* 41       delete_label – delegates to repo.delete
* 70       search_labels – delegates to repo.search
* 107-111  get_or_create_label – the *create* branch (label not found by name)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.models import Label
from todopro_cli.services.label_service import LabelService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_repo():
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    repo.get = AsyncMock()
    repo.create = AsyncMock()
    repo.delete = AsyncMock(return_value=True)
    repo.search = AsyncMock(return_value=[])
    return repo


@pytest.fixture()
def service(mock_repo):
    return LabelService(mock_repo)


def _make_label(name: str, label_id: str = "lbl-1") -> MagicMock:
    lbl = MagicMock(spec=Label)
    lbl.id = label_id
    lbl.name = name
    return lbl


# ---------------------------------------------------------------------------
# delete_label (line 41)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_label_delegates_to_repo(service, mock_repo):
    """delete_label should call repo.delete with the given ID and return the result."""
    mock_repo.delete.return_value = True

    result = await service.delete_label("lbl-42")

    assert result is True
    mock_repo.delete.assert_awaited_once_with("lbl-42")


@pytest.mark.asyncio
async def test_delete_label_returns_false_when_repo_returns_false(service, mock_repo):
    """delete_label should propagate False from the repository."""
    mock_repo.delete.return_value = False

    result = await service.delete_label("lbl-unknown")

    assert result is False


# ---------------------------------------------------------------------------
# search_labels (line 70)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_labels_delegates_to_repo(service, mock_repo):
    """search_labels should call repo.search with the prefix and return its result."""
    labels = [_make_label("@work"), _make_label("@weekend")]
    mock_repo.search.return_value = labels

    result = await service.search_labels("@w")

    assert result == labels
    mock_repo.search.assert_awaited_once_with("@w")


@pytest.mark.asyncio
async def test_search_labels_returns_empty_list_when_no_matches(service, mock_repo):
    """search_labels should return an empty list when the repo finds nothing."""
    mock_repo.search.return_value = []

    result = await service.search_labels("@zzz")

    assert result == []


# ---------------------------------------------------------------------------
# get_or_create_label – existing label branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_label_returns_existing_exact_match(service, mock_repo):
    """get_or_create_label must return the existing label on exact-case match."""
    existing = _make_label("@home")
    mock_repo.list_all.return_value = [existing]

    result = await service.get_or_create_label("@home")

    assert result is existing
    mock_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_label_returns_existing_case_insensitive(service, mock_repo):
    """get_or_create_label uses case-insensitive matching for existing labels."""
    existing = _make_label("@Home")
    mock_repo.list_all.return_value = [existing]

    result = await service.get_or_create_label("@HOME")

    assert result is existing
    mock_repo.create.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_or_create_label – create branch (lines 107-111)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_label_creates_when_not_found(service, mock_repo):
    """get_or_create_label must create and return a new label when none match."""
    mock_repo.list_all.return_value = []  # no existing labels
    new_label = _make_label("@errands", "lbl-new")
    mock_repo.create.return_value = new_label

    result = await service.get_or_create_label("@errands")

    assert result is new_label
    mock_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_label_creates_with_color_when_not_found(service, mock_repo):
    """get_or_create_label passes the optional color to create_label."""
    mock_repo.list_all.return_value = []
    new_label = _make_label("@urgent", "lbl-u")
    mock_repo.create.return_value = new_label

    result = await service.get_or_create_label("@urgent", color="#ff0000")

    assert result is new_label
    # Inspect what was passed to repo.create
    label_create_arg = mock_repo.create.call_args[0][0]
    assert label_create_arg.color == "#ff0000"
    assert label_create_arg.name == "@urgent"


@pytest.mark.asyncio
async def test_get_or_create_label_creates_when_existing_labels_dont_match(
    service, mock_repo
):
    """get_or_create_label creates a new label when existing ones have different names."""
    mock_repo.list_all.return_value = [_make_label("@work"), _make_label("@home")]
    new_label = _make_label("@gym", "lbl-gym")
    mock_repo.create.return_value = new_label

    result = await service.get_or_create_label("@gym")

    assert result is new_label
    mock_repo.create.assert_awaited_once()


# ---------------------------------------------------------------------------
# get_label (line 41)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_label_delegates_to_repo(service, mock_repo):
    """get_label should delegate to repo.get with the given label ID."""
    existing = _make_label("@work")
    mock_repo.get.return_value = existing

    result = await service.get_label("lbl-1")

    assert result is existing
    mock_repo.get.assert_awaited_once_with("lbl-1")


# ---------------------------------------------------------------------------
# get_label_service factory (lines 107-111)
# ---------------------------------------------------------------------------


def test_get_label_service_factory(mocker):
    """get_label_service should return a LabelService wrapping the repo from context."""
    from todopro_cli.services.label_service import get_label_service, LabelService

    mock_repo = MagicMock()
    mock_context = MagicMock()
    mock_context.label_repository = mock_repo

    mocker.patch(
        "todopro_cli.services.config_service.get_storage_strategy_context",
        return_value=mock_context,
    )

    service = get_label_service()
    assert isinstance(service, LabelService)
    assert service.repository is mock_repo
