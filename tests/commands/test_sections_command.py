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


@pytest.fixture
def mock_section_service():
    """Mock SectionService for testing."""
    service_mock = MagicMock()
    service_mock.list_sections = AsyncMock(return_value=[MOCK_SECTION])
    service_mock.get_section = AsyncMock(return_value=MOCK_SECTION)
    service_mock.create_section = AsyncMock(return_value=MOCK_SECTION)
    service_mock.update_section = AsyncMock(return_value=MOCK_SECTION)
    service_mock.delete_section = AsyncMock(return_value=True)
    service_mock.reorder_sections = AsyncMock(return_value=None)

    with patch(
        "todopro_cli.commands.sections.get_section_service",
        return_value=service_mock,
    ):
        yield service_mock


def test_list_sections(mock_section_service):
    """list command invokes service.list_sections and outputs results."""
    result = runner.invoke(app, ["list", PROJECT_ID, "--output", "json"])
    assert result.exit_code == 0
    mock_section_service.list_sections.assert_called_once_with(PROJECT_ID)


def test_list_sections_empty(mock_section_service):
    """list returns gracefully when no sections exist."""
    mock_section_service.list_sections.return_value = []
    result = runner.invoke(app, ["list", PROJECT_ID])
    assert result.exit_code == 0


def test_get_section(mock_section_service):
    """get command fetches a specific section."""
    result = runner.invoke(app, ["get", PROJECT_ID, SECTION_ID])
    assert result.exit_code == 0
    mock_section_service.get_section.assert_called_once_with(PROJECT_ID, SECTION_ID)


def test_create_section(mock_section_service):
    """create command creates a section and prints success."""
    result = runner.invoke(app, ["create", PROJECT_ID, "My Section"])
    assert result.exit_code == 0
    mock_section_service.create_section.assert_called_once_with(
        PROJECT_ID, "My Section", display_order=0
    )


def test_create_section_with_order(mock_section_service):
    """create accepts --order flag."""
    result = runner.invoke(app, ["create", PROJECT_ID, "Sprint", "--order", "3"])
    assert result.exit_code == 0
    mock_section_service.create_section.assert_called_once_with(
        PROJECT_ID, "Sprint", display_order=3
    )


def test_update_section_name(mock_section_service):
    """update command with --name calls service.update_section."""
    result = runner.invoke(app, ["update", PROJECT_ID, SECTION_ID, "--name", "New Name"])
    assert result.exit_code == 0
    mock_section_service.update_section.assert_called_once_with(
        PROJECT_ID, SECTION_ID, name="New Name", display_order=None
    )


def test_update_section_no_flags_exits_nonzero(mock_section_service):
    """update without any flags exits with error."""
    result = runner.invoke(app, ["update", PROJECT_ID, SECTION_ID])
    assert result.exit_code != 0


def test_delete_section_with_yes_flag(mock_section_service):
    """delete with --yes skips confirmation."""
    result = runner.invoke(app, ["delete", PROJECT_ID, SECTION_ID, "--yes"])
    assert result.exit_code == 0
    mock_section_service.delete_section.assert_called_once_with(PROJECT_ID, SECTION_ID)


def test_delete_section_cancel(mock_section_service):
    """delete without --yes prompts and exits cleanly on 'n'."""
    result = runner.invoke(app, ["delete", PROJECT_ID, SECTION_ID], input="n\n")
    assert result.exit_code == 0
    mock_section_service.delete_section.assert_not_called()


def test_reorder_sections(mock_section_service):
    """reorder command parses section_id:order pairs correctly."""
    result = runner.invoke(
        app,
        ["reorder", PROJECT_ID, f"{SECTION_ID}:0", "sec-456:1"],
    )
    assert result.exit_code == 0
    mock_section_service.reorder_sections.assert_called_once_with(
        PROJECT_ID,
        [
            {"section_id": SECTION_ID, "display_order": 0},
            {"section_id": "sec-456", "display_order": 1},
        ],
    )


def test_reorder_sections_invalid_format(mock_section_service):
    """reorder exits nonzero for malformed pair."""
    result = runner.invoke(app, ["reorder", PROJECT_ID, "bad-format"])
    assert result.exit_code != 0


def test_reorder_sections_non_integer_order(mock_section_service):
    """reorder exits nonzero when display_order is not an integer."""
    result = runner.invoke(app, ["reorder", PROJECT_ID, f"{SECTION_ID}:abc"])
    assert result.exit_code != 0
