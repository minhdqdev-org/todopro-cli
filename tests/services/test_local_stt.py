"""Tests for local STT (speech-to-text) service."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock


import todopro_cli.services.audio.local_stt as stt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
# transcribe_audio — failure paths
# ---------------------------------------------------------------------------


def test_transcribe_audio_raises_when_not_available():
    """Raises RuntimeError immediately when WHISPER_AVAILABLE is False."""
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

    result = _transcribe_with_stub(b"fake audio", fake_fw)

    # Both segment texts should appear in the joined result
    assert "Hello" in result
    assert "world" in result


def test_transcribe_audio_empty_segments():
    """Returns an empty string when the model returns no segments."""
    fake_fw, _ = _make_fake_faster_whisper(segments=[])

    result = _transcribe_with_stub(b"fake audio", fake_fw)

    assert result == ""


def test_transcribe_audio_uses_requested_model_size():
    """WhisperModel is instantiated with the requested model_size."""
    fake_fw, _ = _make_fake_faster_whisper(segments=[])

    _transcribe_with_stub(b"fake audio", fake_fw, model_size="tiny")

    # The first positional argument to WhisperModel should be the model size
    call_args = fake_fw.WhisperModel.call_args
    assert call_args[0][0] == "tiny"


def test_transcribe_audio_model_uses_cpu_int8():
    """WhisperModel is always configured with device='cpu' and compute_type='int8'."""
    fake_fw, _ = _make_fake_faster_whisper(segments=[])

    _transcribe_with_stub(b"fake audio", fake_fw)

    call_kwargs = fake_fw.WhisperModel.call_args[1]
    assert call_kwargs.get("device") == "cpu"
    assert call_kwargs.get("compute_type") == "int8"
