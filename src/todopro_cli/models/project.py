"""Project data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Project(BaseModel):
    """Project model."""

    id: str
    name: str
    color: Optional[str] = None
    is_favorite: bool = False
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
