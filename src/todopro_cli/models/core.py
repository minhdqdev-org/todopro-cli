"""Label data models."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class Label(BaseModel):
    """Label model representing a task/project label.

    Attributes:
        id: Unique identifier for the label
        name: Label name (e.g., "@work", "@home")
        color: Optional hex color code for display
    """

    id: str
    name: str
    color: str | None = None


class LabelCreate(BaseModel):
    """Model for creating a new label.

    Attributes:
        name: Label name (required)
        color: Optional hex color code
    """

    name: str
    color: str | None = None


class Section(BaseModel):
    """Section model representing a named group of tasks within a project.

    Attributes:
        id: Unique identifier for the section
        project_id: Reference to the parent project
        name: Section name
        display_order: Order position within the project
        task_count: Number of active tasks in this section
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    project_id: str
    name: str
    display_order: int = 0
    task_count: int = 0
    created_at: datetime
    updated_at: datetime


class SectionCreate(BaseModel):
    """Model for creating a new section.

    Attributes:
        name: Section name (required)
        display_order: Optional order position
    """

    name: str
    display_order: int = 0


class SectionUpdate(BaseModel):
    """Model for updating an existing section.

    All fields are optional — only provided fields will be updated.

    Attributes:
        name: Section name
        display_order: Order position
    """

    name: str | None = None
    display_order: int | None = None


class SectionFilters(BaseModel):
    """Filters for querying sections.

    Attributes:
        project_id: Filter by project ID
    """

    project_id: str | None = None


class Scratchpad(BaseModel):
    """Scratchpad model — a free-form note attached to a project.

    Scratchpads are a **remote-only** concept: they live on the backend and are
    not available in the local SQLite context. A project may have many
    scratchpads (one-to-many); the per-project count is capped by subscription
    tier (free: 2, pro/trial: 20), enforced server-side on create.

    Attributes:
        id: Unique identifier for the scratchpad
        project_id: Reference to the parent project (API field ``project``)
        title: Optional short title
        content: Free-form note body (TipTap HTML, may embed base64 images)
        display_order: Order position within the project
        version: Bumped on every server-side save (conflict awareness)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    model_config = {"populate_by_name": True}

    id: str
    project_id: str = Field(alias="project")
    title: str = ""
    content: str = ""
    display_order: int = 0
    version: int = 1
    created_at: datetime
    updated_at: datetime


class ScratchpadCreate(BaseModel):
    """Model for creating a new scratchpad.

    Attributes:
        title: Optional short title
        content: Optional note body
    """

    title: str = ""
    content: str = ""


class ScratchpadUpdate(BaseModel):
    """Model for updating an existing scratchpad.

    All fields are optional — only provided fields will be updated.

    Attributes:
        title: New title
        content: New note body
    """

    title: str | None = None
    content: str | None = None


class Project(BaseModel):
    """Project model representing a complete project entity.

    Attributes:
        id: Unique identifier for the project
        name: Project name
        color: Optional hex color code for display
        is_favorite: Whether project is marked as favorite
        is_archived: Whether project is archived
        protected: Whether project is protected (e.g. Inbox) and cannot be deleted/archived
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    name: str
    color: str | None = None
    is_favorite: bool = False
    is_archived: bool = False
    protected: bool = False
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    """Model for creating a new project.

    Attributes:
        name: Project name (required)
        color: Optional hex color code
        is_favorite: Whether to mark as favorite
    """

    name: str
    color: str | None = None
    is_favorite: bool = False


class ProjectUpdate(BaseModel):
    """Model for updating an existing project.

    All fields are optional - only provided fields will be updated.

    Attributes:
        name: Project name
        color: Hex color code
        is_favorite: Favorite status
        is_archived: Archived status
    """

    name: str | None = None
    color: str | None = None
    is_favorite: bool | None = None
    is_archived: bool | None = None


class ProjectFilters(BaseModel):
    """Filters for querying projects.

    Attributes:
        id_prefix: Filter by ID prefix (for UUID resolution)
        is_favorite: Filter by favorite status
        is_archived: Filter by archived status
        search: Text search query
    """

    id_prefix: str | None = None
    is_favorite: bool | None = None
    is_archived: bool | None = None
    search: str | None = None


class Task(BaseModel):
    """Task model representing a complete task entity.

    Attributes:
        id: Unique identifier for the task
        content: Main task description
        description: Optional detailed description
        project_id: Optional reference to parent project
        due_date: Optional due date with timezone
        deadline: Optional hard "must finish by" datetime (does not advance on recurrence)
        priority: Priority level (4=lowest, 1=highest)
        is_completed: Completion status
        is_recurring: Whether this is a recurring task
        recurrence_rule: iCalendar RRULE string (e.g., "FREQ=DAILY")
        recurrence_end: Optional date when recurrence stops
        recurrence_from_completion: Re-anchor next occurrence to completion time
        labels: List of label IDs associated with task
        contexts: List of context IDs associated with task
        created_at: Creation timestamp
        updated_at: Last update timestamp
        completed_at: Completion timestamp
        version: Version for optimistic locking
    """

    id: str
    content: str
    description: str | None = None
    project_id: str | None = None
    section_id: str | None = None
    due_date: datetime | None = None
    deadline: datetime | None = None
    priority: int = Field(default=4, ge=1, le=4)
    is_completed: bool = False
    is_recurring: bool = False
    recurrence_rule: str | None = None
    recurrence_end: datetime | None = None
    recurrence_from_completion: bool = False
    labels: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    version: int = Field(default=1)

    @field_validator("labels", "contexts", mode="before")
    @classmethod
    def _coerce_to_str_list(cls, v: object) -> object:
        """Accept either bare strings or expanded objects from the API.

        The REST API serializes labels/contexts as nested objects
        (``{"id": ..., "name": ...}``) while this read model stores display
        strings. Older payloads (and the SQLite adapter) send plain strings.
        Normalize both so list/today don't blow up on label objects.
        """
        if not isinstance(v, list):
            return v
        normalized: list[str] = []
        for item in v:
            if isinstance(item, dict):
                normalized.append(str(item.get("name") or item.get("id") or "").strip())
            else:
                normalized.append(item)
        return normalized


class TaskCreate(BaseModel):
    """Model for creating a new task.

    Attributes:
        content: Main task description (required)
        description: Optional detailed description
        project_id: Optional reference to parent project
        due_date: Optional due date with timezone
        deadline: Optional hard "must finish by" datetime (does not advance on recurrence)
        priority: Priority level (4=lowest, 1=highest)
        is_recurring: Whether to make this a recurring task
        recurrence_rule: iCalendar RRULE string (required if is_recurring=True)
        recurrence_end: Optional date when recurrence stops
        recurrence_from_completion: Re-anchor next occurrence to completion time
        labels: List of label IDs
        contexts: List of context IDs
        parent_id: Optional parent task ID for subtasks
    """

    content: str
    description: str | None = None
    project_id: str | None = None
    section_id: str | None = None
    due_date: datetime | None = None
    deadline: datetime | None = None
    priority: int = Field(default=4, ge=1, le=4)
    recurrence_rule: str | None = None
    recurrence_end: datetime | None = None
    recurrence_from_completion: bool = False
    labels: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    parent_id: str | None = None


class TaskUpdate(BaseModel):
    """Model for updating an existing task.

    All fields are optional - only provided fields will be updated.

    Attributes:
        content: Main task description
        description: Detailed description
        project_id: Reference to parent project
        due_date: Due date with timezone
        deadline: Hard "must finish by" datetime (does not advance on recurrence)
        priority: Priority level (4=lowest, 1=highest)
        is_completed: Completion status
        is_recurring: Whether this is a recurring task
        recurrence_rule: iCalendar RRULE string
        recurrence_end: Optional date when recurrence stops
        recurrence_from_completion: Re-anchor next occurrence to completion time
        labels: List of label IDs
        contexts: List of context IDs
    """

    content: str | None = None
    description: str | None = None
    project_id: str | None = None
    due_date: datetime | None = None
    deadline: datetime | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    is_completed: bool | None = None
    is_recurring: bool | None = None
    recurrence_rule: str | None = None
    recurrence_end: datetime | None = None
    recurrence_from_completion: bool | None = None
    labels: list[str] | None = None
    contexts: list[str] | None = None


class TaskFilters(BaseModel):
    """Filters for querying tasks.

    Attributes:
        id_prefix: Filter by ID prefix (for UUID resolution)
        id_suffix: Filter by ID suffix (for short-ID resolution, e.g. last 3 chars)
        status: Filter by status ("active", "completed", "all")
        project_id: Filter by project ID
        priority: Filter by priority level
        is_recurring: Filter to only recurring tasks when True
        labels: Filter by label IDs (match any)
        contexts: Filter by context IDs (match any)
        search: Full-text search query
        due_before: Tasks due before this date
        due_after: Tasks due after this date
        limit: Maximum number of results
        offset: Pagination offset
        sort: Sort field and direction (e.g., "due_date:asc", "priority:desc")
    """

    id_prefix: str | None = None
    id_suffix: str | None = None
    status: str | None = Field(default=None, pattern="^(active|completed|all)$")
    project_id: str | None = None
    priority: int | None = Field(default=None, ge=1, le=4)
    is_recurring: bool | None = None
    labels: list[str] | None = None
    contexts: list[str] | None = None
    search: str | None = None
    due_before: datetime | None = None
    due_after: datetime | None = None
    limit: int | None = Field(default=None, ge=1)
    offset: int | None = Field(default=None, ge=0)
    sort: str | None = None


class Reminder(BaseModel):
    """Task reminder model."""

    id: str
    task_id: str
    reminder_date: datetime
    is_sent: bool = False
    sent_at: datetime | None = None
    is_snoozed: bool = False
    created_at: datetime
    updated_at: datetime


class SavedFilter(BaseModel):
    """Saved filter/smart view model.

    Attributes:
        id: Unique identifier
        name: Human-readable filter name
        color: Hex color code (e.g., "#FF5733")
        criteria: Filter criteria dict (priority, project_ids, label_ids, due_within_days)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: str
    name: str
    color: str
    criteria: dict
    created_at: datetime
    updated_at: datetime


class User(BaseModel):
    """User model."""

    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: datetime


class LocationContext(BaseModel):
    """Context model representing a location-based context.

    Attributes:
        id: Unique identifier for the context
        name: Context name (e.g., "@office", "@home")
        latitude: Geographic latitude
        longitude: Geographic longitude
        radius: Geofence radius in meters
    """

    id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius: float = Field(gt=0, description="Radius in meters")


class LocationContextCreate(BaseModel):
    """Model for creating a new location-based context.

    Attributes:
        name: Context name (required)
        latitude: Geographic latitude
        longitude: Geographic longitude
        radius: Geofence radius in meters (default: 100m)
    """

    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius: float = Field(default=100.0, gt=0, description="Radius in meters")
