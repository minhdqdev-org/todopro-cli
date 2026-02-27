"""Pydantic models for Todoist API v1 responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TodoistDue(BaseModel):
    """Due date object from Todoist API."""

    date: str
    is_recurring: bool = False
    string: str = ""
    timezone: str | None = None


class TodoistProject(BaseModel):
    """A Todoist project."""

    id: str
    name: str
    color: str | None = None
    is_favorite: bool = False
    is_archived: bool = False


class TodoistSection(BaseModel):
    """A Todoist section within a project."""

    id: str
    name: str
    project_id: str
    order: int = 0


class TodoistLabel(BaseModel):
    """A Todoist personal label."""

    id: str | int
    name: str
    color: str | None = None
    order: int = 0


class TodoistTask(BaseModel):
    """An active Todoist task."""

    id: str
    content: str
    description: str = ""
    project_id: str
    section_id: str | None = None
    priority: int = Field(default=4, ge=1, le=4)
    due: TodoistDue | None = None
    labels: list[str] = Field(default_factory=list)
    added_at: str | None = None
    updated_at: str | None = None
    checked: bool = False
    is_deleted: bool = False


class TodoistImportOptions(BaseModel):
    """Options controlling how Todoist data is imported into TodoPro."""

    project_name_prefix: str = "[Todoist]"
    max_tasks_per_project: int = Field(default=500, ge=1)
    dry_run: bool = False
    include_completed: bool = False


class TodoistImportResult(BaseModel):
    """Summary of a completed Todoist import."""

    projects_created: int = 0
    projects_skipped: int = 0
    labels_created: int = 0
    labels_skipped: int = 0
    tasks_created: int = 0
    tasks_skipped: int = 0
    errors: list[str] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
