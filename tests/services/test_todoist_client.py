"""Unit tests for TodoistClient.

All HTTP calls are mocked via pytest-mock / unittest.mock so tests are
fast, deterministic, and offline.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from todopro_cli.services.todoist.client import TodoistClient, TodoistClientProtocol
from todopro_cli.services.todoist.models import TodoistLabel, TodoistProject, TodoistTask


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestTodoistClientProtocol:
    def test_concrete_client_satisfies_protocol(self):
        client = TodoistClient(api_key="test-key")
        assert isinstance(client, TodoistClientProtocol)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client() -> TodoistClient:
    return TodoistClient(api_key="test-key")


def _make_response(data, *, status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# get_projects
# ---------------------------------------------------------------------------


class TestGetProjects:
    @pytest.mark.asyncio
    async def test_returns_list_of_projects(self):
        raw = [
            {"id": "p1", "name": "Inbox", "color": None, "is_favorite": False, "is_archived": False},
            {"id": "p2", "name": "Work", "color": "red", "is_favorite": True, "is_archived": False},
        ]
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            projects = await client.get_projects()

        assert len(projects) == 2
        assert all(isinstance(p, TodoistProject) for p in projects)
        assert projects[0].id == "p1"
        assert projects[1].color == "red"

    @pytest.mark.asyncio
    async def test_filters_archived_projects(self):
        raw = [
            {"id": "p1", "name": "Active", "is_archived": False},
            {"id": "p2", "name": "Old", "is_archived": True},
        ]
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            projects = await client.get_projects()

        assert len(projects) == 1
        assert projects[0].id == "p1"

    @pytest.mark.asyncio
    async def test_handles_paginated_response_format(self):
        raw = {"results": [{"id": "p1", "name": "Inbox", "is_archived": False}], "next_cursor": None}
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            projects = await client.get_projects()

        assert len(projects) == 1


# ---------------------------------------------------------------------------
# get_tasks
# ---------------------------------------------------------------------------


class TestGetTasks:
    @pytest.mark.asyncio
    async def test_returns_active_tasks(self):
        raw = [
            {"id": "t1", "content": "Buy milk", "project_id": "p1", "priority": 4},
            {"id": "t2", "content": "Done task", "project_id": "p1", "priority": 4, "checked": True},
            {"id": "t3", "content": "Deleted", "project_id": "p1", "priority": 4, "is_deleted": True},
        ]
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            tasks = await client.get_tasks("p1")

        assert len(tasks) == 1
        assert tasks[0].content == "Buy milk"

    @pytest.mark.asyncio
    async def test_returns_todoist_task_instances(self):
        raw = [{"id": "t1", "content": "Task", "project_id": "p1", "priority": 2}]
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            tasks = await client.get_tasks("p1")

        assert isinstance(tasks[0], TodoistTask)
        assert tasks[0].priority == 2

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        raw = [{"id": f"t{i}", "content": f"Task {i}", "project_id": "p1"} for i in range(10)]
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            tasks = await client.get_tasks("p1", limit=3)

        assert len(tasks) == 3

    @pytest.mark.asyncio
    async def test_follows_next_cursor_pagination(self):
        page1 = {"results": [{"id": "t1", "content": "A", "project_id": "p1"}], "next_cursor": "cur2"}
        page2 = {"results": [{"id": "t2", "content": "B", "project_id": "p1"}], "next_cursor": None}
        call_count = 0

        async def fake_get(path, params=None):
            nonlocal call_count
            call_count += 1
            return page1 if call_count == 1 else page2

        client = _make_client()
        with patch.object(client, "_get", new=fake_get):
            tasks = await client.get_tasks("p1", limit=100)

        assert len(tasks) == 2
        assert call_count == 2


# ---------------------------------------------------------------------------
# get_labels
# ---------------------------------------------------------------------------


class TestGetLabels:
    @pytest.mark.asyncio
    async def test_returns_list_of_labels(self):
        raw = {"results": [
            {"id": 1, "name": "@home", "color": "blue", "order": 1},
            {"id": 2, "name": "@work", "color": "red", "order": 2},
        ]}
        client = _make_client()
        with patch.object(client, "_get", new=AsyncMock(return_value=raw)):
            labels = await client.get_labels()

        assert len(labels) == 2
        assert all(isinstance(lbl, TodoistLabel) for lbl in labels)
        assert labels[0].name == "@home"

    @pytest.mark.asyncio
    async def test_requests_maximum_limit(self):
        """Workaround for Todoist labels pagination bug — always fetches 200."""
        captured_params = {}

        async def fake_get(path, params=None):
            captured_params.update(params or {})
            return []

        client = _make_client()
        with patch.object(client, "_get", new=fake_get):
            await client.get_labels()

        assert captured_params.get("limit") == 200


# ---------------------------------------------------------------------------
# HTTP error handling
# ---------------------------------------------------------------------------


class TestHttpErrors:
    @pytest.mark.asyncio
    async def test_401_raises_value_error(self):
        import httpx

        client = _make_client()

        async def fake_get(*_, **__):
            raise ValueError("Invalid Todoist API key — check your credentials.")

        with patch.object(client, "_get", new=fake_get):
            with pytest.raises(ValueError, match="API key"):
                await client.get_projects()

    @pytest.mark.asyncio
    async def test_real_get_raises_value_error_on_401(self):
        """Integration: _get itself raises ValueError for 401."""
        import httpx

        client = _make_client()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status = MagicMock()

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=False)
        mock_async_client.get = AsyncMock(return_value=mock_resp)

        with patch("todopro_cli.services.todoist.client.httpx.AsyncClient", return_value=mock_async_client):
            with pytest.raises(ValueError, match="API key"):
                await client._get("/projects")
