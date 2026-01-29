"""Authentication API endpoints."""

from todopro_cli.api.client import APIClient


class AuthAPI:
    """Authentication API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def login(self, email: str, password: str) -> dict:
        """Login with email and password."""
        response = await self.client.post(
            "/v1/auth/login",
            json={"email": email, "password": password},
            skip_auth=True,
        )
        return response.json()

    async def logout(self) -> None:
        """Logout and revoke tokens."""
        try:
            await self.client.post("/v1/auth/logout")
        except Exception:
            # Logout may fail if token is already invalid
            pass

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token."""
        response = await self.client.post(
            "/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        return response.json()

    async def get_profile(self) -> dict:
        """Get current user profile."""
        response = await self.client.get("/v1/auth/profile")
        return response.json()

    async def update_profile(self, **kwargs) -> dict:
        """Update user profile."""
        response = await self.client.patch("/v1/auth/profile", json=kwargs)
        return response.json()

    async def signup(self, email: str, password: str) -> dict:
        """Create a new account."""
        response = await self.client.post(
            "/v1/auth/register",
            json={"email": email, "password": password},
            skip_auth=True,
        )
        return response.json()
