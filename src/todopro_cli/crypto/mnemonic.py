"""BIP39 mnemonic (recovery phrase) generation and validation."""

from typing import List

from mnemonic import Mnemonic

from todopro_cli.crypto.exceptions import InvalidMnemonicError, InvalidRecoveryPhraseError

LANGUAGE = "english"
WORD_COUNT = 12


class RecoveryPhrase:
    """Represents a BIP39 recovery phrase for master key backup."""

    def __init__(self, words: List[str]):
        """Initialize with recovery phrase words."""
        self.words = words
        self._mnemonic = Mnemonic(LANGUAGE)

        if not self.is_valid():
            raise InvalidRecoveryPhraseError("Invalid recovery phrase")

    @classmethod
    def generate(cls) -> "RecoveryPhrase":
        """Generate a new random recovery phrase."""
        mnemonic = Mnemonic(LANGUAGE)
        words_str = mnemonic.generate(strength=128)
        words = words_str.split()
        return cls(words)

    @classmethod
    def from_words(cls, words_str: str) -> "RecoveryPhrase":
        """Create recovery phrase from space-separated words."""
        words = words_str.strip().lower().split()

        if len(words) != WORD_COUNT:
            raise InvalidRecoveryPhraseError(
                f"Recovery phrase must have exactly {WORD_COUNT} words, got {len(words)}"
            )

        return cls(words)

    @classmethod
    def from_master_key(cls, master_key: "MasterKey") -> "RecoveryPhrase":
        """Generate recovery phrase from existing master key."""
        from todopro_cli.crypto.keys import MasterKey

        mnemonic = Mnemonic(LANGUAGE)
        words_str = mnemonic.to_mnemonic(master_key.key_bytes)
        words = words_str.split()
        return cls(words)

    def is_valid(self) -> bool:
        """Validate recovery phrase checksum."""
        try:
            words_str = " ".join(self.words)
            return self._mnemonic.check(words_str)
        except Exception:
            return False

    def to_string(self) -> str:
        """Convert to space-separated string."""
        return " ".join(self.words)

    def to_master_key(self) -> "MasterKey":
        """Derive master key from recovery phrase."""
        from crypto.keys import MasterKey

        words_str = " ".join(self.words)

        try:
            entropy = self._mnemonic.to_entropy(words_str)

            # Pad or truncate to 32 bytes
            if len(entropy) < 32:
                entropy = entropy + b"\x00" * (32 - len(entropy))
            elif len(entropy) > 32:
                entropy = entropy[:32]

            return MasterKey.from_bytes(entropy)

        except Exception as e:
            raise InvalidMnemonicError(f"Failed to derive key from mnemonic: {str(e)}") from e

    def get_hint(self, word_count: int = 3) -> str:
        """Get first N words as a hint."""
        return " ".join(self.words[:word_count])

    def __str__(self) -> str:
        """String representation."""
        return self.to_string()

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        first_word = self.words[0]
        last_word = self.words[-1]
        return f"RecoveryPhrase('{first_word} ... {last_word}')"
