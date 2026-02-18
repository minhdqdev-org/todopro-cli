"""Task cache utilities (backward compatibility wrappers)."""


def get_suffix_mapping() -> dict:
    """Get suffix mapping for task operations."""
    from todopro_cli.services.cache_service import get_suffix_mapping as _get

    return _get()


def get_background_cache():
    """Get background task cache."""
    from todopro_cli.services.cache_service import get_background_cache as _get

    return _get()
