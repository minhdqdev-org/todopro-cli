# """Tests for RepositoryFactory."""

# import tempfile
# from pathlib import Path
# from unittest.mock import patch

# import pytest

# from todopro_cli.core.factory import RepositoryFactory
# from todopro_cli.core.repository import (
#     LabelRepository,
#     LocationContextRepository,
#     ProjectRepository,
#     TaskRepository,
# )
# from todopro_cli.models.config_models import Context
# from todopro_cli.services.config_service import ConfigService


# @pytest.fixture
# def config_service():
#     """Fixture for ConfigService with temporary directory."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         with patch("platformdirs.user_config_dir", return_value=tmpdir):
#             with patch("platformdirs.user_data_dir", return_value=tmpdir):
#                 yield ConfigService()


# class TestRepositoryFactory:
#     """Test RepositoryFactory functionality."""

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_factory_initialization(self):
#         """Test factory can be initialized."""
#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#         assert factory is not None
#         assert factory._task_repo is None
#         assert factory._project_repo is None
#         assert factory._label_repo is None
#         assert factory._context_repo is None

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_storage_type_local(self, config_service):
#         """Test factory detects local storage type."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             assert factory.storage_type == "local"
#             assert factory.database_path == str(db_path)

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_storage_type_remote(self, config_service):
#         """Test factory detects remote storage type."""
#         # Setup remote context
#         config_service.config.contexts.append(
#             Context(name="test-remote", type="remote", source="https://api.example.com")
#         )
#         config_service.config.current_context_name = "test-remote"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             assert factory.storage_type == "remote"
#             assert factory.database_path is None

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_storage_type_defaults_to_remote(self, config_service):
#         """Test factory defaults to remote when no context configured."""
#         # Don't set any context - config_service defaults to empty config
#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             # With no contexts, it should default to local (changed from remote)
#             assert factory.storage_type == "local"

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_get_task_repository_local(self, config_service):
#         """Test factory creates SQLite task repository for local storage."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             repo = factory.get_task_repository()

#             assert isinstance(repo, TaskRepository)

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_get_task_repository_remote(self, config_service):
#         """Test factory creates REST API task repository for remote storage."""
#         # Setup remote context
#         config_service.config.contexts.append(
#             Context(name="test-remote", type="remote", source="https://api.example.com")
#         )
#         config_service.config.current_context_name = "test-remote"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             repo = factory.get_task_repository()

#             assert isinstance(repo, TaskRepository)

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_get_project_repository_local(self, config_service):
#         """Test factory creates SQLite project repository for local storage."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             repo = factory.get_project_repository()

#             assert isinstance(repo, ProjectRepository)

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_get_label_repository_local(self, config_service):
#         """Test factory creates SQLite label repository for local storage."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             repo = factory.get_label_repository()

#             assert isinstance(repo, LabelRepository)

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_get_context_repository_local(self, config_service):
#         """Test factory creates SQLite context repository for local storage."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()
#             repo = factory.get_context_repository()

#             assert isinstance(repo, LocationContextRepository)

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_lazy_loading(self, config_service):
#         """Test that repositories are only created when first accessed."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()

#             # Should not have created any repos yet
#             assert factory._task_repo is None
#             assert factory._project_repo is None

#             # Access task repo - should create and cache it
#             repo1 = factory.get_task_repository()
#             repo2 = factory.get_task_repository()

#             # Should return same instance (cached)
#             assert repo1 is repo2

#     @pytest.mark.skip(
#         reason="Legacy Factory pattern deprecated, replaced by Strategy pattern"
#     )
#     def test_storage_type_caching(self, config_service):
#         """Test that storage type is cached after first access."""
#         # Setup local context
#         db_path = Path(tempfile.mkdtemp()) / "test.db"
#         config_service.config.contexts.append(
#             Context(name="test-local", type="local", source=str(db_path))
#         )
#         config_service.config.current_context_name = "test-local"
#         config_service.save_config()

#         with patch(
#             "todopro_cli.models.factory.get_config_service", return_value=config_service
#         ):
#             factory = RepositoryFactory()

#             # Access storage_type multiple times
#             storage1 = factory.storage_type
#             assert storage1 == "local"

#             storage2 = factory.storage_type
#             assert storage2 == "local"
