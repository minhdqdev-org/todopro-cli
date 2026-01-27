"""API client for TodoPro."""

from typing import Any, Optional

import httpx
from rich.console import Console

from todopro_cli.config import get_config_manager

console = Console()


class APIClient:
    """HTTP client for TodoPro API."""

    def __init__(self, profile: str = "default"):
        self.config_manager = get_config_manager(profile)
        self.config = self.config_manager.config
        self.base_url = self.config.api.endpoint.rstrip("/")
        self.timeout = self.config.api.timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_headers(self, skip_auth: bool = False) -> dict[str, str]:
        """Get HTTP headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Add authentication token if available and not skipped
        if not skip_auth:
            # Try to load context-specific credentials first
            current_context = self.config_manager.get_current_context()
            if current_context:
                credentials = self.config_manager.load_context_credentials(current_context.name)
            else:
                credentials = None

            # Fall back to default credentials if context credentials not found
            if not credentials:
                credentials = self.config_manager.load_credentials()

            if credentials and "token" in credentials:
                headers["Authorization"] = f"Bearer {credentials['token']}"

        return headers

    async def _get_client(self, skip_auth: bool = False) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                follow_redirects=True,
            )
        # Always update headers to include latest auth token
        self._client.headers.update(self._get_headers(skip_auth=skip_auth))
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        retry: Optional[int] = None,
        skip_auth: bool = False,
    ) -> httpx.Response:
        """Make an HTTP request to the API."""
        if retry is None:
            retry = self.config.api.retry

        client = await self._get_client(skip_auth=skip_auth)
        url = f"{path}" if path.startswith("/") else f"/{path}"

        last_exception: Optional[Exception] = None
        for attempt in range(retry + 1):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json,
                    params=params,
                )
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise
                last_exception = e
            except httpx.RequestError as e:
                last_exception = e

            if attempt < retry:
                # Wait before retry (simple exponential backoff)
                import asyncio

                await asyncio.sleep(2**attempt)

        # All retries failed
        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed after all retries")

    async def get(
        self, path: str, *, params: Optional[dict[str, Any]] = None
    ) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", path, params=params)

    async def post(
        self, path: str, *, json: Optional[dict[str, Any]] = None, skip_auth: bool = False
    ) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", path, json=json, skip_auth=skip_auth)

    async def put(
        self, path: str, *, json: Optional[dict[str, Any]] = None
    ) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", path, json=json)

    async def patch(
        self, path: str, *, json: Optional[dict[str, Any]] = None
    ) -> httpx.Response:
        """Make a PATCH request."""
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", path)


def get_client(profile: str = "default") -> APIClient:
    """Get an API client instance."""
    return APIClient(profile)
