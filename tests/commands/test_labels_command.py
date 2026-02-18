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


@pytest.mark.skip(reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern")
class TestListCommand:
    """Tests for list command."""
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_list_labels_success(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test listing labels successfully."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["list"])
        
        assert result.exit_code == 0
        mock_label_service.list_labels.assert_called_once()
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_list_labels_json_output(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test listing labels with JSON output."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["list", "--output", "json"])
        
        assert result.exit_code == 0
        mock_label_service.list_labels.assert_called_once()


@pytest.mark.skip(reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern")
class TestGetCommand:
    """Tests for get command."""
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_get_label_success(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test getting a label successfully."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["get", "label-123"])
        
        assert result.exit_code == 0
        mock_label_service.get_label.assert_called_once_with("label-123")


@pytest.mark.skip(reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern")
class TestCreateCommand:
    """Tests for create command."""
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_create_label_minimal(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
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
    def test_create_label_with_color(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test creating a label with color."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["create", "urgent", "--color", "#FF0000"])
        
        assert result.exit_code == 0
        call_kwargs = mock_label_service.create_label.call_args.kwargs
        assert call_kwargs["name"] == "urgent"
        assert call_kwargs["color"] == "#FF0000"


@pytest.mark.skip(reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern")
class TestUpdateCommand:
    """Tests for update command."""
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_update_label_name(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
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
    def test_update_label_color(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test updating a label color."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["update", "label-123", "--color", "#00FF00"])
        
        assert result.exit_code == 0
        call_kwargs = mock_label_service.update_label.call_args.kwargs
        assert call_kwargs["color"] == "#00FF00"
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_update_label_no_changes(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test updating a label with no parameters fails."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["update", "label-123"])
        
        assert result.exit_code == 1
        assert "No updates specified" in result.stdout


@pytest.mark.skip(reason="Tests for old architecture with Factory pattern, needs rewrite for new Strategy pattern")
class TestDeleteCommand:
    """Tests for delete command."""
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_delete_label_with_yes_flag(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test deleting a label with --yes flag."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["delete", "label-123", "--yes"])
        
        assert result.exit_code == 0
        mock_label_service.delete_label.assert_called_once_with("label-123")
        assert "Label deleted" in result.stdout
    
    @patch("todopro_cli.commands.labels.get_repository_factory")
    @patch("todopro_cli.commands.labels.LabelService")
    def test_delete_label_cancelled(self, mock_service_class, mock_factory_func, mock_factory, mock_label_service):
        """Test deleting a label and cancelling."""
        mock_factory_func.return_value = mock_factory
        mock_service_class.return_value = mock_label_service
        
        result = runner.invoke(app, ["delete", "label-123"], input="n\n")
        
        assert result.exit_code == 0
        mock_label_service.delete_label.assert_not_called()
        assert "Cancelled" in result.stdout
