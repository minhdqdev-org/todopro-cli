"""Unit tests for TemplatesAPI service.

All HTTP calls are replaced with AsyncMock so no real network is needed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from todopro_cli.services.api.templates import TemplatesAPI


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data) -> MagicMock:
    """Build a mock httpx.Response whose .json() returns json_data."""
    resp = MagicMock()
    resp.json.return_value = json_data
    return resp


@pytest.fixture
def client() -> MagicMock:
    """Fake APIClient with async helpers."""
    c = MagicMock()
    c.get = AsyncMock()
    c.post = AsyncMock()
    c.delete = AsyncMock()
    return c


@pytest.fixture
def api(client) -> TemplatesAPI:
    return TemplatesAPI(client=client)


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


class TestListTemplates:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, api, client):
        client.get.return_value = _mock_response([])
        await api.list_templates()
        client.get.assert_called_once_with("/v1/templates")

    @pytest.mark.asyncio
    async def test_returns_json_list(self, api, client):
        templates = [{"id": "t1", "name": "Daily Standup"}, {"id": "t2", "name": "Bug Report"}]
        client.get.return_value = _mock_response(templates)
        result = await api.list_templates()
        assert result == templates

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self, api, client):
        client.get.return_value = _mock_response([])
        assert await api.list_templates() == []


# ---------------------------------------------------------------------------
# create_template
# ---------------------------------------------------------------------------


class TestCreateTemplate:
    @pytest.mark.asyncio
    async def test_calls_post_with_name_and_content(self, api, client):
        client.post.return_value = _mock_response({"id": "new-1", "name": "Sprint"})
        await api.create_template("Sprint", "Do the sprint tasks")
        client.post.assert_called_once()
        _, kwargs = client.post.call_args
        assert kwargs["json"]["name"] == "Sprint"
        assert kwargs["json"]["content"] == "Do the sprint tasks"

    @pytest.mark.asyncio
    async def test_default_priority_is_4(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c")
        _, kwargs = client.post.call_args
        assert kwargs["json"]["priority"] == 4

    @pytest.mark.asyncio
    async def test_optional_description_included_when_given(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c", description="A desc")
        _, kwargs = client.post.call_args
        assert kwargs["json"]["description"] == "A desc"

    @pytest.mark.asyncio
    async def test_optional_description_omitted_when_none(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c")
        _, kwargs = client.post.call_args
        assert "description" not in kwargs["json"]

    @pytest.mark.asyncio
    async def test_labels_included_when_provided(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c", labels=["work", "urgent"])
        _, kwargs = client.post.call_args
        assert kwargs["json"]["labels"] == ["work", "urgent"]

    @pytest.mark.asyncio
    async def test_labels_omitted_when_none(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c")
        _, kwargs = client.post.call_args
        assert "labels" not in kwargs["json"]

    @pytest.mark.asyncio
    async def test_recurrence_rule_included_when_provided(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c", recurrence_rule="FREQ=WEEKLY")
        _, kwargs = client.post.call_args
        assert kwargs["json"]["recurrence_rule"] == "FREQ=WEEKLY"

    @pytest.mark.asyncio
    async def test_recurrence_rule_omitted_when_none(self, api, client):
        client.post.return_value = _mock_response({})
        await api.create_template("T", "c")
        _, kwargs = client.post.call_args
        assert "recurrence_rule" not in kwargs["json"]

    @pytest.mark.asyncio
    async def test_returns_json_response(self, api, client):
        payload = {"id": "t-x", "name": "Sprint"}
        client.post.return_value = _mock_response(payload)
        result = await api.create_template("Sprint", "content")
        assert result == payload


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------


class TestGetTemplate:
    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self, api, client):
        client.get.return_value = _mock_response({"id": "t-1"})
        await api.get_template("t-1")
        client.get.assert_called_once_with("/v1/templates/t-1")

    @pytest.mark.asyncio
    async def test_returns_template_dict(self, api, client):
        payload = {"id": "t-1", "name": "Bug Report"}
        client.get.return_value = _mock_response(payload)
        result = await api.get_template("t-1")
        assert result == payload


# ---------------------------------------------------------------------------
# delete_template
# ---------------------------------------------------------------------------


class TestDeleteTemplate:
    @pytest.mark.asyncio
    async def test_calls_delete_on_correct_endpoint(self, api, client):
        client.delete.return_value = MagicMock()
        await api.delete_template("t-99")
        client.delete.assert_called_once_with("/v1/templates/t-99")

    @pytest.mark.asyncio
    async def test_returns_none(self, api, client):
        client.delete.return_value = MagicMock()
        result = await api.delete_template("t-99")
        assert result is None


# ---------------------------------------------------------------------------
# apply_template
# ---------------------------------------------------------------------------


class TestApplyTemplate:
    @pytest.mark.asyncio
    async def test_calls_post_on_apply_endpoint(self, api, client):
        client.post.return_value = _mock_response({"id": "task-1"})
        await api.apply_template("tpl-1")
        client.post.assert_called_once()
        args, _ = client.post.call_args
        assert args[0] == "/v1/templates/tpl-1/apply"

    @pytest.mark.asyncio
    async def test_empty_body_when_no_options(self, api, client):
        client.post.return_value = _mock_response({})
        await api.apply_template("tpl-1")
        _, kwargs = client.post.call_args
        assert kwargs["json"] == {}

    @pytest.mark.asyncio
    async def test_content_included_when_given(self, api, client):
        client.post.return_value = _mock_response({})
        await api.apply_template("tpl-1", content="Custom content")
        _, kwargs = client.post.call_args
        assert kwargs["json"]["content"] == "Custom content"

    @pytest.mark.asyncio
    async def test_project_id_included_when_given(self, api, client):
        client.post.return_value = _mock_response({})
        await api.apply_template("tpl-1", project_id="proj-42")
        _, kwargs = client.post.call_args
        assert kwargs["json"]["project_id"] == "proj-42"

    @pytest.mark.asyncio
    async def test_due_date_included_when_given(self, api, client):
        client.post.return_value = _mock_response({})
        await api.apply_template("tpl-1", due_date="2025-12-31")
        _, kwargs = client.post.call_args
        assert kwargs["json"]["due_date"] == "2025-12-31"

    @pytest.mark.asyncio
    async def test_priority_included_when_given(self, api, client):
        client.post.return_value = _mock_response({})
        await api.apply_template("tpl-1", priority=1)
        _, kwargs = client.post.call_args
        assert kwargs["json"]["priority"] == 1

    @pytest.mark.asyncio
    async def test_returns_created_task(self, api, client):
        task = {"id": "task-new", "content": "Follow-up"}
        client.post.return_value = _mock_response(task)
        result = await api.apply_template("tpl-1")
        assert result == task


# ---------------------------------------------------------------------------
# find_template_by_name
# ---------------------------------------------------------------------------


UUID_LIKE = "12345678-1234-1234-1234-123456789abc"


class TestFindTemplateByName:
    @pytest.mark.asyncio
    async def test_treats_uuid_as_id_lookup(self, api, client):
        payload = {"id": UUID_LIKE, "name": "Some Template"}
        client.get.return_value = _mock_response(payload)

        result = await api.find_template_by_name(UUID_LIKE)

        assert result == payload
        client.get.assert_called_once_with(f"/v1/templates/{UUID_LIKE}")

    @pytest.mark.asyncio
    async def test_falls_back_to_name_search_when_uuid_fails(self, api, client):
        """If get_template raises, fall back to listing and searching by name."""
        client.get.side_effect = Exception("not found")
        templates = [{"id": "t-a", "name": "Alpha"}, {"id": "t-b", "name": "Beta"}]
        client.get.side_effect = [Exception("not found"), _mock_response(templates)]

        result = await api.find_template_by_name(UUID_LIKE)
        # UUID not in list → returns None
        assert result is None

    @pytest.mark.asyncio
    async def test_finds_by_name_case_insensitive(self, api, client):
        templates = [{"id": "t-1", "name": "Daily Standup"}, {"id": "t-2", "name": "Bug Report"}]
        client.get.return_value = _mock_response(templates)

        result = await api.find_template_by_name("daily standup")

        assert result is not None
        assert result["id"] == "t-1"

    @pytest.mark.asyncio
    async def test_returns_none_when_name_not_found(self, api, client):
        client.get.return_value = _mock_response([{"id": "t-1", "name": "Alpha"}])

        result = await api.find_template_by_name("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_non_uuid_string_searches_by_name(self, api, client):
        templates = [{"id": "t-3", "name": "Sprint Review"}]
        client.get.return_value = _mock_response(templates)

        result = await api.find_template_by_name("Sprint Review")

        assert result is not None
        assert result["name"] == "Sprint Review"
        # get() should be called for list_templates path
        client.get.assert_called_with("/v1/templates")
