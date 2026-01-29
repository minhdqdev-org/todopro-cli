"""Task data models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Task(BaseModel):
    """Task model."""

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    id: str
    content: str
    description: str | None = None
    project_id: str | None = None
    due_date: datetime | None = None
    priority: int = Field(default=1, ge=1, le=4)
    is_completed: bool = False
    labels: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
