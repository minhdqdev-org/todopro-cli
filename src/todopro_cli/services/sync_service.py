"""Sync service for data synchronization between local and remote storage.

Handles pull and push operations with conflict detection and resolution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from todopro_cli.repositories import (
    ContextRepository,
    LabelRepository,
    ProjectRepository,
    TaskRepository,
)
from todopro_cli.models import (
    Label,
    LabelCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskFilters,
)
from todopro_cli.services.sync_conflicts import SyncConflict, SyncConflictTracker
from todopro_cli.services.sync_state import SyncState


class SyncResult:
    """Result of a sync operation."""

    def __init__(self):
        """Initialize sync result."""
        self.tasks_fetched = 0
        self.tasks_new = 0
        self.tasks_updated = 0
        self.tasks_unchanged = 0
        self.tasks_conflicts = 0

        self.projects_fetched = 0
        self.projects_new = 0
        self.projects_updated = 0
        self.projects_unchanged = 0

        self.labels_fetched = 0
        self.labels_new = 0
        self.labels_updated = 0
        self.labels_unchanged = 0

        self.contexts_fetched = 0
        self.contexts_new = 0
        self.contexts_updated = 0
        self.contexts_unchanged = 0

        self.success = False
        self.error: str | None = None
        self.duration: float = 0.0


class SyncService:
    """Base sync service with common functionality."""

    def __init__(
        self,
        source_task_repo: TaskRepository,
        source_project_repo: ProjectRepository,
        source_label_repo: LabelRepository,
        source_context_repo: ContextRepository,
        target_task_repo: TaskRepository,
        target_project_repo: ProjectRepository,
        target_label_repo: LabelRepository,
        target_context_repo: ContextRepository,
        console: Console | None = None,
    ):
        """Initialize sync service.

        Args:
            source_task_repo: Source task repository
            source_project_repo: Source project repository
            source_label_repo: Source label repository
            source_context_repo: Source context repository
            target_task_repo: Target task repository
            target_project_repo: Target project repository
            target_label_repo: Target label repository
            target_context_repo: Target context repository
            console: Optional Rich console for output
        """
        self.source_task_repo = source_task_repo
        self.source_project_repo = source_project_repo
        self.source_label_repo = source_label_repo
        self.source_context_repo = source_context_repo

        self.target_task_repo = target_task_repo
        self.target_project_repo = target_project_repo
        self.target_label_repo = target_label_repo
        self.target_context_repo = target_context_repo

        self.console = console or Console()
        self.conflict_tracker = SyncConflictTracker()
        self.sync_state = SyncState()

    def _should_update(
        self,
        local_updated_at: str | None,
        remote_updated_at: str | None,
        strategy: Literal["local_wins", "remote_wins"],
    ) -> tuple[bool, str]:
        """Determine if an item should be updated based on timestamps.

        Args:
            local_updated_at: Local update timestamp
            remote_updated_at: Remote update timestamp
            strategy: Conflict resolution strategy

        Returns:
            Tuple of (should_update, reason)
        """
        comparison = SyncConflictTracker.compare_timestamps(
            local_updated_at, remote_updated_at
        )

        if comparison == "equal":
            return False, "equal"

        if strategy == "remote_wins":
            if comparison == "remote":
                return True, "remote_newer"
            return False, "local_newer"
        # local_wins
        if comparison == "local":
            return True, "local_newer"
        return False, "remote_newer"

    def _log_conflict(
        self,
        resource_type: str,
        resource_id: str,
        local_data: dict[str, Any],
        remote_data: dict[str, Any],
        resolution: str,
    ) -> None:
        """Log a sync conflict.

        Args:
            resource_type: Type of resource
            resource_id: Resource UUID
            local_data: Local version data
            remote_data: Remote version data
            resolution: Resolution strategy applied
        """
        conflict = SyncConflict(
            resource_type=resource_type,
            resource_id=resource_id,
            local_data=local_data,
            remote_data=remote_data,
            resolution=resolution,
        )
        self.conflict_tracker.add_conflict(conflict)


class SyncPullService(SyncService):
    """Service for pulling data from remote to local."""

    async def pull(
        self,
        source_context: str,
        target_context: str,
        dry_run: bool = False,
        full_sync: bool = False,
        strategy: Literal["local_wins", "remote_wins"] = "remote_wins",
    ) -> SyncResult:
        """Pull data from source to target.

        Args:
            source_context: Source context name (typically remote)
            target_context: Target context name (typically local)
            dry_run: If True, preview changes without applying
            full_sync: If True, ignore last sync timestamp
            strategy: Conflict resolution strategy

        Returns:
            SyncResult with operation details
        """
        result = SyncResult()
        start_time = datetime.now()

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                # Determine last sync time for incremental sync
                context_key = SyncState.make_context_key(
                    source_context, target_context, "pull"
                )
                last_sync = (
                    None if full_sync else self.sync_state.get_last_sync(context_key)
                )

                # Pull projects first (dependencies)
                task = progress.add_task("Fetching projects...", total=None)
                project_filters = ProjectFilters()
                projects = await self.source_project_repo.list_all(project_filters)
                result.projects_fetched = len(projects)
                progress.update(task, completed=True)

                # Pull labels
                task = progress.add_task("Fetching labels...", total=None)
                labels = await self.source_label_repo.list_all()
                result.labels_fetched = len(labels)
                progress.update(task, completed=True)

                # Pull tasks
                task = progress.add_task("Fetching tasks...", total=None)
                filters = TaskFilters()
                tasks = await self.source_task_repo.list_all(filters)
                result.tasks_fetched = len(tasks)
                progress.update(task, completed=True)

                if dry_run:
                    # Preview mode - just count what would change
                    self.console.print(
                        "\n[yellow]Dry run - no changes applied[/yellow]"
                    )
                else:
                    # Sync projects
                    task = progress.add_task("Syncing projects...", total=len(projects))
                    for project in projects:
                        await self._sync_project(project, result, strategy)
                        progress.advance(task)

                    # Sync labels
                    task = progress.add_task("Syncing labels...", total=len(labels))
                    for label in labels:
                        await self._sync_label(label, result, strategy)
                        progress.advance(task)

                    # Sync tasks
                    task = progress.add_task("Syncing tasks...", total=len(tasks))
                    for task_item in tasks:
                        await self._sync_task(task_item, result, strategy)
                        progress.advance(task)

                    # Update last sync time
                    self.sync_state.set_last_sync(context_key)

            # Save conflicts
            if self.conflict_tracker.has_conflicts():
                self.conflict_tracker.save()

            result.success = True
            result.duration = (datetime.now() - start_time).total_seconds()

        except Exception as e:
            import traceback
            result.success = False
            result.error = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{''.join(traceback.format_tb(e.__traceback__))}"
            result.duration = (datetime.now() - start_time).total_seconds()

        return result

    async def _sync_project(
        self, project: Project, result: SyncResult, strategy: str
    ) -> None:
        """Sync a single project."""
        try:
            # Check if project exists locally
            existing = await self.target_project_repo.get_by_id(project.id)

            if existing is None:
                # New project
                await self.target_project_repo.create(
                    ProjectCreate(
                        id=project.id,
                        name=project.name,
                        description=project.description,
                        color=project.color,
                    )
                )
                result.projects_new += 1
            else:
                # Existing project - check if update needed
                should_update, reason = self._should_update(
                    existing.updated_at, project.updated_at, strategy
                )

                if should_update:
                    await self.target_project_repo.update(
                        project.id,
                        ProjectUpdate(
                            name=project.name,
                            description=project.description,
                            color=project.color,
                        ),
                    )
                    result.projects_updated += 1
                else:
                    result.projects_unchanged += 1

        except Exception as e:
            # Log error but continue
            self.console.print(f"[red]Error syncing project {project.id}: {e}[/red]")

    async def _sync_label(
        self, label: Label, result: SyncResult, strategy: str
    ) -> None:
        """Sync a single label."""
        try:
            existing = await self.target_label_repo.get_by_id(label.id)

            if existing is None:
                await self.target_label_repo.create(
                    LabelCreate(id=label.id, name=label.name, color=label.color)
                )
                result.labels_new += 1
            else:
                should_update, reason = self._should_update(
                    existing.updated_at, label.updated_at, strategy
                )

                if should_update:
                    # Labels don't have explicit update method in some repos
                    # Skip update for now or implement if needed
                    result.labels_unchanged += 1
                else:
                    result.labels_unchanged += 1

        except Exception as e:
            self.console.print(f"[red]Error syncing label {label.id}: {e}[/red]")

    async def _sync_task(self, task: Task, result: SyncResult, strategy: str) -> None:
        """Sync a single task."""
        try:
            existing = await self.target_task_repo.get_by_id(task.id)

            if existing is None:

                await self.target_task_repo.create(
                    TaskCreate(
                        id=task.id,
                        content=task.content,
                        description=task.description,
                        priority=task.priority,
                        status=task.status,
                        project_id=task.project_id,
                        due_date=task.due_date,
                        completed_at=task.completed_at,
                    )
                )
                result.tasks_new += 1
            else:
                should_update, reason = self._should_update(
                    existing.updated_at, task.updated_at, strategy
                )

                if should_update:

                    await self.target_task_repo.update(
                        task.id,
                        TaskUpdate(
                            content=task.content,
                            description=task.description,
                            priority=task.priority,
                            status=task.status,
                            project_id=task.project_id,
                            due_date=task.due_date,
                        ),
                    )
                    result.tasks_updated += 1
                else:
                    if reason == "local_newer":
                        result.tasks_conflicts += 1
                        self._log_conflict(
                            "task",
                            task.id,
                            existing.model_dump(),
                            task.model_dump(),
                            "skipped_local_newer",
                        )
                    else:
                        result.tasks_unchanged += 1

        except Exception as e:
            self.console.print(f"[red]Error syncing task {task.id}: {e}[/red]")


class SyncPushService(SyncService):
    """Service for pushing data from local to remote."""

    async def push(
        self,
        source_context: str,
        target_context: str,
        dry_run: bool = False,
        full_sync: bool = False,
        strategy: Literal["local_wins", "remote_wins"] = "local_wins",
    ) -> SyncResult:
        """Push data from source to target.

        Args:
            source_context: Source context name (typically local)
            target_context: Target context name (typically remote)
            dry_run: If True, preview changes without applying
            full_sync: If True, ignore last sync timestamp
            strategy: Conflict resolution strategy

        Returns:
            SyncResult with operation details
        """
        result = SyncResult()
        start_time = datetime.now()

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                # Fetch local data
                task = progress.add_task("Fetching local projects...", total=None)
                project_filters = ProjectFilters()
                projects = await self.source_project_repo.list_all(project_filters)
                result.projects_fetched = len(projects)
                progress.update(task, completed=True)

                task = progress.add_task("Fetching local labels...", total=None)
                labels = await self.source_label_repo.list_all()
                result.labels_fetched = len(labels)
                progress.update(task, completed=True)

                task = progress.add_task("Fetching local tasks...", total=None)
                filters = TaskFilters()
                tasks = await self.source_task_repo.list_all(filters)
                result.tasks_fetched = len(tasks)
                progress.update(task, completed=True)

                if dry_run:
                    self.console.print(
                        "\n[yellow]Dry run - no changes applied[/yellow]"
                    )
                else:
                    # Push in dependency order
                    task = progress.add_task("Pushing projects...", total=len(projects))
                    for project in projects:
                        await self._sync_project(project, result, strategy)
                        progress.advance(task)

                    task = progress.add_task("Pushing labels...", total=len(labels))
                    for label in labels:
                        await self._sync_label(label, result, strategy)
                        progress.advance(task)

                    task = progress.add_task("Pushing tasks...", total=len(tasks))
                    for task_item in tasks:
                        await self._sync_task(task_item, result, strategy)
                        progress.advance(task)

                    # Update last sync time
                    context_key = SyncState.make_context_key(
                        source_context, target_context, "push"
                    )
                    self.sync_state.set_last_sync(context_key)

            if self.conflict_tracker.has_conflicts():
                self.conflict_tracker.save()

            result.success = True
            result.duration = (datetime.now() - start_time).total_seconds()

        except Exception as e:
            import traceback
            result.success = False
            result.error = f"{type(e).__name__}: {str(e)}\n\nTraceback:\n{''.join(traceback.format_tb(e.__traceback__))}"
            result.duration = (datetime.now() - start_time).total_seconds()

        return result

    async def _sync_project(
        self, project: Project, result: SyncResult, strategy: str
    ) -> None:
        """Sync a single project to target."""
        try:
            existing = await self.target_project_repo.get_by_id(project.id)

            if existing is None:

                await self.target_project_repo.create(
                    ProjectCreate(
                        id=project.id,
                        name=project.name,
                        description=project.description,
                        color=project.color,
                    )
                )
                result.projects_new += 1
            else:
                should_update, reason = self._should_update(
                    project.updated_at, existing.updated_at, strategy
                )

                if should_update:

                    await self.target_project_repo.update(
                        project.id,
                        ProjectUpdate(
                            name=project.name,
                            description=project.description,
                            color=project.color,
                        ),
                    )
                    result.projects_updated += 1
                else:
                    result.projects_unchanged += 1

        except Exception as e:
            self.console.print(f"[red]Error pushing project {project.id}: {e}[/red]")

    async def _sync_label(
        self, label: Label, result: SyncResult, strategy: str
    ) -> None:
        """Sync a single label to target."""
        try:
            existing = await self.target_label_repo.get_by_id(label.id)

            if existing is None:

                await self.target_label_repo.create(
                    LabelCreate(id=label.id, name=label.name, color=label.color)
                )
                result.labels_new += 1
            else:
                result.labels_unchanged += 1

        except Exception as e:
            self.console.print(f"[red]Error pushing label {label.id}: {e}[/red]")

    async def _sync_task(self, task: Task, result: SyncResult, strategy: str) -> None:
        """Sync a single task to target."""
        try:
            existing = await self.target_task_repo.get_by_id(task.id)

            if existing is None:

                await self.target_task_repo.create(
                    TaskCreate(
                        id=task.id,
                        content=task.content,
                        description=task.description,
                        priority=task.priority,
                        status=task.status,
                        project_id=task.project_id,
                        due_date=task.due_date,
                        completed_at=task.completed_at,
                    )
                )
                result.tasks_new += 1
            else:
                should_update, reason = self._should_update(
                    task.updated_at, existing.updated_at, strategy
                )

                if should_update:

                    await self.target_task_repo.update(
                        task.id,
                        TaskUpdate(
                            content=task.content,
                            description=task.description,
                            priority=task.priority,
                            status=task.status,
                            project_id=task.project_id,
                            due_date=task.due_date,
                        ),
                    )
                    result.tasks_updated += 1
                else:
                    if reason == "remote_newer":
                        result.tasks_conflicts += 1
                        self._log_conflict(
                            "task",
                            task.id,
                            task.model_dump(),
                            existing.model_dump(),
                            "skipped_remote_newer",
                        )
                    else:
                        result.tasks_unchanged += 1

        except Exception as e:
            self.console.print(f"[red]Error pushing task {task.id}: {e}[/red]")
