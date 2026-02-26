"""Unit tests for auth service."""

from todopro_cli.services.auth_service import AuthService


class TestAuthService:
    """Unit tests for AuthService."""

    def test_is_authenticated_with_no_credentials(self, mocker):
        """Test is_authenticated returns False when no credentials are stored."""
        # Patch the function where it is IMPORTED, not where it is defined
        mock_config_manager = mocker.patch(
            "todopro_cli.services.auth_service.get_config_service"
        )
        # Setup the chain: manager instance -> load_credentials -> return None
        mock_config_manager.return_value.load_credentials.return_value = None

        assert AuthService.is_authenticated() is False

    def test_is_authenticated_with_credentials(self, mocker):
        """Test is_authenticated returns True when credentials are stored."""
        mock_config_manager = mocker.patch(
            "todopro_cli.services.auth_service.get_config_service"
        )
        mock_config_manager.return_value.load_credentials.return_value = {
            "token": "dummy-token"
        }

        assert AuthService.is_authenticated() is True
