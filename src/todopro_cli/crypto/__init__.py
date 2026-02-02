"""Crypto module for TodoPro end-to-end encryption.

This module provides client-side encryption utilities for protecting user data.
"""

from todopro_cli.crypto.cipher import EncryptedData, decrypt, encrypt
from todopro_cli.crypto.exceptions import (
    DecryptionError,
    InvalidMnemonicError,
    InvalidRecoveryPhraseError,
    KeyDerivationError,
    TodoProCryptoError,
)
from todopro_cli.crypto.keys import MasterKey
from todopro_cli.crypto.manager import EncryptionManager
from todopro_cli.crypto.mnemonic import RecoveryPhrase

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
