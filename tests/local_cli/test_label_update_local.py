"""`label update` against the real local (SQLite) stack."""

from __future__ import annotations

import json


def _create_label(local_cli, name: str) -> str:
    result = local_cli("label", "create", name)
    assert result.exit_code == 0, result.output
    listed = json.loads(local_cli("label", "list", "--json").output)["labels"]
    return next(lbl["id"] for lbl in listed if lbl["name"] == name)


def _labels(local_cli) -> dict[str, dict]:
    listed = json.loads(local_cli("label", "list", "--json").output)["labels"]
    return {lbl["name"]: lbl for lbl in listed}


def test_update_name(local_cli):
    label_id = _create_label(local_cli, "work")

    result = local_cli("label", "update", label_id, "--name", "office")

    assert result.exit_code == 0, result.output
    assert "Label updated" in result.output
    assert set(_labels(local_cli)) == {"office"}


def test_update_color_keeps_name(local_cli):
    label_id = _create_label(local_cli, "work")

    result = local_cli("label", "update", label_id, "--color", "#ff0000")

    assert result.exit_code == 0, result.output
    assert _labels(local_cli)["work"]["color"] == "#ff0000"


def test_update_to_existing_name_is_rejected(local_cli):
    _create_label(local_cli, "work")
    home_id = _create_label(local_cli, "home")

    result = local_cli("label", "update", home_id, "--name", "work")

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert set(_labels(local_cli)) == {"work", "home"}


def test_update_without_changes_exits_1(local_cli):
    label_id = _create_label(local_cli, "work")

    result = local_cli("label", "update", label_id)

    assert result.exit_code == 1
