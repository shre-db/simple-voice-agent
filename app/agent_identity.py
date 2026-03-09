import os

from dotenv import load_dotenv

load_dotenv()


def _env_value(name: str, default: str) -> str:
    value = os.getenv(name, default)
    cleaned = value.strip() if isinstance(value, str) else ""
    return cleaned or default


AGENT_IDENTITY_NAME = _env_value("AGENT_IDENTITY_NAME", "Wise Support Assistant")
AGENT_IDENTITY_ROLE = _env_value("AGENT_IDENTITY_ROLE", "transfer tracking specialist")
AGENT_COMPANY_NAME = _env_value("AGENT_COMPANY_NAME", "Wise")
AGENT_IDENTITY_TONE = _env_value(
    "AGENT_IDENTITY_TONE",
    "calm, confident, and practical",
)


def build_voice_greeting() -> str:
    return (
        f"Hello. You have reached {AGENT_COMPANY_NAME} support. "
        f"This is {AGENT_IDENTITY_NAME}. How can I help with your transfer today?"
    )
