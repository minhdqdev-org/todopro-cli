"""Service for handling authentication-related operations."""

from todopro_cli.services.context_manager import get_context_manager


class AuthService:
    """Service for handling authentication-related operations."""

    @staticmethod
    def is_authenticated() -> bool:
        """Check if the user is authenticated."""
        credentials = get_context_manager().load_credentials()
        return credentials is not None
