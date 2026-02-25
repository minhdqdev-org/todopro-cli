"""Pydantic models for integration API responses."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class GitHubStatus(BaseModel):
    connected: bool
    username: Optional[str] = None
    scopes: Optional[str] = None
    connected_at: Optional[str] = None


class GitHubDeviceAuth(BaseModel):
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int = 900
    interval: int = 5


class GitHubProject(BaseModel):
    id: str
    number: Optional[int] = None
    title: str


class ProjectLink(BaseModel):
    id: int
    todopro_project_id: str
    external_id: str
    external_name: str
    sync_direction: str


class GoogleStatus(BaseModel):
    connected: bool
    email: Optional[str] = None
    scopes: Optional[str] = None
    connected_at: Optional[str] = None


class GoogleAuthUrl(BaseModel):
    auth_url: str


class GoogleCalendar(BaseModel):
    id: str
    summary: str
    timeZone: Optional[str] = None
    primary: Optional[bool] = False


class SyncStats(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0


class SyncState(BaseModel):
    last_synced_at: Optional[str] = None
    stats: dict = {}
