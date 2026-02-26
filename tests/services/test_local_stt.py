"""Tests for local STT (speech-to-text) service.

faster-whisper is not installed in the test environment.  All tests either
exercise the graceful-degradation paths (WHISPER_AVAILABLE=False) or inject a
fully-mocked faster_whisper module into sys.modules before calling the code
under test.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

import todopro_cli.services.audio.local_stt as stt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _WhisperFlag:
    """Context manager that temporarily overrides stt.WHISPER_AVAILABLE."""

    def __init__(self, available: bool) -> None:
        self._value = available
        self._original = stt.WHISPER_AVAILABLE

    def __enter__(self):
        stt.WHISPER_AVAILABLE = self._value
        return self

    def __exit__(self, *_):
        stt.WHISPER_AVAILABLE = self._original


def _make_fake_faster_whisper(segments=None, model_info=None):
    """Build a minimal faster_whisper stub.

    Returns (fake_module, mock_model_instance).
    """
    if segments is None:
        segments = []

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (segments, model_info or MagicMock())

    mock_whisper_class = MagicMock(return_value=mock_model)

    fake_fw = MagicMock()
    fake_fw.WhisperModel = mock_whisper_class

    return fake_fw, mock_model


# ---------------------------------------------------------------------------
# check_whisper
# ---------------------------------------------------------------------------


def test_check_whisper_not_available():
    """Returns (False, msg containing 'faster-whisper') when not installed."""
    with _WhisperFlag(available=False):
        ok, msg = stt.check_whisper()

    assert ok is False
    assert "faster-whisper" in msg


def test_check_whisper_available():
    """Returns (True, '') when faster-whisper is reported as available."""
    with _WhisperFlag(available=True):
        ok, msg = stt.check_whisper()

    assert ok is True
    assert msg == ""


# ---------------------------------------------------------------------------
# transcribe_audio — failure paths
# ---------------------------------------------------------------------------


def test_transcribe_audio_raises_when_not_available():
    """Raises RuntimeError immediately when WHISPER_AVAILABLE is False."""
    with _WhisperFlag(available=False):
        with pytest.raises(RuntimeError, match="faster-whisper not installed"):
            stt.transcribe_audio(b"fake audio data")


# ---------------------------------------------------------------------------
# transcribe_audio — happy paths (fully mocked)
# ---------------------------------------------------------------------------


def _transcribe_with_stub(audio_data: bytes, fake_fw, **kwargs) -> str:
    """Helper: inject fake_fw into sys.modules and call transcribe_audio."""
    sys.modules["faster_whisper"] = fake_fw
    try:
        return stt.transcribe_audio(audio_data, **kwargs)
    finally:
        sys.modules.pop("faster_whisper", None)


def test_transcribe_audio_with_auto_language():
    """Transcribes correctly when language='auto' (None is passed to model)."""
    mock_seg = MagicMock()
    mock_seg.text = "  Hello world  "

    fake_fw, mock_model = _make_fake_faster_whisper(segments=[mock_seg])

    with _WhisperFlag(available=True):
        result = _transcribe_with_stub(
            b"fake audio", fake_fw, model_size="base", language="auto"
        )

    assert "Hello world" in result

    # Verify transcribe was called with language=None for "auto"
    _, call_kwargs = mock_model.transcribe.call_args
    assert call_kwargs.get("language") is None


def test_transcribe_audio_with_specific_language():
    """Transcribes correctly when a specific BCP-47 language code is given."""
    mock_seg = MagicMock()
    mock_seg.text = "Bonjour monde"

    fake_fw, mock_model = _make_fake_faster_whisper(segments=[mock_seg])

    with _WhisperFlag(available=True):
        result = _transcribe_with_stub(
            b"fake audio", fake_fw, model_size="base", language="fr"
        )

    assert "Bonjour monde" in result

    _, call_kwargs = mock_model.transcribe.call_args
    assert call_kwargs.get("language") == "fr"


def test_transcribe_audio_joins_multiple_segments():
    """Multiple segments are joined with spaces."""
    segs = [MagicMock(text=" Hello "), MagicMock(text=" world ")]
    fake_fw, _ = _make_fake_faster_whisper(segments=segs)

    with _WhisperFlag(available=True):
        result = _transcribe_with_stub(b"fake audio", fake_fw)

    # Both segment texts should appear in the joined result
    assert "Hello" in result
    assert "world" in result


def test_transcribe_audio_empty_segments():
    """Returns an empty string when the model returns no segments."""
    fake_fw, _ = _make_fake_faster_whisper(segments=[])

    with _WhisperFlag(available=True):
        result = _transcribe_with_stub(b"fake audio", fake_fw)

    assert result == ""


def test_transcribe_audio_uses_requested_model_size():
    """WhisperModel is instantiated with the requested model_size."""
    fake_fw, _ = _make_fake_faster_whisper(segments=[])

    with _WhisperFlag(available=True):
        _transcribe_with_stub(b"fake audio", fake_fw, model_size="tiny")

    # The first positional argument to WhisperModel should be the model size
    call_args = fake_fw.WhisperModel.call_args
    assert call_args[0][0] == "tiny"


def test_transcribe_audio_model_uses_cpu_int8():
    """WhisperModel is always configured with device='cpu' and compute_type='int8'."""
    fake_fw, _ = _make_fake_faster_whisper(segments=[])

    with _WhisperFlag(available=True):
        _transcribe_with_stub(b"fake audio", fake_fw)

    call_kwargs = fake_fw.WhisperModel.call_args[1]
    assert call_kwargs.get("device") == "cpu"
    assert call_kwargs.get("compute_type") == "int8"


# ---------------------------------------------------------------------------
# Module-level import flag (covered via reload)
# ---------------------------------------------------------------------------


def test_whisper_available_flag_set_when_importable():
    """WHISPER_AVAILABLE becomes True when faster-whisper is importable.

    Covers line 6 (the ``WHISPER_AVAILABLE = True`` assignment inside the
    module-level try/import block).
    """
    import importlib

    fake_fw = MagicMock()
    sys.modules["faster_whisper"] = fake_fw
    try:
        importlib.reload(stt)
        assert stt.WHISPER_AVAILABLE is True
    finally:
        sys.modules.pop("faster_whisper", None)
        importlib.reload(stt)
