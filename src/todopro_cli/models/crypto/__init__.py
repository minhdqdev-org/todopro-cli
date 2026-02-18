"""Crypto module for TodoPro end-to-end encryption.

This module provides client-side encryption utilities for protecting user data.
"""

from .cipher import EncryptedData, decrypt, encrypt
from .exceptions import (
    DecryptionError,
    InvalidMnemonicError,
    InvalidRecoveryPhraseError,
    KeyDerivationError,
    TodoProCryptoError,
)
from .keys import MasterKey
from .manager import EncryptionManager
from .mnemonic import RecoveryPhrase

__all__ = [
    "EncryptionManager",
    "MasterKey",
    "RecoveryPhrase",
    "EncryptedData",
    "encrypt",
    "decrypt",
    "TodoProCryptoError",
    "DecryptionError",
    "KeyDerivationError",
    "InvalidMnemonicError",
    "InvalidRecoveryPhraseError",
]
