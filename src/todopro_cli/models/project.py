"""Project data models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Project(BaseModel):
    """Project model."""

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    id: str
    name: str
    color: str | None = None
    is_favorite: bool = False
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
