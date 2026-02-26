"""Unit tests for todopro_cli/adapters/sqlite.py (the re-export module)."""

from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

import pytest

# Path to the sqlite.py adapter file (shadowed at runtime by the sqlite/ package)
_SQLITE_PY_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "todopro_cli"
    / "adapters"
    / "sqlite.py"
)


class TestSqliteAdapterModule:
    """Verify that sqlite.py correctly re-exports repository classes."""

    def test_module_importable(self):
        import todopro_cli.adapters.sqlite as m
        assert m is not None

    def test_task_repository_exported(self):
        from todopro_cli.adapters.sqlite import SqliteTaskRepository
        assert SqliteTaskRepository is not None

    def test_project_repository_exported(self):
        from todopro_cli.adapters.sqlite import SqliteProjectRepository
        assert SqliteProjectRepository is not None

    def test_label_repository_exported(self):
        from todopro_cli.adapters.sqlite import SqliteLabelRepository
        assert SqliteLabelRepository is not None

    def test_context_repository_exported(self):
        from todopro_cli.adapters.sqlite import SqliteLocationContextRepository
        assert SqliteLocationContextRepository is not None

    def test_all_contains_expected_classes(self):
        import todopro_cli.adapters.sqlite as m
        expected = {
            "SqliteTaskRepository",
            "SqliteProjectRepository",
            "SqliteLabelRepository",
            "SqliteLocationContextRepository",
        }
        assert expected.issubset(set(m.__all__))

    def test_sqlite_py_re_exports_from_submodules(self):
        """Importing from sqlite.py and from the sub-modules yields the same class."""
        from todopro_cli.adapters import sqlite as top_level
        from todopro_cli.adapters.sqlite.task_repository import SqliteTaskRepository

        assert top_level.SqliteTaskRepository is SqliteTaskRepository


class TestSqlitePyFileDirectly:
    """Execute sqlite.py directly to ensure its import lines are covered.

    The sqlite/ package directory shadows sqlite.py at runtime (Python always
    prefers packages over modules with the same name), so we must load the file
    explicitly with importlib to trigger coverage on those lines.
    """

    def test_sqlite_py_can_be_loaded(self):
        assert _SQLITE_PY_PATH.exists(), f"Expected {_SQLITE_PY_PATH} to exist"
        spec = importlib.util.spec_from_file_location(
            "_todopro_sqlite_standalone", str(_SQLITE_PY_PATH)
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "SqliteTaskRepository")

    def test_sqlite_py_exports_all_classes(self):
        spec = importlib.util.spec_from_file_location(
            "_todopro_sqlite_standalone2", str(_SQLITE_PY_PATH)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in [
            "SqliteTaskRepository",
            "SqliteProjectRepository",
            "SqliteLabelRepository",
            "SqliteLocationContextRepository",
        ]:
            assert hasattr(mod, name), f"Missing: {name}"

    def test_sqlite_py_dunder_all(self):
        spec = importlib.util.spec_from_file_location(
            "_todopro_sqlite_standalone3", str(_SQLITE_PY_PATH)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "__all__")
        assert len(mod.__all__) == 4
