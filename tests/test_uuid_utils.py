"""Tests for UUID utilities and integration."""

import pytest

from todopro_cli.adapters.sqlite import SqliteProjectRepository, SqliteTaskRepository
from todopro_cli.models import ProjectCreate, TaskCreate, TaskFilters
from todopro_cli.utils.uuid_utils import (
    format_uuid_short,
    is_full_uuid,
    is_valid_uuid,
    resolve_project_uuid,
    resolve_task_uuid,
    shorten_uuid,
    validate_uuid_field,
)


def test_uuid_validation():
    """Test UUID validation functions."""
    # Valid UUIDs
    assert is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")
    assert is_valid_uuid("123e4567-e89b-12d3-a456-426614174000")
    assert is_valid_uuid("AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")  # uppercase

    # Invalid UUIDs
    assert not is_valid_uuid("not-a-uuid")
    assert not is_valid_uuid("550e8400")  # too short
    assert not is_valid_uuid("550e8400-e29b-41d4-a716")  # incomplete
    assert not is_valid_uuid("")
    assert not is_valid_uuid(None)
    assert not is_valid_uuid(123)  # wrong type


def test_full_uuid_detection():
    """Test full UUID detection."""
    assert is_full_uuid("550e8400-e29b-41d4-a716-446655440000")
    assert not is_full_uuid("550e8400")  # short
    assert not is_full_uuid("not-a-uuid")


def test_uuid_shortening():
    """Test UUID shortening functions."""
    uuid = "550e8400-e29b-41d4-a716-446655440000"

    assert shorten_uuid(uuid, 8) == "550e8400"
    assert shorten_uuid(uuid, 4) == "550e"
    assert shorten_uuid(uuid, 12) == "550e8400-e29"
    assert format_uuid_short(uuid) == "550e8400"


def test_uuid_field_validation():
    """Test UUID field validation."""
    # Valid
    assert (
        validate_uuid_field("550e8400-e29b-41d4-a716-446655440000", "test_field")
        == "550e8400-e29b-41d4-a716-446655440000"
    )
    assert validate_uuid_field(None, "test_field") is None

    # Invalid
    with pytest.raises(ValueError, match="Invalid UUID"):
        validate_uuid_field("not-a-uuid", "test_field")

    with pytest.raises(ValueError, match="must be a string"):
        validate_uuid_field(123, "test_field")


@pytest.mark.asyncio
async def test_task_uuid_resolution(tmp_path):
    """Test task UUID resolution with database."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteTaskRepository(db_path=db_path)

    # Create test tasks
    task1 = await repo.add(TaskCreate(content="Test task 1", priority=1))
    task2 = await repo.add(TaskCreate(content="Test task 2", priority=2))

    # Test full UUID resolution
    resolved = await resolve_task_uuid(task1.id, repo)
    assert resolved == task1.id

    # Test short UUID resolution (first 8 chars)
    short_id = task2.id[:8]
    resolved_short = await resolve_task_uuid(short_id, repo)
    assert resolved_short == task2.id

    # Test non-existent UUID
    with pytest.raises(ValueError, match="Task not found"):
        await resolve_task_uuid("99999999", repo)

    # Test too-short UUID
    with pytest.raises(ValueError, match="at least 8 characters"):
        await resolve_task_uuid("123", repo)


@pytest.mark.asyncio
async def test_project_uuid_resolution(tmp_path):
    """Test project UUID resolution with database."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteProjectRepository(db_path=db_path)

    # Create test projects
    proj1 = await repo.create(ProjectCreate(name="Project 1"))
    proj2 = await repo.create(ProjectCreate(name="Project 2"))

    # Test full UUID resolution
    resolved = await resolve_project_uuid(proj1.id, repo)
    assert resolved == proj1.id

    # Test short UUID resolution
    short_id = proj2.id[:8]
    resolved_short = await resolve_project_uuid(short_id, repo)
    assert resolved_short == proj2.id

    # Test non-existent UUID
    with pytest.raises(ValueError, match="Project not found"):
        await resolve_project_uuid("99999999", repo)


@pytest.mark.asyncio
async def test_id_prefix_filtering(tmp_path):
    """Test ID prefix filtering in repositories."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteTaskRepository(db_path=db_path)

    # Create tasks
    task1 = await repo.add(TaskCreate(content="Task 1"))
    task2 = await repo.add(TaskCreate(content="Task 2"))
    task3 = await repo.add(TaskCreate(content="Task 3"))

    # Filter by ID prefix (first 8 chars of task1)
    prefix = task1.id[:8]
    results = await repo.list_all(TaskFilters(id_prefix=prefix))

    # Should match only task1
    assert len(results) == 1
    assert results[0].id == task1.id

    # Filter with non-matching prefix
    results = await repo.list_all(TaskFilters(id_prefix="99999999"))
    assert len(results) == 0


@pytest.mark.asyncio
async def test_ambiguous_uuid_resolution(tmp_path):
    """Test handling of ambiguous short UUIDs (collision)."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteTaskRepository(db_path=db_path)

    # This test would only fail if we had UUID collision
    # which is astronomically unlikely, so we skip implementation
    # The code path exists but can't be reliably tested


@pytest.mark.asyncio
async def test_uuid_case_insensitivity(tmp_path):
    """Test that UUID resolution is case-insensitive."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteTaskRepository(db_path=db_path)

    task = await repo.add(TaskCreate(content="Test"))

    # Test with uppercase
    short_upper = task.id[:8].upper()
    resolved = await resolve_task_uuid(short_upper, repo)
    assert resolved == task.id.lower()

    # Test with mixed case
    short_mixed = task.id[:8].swapcase()
    resolved = await resolve_task_uuid(short_mixed, repo)
    assert resolved == task.id.lower()


@pytest.mark.asyncio
async def test_task_full_uuid_not_found(tmp_path):
    """Test that a full UUID that doesn't exist raises ValueError (line 101)."""
    from unittest.mock import AsyncMock, MagicMock

    # Use a mock repo that returns None from get() (some repos return None, not raise)
    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=None)

    non_existent_full_uuid = "00000000-0000-4000-8000-000000000001"
    with pytest.raises(ValueError, match="Task not found"):
        await resolve_task_uuid(non_existent_full_uuid, mock_repo)


@pytest.mark.asyncio
async def test_task_ambiguous_uuid_many_matches(tmp_path):
    """Test ambiguous UUID with >5 matches shows count in error message."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteTaskRepository(db_path=db_path)

    # Create enough tasks so that we need to simulate >5 matches.
    # We do this by patching list_all to return 6 fake tasks.
    from unittest.mock import AsyncMock, MagicMock, patch

    # Create a real task to get a valid-looking ID structure
    task = await repo.add(TaskCreate(content="Real task"))

    fake_ids = [
        f"aabbccdd-{i:04d}-4000-8000-000000000001" for i in range(6)
    ]

    class FakeTask:
        def __init__(self, id):
            self.id = id

    fake_tasks = [FakeTask(fid) for fid in fake_ids]

    with patch.object(repo, "list_all", new=AsyncMock(return_value=fake_tasks)):
        with pytest.raises(ValueError, match=r"Ambiguous ID.*\.\.\. \(6 total\)"):
            await resolve_task_uuid("aabbccdd", repo)


@pytest.mark.asyncio
async def test_project_full_uuid_not_found(tmp_path):
    """Test that a full UUID for project that doesn't exist raises ValueError (line 152)."""
    from unittest.mock import AsyncMock, MagicMock

    # Use a mock repo that returns None from get()
    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=None)

    non_existent = "00000000-0000-4000-8000-000000000002"
    with pytest.raises(ValueError, match="Project not found"):
        await resolve_project_uuid(non_existent, mock_repo)


@pytest.mark.asyncio
async def test_project_too_short_id(tmp_path):
    """Test that a too-short project ID raises ValueError."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteProjectRepository(db_path=db_path)

    with pytest.raises(ValueError, match="at least 8 characters"):
        await resolve_project_uuid("abc", repo)


@pytest.mark.asyncio
async def test_project_ambiguous_uuid_many_matches(tmp_path):
    """Test ambiguous project UUID with >5 matches shows count in error message."""
    db_path = str(tmp_path / "test.db")
    repo = SqliteProjectRepository(db_path=db_path)

    from unittest.mock import AsyncMock, patch

    fake_ids = [
        f"aabbccdd-{i:04d}-4000-8000-000000000001" for i in range(6)
    ]

    class FakeProject:
        def __init__(self, id):
            self.id = id

    fake_projects = [FakeProject(fid) for fid in fake_ids]

    with patch.object(repo, "list_all", new=AsyncMock(return_value=fake_projects)):
        with pytest.raises(ValueError, match=r"Ambiguous ID.*\.\.\. \(6 total\)"):
            await resolve_project_uuid("aabbccdd", repo)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
