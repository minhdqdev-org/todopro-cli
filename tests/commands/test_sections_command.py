"""Tests for section commands."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.sections import app
from todopro_cli.models import Section

runner = CliRunner()

PROJECT_ID = "proj-abc"
SECTION_ID = "sec-123"

MOCK_SECTION = Section(
    id=SECTION_ID,
    project_id=PROJECT_ID,
    name="Sprint 1",
    display_order=0,
    task_count=3,
    created_at=datetime(2024, 1, 1, 12, 0, 0),
    updated_at=datetime(2024, 1, 1, 12, 0, 0),
)


# ---------------------------------------------------------------------------
# Shared mock for resolve functions and storage context
# ---------------------------------------------------------------------------

def _make_ctx():
    ctx = MagicMock()
    ctx.project_repository = MagicMock()
    return ctx


def _patches(section_service_mock):
    """Return a list of context managers that patch all external dependencies."""
    return [
        patch("todopro_cli.commands.sections.get_section_service", return_value=section_service_mock),
        patch("todopro_cli.commands.sections.get_storage_strategy_context", return_value=_make_ctx()),
        patch("todopro_cli.commands.sections.resolve_project_uuid", new=AsyncMock(return_value=PROJECT_ID)),
        patch("todopro_cli.commands.sections.resolve_section_id", new=AsyncMock(return_value=SECTION_ID)),
    ]


@pytest.fixture
def mock_section_service():
    """Mock SectionService for testing."""
    service_mock = MagicMock()
    service_mock.repository = MagicMock()
    service_mock.list_sections = AsyncMock(return_value=[MOCK_SECTION])
    service_mock.get_section = AsyncMock(return_value=MOCK_SECTION)
    service_mock.create_section = AsyncMock(return_value=MOCK_SECTION)
    service_mock.update_section = AsyncMock(return_value=MOCK_SECTION)
    service_mock.delete_section = AsyncMock(return_value=True)
    service_mock.reorder_sections = AsyncMock(return_value=None)
    return service_mock


def _invoke(args, svc):
    with _patches(svc)[0], _patches(svc)[1], _patches(svc)[2], _patches(svc)[3]:
        return runner.invoke(app, args)


# Cleaner helper that applies all patches at once
from contextlib import ExitStack


def invoke(args, svc):
    with ExitStack() as stack:
        for p in _patches(svc):
            stack.enter_context(p)
        return runner.invoke(app, args)


def test_list_sections(mock_section_service):
    """list command invokes service.list_sections and outputs results."""
    result = invoke(["list", PROJECT_ID, "--output", "json"], mock_section_service)
    assert result.exit_code == 0
    mock_section_service.list_sections.assert_called_once_with(PROJECT_ID)


def test_list_sections_empty(mock_section_service):
    """list returns gracefully when no sections exist."""
    mock_section_service.list_sections.return_value = []
    result = invoke(["list", PROJECT_ID], mock_section_service)
    assert result.exit_code == 0


def test_get_section(mock_section_service):
    """get command fetches a specific section."""
    result = invoke(["get", PROJECT_ID, SECTION_ID], mock_section_service)
    assert result.exit_code == 0
    mock_section_service.get_section.assert_called_once_with(PROJECT_ID, SECTION_ID)


def test_create_section(mock_section_service):
    """create command creates a section and prints success."""
    result = invoke(["create", PROJECT_ID, "My Section"], mock_section_service)
    assert result.exit_code == 0
    mock_section_service.create_section.assert_called_once_with(
        PROJECT_ID, "My Section", display_order=0
    )


def test_create_section_with_order(mock_section_service):
    """create accepts --order flag."""
    result = invoke(["create", PROJECT_ID, "Sprint", "--order", "3"], mock_section_service)
    assert result.exit_code == 0
    mock_section_service.create_section.assert_called_once_with(
        PROJECT_ID, "Sprint", display_order=3
    )


def test_update_section_name(mock_section_service):
    """update command with --name calls service.update_section."""
    result = invoke(["update", PROJECT_ID, SECTION_ID, "--name", "New Name"], mock_section_service)
    assert result.exit_code == 0
    mock_section_service.update_section.assert_called_once_with(
        PROJECT_ID, SECTION_ID, name="New Name", display_order=None
    )


def test_update_section_no_flags_exits_nonzero(mock_section_service):
    """update without any flags exits with error."""
    result = invoke(["update", PROJECT_ID, SECTION_ID], mock_section_service)
    assert result.exit_code != 0


def test_delete_section_with_yes_flag(mock_section_service):
    """delete with --yes skips confirmation."""
    result = invoke(["delete", PROJECT_ID, SECTION_ID, "--yes"], mock_section_service)
    assert result.exit_code == 0
    mock_section_service.delete_section.assert_called_once_with(PROJECT_ID, SECTION_ID)


def test_delete_section_cancel(mock_section_service):
    """delete without --yes prompts and exits cleanly on 'n'."""
    result = invoke(["delete", PROJECT_ID, SECTION_ID], mock_section_service)
    # Default input is empty → typer treats empty as "n"
    assert result.exit_code == 0


def test_reorder_sections(mock_section_service):
    """reorder command parses section_id:order pairs and resolves each section ID."""
    result = invoke(
        ["reorder", PROJECT_ID, f"{SECTION_ID}:0", "sec-456:1"],
        mock_section_service,
    )
    assert result.exit_code == 0
    # resolve_section_id is mocked to always return SECTION_ID
    mock_section_service.reorder_sections.assert_called_once_with(
        PROJECT_ID,
        [
            {"section_id": SECTION_ID, "display_order": 0},
            {"section_id": SECTION_ID, "display_order": 1},
        ],
    )


def test_reorder_sections_invalid_format(mock_section_service):
    """reorder exits nonzero for malformed pair."""
    result = invoke(["reorder", PROJECT_ID, "bad-format"], mock_section_service)
    assert result.exit_code != 0


def test_reorder_sections_non_integer_order(mock_section_service):
    """reorder exits nonzero when display_order is not an integer."""
    result = invoke(["reorder", PROJECT_ID, f"{SECTION_ID}:abc"], mock_section_service)
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# New tests: suffix/name resolution behaviours
# ---------------------------------------------------------------------------


class TestSuffixResolution:
    """Verify that resolve_project_uuid and resolve_section_id are called for suffixes."""

    def test_project_name_accepted(self, mock_section_service):
        """list accepts a project name (resolve_project_uuid handles it)."""
        with ExitStack() as stack:
            for p in _patches(mock_section_service):
                stack.enter_context(p)
            result = runner.invoke(app, ["list", "Inbox"])
        assert result.exit_code == 0

    def test_project_suffix_accepted(self, mock_section_service):
        """list accepts #suffix prefix for project (resolve_project_uuid handles it)."""
        with ExitStack() as stack:
            for p in _patches(mock_section_service):
                stack.enter_context(p)
            result = runner.invoke(app, ["list", "#abc"])
        assert result.exit_code == 0

    def test_section_suffix_accepted_for_get(self, mock_section_service):
        """get command accepts #suffix for section_id."""
        with ExitStack() as stack:
            for p in _patches(mock_section_service):
                stack.enter_context(p)
            result = runner.invoke(app, ["get", PROJECT_ID, "#ff1"])
        assert result.exit_code == 0
