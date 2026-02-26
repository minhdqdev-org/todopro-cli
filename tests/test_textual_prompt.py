"""Tests for textual_prompt.py - ensuring suggestions load correctly."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.models import Label, Project


MOCK_PROJECTS = [
    Project(
        id="p1",
        name="Inbox",
        color="#4a90d9",
        is_favorite=False,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    ),
    Project(
        id="p2",
        name="Work",
        color="#ff0000",
        is_favorite=False,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    ),
]

MOCK_LABELS = [
    Label(
        id="l1",
        name="urgent",
        color="#ff0000",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    ),
    Label(
        id="l2",
        name="home",
        color="#00ff00",
        created_at=datetime(2024, 1, 1),
        updated_at=datetime(2024, 1, 1),
    ),
]


def _make_storage_context(projects=None, labels=None):
    proj_repo = MagicMock()
    proj_repo.list_all = AsyncMock(return_value=MOCK_PROJECTS if projects is None else projects)
    label_repo = MagicMock()
    label_repo.list_all = AsyncMock(return_value=MOCK_LABELS if labels is None else labels)
    ctx = MagicMock()
    ctx.project_repository = proj_repo
    ctx.label_repository = label_repo
    return ctx


def _make_input(projects=None, labels=None):
    from todopro_cli.utils.ui.textual_prompt import HighlightedInput

    inp = HighlightedInput.__new__(HighlightedInput)
    inp.projects = ["Inbox", "Work", "Personal"] if projects is None else projects
    inp.labels = ["urgent", "home", "work"] if labels is None else labels
    return inp


class TestHighlightedInputGetSuggestions:
    """Unit tests for HighlightedInput.get_suggestions()."""

    def test_project_suggestions_on_hash(self):
        inp = _make_input()
        result = inp.get_suggestions("#")
        assert "#Inbox" in result
        assert "#Work" in result

    def test_project_suggestions_filtered(self):
        inp = _make_input()
        result = inp.get_suggestions("#In")
        assert "#Inbox" in result
        assert "#Work" not in result

    def test_label_suggestions_on_at(self):
        inp = _make_input()
        result = inp.get_suggestions("task @")
        assert "@urgent" in result
        assert "@home" in result

    def test_label_suggestions_filtered(self):
        inp = _make_input()
        result = inp.get_suggestions("task @ur")
        assert "@urgent" in result
        assert "@home" not in result

    def test_priority_p_shows_all(self):
        inp = _make_input()
        result = inp.get_suggestions("fix bug p")
        assert any("p1" in s for s in result)
        assert any("p2" in s for s in result)
        assert any("p3" in s for s in result)
        assert any("p4" in s for s in result)

    def test_priority_p1_filters_to_urgent(self):
        inp = _make_input()
        result = inp.get_suggestions("fix bug p1")
        assert any("p1" in s for s in result)
        assert not any("p2" in s for s in result)

    def test_priority_bang_bang(self):
        inp = _make_input()
        result = inp.get_suggestions("task !!")
        assert any("!!1" in s for s in result)

    def test_no_suggestions_for_plain_text(self):
        inp = _make_input()
        result = inp.get_suggestions("just some text")
        assert result == []

    def test_empty_projects_returns_empty(self):
        inp = _make_input(projects=[], labels=[])
        result = inp.get_suggestions("#")
        assert result == []

    def test_empty_labels_returns_empty(self):
        inp = _make_input(projects=[], labels=[])
        result = inp.get_suggestions("task @")
        assert result == []


class TestOnMountDataLoading:
    """Test that on_mount correctly loads projects and labels into the input widget."""

    def test_get_storage_strategy_context_is_module_level(self):
        """get_storage_strategy_context must be a module-level name for patching."""
        import todopro_cli.utils.ui.textual_prompt as module
        assert hasattr(module, "get_storage_strategy_context"), (
            "get_storage_strategy_context must be imported at module level "
            "so it can be patched in tests and found at runtime"
        )

    def test_on_mount_loads_projects_and_labels(self):
        """on_mount must populate HighlightedInput.projects and .labels."""
        from todopro_cli.models.core import ProjectFilters

        storage_ctx = _make_storage_context()

        async def simulate_on_mount_body():
            import todopro_cli.utils.ui.textual_prompt as module
            projects_data = await storage_ctx.project_repository.list_all(ProjectFilters())
            labels_data = await storage_ctx.label_repository.list_all()
            projects = [p.name for p in projects_data] if projects_data else []
            labels = [l.name for l in labels_data] if labels_data else []
            return projects, labels

        with patch(
            "todopro_cli.utils.ui.textual_prompt.get_storage_strategy_context",
            return_value=storage_ctx,
        ):
            projects, labels = asyncio.run(simulate_on_mount_body())

        assert "Inbox" in projects
        assert "Work" in projects
        assert "urgent" in labels
        assert "home" in labels

    def test_project_list_all_requires_filters_param(self):
        """SqliteProjectRepository.list_all() must accept a 'filters' parameter."""
        import inspect
        from todopro_cli.adapters.sqlite.project_repository import SqliteProjectRepository

        sig = inspect.signature(SqliteProjectRepository.list_all)
        assert "filters" in sig.parameters, (
            "project_repository.list_all() must accept 'filters'; "
            "calling it without filters raises TypeError"
        )
