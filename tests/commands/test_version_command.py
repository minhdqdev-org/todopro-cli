"""Unit tests for version command."""

from importlib.metadata import PackageNotFoundError, version
from unittest.mock import patch

from typer.testing import CliRunner

from todopro_cli import __version__
from todopro_cli.commands.version_command import app

runner = CliRunner()


class TestVersionCommand:
    """Tests for the 'version' command."""

    def test_version_output(self):
        """Test that the version command outputs the correct version."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_matches_installed_distribution(self):
        """The reported version comes from package metadata, not a literal."""
        assert __version__ == version("todopro-cli")
        assert __version__ != "1.0.0"


def test_version_falls_back_when_not_installed():
    """An uninstalled source tree must still import and report something."""
    import importlib

    import todopro_cli

    try:
        with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
            reloaded = importlib.reload(todopro_cli)
            assert reloaded.__version__ == "0.0.0+unknown"
    finally:
        importlib.reload(todopro_cli)
