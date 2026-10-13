"""TodoPro CLI - Professional command-line task management."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("todopro-cli")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"
