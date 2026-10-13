"""Authentication API endpoints."""

import contextlib

import httpx

from todopro_cli.services.api.client import APIClient

SIGNUP_WEB_URL = "https://app.todopro.xyz"


class SignupCaptchaRequired(Exception):
    """The server demands a CAPTCHA token that the CLI cannot produce."""


def _is_captcha_failure(response: httpx.Response) -> bool:
    """Is this 400 the Turnstile gate (`code: captcha_failed`)?"""
    try:
        body = response.json()
    except Exception:
        return False
    if not isinstance(body, dict):
        return False
    envelope = body.get("error")
    code = envelope.get("code") if isinstance(envelope, dict) else body.get("code")
    return code == "captcha_failed"


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
        with contextlib.suppress(Exception):
            await self.client.post("/v1/auth/logout")

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
        try:
            response = await self.client.post(
                "/v1/auth/register",
                json={"email": email, "password": password},
                skip_auth=True,
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400 and _is_captcha_failure(e.response):
                raise SignupCaptchaRequired() from e
            raise
        return response.json()

    async def resend_verification(self, email: str | None = None) -> dict:
        """S-80: request a fresh email-confirmation link.

        ``skip_auth`` when an address is supplied, so this works from a machine
        that is walled out or not signed in at all. With no address the backend
        uses the session's own. Either way the response is deliberately generic
        — it never reveals whether an account exists or is already confirmed.
        """
        response = await self.client.post(
            "/v1/auth/resend-verification",
            json={"email": email} if email else {},
            skip_auth=email is not None,
        )
        return response.json()
