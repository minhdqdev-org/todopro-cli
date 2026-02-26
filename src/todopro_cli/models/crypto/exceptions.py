"""Custom exceptions for TodoPro Crypto."""


class TodoProCryptoError(Exception):
    """Base exception for all TodoPro Crypto errors."""


class DecryptionError(TodoProCryptoError):
    """Raised when decryption fails (wrong key, corrupted data, or tampered data)."""


class KeyDerivationError(TodoProCryptoError):
    """Raised when key derivation fails."""


class InvalidMnemonicError(TodoProCryptoError):
    """Raised when BIP39 mnemonic validation fails."""


class InvalidRecoveryPhraseError(TodoProCryptoError):
    """Raised when recovery phrase is invalid or cannot restore key."""
