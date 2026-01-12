"""User data models."""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class User(BaseModel):
    """User model."""

    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
