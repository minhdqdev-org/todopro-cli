"""Authentication API endpoints."""

from typing import Optional

from todopro_cli.api.client import APIClient


class AuthAPI:
    """Authentication API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def login(self, email: str, password: str) -> dict:
        """Login with email and password."""
        response = await self.client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return response.json()

    async def logout(self) -> None:
        """Logout and revoke tokens."""
        try:
            await self.client.post("/auth/logout")
        except Exception:
            # Logout may fail if token is already invalid
            pass

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token."""
        response = await self.client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        return response.json()

    async def get_profile(self) -> dict:
        """Get current user profile."""
        response = await self.client.get("/auth/me")
        return response.json()

    async def update_profile(self, **kwargs) -> dict:
        """Update user profile."""
        response = await self.client.patch("/auth/me", json=kwargs)
        return response.json()
