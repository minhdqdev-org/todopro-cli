"""API client for TodoPro."""

import asyncio
import os
from typing import Any

import httpx

from todopro_cli.services.config_service import get_config_service
from todopro_cli.utils.ui.console import get_console
from todopro_cli.utils.update_checker import DEFAULT_BACKEND_URL, get_backend_url


class APIClient:
    """HTTP client for TodoPro API."""

    def __init__(self):
        self.config_manager = get_config_service()
        self.config = self.config_manager.config
        self.base_url = self._resolve_base_url()
        self.timeout = self.config.api.timeout
        self._client: httpx.AsyncClient | None = None

    def _resolve_base_url(self) -> str:
        """Resolve the API base URL.

        Priority:
          1. ``TODOPRO_BACKEND_URL`` env var (dev/testing override)
          2. the active **remote** context's ``source`` (the normal way users
             select an environment via ``context use`` / ``context create``)
          3. ``api.endpoint`` if explicitly changed from the default
          4. cache / PyPI / hard-coded default (``get_backend_url``)
        """
        env_url = os.getenv("TODOPRO_BACKEND_URL")
        if env_url:
            return env_url.rstrip("/")
        try:
            ctx = self.config_manager.get_current_context()
            if ctx is not None and ctx.type == "remote" and isinstance(ctx.source, str):
                return ctx.source.rstrip("/")
        except Exception:
            pass
        endpoint = getattr(self.config.api, "endpoint", None)
        if isinstance(endpoint, str) and endpoint.rstrip(
            "/"
        ) != DEFAULT_BACKEND_URL.rstrip("/"):
            return endpoint.rstrip("/")
        return get_backend_url()

    async def __aenter__(self) -> "APIClient":
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the async context manager and ensure the client is closed."""
        await self.close()

    def _get_headers(self, skip_auth: bool = False) -> dict[str, str]:
        """Get HTTP headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Identify this install so the backend's real-time layer can skip
        # echoing a change back to the device that made it.
        client_id = getattr(self.config_manager.config, "client_id", None)
        if client_id:
            headers["X-Client-Id"] = client_id

        # Add authentication token if available and not skipped
        if not skip_auth:
            # Try to load context-specific credentials first
            current_context = self.config_manager.get_current_context()
            if current_context:
                credentials = self.config_manager.load_context_credentials(
                    current_context.name
                )
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
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        retry: int | None = None,
        skip_auth: bool = False,
    ) -> httpx.Response:
        """Make an HTTP request to the API."""
        if retry is None:
            retry = self.config.api.retry

        client = await self._get_client(skip_auth=skip_auth)
        url = f"{path}" if path.startswith("/") else f"/{path}"

        last_exception: Exception | None = None
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
                # Knox tokens are validated server-side and auto-refresh on use;
                # there is no client-side refresh endpoint. A 401 therefore means
                # the stored token is expired, revoked, or otherwise invalid, and
                # the user must authenticate again.
                if e.response.status_code == 401 and not skip_auth:
                    rich_console = get_console()
                    rich_console.print(
                        "\n[yellow]⚠ Your session has expired or is no longer valid.[/yellow]"
                    )
                    rich_console.print(
                        "[dim]Please login again:[/dim] [cyan]todopro login[/cyan]\n"
                    )
                    raise

                # Don't retry other client errors (4xx)
                if 400 <= e.response.status_code < 500:
                    raise
                last_exception = e
            except httpx.RequestError as e:
                last_exception = e

            if attempt < retry:
                # Wait before retry (simple exponential backoff)

                await asyncio.sleep(2**attempt)

        # All retries failed
        if last_exception:
            raise last_exception
        raise RuntimeError("Request failed after all retries")

    async def get(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", path, params=params)

    async def post(
        self, path: str, *, json: dict[str, Any] | None = None, skip_auth: bool = False
    ) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", path, json=json, skip_auth=skip_auth)

    async def put(
        self, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", path, json=json)

    async def patch(
        self, path: str, *, json: dict[str, Any] | None = None
    ) -> httpx.Response:
        """Make a PATCH request."""
        return await self.request("PATCH", path, json=json)

    async def delete(self, path: str) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", path)


def get_client() -> APIClient:
    """Get an API client instance."""
    return APIClient()
