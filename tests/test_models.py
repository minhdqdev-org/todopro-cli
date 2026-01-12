"""Tests for data models."""

from datetime import datetime

from todopro_cli.models.project import Project
from todopro_cli.models.task import Task
from todopro_cli.models.user import User


def test_task_model():
    """Test Task model."""
    now = datetime.now()
    task = Task(
        id="task-123",
        content="Test task",
        description="Test description",
        priority=2,
        is_completed=False,
        labels=["test", "urgent"],
        created_at=now,
        updated_at=now,
    )

    assert task.id == "task-123"
    assert task.content == "Test task"
    assert task.description == "Test description"
    assert task.priority == 2
    assert task.is_completed is False
    assert task.labels == ["test", "urgent"]


def test_project_model():
    """Test Project model."""
    now = datetime.now()
    project = Project(
        id="proj-123",
        name="Test Project",
        color="#FF0000",
        is_favorite=True,
        is_archived=False,
        created_at=now,
        updated_at=now,
    )

    assert project.id == "proj-123"
    assert project.name == "Test Project"
    assert project.color == "#FF0000"
    assert project.is_favorite is True
    assert project.is_archived is False


def test_user_model():
    """Test User model."""
    now = datetime.now()
    user = User(
        id="user-123",
        email="test@example.com",
        name="Test User",
        created_at=now,
        updated_at=now,
    )

    assert user.id == "user-123"
    assert user.email == "test@example.com"
    assert user.name == "Test User"
