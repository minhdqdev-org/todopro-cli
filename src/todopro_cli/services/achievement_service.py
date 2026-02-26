class AchievementService:
    def __init__(self, context_repository):
        self.context_repository = context_repository

    async def check_achievement(self, latitude: float, longitude: float) -> bool:
        """Check if any achievements are available at the given location."""
        available_contexts = await self.context_repository.get_available(
            latitude, longitude
        )
        return len(available_contexts) > 0


def get_achievement_service():
    from todopro_cli.services.config_service import (
        get_storage_strategy_context,
    )

    storage_strategy_context = get_storage_strategy_context()
    return AchievementService(storage_strategy_context.achievement_repository)
