"""Goal management service."""

from todopro_cli.services.config_service import get_config_service


class GoldService:
    def __init__(self):
        pass

    def reset_goals(self):
        get_config_service().save_config()


def get_goal_service() -> GoldService:
    return GoldService()
