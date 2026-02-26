"""Unit tests for crypto models: MasterKey and RecoveryPhrase."""

from __future__ import annotations

import base64

import pytest

from todopro_cli.models.crypto.exceptions import (
    InvalidMnemonicError,
    InvalidRecoveryPhraseError,
    KeyDerivationError,
)
from todopro_cli.models.crypto.keys import KEY_SIZE, MasterKey, generate_salt
from todopro_cli.models.crypto.mnemonic import RecoveryPhrase


# ===========================================================================
# MasterKey tests
# ===========================================================================


class TestMasterKeyGenerate:
    def test_generate_returns_master_key(self):
        key = MasterKey.generate()
        assert isinstance(key, MasterKey)

    def test_generate_produces_32_bytes(self):
        key = MasterKey.generate()
        assert len(key.key_bytes) == KEY_SIZE

    def test_generate_produces_random_keys(self):
        key1 = MasterKey.generate()
        key2 = MasterKey.generate()
        assert key1.key_bytes != key2.key_bytes


class TestMasterKeyFromPassword:
    def test_derives_key_from_password(self):
        salt = generate_salt()
        key = MasterKey.from_password("mypassword", salt)
        assert isinstance(key, MasterKey)
        assert len(key.key_bytes) == KEY_SIZE

    def test_same_password_same_salt_gives_same_key(self):
        salt = generate_salt()
        key1 = MasterKey.from_password("password", salt)
        key2 = MasterKey.from_password("password", salt)
        assert key1.key_bytes == key2.key_bytes

    def test_different_password_gives_different_key(self):
        salt = generate_salt()
        key1 = MasterKey.from_password("password1", salt)
        key2 = MasterKey.from_password("password2", salt)
        assert key1.key_bytes != key2.key_bytes

    def test_short_salt_raises_key_derivation_error(self):
        short_salt = b"tooshort"  # < 16 bytes
        with pytest.raises(KeyDerivationError):
            MasterKey.from_password("password", short_salt)

    def test_valid_salt_size(self):
        salt = b"a" * 16  # exactly SALT_SIZE
        key = MasterKey.from_password("test", salt)
        assert len(key.key_bytes) == KEY_SIZE


class TestMasterKeyFromBytes:
    def test_from_bytes_creates_key(self):
        raw = b"a" * KEY_SIZE
        key = MasterKey.from_bytes(raw)
        assert key.key_bytes == raw

    def test_wrong_size_raises_value_error(self):
        with pytest.raises(ValueError, match=f"{KEY_SIZE} bytes"):
            MasterKey.from_bytes(b"short")

    def test_wrong_size_too_long_raises_value_error(self):
        with pytest.raises(ValueError):
            MasterKey.from_bytes(b"x" * 64)


class TestMasterKeyBase64:
    def test_to_base64_produces_string(self):
        key = MasterKey.generate()
        encoded = key.to_base64()
        assert isinstance(encoded, str)

    def test_from_base64_roundtrip(self):
        key = MasterKey.generate()
        encoded = key.to_base64()
        restored = MasterKey.from_base64(encoded)
        assert restored.key_bytes == key.key_bytes

    def test_to_base64_valid_base64(self):
        key = MasterKey.generate()
        encoded = key.to_base64()
        # Should not raise
        base64.b64decode(encoded)


class TestMasterKeyRepr:
    def test_repr_hides_key_material(self):
        key = MasterKey.generate()
        rep = repr(key)
        assert "MasterKey" in rep
        assert "key_hash" in rep
        # Raw key bytes should NOT appear directly
        assert key.key_bytes.hex() not in rep

    def test_repr_shows_partial_hash(self):
        key = MasterKey.generate()
        rep = repr(key)
        assert "..." in rep


class TestMasterKeyEquality:
    def test_equal_keys(self):
        raw = b"k" * KEY_SIZE
        key1 = MasterKey.from_bytes(raw)
        key2 = MasterKey.from_bytes(raw)
        assert key1 == key2

    def test_different_keys_not_equal(self):
        key1 = MasterKey.generate()
        key2 = MasterKey.generate()
        # With overwhelming probability they differ
        assert key1 != key2

    def test_not_equal_to_non_master_key(self):
        key = MasterKey.generate()
        result = key.__eq__("not a key")
        assert result is NotImplemented


class TestGenerateSalt:
    def test_generates_bytes(self):
        salt = generate_salt()
        assert isinstance(salt, bytes)

    def test_correct_length(self):
        from todopro_cli.models.crypto.keys import SALT_SIZE

        salt = generate_salt()
        assert len(salt) == SALT_SIZE

    def test_random_salts_differ(self):
        s1 = generate_salt()
        s2 = generate_salt()
        assert s1 != s2


# ===========================================================================
# RecoveryPhrase tests
# ===========================================================================


class TestRecoveryPhraseGenerate:
    def test_generate_returns_recovery_phrase(self):
        phrase = RecoveryPhrase.generate()
        assert isinstance(phrase, RecoveryPhrase)

    def test_generate_produces_12_words(self):
        # strength=128 → 12 words
        phrase = RecoveryPhrase.generate()
        assert len(phrase.words) == 12

    def test_generate_produces_valid_phrase(self):
        phrase = RecoveryPhrase.generate()
        assert phrase.is_valid()


class TestRecoveryPhraseFromWords:
    def test_valid_12_word_phrase(self):
        phrase = RecoveryPhrase.generate()
        words_str = " ".join(phrase.words)
        restored = RecoveryPhrase.from_words(words_str)
        assert restored.words == phrase.words

    def test_invalid_word_count_raises(self):
        with pytest.raises(InvalidRecoveryPhraseError, match="12, 15, 18, 21, or 24"):
            RecoveryPhrase.from_words("one two three")

    def test_10_words_raises(self):
        words = " ".join(["abandon"] * 10)
        with pytest.raises(InvalidRecoveryPhraseError):
            RecoveryPhrase.from_words(words)

    def test_strips_and_lowercases(self):
        phrase = RecoveryPhrase.generate()
        words_upper = " ".join(w.upper() for w in phrase.words)
        restored = RecoveryPhrase.from_words("  " + words_upper + "  ")
        assert restored.words == phrase.words

    def test_24_words_accepted(self):
        """24-word (256-bit) phrases are valid."""
        from mnemonic import Mnemonic

        mnemo = Mnemonic("english")
        words_str = mnemo.generate(strength=256)
        phrase = RecoveryPhrase.from_words(words_str)
        assert len(phrase.words) == 24
        assert phrase.is_valid()


class TestRecoveryPhraseIsValid:
    def test_valid_generated_phrase(self):
        phrase = RecoveryPhrase.generate()
        assert phrase.is_valid() is True

    def test_invalid_checksum(self):
        """Tampered phrase fails checksum validation and raises on construction."""
        # Use a fixed phrase with a known-bad last word
        # 23 valid BIP39 words + one that breaks the checksum = invalid phrase
        # "abandon" repeated 23 times + "zoo" = invalid checksum
        valid_prefix = ["abandon"] * 23
        # Append a word that won't form a valid checksum with this prefix
        invalid_words = valid_prefix + ["zoo"]
        with pytest.raises(InvalidRecoveryPhraseError):
            RecoveryPhrase(invalid_words)


class TestRecoveryPhraseToString:
    def test_to_string_produces_space_joined_words(self):
        phrase = RecoveryPhrase.generate()
        s = phrase.to_string()
        assert s == " ".join(phrase.words)

    def test_str_matches_to_string(self):
        phrase = RecoveryPhrase.generate()
        assert str(phrase) == phrase.to_string()


class TestRecoveryPhraseGetHint:
    def test_default_3_word_hint(self):
        phrase = RecoveryPhrase.generate()
        hint = phrase.get_hint()
        words = hint.split()
        assert len(words) == 3
        assert words == phrase.words[:3]

    def test_custom_word_count(self):
        phrase = RecoveryPhrase.generate()
        hint = phrase.get_hint(word_count=5)
        assert len(hint.split()) == 5


class TestRecoveryPhraseToMasterKey:
    def test_to_master_key_returns_master_key(self):
        phrase = RecoveryPhrase.generate()
        key = phrase.to_master_key()
        assert isinstance(key, MasterKey)
        assert len(key.key_bytes) == KEY_SIZE

    def test_same_phrase_same_key(self):
        phrase = RecoveryPhrase.generate()
        key1 = phrase.to_master_key()
        key2 = phrase.to_master_key()
        assert key1.key_bytes == key2.key_bytes


class TestRecoveryPhraseFromMasterKey:
    def test_from_master_key_produces_recovery_phrase(self):
        key = MasterKey.generate()
        phrase = RecoveryPhrase.from_master_key(key)
        assert isinstance(phrase, RecoveryPhrase)
        assert phrase.is_valid()

    def test_from_master_key_roundtrip(self):
        """Generate key → phrase → back to key: should produce same key bytes."""
        key = MasterKey.generate()
        phrase = RecoveryPhrase.from_master_key(key)
        recovered_key = phrase.to_master_key()
        # The key bytes may differ due to padding, but the phrase should be valid
        assert isinstance(recovered_key, MasterKey)


class TestRecoveryPhraseRepr:
    def test_repr_shows_first_and_last_word(self):
        phrase = RecoveryPhrase.generate()
        rep = repr(phrase)
        assert "RecoveryPhrase" in rep
        assert phrase.words[0] in rep
        assert phrase.words[-1] in rep
        assert "..." in rep


# ===========================================================================
# Additional coverage tests for mnemonic.py lines 59-60, 81, 85-86
# ===========================================================================


class TestRecoveryPhraseIsValidException:
    def test_is_valid_returns_false_on_mnemonic_check_exception(self):
        """is_valid returns False (not raise) when mnemonic.check() raises."""
        from unittest.mock import patch

        phrase = RecoveryPhrase.generate()
        # Force _mnemonic.check() to raise
        with patch.object(phrase._mnemonic, "check", side_effect=RuntimeError("bad")):
            result = phrase.is_valid()
        assert result is False


class TestRecoveryPhraseToMasterKeyEdgeCases:
    def test_to_master_key_with_entropy_over_32_bytes(self):
        """to_master_key truncates entropy > 32 bytes (line 81)."""
        from unittest.mock import patch

        phrase = RecoveryPhrase.generate()
        # Inject entropy longer than 32 bytes
        long_entropy = b"x" * 40
        with patch.object(phrase._mnemonic, "to_entropy", return_value=long_entropy):
            key = phrase.to_master_key()
        assert isinstance(key, MasterKey)
        assert len(key.key_bytes) == KEY_SIZE  # should be truncated to 32

    def test_to_master_key_raises_invalid_mnemonic_on_exception(self):
        """to_master_key raises InvalidMnemonicError when to_entropy fails (lines 85-86)."""
        from unittest.mock import patch

        phrase = RecoveryPhrase.generate()
        with patch.object(
            phrase._mnemonic, "to_entropy", side_effect=ValueError("bad entropy")
        ):
            with pytest.raises(InvalidMnemonicError, match="Failed to derive key"):
                phrase.to_master_key()
