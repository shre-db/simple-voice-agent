import os

SUPPORTED_VOICE_BACKENDS = {"twilio", "livekit"}
DEFAULT_VOICE_BACKEND = "twilio"


def get_voice_backend() -> str:
    backend = os.getenv("VOICE_BACKEND", DEFAULT_VOICE_BACKEND).strip().lower()
    if backend not in SUPPORTED_VOICE_BACKENDS:
        return DEFAULT_VOICE_BACKEND
    return backend
