"""Unit tests for abstract repository base classes in repository.py.

Tests the `raise NotImplementedError` bodies of each abstract method by creating
concrete subclasses that delegate straight back to `super()`.  This ensures the
docstring / error-message contract is tested as well as 100% line coverage for
every `raise` statement in the module.
"""

from __future__ import annotations

import pytest

from todopro_cli.models import (
    Label,
    LabelCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)
from todopro_cli.models.core import LocationContext, LocationContextCreate
from todopro_cli.models.focus.achievements import Achievement, AchievementCreate
from todopro_cli.repositories.repository import (
    AchievementRepository,
    LabelRepository,
    LocationContextRepository,
    ProjectRepository,
    TaskRepository,
)


# ---------------------------------------------------------------------------
# Concrete pass-through implementations
# ---------------------------------------------------------------------------


class _ConcreteTaskRepo(TaskRepository):
    """Calls super() on every abstract method to hit the raise lines."""

    async def list_all(self, filters: TaskFilters) -> list[Task]:
        return await super().list_all(filters)

    async def get(self, task_id: str) -> Task:
        return await super().get(task_id)

    async def add(self, task_data: TaskCreate) -> Task:
        return await super().add(task_data)

    async def update(self, task_id: str, updates: TaskUpdate) -> Task:
        return await super().update(task_id, updates)

    async def delete(self, task_id: str) -> bool:
        return await super().delete(task_id)

    async def complete(self, task_id: str) -> Task:
        return await super().complete(task_id)

    async def bulk_update(self, task_ids: list[str], updates: TaskUpdate) -> list[Task]:
        return await super().bulk_update(task_ids, updates)


class _ConcreteProjectRepo(ProjectRepository):
    async def list_all(self, filters: ProjectFilters) -> list[Project]:
        return await super().list_all(filters)

    async def get(self, project_id: str) -> Project:
        return await super().get(project_id)

    async def create(self, project_data: ProjectCreate) -> Project:
        return await super().create(project_data)

    async def update(self, project_id: str, updates: ProjectUpdate) -> Project:
        return await super().update(project_id, updates)

    async def delete(self, project_id: str) -> bool:
        return await super().delete(project_id)

    async def archive(self, project_id: str) -> Project:
        return await super().archive(project_id)

    async def unarchive(self, project_id: str) -> Project:
        return await super().unarchive(project_id)

    async def get_stats(self, project_id: str) -> dict:
        return await super().get_stats(project_id)


class _ConcreteLabelRepo(LabelRepository):
    async def list_all(self) -> list[Label]:
        return await super().list_all()

    async def get(self, label_id: str) -> Label:
        return await super().get(label_id)

    async def create(self, label_data: LabelCreate) -> Label:
        return await super().create(label_data)

    async def delete(self, label_id: str) -> bool:
        return await super().delete(label_id)

    async def search(self, prefix: str) -> list[Label]:
        return await super().search(prefix)


class _ConcreteLocationContextRepo(LocationContextRepository):
    async def list_all(self) -> list[LocationContext]:
        return await super().list_all()

    async def get(self, context_id: str) -> LocationContext:
        return await super().get(context_id)

    async def create(self, context_data: LocationContextCreate) -> LocationContext:
        return await super().create(context_data)

    async def delete(self, context_id: str) -> bool:
        return await super().delete(context_id)

    async def get_available(
        self, latitude: float, longitude: float
    ) -> list[LocationContext]:
        return await super().get_available(latitude, longitude)


class _ConcreteAchievementRepo(AchievementRepository):
    async def list_all(self) -> list[Achievement]:
        return await super().list_all()

    async def get(self, achievement_id: str) -> Achievement:
        return await super().get(achievement_id)

    async def create(self, achievement_data: AchievementCreate) -> Achievement:
        return await super().create(achievement_data)

    async def delete(self, achievement_id: str) -> bool:
        return await super().delete(achievement_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_repo():
    return _ConcreteTaskRepo()


@pytest.fixture
def project_repo():
    return _ConcreteProjectRepo()


@pytest.fixture
def label_repo():
    return _ConcreteLabelRepo()


@pytest.fixture
def context_repo():
    return _ConcreteLocationContextRepo()


@pytest.fixture
def achievement_repo():
    return _ConcreteAchievementRepo()


# ---------------------------------------------------------------------------
# TaskRepository – each abstract method raises NotImplementedError
# ---------------------------------------------------------------------------


class TestTaskRepositoryAbstractMethods:
    @pytest.mark.asyncio
    async def test_list_all_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="list_all"):
            await task_repo.list_all(TaskFilters())

    @pytest.mark.asyncio
    async def test_get_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="get"):
            await task_repo.get("some-id")

    @pytest.mark.asyncio
    async def test_add_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="add"):
            await task_repo.add(TaskCreate(content="x"))

    @pytest.mark.asyncio
    async def test_update_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="update"):
            await task_repo.update("some-id", TaskUpdate())

    @pytest.mark.asyncio
    async def test_delete_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="delete"):
            await task_repo.delete("some-id")

    @pytest.mark.asyncio
    async def test_complete_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="complete"):
            await task_repo.complete("some-id")

    @pytest.mark.asyncio
    async def test_bulk_update_raises(self, task_repo):
        with pytest.raises(NotImplementedError, match="bulk_update"):
            await task_repo.bulk_update(["id1", "id2"], TaskUpdate())


# ---------------------------------------------------------------------------
# ProjectRepository
# ---------------------------------------------------------------------------


class TestProjectRepositoryAbstractMethods:
    @pytest.mark.asyncio
    async def test_list_all_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="list_all"):
            await project_repo.list_all(ProjectFilters())

    @pytest.mark.asyncio
    async def test_get_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="get"):
            await project_repo.get("p-id")

    @pytest.mark.asyncio
    async def test_create_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="create"):
            await project_repo.create(ProjectCreate(name="Proj"))

    @pytest.mark.asyncio
    async def test_update_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="update"):
            await project_repo.update("p-id", ProjectUpdate())

    @pytest.mark.asyncio
    async def test_delete_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="delete"):
            await project_repo.delete("p-id")

    @pytest.mark.asyncio
    async def test_archive_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="archive"):
            await project_repo.archive("p-id")

    @pytest.mark.asyncio
    async def test_unarchive_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="unarchive"):
            await project_repo.unarchive("p-id")

    @pytest.mark.asyncio
    async def test_get_stats_raises(self, project_repo):
        with pytest.raises(NotImplementedError, match="get_stats"):
            await project_repo.get_stats("p-id")


# ---------------------------------------------------------------------------
# LabelRepository
# ---------------------------------------------------------------------------


class TestLabelRepositoryAbstractMethods:
    @pytest.mark.asyncio
    async def test_list_all_raises(self, label_repo):
        with pytest.raises(NotImplementedError, match="list_all"):
            await label_repo.list_all()

    @pytest.mark.asyncio
    async def test_get_raises(self, label_repo):
        with pytest.raises(NotImplementedError, match="get"):
            await label_repo.get("l-id")

    @pytest.mark.asyncio
    async def test_create_raises(self, label_repo):
        with pytest.raises(NotImplementedError, match="create"):
            await label_repo.create(LabelCreate(name="tag"))

    @pytest.mark.asyncio
    async def test_delete_raises(self, label_repo):
        with pytest.raises(NotImplementedError, match="delete"):
            await label_repo.delete("l-id")

    @pytest.mark.asyncio
    async def test_search_raises(self, label_repo):
        with pytest.raises(NotImplementedError, match="search"):
            await label_repo.search("pre")


# ---------------------------------------------------------------------------
# LocationContextRepository
# ---------------------------------------------------------------------------


class TestLocationContextRepositoryAbstractMethods:
    @pytest.mark.asyncio
    async def test_list_all_raises(self, context_repo):
        with pytest.raises(NotImplementedError, match="list_all"):
            await context_repo.list_all()

    @pytest.mark.asyncio
    async def test_get_raises(self, context_repo):
        with pytest.raises(NotImplementedError, match="get"):
            await context_repo.get("c-id")

    @pytest.mark.asyncio
    async def test_create_raises(self, context_repo):
        with pytest.raises(NotImplementedError, match="create"):
            await context_repo.create(
                LocationContextCreate(
                    name="Home", latitude=0.0, longitude=0.0, radius=100.0
                )
            )

    @pytest.mark.asyncio
    async def test_delete_raises(self, context_repo):
        with pytest.raises(NotImplementedError, match="delete"):
            await context_repo.delete("c-id")

    @pytest.mark.asyncio
    async def test_get_available_raises(self, context_repo):
        with pytest.raises(NotImplementedError, match="get_available"):
            await context_repo.get_available(0.0, 0.0)


# ---------------------------------------------------------------------------
# AchievementRepository
# ---------------------------------------------------------------------------


class TestAchievementRepositoryAbstractMethods:
    @pytest.mark.asyncio
    async def test_list_all_raises(self, achievement_repo):
        with pytest.raises(NotImplementedError, match="list_all"):
            await achievement_repo.list_all()

    @pytest.mark.asyncio
    async def test_get_raises(self, achievement_repo):
        with pytest.raises(NotImplementedError, match="get"):
            await achievement_repo.get("a-id")

    @pytest.mark.asyncio
    async def test_create_raises(self, achievement_repo):
        with pytest.raises(NotImplementedError, match="create"):
            await achievement_repo.create(
                AchievementCreate(
                    name="Win",
                    description="You won",
                    icon="🏆",
                    requirement={},
                )
            )

    @pytest.mark.asyncio
    async def test_delete_raises(self, achievement_repo):
        with pytest.raises(NotImplementedError, match="delete"):
            await achievement_repo.delete("a-id")
