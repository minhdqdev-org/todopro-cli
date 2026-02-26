"""Tests for service layer with mock repositories."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.models import (
    Label,
    LabelCreate,
    LocationContext,
    LocationContextCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)
from todopro_cli.services import (
    LabelService,
    LocationContextService,
    ProjectService,
    TaskService,
)


class TestTaskService:
    """Test TaskService with mock repository."""

    @pytest.fixture
    def mock_task_repo(self):
        """Create a mock task repository."""
        repo = MagicMock()
        # Make all methods async
        repo.list_all = AsyncMock()
        repo.get = AsyncMock()
        repo.add = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.complete = AsyncMock()
        repo.bulk_update = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_list_tasks(self, mock_task_repo):
        """Test listing tasks through service."""
        mock_tasks = [
            Task(
                id="1",
                content="Test task 1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="2",
                content="Test task 2",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_task_repo.list_all.return_value = mock_tasks

        service = TaskService(mock_task_repo)
        tasks = await service.list_tasks(status="active", priority=2)

        assert len(tasks) == 2
        assert tasks[0].content == "Test task 1"
        mock_task_repo.list_all.assert_called_once()

        # Check filters were constructed correctly
        call_args = mock_task_repo.list_all.call_args
        filters = call_args[0][0]
        assert isinstance(filters, TaskFilters)
        assert filters.status == "active"
        assert filters.priority == 2

    @pytest.mark.asyncio
    async def test_get_task(self, mock_task_repo):
        """Test getting a single task."""
        mock_task = Task(
            id="123",
            content="Test task",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_task_repo.get.return_value = mock_task

        service = TaskService(mock_task_repo)
        task = await service.get_task("123")

        assert task.id == "123"
        assert task.content == "Test task"
        mock_task_repo.get.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_add_task(self, mock_task_repo):
        """Test creating a new task."""
        mock_task = Task(
            id="new-123",
            content="New task",
            priority=3,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_task_repo.add.return_value = mock_task

        service = TaskService(mock_task_repo)
        task = await service.add_task(
            content="New task",
            priority=3,
            labels=["label1"],
        )

        assert task.id == "new-123"
        assert task.content == "New task"
        assert task.priority == 3

        # Check TaskCreate was constructed correctly
        call_args = mock_task_repo.add.call_args
        task_data = call_args[0][0]
        assert isinstance(task_data, TaskCreate)
        assert task_data.content == "New task"
        assert task_data.priority == 3
        assert task_data.labels == ["label1"]

    @pytest.mark.asyncio
    async def test_update_task(self, mock_task_repo):
        """Test updating a task."""
        mock_task = Task(
            id="123",
            content="Updated task",
            priority=4,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_task_repo.update.return_value = mock_task

        service = TaskService(mock_task_repo)
        task = await service.update_task(
            "123",
            content="Updated task",
            priority=4,
        )

        assert task.content == "Updated task"
        assert task.priority == 4

        # Check TaskUpdate was constructed correctly
        call_args = mock_task_repo.update.call_args
        assert call_args[0][0] == "123"
        updates = call_args[0][1]
        assert isinstance(updates, TaskUpdate)
        assert updates.content == "Updated task"
        assert updates.priority == 4

    @pytest.mark.asyncio
    async def test_delete_task(self, mock_task_repo):
        """Test deleting a task."""
        mock_task_repo.delete.return_value = True

        service = TaskService(mock_task_repo)
        result = await service.delete_task("123")

        assert result is True
        mock_task_repo.delete.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_complete_task(self, mock_task_repo):
        """Test completing a task."""
        mock_task = Task(
            id="123",
            content="Test task",
            is_completed=True,
            completed_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_task_repo.complete.return_value = mock_task

        service = TaskService(mock_task_repo)
        task = await service.complete_task("123")

        assert task.is_completed is True
        assert task.completed_at is not None
        mock_task_repo.complete.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_bulk_complete_tasks(self, mock_task_repo):
        """Test bulk completing tasks."""
        mock_tasks = [
            Task(
                id="1",
                content="Task 1",
                is_completed=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Task(
                id="2",
                content="Task 2",
                is_completed=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_task_repo.bulk_update.return_value = mock_tasks

        service = TaskService(mock_task_repo)
        tasks = await service.bulk_complete_tasks(["1", "2"])

        assert len(tasks) == 2
        assert all(task.is_completed for task in tasks)

        # Check bulk_update was called correctly
        call_args = mock_task_repo.bulk_update.call_args
        assert call_args[0][0] == ["1", "2"]
        updates = call_args[0][1]
        assert isinstance(updates, TaskUpdate)
        assert updates.is_completed is True


class TestProjectService:
    """Test ProjectService with mock repository."""

    @pytest.fixture
    def mock_project_repo(self):
        """Create a mock project repository."""
        repo = MagicMock()
        repo.list_all = AsyncMock()
        repo.get = AsyncMock()
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.archive = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_list_projects(self, mock_project_repo):
        """Test listing projects through service."""
        mock_projects = [
            Project(
                id="1",
                name="Project 1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_project_repo.list_all.return_value = mock_projects

        service = ProjectService(mock_project_repo)
        projects = await service.list_projects(is_favorite=True)

        assert len(projects) == 1
        assert projects[0].name == "Project 1"

        # Check filters
        call_args = mock_project_repo.list_all.call_args
        filters = call_args[0][0]
        assert isinstance(filters, ProjectFilters)
        assert filters.is_favorite is True

    @pytest.mark.asyncio
    async def test_create_project(self, mock_project_repo):
        """Test creating a project."""
        mock_project = Project(
            id="new-123",
            name="New Project",
            color="#ff0000",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_project_repo.create.return_value = mock_project

        service = ProjectService(mock_project_repo)
        project = await service.create_project(
            name="New Project",
            color="#ff0000",
        )

        assert project.name == "New Project"
        assert project.color == "#ff0000"

        # Check ProjectCreate
        call_args = mock_project_repo.create.call_args
        project_data = call_args[0][0]
        assert isinstance(project_data, ProjectCreate)
        assert project_data.name == "New Project"

    @pytest.mark.asyncio
    async def test_archive_project(self, mock_project_repo):
        """Test archiving a project."""
        mock_project = Project(
            id="123",
            name="Project",
            is_archived=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_project_repo.archive.return_value = mock_project

        service = ProjectService(mock_project_repo)
        project = await service.archive_project("123")

        assert project.is_archived is True
        mock_project_repo.archive.assert_called_once_with("123")

    @pytest.mark.asyncio
    async def test_favorite_project(self, mock_project_repo):
        """Test favoriting a project."""
        mock_project = Project(
            id="123",
            name="Project",
            is_favorite=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_project_repo.update.return_value = mock_project

        service = ProjectService(mock_project_repo)
        project = await service.favorite_project("123")

        assert project.is_favorite is True

        # Check update was called with is_favorite=True
        call_args = mock_project_repo.update.call_args
        assert call_args[0][0] == "123"
        updates = call_args[0][1]
        assert updates.is_favorite is True


class TestLabelService:
    """Test LabelService with mock repository."""

    @pytest.fixture
    def mock_label_repo(self):
        """Create a mock label repository."""
        repo = MagicMock()
        repo.list_all = AsyncMock()
        repo.get = AsyncMock()
        repo.create = AsyncMock()
        repo.delete = AsyncMock()
        repo.search = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_list_labels(self, mock_label_repo):
        """Test listing labels."""
        mock_labels = [
            Label(id="1", name="@work"),
            Label(id="2", name="@home"),
        ]
        mock_label_repo.list_all.return_value = mock_labels

        service = LabelService(mock_label_repo)
        labels = await service.list_labels()

        assert len(labels) == 2
        assert labels[0].name == "@work"
        mock_label_repo.list_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_label(self, mock_label_repo):
        """Test creating a label."""
        mock_label = Label(id="new-123", name="@urgent", color="#ff0000")
        mock_label_repo.create.return_value = mock_label

        service = LabelService(mock_label_repo)
        label = await service.create_label(name="@urgent", color="#ff0000")

        assert label.name == "@urgent"
        assert label.color == "#ff0000"

        # Check LabelCreate
        call_args = mock_label_repo.create.call_args
        label_data = call_args[0][0]
        assert isinstance(label_data, LabelCreate)
        assert label_data.name == "@urgent"

    @pytest.mark.asyncio
    async def test_search_labels(self, mock_label_repo):
        """Test searching labels by prefix."""
        mock_labels = [
            Label(id="1", name="@work"),
            Label(id="2", name="@workout"),
        ]
        mock_label_repo.search.return_value = mock_labels

        service = LabelService(mock_label_repo)
        labels = await service.search_labels("@wo")

        assert len(labels) == 2
        mock_label_repo.search.assert_called_once_with("@wo")

    @pytest.mark.asyncio
    async def test_get_or_create_label_existing(self, mock_label_repo):
        """Test get_or_create returns existing label."""
        existing_labels = [
            Label(id="1", name="@work"),
        ]
        mock_label_repo.list_all.return_value = existing_labels

        service = LabelService(mock_label_repo)
        label = await service.get_or_create_label("@work")

        assert label.id == "1"
        assert label.name == "@work"
        mock_label_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_label_new(self, mock_label_repo):
        """Test get_or_create creates new label if not exists."""
        mock_label_repo.list_all.return_value = []
        new_label = Label(id="new-123", name="@newlabel")
        mock_label_repo.create.return_value = new_label

        service = LabelService(mock_label_repo)
        label = await service.get_or_create_label("@newlabel")

        assert label.id == "new-123"
        assert label.name == "@newlabel"
        mock_label_repo.create.assert_called_once()


class TestContextService:
    """Test ContextService with mock repository."""

    @pytest.fixture
    def mock_context_repo(self):
        """Create a mock context repository."""
        repo = MagicMock()
        repo.list_all = AsyncMock()
        repo.get = AsyncMock()
        repo.create = AsyncMock()
        repo.delete = AsyncMock()
        repo.get_available = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_list_contexts(self, mock_context_repo):
        """Test listing contexts."""
        mock_contexts = [
            LocationContext(
                id="1", name="@office", latitude=40.7, longitude=-74.0, radius=100
            ),
            LocationContext(
                id="2", name="@home", latitude=40.8, longitude=-73.9, radius=50
            ),
        ]
        mock_context_repo.list_all.return_value = mock_contexts

        service = LocationContextService(mock_context_repo)
        contexts = await service.list_location_contexts()

        assert len(contexts) == 2
        assert contexts[0].name == "@office"
        mock_context_repo.list_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_location_context(self, mock_context_repo):
        """Test creating a location context."""
        mock_context = LocationContext(
            id="new-123",
            name="@gym",
            latitude=40.75,
            longitude=-73.98,
            radius=150,
        )
        mock_context_repo.create.return_value = mock_context

        service = LocationContextService(mock_context_repo)
        context = await service.create_location_context(
            name="@gym",
            latitude=40.75,
            longitude=-73.98,
            radius=150,
        )

        assert context.name == "@gym"
        assert context.radius == 150

        # Check LocationContextCreate
        call_args = mock_context_repo.create.call_args
        context_data = call_args[0][0]
        assert isinstance(context_data, LocationContextCreate)
        assert context_data.name == "@gym"
        assert context_data.latitude == 40.75

    @pytest.mark.asyncio
    async def test_get_available_contexts(self, mock_context_repo):
        """Test getting contexts available at location."""
        mock_contexts = [
            LocationContext(
                id="1", name="@office", latitude=40.7, longitude=-74.0, radius=100
            ),
        ]
        mock_context_repo.get_available.return_value = mock_contexts

        service = LocationContextService(mock_context_repo)
        contexts = await service.get_available_location_contexts(40.7, -74.0)

        assert len(contexts) == 1
        assert contexts[0].name == "@office"
        mock_context_repo.get_available.assert_called_once_with(40.7, -74.0)

    @pytest.mark.asyncio
    async def test_get_or_create_location_context_existing(self, mock_context_repo):
        """Test get_or_create returns existing location context."""
        existing_contexts = [
            LocationContext(
                id="1", name="@office", latitude=40.7, longitude=-74.0, radius=100
            ),
        ]
        mock_context_repo.list_all.return_value = existing_contexts

        service = LocationContextService(mock_context_repo)
        context = await service.get_or_create_location_context("@office", 40.7, -74.0)

        assert context.id == "1"
        assert context.name == "@office"
        mock_context_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_location_context_new(self, mock_context_repo):
        """Test get_or_create creates new location context if not exists."""
        mock_context_repo.list_all.return_value = []
        new_context = LocationContext(
            id="new-123",
            name="@newlocation",
            latitude=40.7,
            longitude=-74.0,
            radius=100,
        )
        mock_context_repo.create.return_value = new_context

        service = LocationContextService(mock_context_repo)
        context = await service.get_or_create_location_context(
            "@newlocation", 40.7, -74.0, radius=100
        )

        assert context.id == "new-123"
        assert context.name == "@newlocation"
        mock_context_repo.create.assert_called_once()
