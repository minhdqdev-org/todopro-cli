"""Secure key storage for CLI."""

import os
from pathlib import Path
from typing import Optional


class KeyStorage:
    """Store encrypted master key in config file."""

    def __init__(self, config_dir: Path):
        """
        Initialize key storage.

        Args:
            config_dir: Directory to store key file
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.key_file = self.config_dir / ".todopro_key"

    def save_key(self, key_base64: str) -> None:
        """
        Save master key to file with restricted permissions.

        Args:
            key_base64: Base64-encoded master key
        """
        self.key_file.write_text(key_base64)
        # Set file permissions to read/write for owner only (0o600)
        os.chmod(self.key_file, 0o600)

    def load_key(self) -> str:
        """
        Load master key from file.

        Returns:
            Base64-encoded master key

        Raises:
            FileNotFoundError: If key file doesn't exist
        """
        if not self.key_file.exists():
            raise FileNotFoundError("No encryption key found. Run 'todopro encryption setup' first.")
        return self.key_file.read_text().strip()

    def has_key(self) -> bool:
        """Check if key file exists."""
        return self.key_file.exists()

    def delete_key(self) -> None:
        """Delete stored key file."""
        if self.key_file.exists():
            self.key_file.unlink()

    def get_key_path(self) -> Optional[Path]:
        """Get path to key file if it exists."""
        return self.key_file if self.has_key() else None
