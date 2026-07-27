"""Goals and achievements API endpoints.

Backs the `remote` context for `todopro goals` / `todopro achievements`. Both
commands used to be purely local (config file + the focus-session SQLite DB), so
targets and badges were per-device and lost on reinstall. Against a remote
context they now read the server, which is the source of truth.
"""

from typing import Any

from todopro_cli.services.api.client import APIClient


class GoalsAPI:
    """Goals API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_goals(self, include_archived: bool = False) -> list[dict[str, Any]]:
        params = {"include_archived": "true"} if include_archived else None
        response = await self.client.get("/v1/goals", params=params)
        return response.json()

    async def create_goal(
        self, period: str, target_value: int, goal_type: str = "tasks_completed"
    ) -> dict[str, Any]:
        response = await self.client.post(
            "/v1/goals",
            json={
                "goal_type": goal_type,
                "period": period,
                "target_value": target_value,
            },
        )
        return response.json()

    async def update_goal(self, goal_id: str, **updates: Any) -> dict[str, Any]:
        response = await self.client.patch(f"/v1/goals/{goal_id}", json=updates)
        return response.json()

    async def delete_goal(self, goal_id: str) -> None:
        """Archives the goal server-side — the progress history is retained."""
        await self.client.delete(f"/v1/goals/{goal_id}")

    async def get_progress(self) -> dict[str, Any]:
        response = await self.client.get("/v1/goals/progress")
        return response.json()

    async def get_history(self, goal_id: str, limit: int = 30) -> dict[str, Any]:
        response = await self.client.get(
            f"/v1/goals/{goal_id}/history", params={"limit": str(limit)}
        )
        return response.json()


class AchievementsAPI:
    """Achievements API client."""

    def __init__(self, client: APIClient):
        self.client = client

    async def list_achievements(self) -> dict[str, Any]:
        """The whole catalogue, each entry flagged with `earned`."""
        response = await self.client.get("/v1/achievements")
        return response.json()

    async def list_earned(self) -> dict[str, Any]:
        response = await self.client.get("/v1/achievements/earned")
        return response.json()
