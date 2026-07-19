"""Sync service for data synchronization between local and remote storage.

Handles pull and push operations with conflict detection and resolution.
"""

from __future__ import annotations

import contextlib
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any, Literal

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from todopro_cli.models import (
    Label,
    LabelCreate,
    Project,
    ProjectCreate,
    ProjectFilters,
    ProjectUpdate,
    Task,
    TaskCreate,
    TaskFilters,
    TaskUpdate,
)
from todopro_cli.repositories import (
    LabelRepository,
    LocationContextRepository,
    ProjectRepository,
    TaskRepository,
)
from todopro_cli.services.sync_auto_fix import (
    compute_auto_fix,
    describe_fix,
    is_pro_required,
    parse_api_error,
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

        # Push auto-fix / failure tracking (see SyncPushService._attempt_push).
        self.tasks_auto_fixed = 0
        self.projects_auto_fixed = 0
        self.labels_auto_fixed = 0
        # Each: {"type", "id", "title", "message"} (auto-fix) /
        # {"type", "id", "title", "reason"} (unfixable).
        self.auto_fixes: list[dict[str, str]] = []
        self.failures: list[dict[str, str]] = []

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
        source_context_repo: LocationContextRepository,
        target_task_repo: TaskRepository,
        target_project_repo: ProjectRepository,
        target_label_repo: LabelRepository,
        target_context_repo: LocationContextRepository,
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
                (None if full_sync else self.sync_state.get_last_sync(context_key))

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
        _full_sync: bool = False,
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

    @staticmethod
    def _shorten(text: str | None, width: int = 40) -> str:
        t = (text or "").strip()
        return t if len(t) <= width else f"{t[:width]}…"

    async def _attempt_push(
        self,
        *,
        entity_type: str,
        entity_id: str,
        title: str | None,
        push_fn: Callable[[dict[str, Any]], Awaitable[Any]],
        persist_local_fn: Callable[[dict[str, Any]], Awaitable[Any]] | None,
        fixable_values: dict[str, Any],
        result: SyncResult,
    ) -> bool:
        """Push one entity, auto-fixing mechanically-fixable validation errors.

        On a permanent (4xx) validation failure we correct the payload (truncate
        over-length text, normalize a bad color), persist the correction locally
        so it isn't re-pushed, and retry once. Pro-gated (402) and otherwise
        unfixable errors are reported with the item name + reason instead of a
        raw exception. Returns True iff the entity is now on the remote.
        """
        short = self._shorten(title)

        try:
            await push_fn({})
            return True
        except httpx.HTTPStatusError as exc:
            api_err = parse_api_error(exc)
        except Exception as exc:  # network/other — surface, don't crash the sync
            self.console.print(
                f"[red]Error pushing {entity_type} '{short}': {exc}[/red]"
            )
            result.failures.append(
                {
                    "type": entity_type,
                    "id": entity_id,
                    "title": short,
                    "reason": str(exc),
                }
            )
            return False

        # Pro-gated: the field is valid, just gated — nothing to auto-fix.
        if is_pro_required(api_err):
            reason = "requires TodoPro Pro"
            self.console.print(
                f"[yellow]Skipped {entity_type} '{short}': {reason}.[/yellow]"
            )
            result.failures.append(
                {"type": entity_type, "id": entity_id, "title": short, "reason": reason}
            )
            return False

        fix = compute_auto_fix(entity_type, fixable_values, api_err)
        if fix is None:
            reason = api_err.first_reason or f"HTTP {api_err.status}"
            self.console.print(
                f"[red]Couldn't push {entity_type} '{short}': {reason}[/red]"
            )
            result.failures.append(
                {"type": entity_type, "id": entity_id, "title": short, "reason": reason}
            )
            return False

        # Persist the correction locally so the next sync doesn't re-push the bad
        # value and re-trigger the same failure. Best-effort — the remote push is
        # what actually matters.
        if persist_local_fn is not None:
            with contextlib.suppress(Exception):
                await persist_local_fn(fix.overrides)

        try:
            await push_fn(fix.overrides)
        except Exception as exc:
            self.console.print(
                f"[red]Couldn't push {entity_type} '{short}' after auto-fix: {exc}[/red]"
            )
            result.failures.append(
                {
                    "type": entity_type,
                    "id": entity_id,
                    "title": short,
                    "reason": str(exc),
                }
            )
            return False

        message = describe_fix(entity_type, fix.fixes)
        self.console.print(
            f"[yellow]Auto-fixed {entity_type} '{short}': {message}.[/yellow]"
        )
        result.auto_fixes.append(
            {"type": entity_type, "id": entity_id, "title": short, "message": message}
        )
        if entity_type == "task":
            result.tasks_auto_fixed += 1
        elif entity_type == "project":
            result.projects_auto_fixed += 1
        elif entity_type == "label":
            result.labels_auto_fixed += 1
        return True

    # ── payload builders (base + auto-fix overrides) ──────────────────────────

    @staticmethod
    def _task_create(task: Task, ov: dict[str, Any]) -> TaskCreate:
        return TaskCreate(
            id=task.id,
            content=ov.get("content", task.content),
            description=ov.get("description", task.description),
            priority=task.priority,
            status=task.status,
            project_id=task.project_id,
            due_date=task.due_date,
            completed_at=task.completed_at,
        )

    @staticmethod
    def _task_update(task: Task, ov: dict[str, Any]) -> TaskUpdate:
        return TaskUpdate(
            content=ov.get("content", task.content),
            description=ov.get("description", task.description),
            priority=task.priority,
            status=task.status,
            project_id=task.project_id,
            due_date=task.due_date,
        )

    @staticmethod
    def _project_create(project: Project, ov: dict[str, Any]) -> ProjectCreate:
        # NB: Project has no `description` field, so it isn't sent (the old code
        # referenced project.description and crashed on every project).
        return ProjectCreate(
            id=project.id,
            name=ov.get("name", project.name),
            color=ov.get("color", project.color),
        )

    @staticmethod
    def _project_update(project: Project, ov: dict[str, Any]) -> ProjectUpdate:
        return ProjectUpdate(
            name=ov.get("name", project.name),
            color=ov.get("color", project.color),
        )

    @staticmethod
    def _label_create(label: Label, ov: dict[str, Any]) -> LabelCreate:
        return LabelCreate(
            id=label.id,
            name=ov.get("name", label.name),
            color=ov.get("color", label.color),
        )

    async def _sync_project(
        self, project: Project, result: SyncResult, strategy: str
    ) -> None:
        """Sync a single project to target."""
        try:
            existing = await self.target_project_repo.get_by_id(project.id)
        except Exception as e:
            self.console.print(
                f"[red]Error pushing project '{self._shorten(project.name)}': {e}[/red]"
            )
            return

        fixable = {"name": project.name, "color": project.color}
        if existing is None:
            if await self._attempt_push(
                entity_type="project",
                entity_id=project.id,
                title=project.name,
                push_fn=lambda ov: self.target_project_repo.create(
                    self._project_create(project, ov)
                ),
                persist_local_fn=lambda ov: self.source_project_repo.update(
                    project.id, self._project_update(project, ov)
                ),
                fixable_values=fixable,
                result=result,
            ):
                result.projects_new += 1
        else:
            should_update, _reason = self._should_update(
                project.updated_at, existing.updated_at, strategy
            )
            if should_update:
                if await self._attempt_push(
                    entity_type="project",
                    entity_id=project.id,
                    title=project.name,
                    push_fn=lambda ov: self.target_project_repo.update(
                        project.id, self._project_update(project, ov)
                    ),
                    persist_local_fn=lambda ov: self.source_project_repo.update(
                        project.id, self._project_update(project, ov)
                    ),
                    fixable_values=fixable,
                    result=result,
                ):
                    result.projects_updated += 1
            else:
                result.projects_unchanged += 1

    async def _sync_label(
        self, label: Label, result: SyncResult, _strategy: str
    ) -> None:
        """Sync a single label to target."""
        try:
            existing = await self.target_label_repo.get_by_id(label.id)
        except Exception as e:
            self.console.print(
                f"[red]Error pushing label '{self._shorten(label.name)}': {e}[/red]"
            )
            return

        if existing is None:
            # No LabelUpdate model exists, so we can't persist a local correction
            # (persist_local_fn=None); the fixed create still succeeds remotely.
            if await self._attempt_push(
                entity_type="label",
                entity_id=label.id,
                title=label.name,
                push_fn=lambda ov: self.target_label_repo.create(
                    self._label_create(label, ov)
                ),
                persist_local_fn=None,
                fixable_values={"name": label.name, "color": label.color},
                result=result,
            ):
                result.labels_new += 1
        else:
            result.labels_unchanged += 1

    async def _sync_task(self, task: Task, result: SyncResult, strategy: str) -> None:
        """Sync a single task to target."""
        try:
            existing = await self.target_task_repo.get_by_id(task.id)
        except Exception as e:
            self.console.print(
                f"[red]Error pushing task '{self._shorten(task.content)}': {e}[/red]"
            )
            return

        fixable = {"content": task.content, "description": task.description}
        if existing is None:
            if await self._attempt_push(
                entity_type="task",
                entity_id=task.id,
                title=task.content,
                push_fn=lambda ov: self.target_task_repo.create(
                    self._task_create(task, ov)
                ),
                persist_local_fn=lambda ov: self.source_task_repo.update(
                    task.id, self._task_update(task, ov)
                ),
                fixable_values=fixable,
                result=result,
            ):
                result.tasks_new += 1
        else:
            should_update, reason = self._should_update(
                task.updated_at, existing.updated_at, strategy
            )
            if should_update:
                if await self._attempt_push(
                    entity_type="task",
                    entity_id=task.id,
                    title=task.content,
                    push_fn=lambda ov: self.target_task_repo.update(
                        task.id, self._task_update(task, ov)
                    ),
                    persist_local_fn=lambda ov: self.source_task_repo.update(
                        task.id, self._task_update(task, ov)
                    ),
                    fixable_values=fixable,
                    result=result,
                ):
                    result.tasks_updated += 1
            elif reason == "remote_newer":
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
