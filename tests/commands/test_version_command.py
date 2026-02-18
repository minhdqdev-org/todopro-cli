"""Unit tests for version command."""

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
