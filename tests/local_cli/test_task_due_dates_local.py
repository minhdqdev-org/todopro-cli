"""Natural-language due dates through `edit`, `reschedule` and `task create/update`."""

from __future__ import annotations

import json
from datetime import date, timedelta


def _task_due(local_cli, task_id: str) -> str:
    out = local_cli("task", "get", task_id, "-o", "json")
    assert out.exit_code == 0, out.output
    return json.loads(out.output)["due_date"]


def _new_task(local_cli, title: str = "write report") -> str:
    created = local_cli("task", "create", title, "-o", "json")
    assert created.exit_code == 0, created.output
    # Output is "Success: Task created: <id>" followed by the JSON document.
    line = next(ln for ln in created.output.splitlines() if "Task created:" in ln)
    return line.rsplit(" ", 1)[-1]


def _tomorrow() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


def test_edit_due_natural_language(local_cli):
    task_id = _new_task(local_cli)

    result = local_cli("edit", task_id, "--due", "tomorrow")

    assert result.exit_code == 0, result.output
    assert _task_due(local_cli, task_id).startswith(_tomorrow())


def test_reschedule_natural_language(local_cli):
    task_id = _new_task(local_cli)

    result = local_cli("reschedule", task_id, "-d", "tomorrow")

    assert result.exit_code == 0, result.output
    assert _task_due(local_cli, task_id).startswith(_tomorrow())


def test_task_create_and_update_due_natural_language(local_cli):
    created = local_cli("task", "create", "ship it", "--due", "tomorrow", "-o", "json")
    assert created.exit_code == 0, created.output
    task_id = next(
        ln for ln in created.output.splitlines() if "Task created:" in ln
    ).rsplit(" ", 1)[-1]
    assert _task_due(local_cli, task_id).startswith(_tomorrow())

    result = local_cli("task", "update", task_id, "--due", "in 3 days")

    assert result.exit_code == 0, result.output
    expected = (date.today() + timedelta(days=3)).isoformat()
    assert _task_due(local_cli, task_id).startswith(expected)


def test_iso_datetime_keeps_exact_time(local_cli):
    task_id = _new_task(local_cli)

    result = local_cli("edit", task_id, "--due", "2030-03-01 14:30")

    assert result.exit_code == 0, result.output
    assert "2030-03-01" in _task_due(local_cli, task_id)
    assert "14:30" in _task_due(local_cli, task_id)


def test_unparseable_due_is_a_clear_error(local_cli):
    task_id = _new_task(local_cli)

    result = local_cli("edit", task_id, "--due", "whenever")

    assert result.exit_code != 0
    assert "Could not understand date 'whenever'" in result.output
