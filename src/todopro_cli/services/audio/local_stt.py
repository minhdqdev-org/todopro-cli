"""Local Whisper speech-to-text for offline mode."""

WHISPER_AVAILABLE = False
try:
    import faster_whisper  # noqa: F401
    WHISPER_AVAILABLE = True
except ImportError:
    pass


def check_whisper() -> tuple[bool, str]:
    """Check if Whisper is available."""
    if not WHISPER_AVAILABLE:
        return False, "faster-whisper not installed. Run: pip install faster-whisper"
    return True, ""


def transcribe_audio(audio_data: bytes, model_size: str = "base", language: str = "auto") -> str:
    """Transcribe audio bytes using local Whisper model."""
    if not WHISPER_AVAILABLE:
        raise RuntimeError("faster-whisper not installed. Run: pip install faster-whisper")
    
    import io
    from faster_whisper import WhisperModel
    
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    lang = None if language == "auto" else language
    audio_file = io.BytesIO(audio_data)
    segments, _ = model.transcribe(audio_file, language=lang)
    return " ".join(seg.text.strip() for seg in segments)
