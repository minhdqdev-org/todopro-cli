"""Fixtures that drive the real CLI against a throwaway local SQLite context.

Nothing in the config, storage, service or repository layers is mocked, so a
command that calls a method its service does not have fails here the same way
it does for a user.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from todopro_cli.services.config_service import get_config_service


@pytest.fixture()
def local_cli(tmp_path, monkeypatch):
    """Return ``invoke(*args)`` running the real app in a sandboxed local context."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    # The very first load of a missing config builds a remote storage strategy
    # while persisting "local" as the current context; load once, then reload
    # from the file the way every later invocation does.
    get_config_service.cache_clear()
    get_config_service().load_config()
    get_config_service.cache_clear()

    from todopro_cli.main import app

    runner = CliRunner()

    def invoke(*args: str):
        return runner.invoke(app, list(args), catch_exceptions=False)

    yield invoke
    get_config_service.cache_clear()
