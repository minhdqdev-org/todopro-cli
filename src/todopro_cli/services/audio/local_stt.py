"""Local Whisper speech-to-text for offline mode."""


def transcribe_audio(
    audio_data: bytes, model_size: str = "base", language: str = "auto"
) -> str:
    """Transcribe audio bytes using local Whisper model."""

    import io

    from faster_whisper import WhisperModel

    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    lang = None if language == "auto" else language
    audio_file = io.BytesIO(audio_data)
    segments, _ = model.transcribe(audio_file, language=lang)
    return " ".join(seg.text.strip() for seg in segments)
