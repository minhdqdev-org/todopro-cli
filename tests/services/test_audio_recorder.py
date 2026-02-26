"""Tests for audio recorder service.

All audio dependencies (sounddevice, numpy) are mocked because they are not
installed in the test environment — the module itself is designed to degrade
gracefully when they are absent.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

import todopro_cli.services.audio.recorder as recorder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _BoolFlags:
    """Context manager that temporarily patches SOUNDDEVICE_AVAILABLE / NUMPY_AVAILABLE."""

    def __init__(self, sd: bool, np: bool) -> None:
        self._sd = sd
        self._np = np
        self._orig_sd = recorder.SOUNDDEVICE_AVAILABLE
        self._orig_np = recorder.NUMPY_AVAILABLE

    def __enter__(self):
        recorder.SOUNDDEVICE_AVAILABLE = self._sd
        recorder.NUMPY_AVAILABLE = self._np
        return self

    def __exit__(self, *_):
        recorder.SOUNDDEVICE_AVAILABLE = self._orig_sd
        recorder.NUMPY_AVAILABLE = self._orig_np


# ---------------------------------------------------------------------------
# check_dependencies
# ---------------------------------------------------------------------------


def test_check_dependencies_sounddevice_missing():
    """Returns (False, msg) when sounddevice is not available."""
    with _BoolFlags(sd=False, np=True):
        ok, msg = recorder.check_dependencies()

    assert ok is False
    assert "sounddevice" in msg


def test_check_dependencies_numpy_missing():
    """Returns (False, msg) when numpy is not available."""
    with _BoolFlags(sd=True, np=False):
        ok, msg = recorder.check_dependencies()

    assert ok is False
    assert "numpy" in msg


def test_check_dependencies_all_available():
    """Returns (True, '') when both deps are available."""
    with _BoolFlags(sd=True, np=True):
        ok, msg = recorder.check_dependencies()

    assert ok is True
    assert msg == ""


# ---------------------------------------------------------------------------
# record_audio — failure path
# ---------------------------------------------------------------------------


def test_record_audio_raises_when_sounddevice_missing():
    """Raises RuntimeError when sounddevice is not available."""
    with _BoolFlags(sd=False, np=True):
        with pytest.raises(RuntimeError, match="Audio dependencies not available"):
            recorder.record_audio()


def test_record_audio_raises_when_numpy_missing():
    """Raises RuntimeError when numpy is not available."""
    with _BoolFlags(sd=True, np=False):
        with pytest.raises(RuntimeError, match="Audio dependencies not available"):
            recorder.record_audio()


def test_record_audio_raises_when_both_missing():
    """Raises RuntimeError when both deps are missing."""
    with _BoolFlags(sd=False, np=False):
        with pytest.raises(RuntimeError, match="Audio dependencies not available"):
            recorder.record_audio()


# ---------------------------------------------------------------------------
# record_audio — happy path (fully mocked)
# ---------------------------------------------------------------------------


def test_record_audio_returns_wav_bytes():
    """record_audio returns valid WAV bytes when deps are mocked."""
    # Build a mock recording whose tobytes() yields 16-bit PCM silence
    mock_recording = MagicMock()
    # 1 second @ 16 000 Hz, mono, 16-bit  →  32 000 bytes of raw PCM
    mock_recording.tobytes.return_value = b"\x00\x00" * 16_000

    mock_sd = MagicMock()
    mock_sd.rec.return_value = mock_recording
    mock_sd.wait = MagicMock()

    # numpy is unused at runtime (only imported), so a plain MagicMock suffices
    mock_np = MagicMock()

    with _BoolFlags(sd=True, np=True):
        # Inject the sounddevice stub at module level (create=True because the
        # real 'sd' name never existed when sounddevice is absent)
        with patch.object(recorder, "sd", mock_sd, create=True):
            sys.modules.setdefault("numpy", mock_np)  # satisfy the inner import
            try:
                result = recorder.record_audio(
                    duration_seconds=1, sample_rate=16_000, channels=1
                )
            finally:
                # Only remove the stub if we inserted it
                if sys.modules.get("numpy") is mock_np:
                    del sys.modules["numpy"]

    assert isinstance(result, bytes)
    # A well-formed WAV file always begins with the RIFF header
    assert result[:4] == b"RIFF"
    assert result[8:12] == b"WAVE"


def test_record_audio_calls_sd_rec_with_correct_args():
    """sd.rec is called with the expected frame count and parameters."""
    mock_recording = MagicMock()
    mock_recording.tobytes.return_value = b"\x00\x00" * 8_000

    mock_sd = MagicMock()
    mock_sd.rec.return_value = mock_recording
    mock_np = MagicMock()

    with _BoolFlags(sd=True, np=True):
        with patch.object(recorder, "sd", mock_sd, create=True):
            sys.modules.setdefault("numpy", mock_np)
            try:
                recorder.record_audio(duration_seconds=1, sample_rate=8_000, channels=1)
            finally:
                if sys.modules.get("numpy") is mock_np:
                    del sys.modules["numpy"]

    mock_sd.rec.assert_called_once_with(
        8_000,  # frames = duration * sample_rate
        samplerate=8_000,
        channels=1,
        dtype="int16",
    )
    mock_sd.wait.assert_called_once()


# ---------------------------------------------------------------------------
# Module-level import flags (covered via reload)
# ---------------------------------------------------------------------------


def test_sounddevice_and_numpy_available_flags_set_when_importable():
    """SOUNDDEVICE_AVAILABLE and NUMPY_AVAILABLE become True when libs importable.

    Covers lines 8 and 14 (the ``Flag = True`` assignments inside the
    module-level try/import blocks).
    """
    import importlib

    fake_sd = MagicMock()
    fake_np = MagicMock()

    sys.modules["sounddevice"] = fake_sd
    sys.modules["numpy"] = fake_np
    try:
        importlib.reload(recorder)
        assert recorder.SOUNDDEVICE_AVAILABLE is True
        assert recorder.NUMPY_AVAILABLE is True
    finally:
        # Remove the stubs and reload to restore the original False state
        sys.modules.pop("sounddevice", None)
        sys.modules.pop("numpy", None)
        importlib.reload(recorder)
