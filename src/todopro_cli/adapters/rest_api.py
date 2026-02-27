"""REST API adapters - Repository implementations using the TodoPro REST API.

These adapters wrap the existing API client to implement the repository interfaces.
"""

from __future__ import annotations

from datetime import datetime

from todopro_cli.models import (
    Label,
    LabelCreate,
    LocationContext,
    LocationContextCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Section,
    SectionCreate,
    SectionUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)
from todopro_cli.repositories.repository import (
    LabelRepository,
    LocationContextRepository,
    ProjectRepository,
    SectionRepository,
    TaskRepository,
)
from todopro_cli.services.api.client import APIClient
from todopro_cli.services.api.labels import LabelsAPI
from todopro_cli.services.api.projects import ProjectsAPI
from todopro_cli.services.api.sections import SectionsAPI
from todopro_cli.services.api.tasks import TasksAPI


class RestApiTaskRepository(TaskRepository):
    """Task repository implementation using REST API with E2EE support."""

    def __init__(self):
        """Initialize REST API task repository.

        Args:
            config_service: ConfigService instance for API configuration
        """
        self._client: APIClient | None = None
        self._tasks_api: TasksAPI | None = None
        self._e2ee_handler = None

    @property
    def e2ee(self):
        """Get E2EE handler instance (lazy initialization)."""
        if self._e2ee_handler is None:
            from todopro_cli.adapters.sqlite.e2ee import get_e2ee_handler

            self._e2ee_handler = get_e2ee_handler()
        return self._e2ee_handler

    @property
    def tasks_api(self) -> TasksAPI:
        """Get or create TasksAPI instance."""
        if self._tasks_api is None:
            if self._client is None:
                self._client = APIClient()
            self._tasks_api = TasksAPI(self._client)
        return self._tasks_api

    def _encrypt_task_fields(self, task_data: dict) -> dict:
        """Encrypt sensitive task fields before sending to server.

        Args:
            task_data: Task data dictionary

        Returns:
            Modified task data with encrypted fields
        """
        if not self.e2ee.enabled:
            return task_data

        # Encrypt content and description
        if "content" in task_data and task_data["content"]:
            (
                plain_content,
                encrypted_content,
                plain_desc,
                encrypted_desc,
            ) = self.e2ee.prepare_task_for_storage(
                task_data["content"], task_data.get("description")
            )
            task_data["content"] = plain_content  # Empty in E2EE mode
            task_data["content_encrypted"] = encrypted_content
            if "description" in task_data:
                task_data["description"] = plain_desc  # Empty in E2EE mode
                task_data["description_encrypted"] = encrypted_desc

        return task_data

    def _decrypt_task_fields(self, task_data: dict) -> dict:
        """Decrypt sensitive task fields after receiving from server.

        Args:
            task_data: Task data dictionary from server

        Returns:
            Modified task data with decrypted fields
        """
        if not self.e2ee.enabled:
            return task_data

        # Decrypt content and description if encrypted fields exist
        if "content_encrypted" in task_data and task_data.get("content_encrypted"):
            content, description = self.e2ee.extract_task_content(
                task_data.get("content", ""),
                task_data.get("content_encrypted"),
                task_data.get("description", ""),
                task_data.get("description_encrypted"),
            )
            task_data["content"] = content
            task_data["description"] = description

        return task_data

    async def list_all(self, filters: TaskFilters) -> list[Task]:
        """List all tasks with filtering."""
        params = {}

        if filters.status:
            params["status"] = filters.status
        if filters.project_id:
            params["project_id"] = filters.project_id
        if filters.priority is not None:
            params["priority"] = filters.priority
        if filters.search:
            params["search"] = filters.search
        if filters.limit is not None:
            params["limit"] = filters.limit
        if filters.offset is not None:
            params["offset"] = filters.offset
        if filters.sort:
            params["sort"] = filters.sort

        result = await self.tasks_api.list_tasks(**params)

        # Parse response - API returns {"tasks": [...]}
        tasks_data = result.get("tasks", []) if isinstance(result, dict) else result

        # Decrypt task fields if E2EE is enabled
        if self.e2ee.enabled:
            tasks_data = [
                self._decrypt_task_fields(task_dict) for task_dict in tasks_data
            ]

        return [Task(**task_dict) for task_dict in tasks_data]

    async def get(self, task_id: str) -> Task:
        """Get a specific task by ID."""
        result = await self.tasks_api.get_task(task_id)

        # Decrypt task fields if E2EE is enabled
        if self.e2ee.enabled:
            result = self._decrypt_task_fields(result)

        return Task(**result)

    async def add(self, task_data: TaskCreate) -> Task:
        """Create a new task."""
        data = task_data.model_dump(exclude_none=True)

        # Convert datetime to ISO string
        if "due_date" in data and isinstance(data["due_date"], datetime):
            data["due_date"] = data["due_date"].isoformat()

        # Encrypt sensitive fields if E2EE is enabled
        if self.e2ee.enabled:
            data = self._encrypt_task_fields(data)

        result = await self.tasks_api.create_task(**data)

        # Decrypt the returned task
        if self.e2ee.enabled:
            result = self._decrypt_task_fields(result)

        return Task(**result)

    async def update(self, task_id: str, updates: TaskUpdate) -> Task:
        """Update an existing task."""
        update_data = updates.model_dump(exclude_none=True)

        # Convert datetime to ISO string
        if "due_date" in update_data and isinstance(update_data["due_date"], datetime):
            update_data["due_date"] = update_data["due_date"].isoformat()

        # Encrypt sensitive fields if E2EE is enabled
        if self.e2ee.enabled:
            update_data = self._encrypt_task_fields(update_data)

        result = await self.tasks_api.update_task(task_id, **update_data)

        # Decrypt the returned task
        if self.e2ee.enabled:
            result = self._decrypt_task_fields(result)

        return Task(**result)

    async def delete(self, task_id: str) -> bool:
        """Delete a task."""
        await self.tasks_api.delete_task(task_id)
        return True

    async def complete(self, task_id: str) -> Task:
        """Mark a task as completed."""
        result = await self.tasks_api.complete_task(task_id)

        # Decrypt the returned task
        if self.e2ee.enabled:
            result = self._decrypt_task_fields(result)

        return Task(**result)

    async def bulk_update(self, task_ids: list[str], updates: TaskUpdate) -> list[Task]:
        """Update multiple tasks at once."""
        # Note: Current API might not have a true bulk update endpoint
        # We'll use the batch complete if only updating completion status
        if updates.is_completed is True and all(
            v is None for k, v in updates.model_dump().items() if k != "is_completed"
        ):
            result = await self.tasks_api.batch_complete_tasks(task_ids)
            tasks_data = result.get("tasks", []) if isinstance(result, dict) else []

            # Decrypt task fields if E2EE is enabled
            if self.e2ee.enabled:
                tasks_data = [
                    self._decrypt_task_fields(task_dict) for task_dict in tasks_data
                ]

            return [Task(**task_dict) for task_dict in tasks_data]

        # Otherwise, update tasks one by one (already calls self.update which handles encryption)
        updated_tasks = []
        for task_id in task_ids:
            task = await self.update(task_id, updates)
            updated_tasks.append(task)
        return updated_tasks


class RestApiProjectRepository(ProjectRepository):
    """Project repository implementation using REST API."""

    def __init__(self):
        """Initialize REST API project repository."""
        self._client: APIClient | None = None
        self._projects_api: ProjectsAPI | None = None

    @property
    def projects_api(self) -> ProjectsAPI:
        """Get or create ProjectsAPI instance."""
        if self._projects_api is None:
            if self._client is None:
                self._client = APIClient()
            self._projects_api = ProjectsAPI(self._client)
        return self._projects_api

    async def list_all(self, filters: ProjectFilters) -> list[Project]:
        """List all projects with filtering."""
        # The projects API might not support all filters yet
        # We'll fetch all and filter in memory if needed
        result = await self.projects_api.list_projects()
        projects_data = (
            result.get("projects", []) if isinstance(result, dict) else result
        )
        projects = [Project(**proj_dict) for proj_dict in projects_data]

        # Apply filters
        if filters.is_favorite is not None:
            projects = [p for p in projects if p.is_favorite == filters.is_favorite]
        if filters.is_archived is not None:
            projects = [p for p in projects if p.is_archived == filters.is_archived]
        if filters.workspace_id is not None:
            projects = [p for p in projects if p.workspace_id == filters.workspace_id]
        if filters.search:
            search_lower = filters.search.lower()
            projects = [p for p in projects if search_lower in p.name.lower()]

        return projects

    async def get(self, project_id: str) -> Project:
        """Get a specific project by ID."""
        result = await self.projects_api.get_project(project_id)
        return Project(**result)

    async def create(self, project_data: ProjectCreate) -> Project:
        """Create a new project."""
        data = project_data.model_dump(exclude_none=True)
        result = await self.projects_api.create_project(**data)
        return Project(**result)

    async def update(self, project_id: str, updates: ProjectUpdate) -> Project:
        """Update an existing project."""
        update_data = updates.model_dump(exclude_none=True)
        result = await self.projects_api.update_project(project_id, **update_data)
        return Project(**result)

    async def delete(self, project_id: str) -> bool:
        """Delete a project."""
        await self.projects_api.delete_project(project_id)
        return True

    async def archive(self, project_id: str) -> Project:
        """Archive a project."""
        result = await self.projects_api.archive_project(project_id)
        return Project(**result)

    async def unarchive(self, project_id: str) -> Project:
        """Unarchive a project."""
        result = await self.projects_api.unarchive_project(project_id)
        return Project(**result)

    async def get_stats(self, project_id: str) -> dict:
        """Get project statistics."""
        return await self.projects_api.get_project_stats(project_id)


class RestApiLabelRepository(LabelRepository):
    """Label repository implementation using REST API."""

    def __init__(self):
        """Initialize REST API label repository."""

        self._client: APIClient | None = None
        self._labels_api: LabelsAPI | None = None

    @property
    def labels_api(self) -> LabelsAPI:
        """Get or create LabelsAPI instance."""
        if self._labels_api is None:
            if self._client is None:
                self._client = APIClient()
            self._labels_api = LabelsAPI(self._client)
        return self._labels_api

    async def list_all(self) -> list[Label]:
        """List all labels."""
        result = await self.labels_api.list_labels()
        labels_data = result.get("labels", []) if isinstance(result, dict) else result
        return [Label(**label_dict) for label_dict in labels_data]

    async def get(self, label_id: str) -> Label:
        """Get a specific label by ID."""
        result = await self.labels_api.get_label(label_id)
        return Label(**result)

    async def create(self, label_data: LabelCreate) -> Label:
        """Create a new label."""
        data = label_data.model_dump(exclude_none=True)
        result = await self.labels_api.create_label(**data)
        return Label(**result)

    async def delete(self, label_id: str) -> bool:
        """Delete a label."""
        await self.labels_api.delete_label(label_id)
        return True

    async def search(self, prefix: str) -> list[Label]:
        """Search labels by name prefix."""
        # Fetch all labels and filter by prefix
        all_labels = await self.list_all()
        prefix_lower = prefix.lower()
        return [
            label for label in all_labels if label.name.lower().startswith(prefix_lower)
        ]


class RestApiLocationContextRepository(LocationContextRepository):
    """Context repository implementation using REST API.

    Implements location-based context management with geofencing support.
    All 5 methods fully implemented (Spec 13, 2025-02-18).

    Capabilities:
    - List all contexts for authenticated user
    - Get context details by ID
    - Create new contexts with geofencing
    - Delete contexts
    - Check available contexts based on current location

    Geofencing:
    - Server-side Haversine distance calculation
    - Contexts have latitude, longitude, and radius
    - get_available() filters contexts within range

    Error Handling:
    - Queries (list_all, get_available): Return empty on error (graceful)
    - Actions (get, create, delete): Raise ValueError (explicit feedback)

    Backend API Endpoints:
    - GET /v1/contexts - list all
    - GET /v1/contexts/{id} - get by ID
    - POST /v1/contexts - create
    - DELETE /v1/contexts/{id} - delete
    - POST /v1/contexts/check-available - geofencing query
    """

    def __init__(self):
        """Initialize REST API context repository."""

        self._client: APIClient | None = None

    @property
    def client(self) -> APIClient:
        """Get or create API client."""
        if self._client is None:
            self._client = APIClient()
        return self._client

    async def list_all(self) -> list[LocationContext]:
        """List all contexts for the authenticated user."""
        try:
            response = await self.client.get("/v1/contexts")

            # Response is a list of context objects
            contexts = []
            for ctx_data in response:
                # Map backend fields to our model
                context = LocationContext(
                    id=ctx_data["id"],
                    name=ctx_data["name"],
                    latitude=ctx_data["latitude"],
                    longitude=ctx_data["longitude"],
                    radius=ctx_data["radius"],
                )
                contexts.append(context)

            return contexts
        except Exception:
            # Return empty list on error (user may not have permission or contexts)
            return []

    async def get(self, context_id: str) -> LocationContext:
        """Get a specific context by ID."""
        try:
            response = await self.client.get(f"/v1/contexts/{context_id}")

            return LocationContext(
                id=response["id"],
                name=response["name"],
                latitude=response["latitude"],
                longitude=response["longitude"],
                radius=response["radius"],
            )
        except Exception as e:
            raise ValueError(f"Context {context_id} not found") from e

    async def create(self, context_data: LocationContextCreate) -> LocationContext:
        """Create a new context."""
        payload = {
            "name": context_data.name,
            "latitude": context_data.latitude,
            "longitude": context_data.longitude,
            "radius": context_data.radius,
        }

        try:
            response = await self.client.post("/v1/contexts", json=payload)

            return LocationContext(
                id=response["id"],
                name=response["name"],
                latitude=response["latitude"],
                longitude=response["longitude"],
                radius=response["radius"],
            )
        except Exception as e:
            raise ValueError(f"Failed to create context: {e}") from e

    async def delete(self, context_id: str) -> bool:
        """Delete a context (soft delete)."""
        try:
            await self.client.delete(f"/v1/contexts/{context_id}")
            return True
        except Exception:
            return False

    async def get_available(
        self, latitude: float, longitude: float
    ) -> list[LocationContext]:
        """Get contexts available at a specific location.

        Uses the backend's geofencing check to determine which contexts
        are within range of the given coordinates.
        """
        try:
            response = await self.client.post(
                "/v1/contexts/check-available",
                json={"latitude": latitude, "longitude": longitude},
            )

            # Backend returns {"available": [...], "unavailable": [...], "user_location": {...}}
            available_contexts = []
            for ctx_data in response.get("available", []):
                context = LocationContext(
                    id=ctx_data["id"],
                    name=ctx_data["name"],
                    latitude=ctx_data["latitude"],
                    longitude=ctx_data["longitude"],
                    radius=ctx_data["radius"],
                )
                available_contexts.append(context)

            return available_contexts
        except Exception:
            # Return empty list on error
            return []


class RestApiSectionRepository(SectionRepository):
    """Section repository implementation using REST API."""

    def __init__(self):
        self._client: APIClient | None = None
        self._sections_api: SectionsAPI | None = None

    @property
    def sections_api(self) -> SectionsAPI:
        if self._sections_api is None:
            if self._client is None:
                self._client = APIClient()
            self._sections_api = SectionsAPI(self._client)
        return self._sections_api

    async def list_all(self, project_id: str) -> list[Section]:
        """List all sections for a project."""
        result = await self.sections_api.list_sections(project_id)
        sections_data = result if isinstance(result, list) else []
        return [Section(**s) for s in sections_data]

    async def get(self, project_id: str, section_id: str) -> Section:
        """Get a specific section by ID."""
        result = await self.sections_api.get_section(project_id, section_id)
        return Section(**result)

    async def create(self, project_id: str, section_data: SectionCreate) -> Section:
        """Create a new section."""
        data = section_data.model_dump()
        result = await self.sections_api.create_section(project_id, **data)
        return Section(**result)

    async def update(
        self, project_id: str, section_id: str, updates: SectionUpdate
    ) -> Section:
        """Update an existing section."""
        update_data = updates.model_dump(exclude_none=True)
        result = await self.sections_api.update_section(
            project_id, section_id, **update_data
        )
        return Section(**result)

    async def delete(self, project_id: str, section_id: str) -> bool:
        """Delete a section."""
        await self.sections_api.delete_section(project_id, section_id)
        return True

    async def reorder(self, project_id: str, section_orders: list[dict]) -> None:
        """Reorder sections within a project."""
        await self.sections_api.reorder_sections(project_id, section_orders)
