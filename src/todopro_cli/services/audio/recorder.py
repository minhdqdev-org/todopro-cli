"""Microphone audio recorder for CLI Ramble."""

SOUNDDEVICE_AVAILABLE = False
NUMPY_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    pass

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    pass


def check_dependencies() -> tuple[bool, str]:
    """Check if audio dependencies are available."""
    if not SOUNDDEVICE_AVAILABLE:
        return False, "sounddevice not installed. Run: pip install sounddevice"
    if not NUMPY_AVAILABLE:
        return False, "numpy not installed. Run: pip install numpy"
    return True, ""


def record_audio(duration_seconds: int = 30, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Record audio from microphone for N seconds. Returns WAV bytes."""
    if not SOUNDDEVICE_AVAILABLE or not NUMPY_AVAILABLE:
        raise RuntimeError("Audio dependencies not available. Run: pip install sounddevice numpy")
    
    import io
    import wave
    import numpy as np
    
    recording = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype='int16',
    )
    sd.wait()  # Wait until recording is finished
    
    # Convert to WAV bytes
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(recording.tobytes())
    
    return buffer.getvalue()
