"""TodoistImportService — orchestrates Todoist → TodoPro data migration.

Design follows SOLID:
  S – each method has one responsibility (fetch, convert, persist)
  O – extend by subclassing; no ifs for different storage backends
  L – any TodoistClientProtocol implementation is substitutable
  I – client protocol exposes only the three methods this service needs
  D – depends on abstractions (protocol + repository interfaces), not concretes
"""

from __future__ import annotations

from datetime import UTC, datetime

from todopro_cli.models import LabelCreate, ProjectCreate, ProjectFilters, TaskCreate, TaskFilters

from .client import TodoistClientProtocol
from .models import (
    TodoistImportOptions,
    TodoistImportResult,
    TodoistLabel,
    TodoistProject,
    TodoistTask,
)


class TodoistImportService:
    """Fetches data from Todoist and imports it into a TodoPro storage backend.

    Args:
        client: Todoist API client implementing :class:`TodoistClientProtocol`.
        storage: TodoPro storage strategy context providing repository access.
    """

    def __init__(self, client: TodoistClientProtocol, storage) -> None:
        self._client = client
        self._storage = storage

    async def import_all(self, options: TodoistImportOptions) -> TodoistImportResult:
        """Run the full Todoist → TodoPro import.

        Execution order: projects → labels → tasks (tasks reference both).
        When *dry_run* is True, data is fetched and counted but never written.

        Returns:
            :class:`TodoistImportResult` summarising what was imported.
        """
        result = TodoistImportResult()

        projects = await self._client.get_projects()
        labels = await self._client.get_labels()
        project_name_map = await self._import_projects(projects, options, result)
        label_name_map = await self._import_labels(labels, options, result)
        await self._import_tasks(projects, project_name_map, label_name_map, options, result)

        return result

    # ------------------------------------------------------------------
    # Private helpers — each handles exactly one resource type
    # ------------------------------------------------------------------

    async def _import_projects(
        self,
        projects: list[TodoistProject],
        options: TodoistImportOptions,
        result: TodoistImportResult,
    ) -> dict[str, str]:
        """Import projects; return mapping todoist_id → todopro_name."""
        id_to_name: dict[str, str] = {}

        for project in projects:
            prefixed_name = f"{options.project_name_prefix} {project.name}".strip()
            id_to_name[project.id] = prefixed_name

            if options.dry_run:
                result.projects_created += 1
                continue

            try:
                existing = await self._storage.project_repository.list_all(
                    ProjectFilters(search=prefixed_name)
                )
                if any(p.name == prefixed_name for p in existing):
                    result.projects_skipped += 1
                    continue

                await self._storage.project_repository.create(
                    ProjectCreate(
                        name=prefixed_name,
                        color=project.color,
                        archived=project.is_archived,
                    )
                )
                result.projects_created += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Project '{prefixed_name}': {exc}")

        return id_to_name

    async def _import_labels(
        self,
        labels: list[TodoistLabel],
        options: TodoistImportOptions,
        result: TodoistImportResult,
    ) -> dict[str, str]:
        """Import labels; return mapping todoist_label_name → todopro_label_id."""
        name_to_id: dict[str, str] = {}

        if options.dry_run:
            result.labels_created = len(labels)
            return name_to_id

        existing_labels = await self._storage.label_repository.list_all()
        existing_names = {lbl.name.lower(): lbl.id for lbl in existing_labels}

        for label in labels:
            name_lower = label.name.lower()
            if name_lower in existing_names:
                name_to_id[label.name] = existing_names[name_lower]
                result.labels_skipped += 1
                continue

            try:
                created = await self._storage.label_repository.create(
                    LabelCreate(name=label.name, color=label.color)
                )
                name_to_id[label.name] = created.id
                result.labels_created += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Label '{label.name}': {exc}")

        return name_to_id

    async def _import_tasks(
        self,
        projects: list[TodoistProject],
        project_name_map: dict[str, str],
        label_name_map: dict[str, str],
        options: TodoistImportOptions,
        result: TodoistImportResult,
    ) -> None:
        """Fetch and import tasks for every project."""
        for project in projects:
            tasks = await self._client.get_tasks(
                project.id, limit=options.max_tasks_per_project
            )
            await self._import_project_tasks(
                tasks, project_name_map, label_name_map, options, result
            )

    async def _import_project_tasks(
        self,
        tasks: list[TodoistTask],
        project_name_map: dict[str, str],
        label_name_map: dict[str, str],
        options: TodoistImportOptions,
        result: TodoistImportResult,
    ) -> None:
        """Persist a batch of tasks, resolving project/label references."""
        for task in tasks:
            if options.dry_run:
                result.tasks_created += 1
                continue

            try:
                # Skip if a task with identical content already exists
                existing = await self._storage.task_repository.list_all(
                    TaskFilters(search=task.content)
                )
                if any(t.content == task.content for t in existing):
                    result.tasks_skipped += 1
                    continue

                project_id = await self._resolve_project_id(
                    task.project_id, project_name_map
                )
                label_ids = self._resolve_label_ids(task.labels, label_name_map)
                due_date = self._parse_due_date(task)

                await self._storage.task_repository.add(
                    TaskCreate(
                        content=task.content,
                        description=task.description or None,
                        project_id=project_id,
                        due_date=due_date,
                        priority=task.priority,
                        labels=label_ids,
                    )
                )
                result.tasks_created += 1
            except Exception as exc:  # noqa: BLE001
                result.errors.append(f"Task '{task.content[:40]}': {exc}")

    async def _resolve_project_id(
        self, todoist_project_id: str, project_name_map: dict[str, str]
    ) -> str | None:
        """Resolve Todoist project ID to the corresponding TodoPro project ID."""
        prefixed_name = project_name_map.get(todoist_project_id)
        if not prefixed_name:
            return None

        projects = await self._storage.project_repository.list_all(
            ProjectFilters(search=prefixed_name)
        )
        match = next((p for p in projects if p.name == prefixed_name), None)
        return match.id if match else None

    @staticmethod
    def _resolve_label_ids(
        todoist_label_names: list[str], label_name_map: dict[str, str]
    ) -> list[str]:
        """Map Todoist label names to TodoPro label IDs."""
        return [
            label_name_map[name]
            for name in todoist_label_names
            if name in label_name_map
        ]

    @staticmethod
    def _parse_due_date(task: TodoistTask) -> datetime | None:
        """Convert Todoist due date string to an aware datetime, or None."""
        if not task.due or not task.due.date:
            return None
        raw = task.due.date
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.replace(tzinfo=UTC)
            except ValueError:
                continue
        return None
