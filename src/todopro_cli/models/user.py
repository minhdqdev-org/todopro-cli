"""User data models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class User(BaseModel):
    """User model."""

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime
