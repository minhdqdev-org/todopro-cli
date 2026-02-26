"""Unit tests for background task runner (background.py)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from todopro_cli.utils.background import run_in_background


class TestRunInBackground:
    """Tests for run_in_background()."""

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_starts_subprocess(self, mock_tmp, mock_popen):
        """run_in_background launches a subprocess."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker_123.py"
        mock_tmp.return_value = mock_file

        run_in_background(command="complete", context={"task_id": "abc123"})

        assert mock_popen.called
        call_args = mock_popen.call_args
        args = call_args[0][0]  # first positional arg is the args list
        assert isinstance(args, list)
        assert len(args) > 0

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_popen_detached(self, mock_tmp, mock_popen):
        """Subprocess is started detached (start_new_session=True)."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_tmp.return_value = mock_file

        run_in_background(command="complete", context={"task_id": "task-1"})

        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("start_new_session") is True
        assert call_kwargs.get("stdout") == subprocess.DEVNULL
        assert call_kwargs.get("stderr") == subprocess.DEVNULL
        assert call_kwargs.get("stdin") == subprocess.DEVNULL

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_context_none_defaults_to_empty_dict(self, mock_tmp, mock_popen):
        """context=None defaults to empty dict (no crash)."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_tmp.return_value = mock_file

        # Should not raise
        run_in_background(command="complete", context=None)
        assert mock_popen.called

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_task_type_passed_in_args(self, mock_tmp, mock_popen):
        """task_type is passed as first argv argument to worker script."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_tmp.return_value = mock_file

        run_in_background(
            command="batch_complete",
            context={"task_ids": ["t1", "t2"]},
            task_type="batch_complete",
        )

        args_list = mock_popen.call_args[0][0]
        assert "batch_complete" in args_list

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_max_retries_passed_in_args(self, mock_tmp, mock_popen):
        """max_retries is serialized into args list."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_tmp.return_value = mock_file

        run_in_background(command="complete", context={"task_id": "x"}, max_retries=5)

        args_list = mock_popen.call_args[0][0]
        assert "5" in args_list

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_context_json_serialized(self, mock_tmp, mock_popen):
        """context dict is JSON-serialized and passed in args."""
        import json

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_tmp.return_value = mock_file

        context = {"task_id": "abc-123"}
        run_in_background(command="complete", context=context)

        args_list = mock_popen.call_args[0][0]
        # Find the JSON arg
        json_arg = next(
            (a for a in args_list if isinstance(a, str) and "task_id" in a), None
        )
        assert json_arg is not None
        parsed = json.loads(json_arg)
        assert parsed["task_id"] == "abc-123"

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_task_type_defaults_to_command(self, mock_tmp, mock_popen):
        """If task_type is None, command is used as the task_type."""
        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_tmp.return_value = mock_file

        run_in_background(command="complete", context={"task_id": "t1"}, task_type=None)

        args_list = mock_popen.call_args[0][0]
        assert "complete" in args_list

    @patch("todopro_cli.utils.background.subprocess.Popen")
    @patch("todopro_cli.utils.background.tempfile.NamedTemporaryFile")
    def test_worker_script_written_to_file(self, mock_tmp, mock_popen):
        """Worker script template is written to the temp file."""
        written_content = []

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/worker.py"
        mock_file.write.side_effect = lambda s: written_content.append(s)
        mock_tmp.return_value = mock_file

        run_in_background(command="complete", context={"task_id": "t1"})

        assert len(written_content) > 0
        assert "asyncio" in written_content[0]
