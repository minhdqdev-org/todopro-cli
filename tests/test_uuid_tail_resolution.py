"""Resolution of UUIDv7 ids by their random tail.

UUIDv7 ids created together share their first 8 hex chars (a timestamp that
changes about once a minute), so these tests use the real id generator.
"""

import pytest

from todopro_cli.adapters.sqlite import SqliteProjectRepository, SqliteTaskRepository
from todopro_cli.models import ProjectCreate, TaskCreate
from todopro_cli.utils.uuid_utils import (
    format_uuid_short,
    resolve_project_uuid,
    resolve_task_uuid,
    shorten_uuid,
)


class _Item:
    def __init__(self, id: str):
        self.id = id


class _FakeRepo:
    def __init__(self, ids: list[str]):
        self.items = [_Item(i) for i in ids]

    async def list_all(self, filters=None):
        return self.items


def _ids(prefix: str, tails: list[str]) -> list[str]:
    return [f"{prefix}-0000-7000-8000-{tail}" for tail in tails]


@pytest.mark.asyncio
async def test_back_to_back_tasks_resolve_via_tail(tmp_path):
    repo = SqliteTaskRepository(db_path=str(tmp_path / "test.db"))
    tasks = [await repo.add(TaskCreate(content=f"Task {i}")) for i in range(5)]

    assert len({t.id[:8] for t in tasks}) < len(tasks)
    for task in tasks:
        assert await resolve_task_uuid(format_uuid_short(task.id), repo) == task.id
        assert await resolve_task_uuid(task.id[-12:].upper(), repo) == task.id


@pytest.mark.asyncio
async def test_back_to_back_projects_resolve_via_tail(tmp_path):
    repo = SqliteProjectRepository(db_path=str(tmp_path / "test.db"))
    projects = [await repo.create(ProjectCreate(name=f"P{i}")) for i in range(5)]

    assert len({p.id[:8] for p in projects}) < len(projects)
    for project in projects:
        assert (
            await resolve_project_uuid(shorten_uuid(project.id), repo) == project.id
        )


@pytest.mark.asyncio
async def test_prefix_still_wins_when_unique(tmp_path):
    repo = SqliteTaskRepository(db_path=str(tmp_path / "test.db"))
    task = await repo.add(TaskCreate(content="Only task"))

    assert await resolve_task_uuid(task.id[:8], repo) == task.id


@pytest.mark.asyncio
async def test_unknown_tail_not_found(tmp_path):
    repo = SqliteTaskRepository(db_path=str(tmp_path / "test.db"))
    await repo.add(TaskCreate(content="Task"))

    with pytest.raises(ValueError, match="Task not found"):
        await resolve_task_uuid("zzzzzzzz", repo)


@pytest.mark.asyncio
async def test_ambiguous_task_tail_lists_distinct_values():
    ids = _ids("01a13634", ["aaaaaaaa1111", "bbbbbbbb1111", "cccccccc1111"])
    repo = _FakeRepo(ids)

    with pytest.raises(ValueError, match="Ambiguous ID") as exc:
        await resolve_task_uuid("1111", repo, min_length=4)

    message = str(exc.value)
    assert "longer value" in message
    listed = message.split(": ", 1)[1].split(". ")[0].split(", ")
    assert len(listed) == len(set(listed)) == 3
    assert all(any(i.endswith(value) for i in ids) for value in listed)


@pytest.mark.asyncio
async def test_ambiguous_project_tail_lists_distinct_values():
    ids = _ids("01a13634", ["aaaa00001111", "bbbb00001111"])
    repo = _FakeRepo(ids)

    with pytest.raises(ValueError, match="Ambiguous ID") as exc:
        await resolve_project_uuid("1111", repo)

    message = str(exc.value)
    assert "longer value" in message
    listed = message.split(": ", 1)[1].split(". ")[0].split(", ")
    assert len(listed) == len(set(listed)) == 2


@pytest.mark.asyncio
async def test_ambiguous_prefix_error_lists_tails_not_prefixes():
    ids = _ids("01a13634", ["aaaaaaaaaaaa", "bbbbbbbbbbbb"])
    repo = _FakeRepo(ids)

    with pytest.raises(ValueError, match="Ambiguous ID") as exc:
        await resolve_task_uuid("01a13634", repo)

    assert "aaaaaaaa" in str(exc.value)
    assert "bbbbbbbb" in str(exc.value)
