import asyncio
import inspect
import os
import re
from typing import Any
from urllib.parse import parse_qs

SUPPORTED_VOICE_BACKENDS = {"twilio", "livekit"}
DEFAULT_VOICE_BACKEND = "twilio"

DEFAULT_HUMAN_ESCALATION_MESSAGE = (
    "I'm sorry, this question requires a human support agent. Please contact Wise support."
)

LOW_SIGNAL_WORDS = {
    "hey",
    "hi",
    "hello",
    "yo",
    "um",
    "uh",
    "hmm",
    "huh",
    "okay",
    "ok",
}


def get_env_str(name: str, default: str) -> str:
    value = os.getenv(name, default)
    if not isinstance(value, str):
        return default
    cleaned = value.strip()
    return cleaned or default


def get_env_optional(name: str, default: str = "") -> str:
    if name not in os.environ:
        return default
    value = os.getenv(name, default)
    if not isinstance(value, str):
        return default
    return value.strip()


def parse_positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def parse_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_bool(value: str, default: bool) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def normalize_single_line(text: str) -> str:
    return " ".join((text or "").split())


def get_voice_backend() -> str:
    backend = get_env_str("VOICE_BACKEND", DEFAULT_VOICE_BACKEND).lower()
    if backend not in SUPPORTED_VOICE_BACKENDS:
        return DEFAULT_VOICE_BACKEND
    return backend


def build_voice_greeting() -> str:
    company_name = get_env_str("AGENT_COMPANY_NAME", "Wise")
    agent_name = get_env_str("AGENT_IDENTITY_NAME", "Wise Support Assistant")
    return (
        f"Hello. You have reached {company_name} support. "
        f"This is {agent_name}. How can I help with your transfer today?"
    )


def extract_speech_result(body: bytes) -> str | None:
    if not body:
        return None
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    speech_values = parsed.get("SpeechResult")
    if not speech_values:
        return None
    value = speech_values[0].strip()
    return value or None


def parse_speech_timeout(value: str) -> int:
    # Twilio accepts positive integers when speechModel is explicitly set.
    return parse_positive_int(value, 3)


def is_low_signal_input(user_text: str) -> bool:
    words = re.findall(r"[a-zA-Z']+", (user_text or "").lower())
    if not words:
        return True
    meaningful = [word for word in words if word not in LOW_SIGNAL_WORDS]
    return len(meaningful) == 0


def extract_livekit_message_text(message: Any) -> str:
    text_content = getattr(message, "text_content", "")
    if callable(text_content):
        return (text_content() or "").strip()
    return (text_content or "").strip()


async def say_and_wait(session: Any, text: str) -> None:
    say_result = session.say(text)
    speech_handle = await say_result if inspect.isawaitable(say_result) else say_result

    wait_for_playout = getattr(speech_handle, "wait_for_playout", None)
    if callable(wait_for_playout):
        wait_result = wait_for_playout()
        if inspect.isawaitable(wait_result):
            await wait_result
        return

    # Fallback when speech handle APIs differ across SDK versions.
    await asyncio.sleep(0.75)
