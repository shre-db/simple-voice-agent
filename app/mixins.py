from app.utils import build_voice_greeting, get_env_str, normalize_single_line


class IdentityMixin:
    @property
    def identity_name(self) -> str:
        return get_env_str("AGENT_IDENTITY_NAME", "Wise Support Assistant")

    @property
    def identity_role(self) -> str:
        return get_env_str("AGENT_IDENTITY_ROLE", "transfer tracking specialist")

    @property
    def company_name(self) -> str:
        return get_env_str("AGENT_COMPANY_NAME", "Wise")

    @property
    def identity_tone(self) -> str:
        return get_env_str("AGENT_IDENTITY_TONE", "calm, confident, and practical")

    def greeting_message(self) -> str:
        return build_voice_greeting()


class SupportLoggingMixin:
    def log_support_response(self, user_question: str, response) -> None:
        faq_id = response.faq_match.id if response.faq_match else None
        faq_score = response.faq_match.score if response.faq_match else None
        faq_source = response.faq_match.source_url if response.faq_match else None
        print(
            "[SUPPORT] "
            f"question={normalize_single_line(user_question)} | "
            f"requires_human={response.requires_human} | "
            f"faq_id={faq_id} | "
            f"score={faq_score} | "
            f"source={faq_source} | "
            f"response={normalize_single_line(response.text)}"
        )
