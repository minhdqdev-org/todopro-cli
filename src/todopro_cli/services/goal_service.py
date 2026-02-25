"""Goal management service."""

from todopro_cli.services.config_service import get_config_service


class GoldService:
    def __init__(self):
        pass

    def reset_goals(self):
        defaults = {
            "daily_sessions": 8,
            "daily_minutes": 200,
            "weekly_sessions": 40,
            "weekly_minutes": 1000,
            "streak_target": 30,
        }
        get_config_service().save_config()


def get_goal_service() -> GoldService:
    return GoldService()
