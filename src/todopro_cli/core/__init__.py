"""Core package re-exports for backward compatibility.

This package exists to maintain backward compatibility with imports from
todopro_cli.core during the architecture refactoring. The actual implementations
have been moved to their proper locations:

- Factory pattern → todopro_cli.models.factory
- Repository interfaces → todopro_cli.repositories.repository

This package will be deprecated in v3.0. Please migrate to the new import paths.
"""
