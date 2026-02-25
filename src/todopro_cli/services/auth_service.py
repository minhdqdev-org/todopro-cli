"""Service for handling authentication-related operations."""


class AuthService:
    """Service for handling authentication-related operations."""

    @staticmethod
    def is_authenticated() -> bool:
        """Check if the user is authenticated."""
        credentials = get_config_service().load_credentials()
        return credentials is not None
