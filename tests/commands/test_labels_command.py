"""Unit tests for labels command."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from todopro_cli.commands.labels import app
from todopro_cli.models import Label

runner = CliRunner()


@pytest.fixture
def mock_label_service():
    """Create a mock label service."""
    service = MagicMock()

    # Sample label data
    sample_label = Label(
        id="label-123",
        name="urgent",
        color="#FF0000",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Mock all async methods
    service.list_labels = AsyncMock(return_value=[sample_label])
    service.get_label = AsyncMock(return_value=sample_label)
    service.create_label = AsyncMock(return_value=sample_label)
    service.update_label = AsyncMock(return_value=sample_label)
    service.delete_label = AsyncMock(return_value=True)

    return service


@pytest.fixture
def mock_factory(mock_label_service):
    """Create a mock repository factory."""
    factory = MagicMock()
    repo = MagicMock()
    factory.get_label_repository = MagicMock(return_value=repo)

    return factory


@pytest.mark.skip(
    reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern"
)
class TestListCommand:
    """Tests for list command."""

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_list_labels_success(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test listing labels successfully."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        mock_label_service.list_labels.assert_called_once()

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_list_labels_json_output(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test listing labels with JSON output."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["list", "--output", "json"])

        assert result.exit_code == 0
        mock_label_service.list_labels.assert_called_once()


@pytest.mark.skip(
    reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern"
)
class TestGetCommand:
    """Tests for get command."""

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_get_label_success(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test getting a label successfully."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["get", "label-123"])

        assert result.exit_code == 0
        mock_label_service.get_label.assert_called_once_with("label-123")


@pytest.mark.skip(
    reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern"
)
class TestCreateCommand:
    """Tests for create command."""

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_create_label_minimal(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test creating a label with minimal parameters."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["create", "urgent"])

        assert result.exit_code == 0
        mock_label_service.create_label.assert_called_once()
        call_kwargs = mock_label_service.create_label.call_args.kwargs
        assert call_kwargs["name"] == "urgent"
        assert "Label created" in result.stdout

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_create_label_with_color(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test creating a label with color."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["create", "urgent", "--color", "#FF0000"])

        assert result.exit_code == 0
        call_kwargs = mock_label_service.create_label.call_args.kwargs
        assert call_kwargs["name"] == "urgent"
        assert call_kwargs["color"] == "#FF0000"


@pytest.mark.skip(
    reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern"
)
class TestUpdateCommand:
    """Tests for update command."""

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_update_label_name(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test updating a label name."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["update", "label-123", "--name", "critical"])

        assert result.exit_code == 0
        mock_label_service.update_label.assert_called_once()
        call_kwargs = mock_label_service.update_label.call_args.kwargs
        assert call_kwargs["name"] == "critical"

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_update_label_color(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test updating a label color."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["update", "label-123", "--color", "#00FF00"])

        assert result.exit_code == 0
        call_kwargs = mock_label_service.update_label.call_args.kwargs
        assert call_kwargs["color"] == "#00FF00"

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_update_label_no_changes(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test updating a label with no parameters fails."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["update", "label-123"])

        assert result.exit_code == 1
        assert "No updates specified" in result.stdout


@pytest.mark.skip(
    reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern"
)
class TestDeleteCommand:
    """Tests for delete command."""

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_delete_label_with_yes_flag(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test deleting a label with --yes flag."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["delete", "label-123", "--yes"])

        assert result.exit_code == 0
        mock_label_service.delete_label.assert_called_once_with("label-123")
        assert "Label deleted" in result.stdout

    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_delete_label_cancelled(
        self, mock_service_class, mock_factory_func, mock_factory, mock_label_service
    ):
        """Test deleting a label and cancelling."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service

        result = runner.invoke(app, ["delete", "label-123"], input="n\n")

        assert result.exit_code == 0
        mock_label_service.delete_label.assert_not_called()
        assert "Cancelled" in result.stdout


# ===========================================================================
# NEW TESTS — Strategy pattern (replaces the skipped Factory-based tests)
# Covers lines 21-27, 37-42, 53-59, 71-81, 91-102
# ===========================================================================

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from todopro_cli.commands.labels import app
from todopro_cli.models import Label

_runner = CliRunner()

_SAMPLE_LABEL = Label(
    id="lbl-999",
    name="urgent",
    color="#FF0000",
    created_at=datetime(2027, 1, 1, 0, 0, 0),
    updated_at=datetime(2027, 1, 1, 0, 0, 0),
)


def _make_strategy_ctx(label_service):
    """Build a MagicMock that impersonates a StorageStrategyContext."""
    ctx = MagicMock()
    ctx.label_repository = MagicMock()
    return ctx


def _patch_labels(label_service_mock):
    """Context manager: injects get_storage_strategy_context, LabelService, and resolve_label_id."""
    ctx_mock = _make_strategy_ctx(label_service_mock)

    return patch(
        "todopro_cli.commands.labels.get_storage_strategy_context",
        return_value=ctx_mock,
    )


@pytest.fixture
def label_svc():
    svc = MagicMock()
    svc.list_labels = AsyncMock(return_value=[_SAMPLE_LABEL])
    svc.get_label = AsyncMock(return_value=_SAMPLE_LABEL)
    svc.create_label = AsyncMock(return_value=_SAMPLE_LABEL)
    svc.update_label = AsyncMock(return_value=_SAMPLE_LABEL)
    svc.delete_label = AsyncMock(return_value=True)
    return svc


class TestLabelsCommandsStrategyPattern:
    """
    Tests for label commands using the Strategy pattern (no Factory).
    Patches get_storage_strategy_context, LabelService, and resolve_label_id
    so commands complete end-to-end without needing a real DB or cache.
    """

    # resolve_label_id is patched to pass through the raw value in all tests
    _RESOLVE = patch("todopro_cli.commands.labels.resolve_label_id", new=AsyncMock(side_effect=lambda lid, _repo: lid))

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------

    def test_list_labels_success(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["list"])
        assert result.exit_code == 0
        label_svc.list_labels.assert_called_once()

    def test_list_labels_json_output(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["list", "--output", "json"])
        assert result.exit_code == 0

    # ------------------------------------------------------------------
    # get
    # ------------------------------------------------------------------

    def test_get_label_success(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["get", "lbl-999"])
        assert result.exit_code == 0
        label_svc.get_label.assert_called_once_with("lbl-999")

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    def test_create_label_name_only(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["create", "urgent"])
        assert result.exit_code == 0
        assert "Label created" in result.output
        call_kwargs = label_svc.create_label.call_args.kwargs
        assert call_kwargs["name"] == "urgent"

    def test_create_label_with_color(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["create", "work", "--color", "#0000FF"])
        assert result.exit_code == 0
        call_kwargs = label_svc.create_label.call_args.kwargs
        assert call_kwargs["color"] == "#0000FF"
        assert call_kwargs["name"] == "work"

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_label_name(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["update", "lbl-999", "--name", "critical"])
        assert result.exit_code == 0
        assert "Label updated" in result.output
        call_kwargs = label_svc.update_label.call_args.kwargs
        assert call_kwargs["name"] == "critical"

    def test_update_label_color(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["update", "lbl-999", "--color", "#00FF00"])
        assert result.exit_code == 0
        call_kwargs = label_svc.update_label.call_args.kwargs
        assert call_kwargs["color"] == "#00FF00"

    def test_update_label_no_changes_exits_1(self, label_svc):
        """Calling update with no flags → 'No updates specified' and exit 1."""
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["update", "lbl-999"])
        assert result.exit_code == 1
        assert "No updates" in result.output

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    def test_delete_label_with_yes_flag(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["delete", "lbl-999", "--yes"])
        assert result.exit_code == 0
        label_svc.delete_label.assert_called_once_with("lbl-999")
        assert "Label deleted" in result.output

    def test_delete_label_confirmed_interactively(self, label_svc):
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["delete", "lbl-999"], input="y\n")
        assert result.exit_code == 0
        label_svc.delete_label.assert_called_once_with("lbl-999")

    def test_delete_label_cancelled(self, label_svc):
        """Answering 'no' to confirm prompt cancels deletion."""
        with _patch_labels(label_svc), self._RESOLVE:
            with patch("todopro_cli.commands.labels.LabelService", return_value=label_svc):
                result = _runner.invoke(app, ["delete", "lbl-999"], input="n\n")
        assert result.exit_code == 0
        label_svc.delete_label.assert_not_called()
        assert "Cancelled" in result.output
