"""Task data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Task(BaseModel):
    """Task model."""

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    id: str
    content: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: int = Field(default=1, ge=1, le=4)
    is_completed: bool = False
    labels: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
