"""Custom exceptions for TodoPro Crypto."""


class TodoProCryptoError(Exception):
    """Base exception for all TodoPro Crypto errors."""

    pass


class DecryptionError(TodoProCryptoError):
    """Raised when decryption fails (wrong key, corrupted data, or tampered data)."""

    pass


class KeyDerivationError(TodoProCryptoError):
    """Raised when key derivation fails."""

    pass


class InvalidMnemonicError(TodoProCryptoError):
    """Raised when BIP39 mnemonic validation fails."""

    pass


class InvalidRecoveryPhraseError(TodoProCryptoError):
    """Raised when recovery phrase is invalid or cannot restore key."""

    pass
