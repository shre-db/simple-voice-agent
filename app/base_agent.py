from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.llm import HUMAN_ESCALATION_TOKEN, generate_answer
from app.mixins import IdentityMixin, SupportLoggingMixin
from app.rag import query_faq
from app.utils import DEFAULT_HUMAN_ESCALATION_MESSAGE, get_env_str


@dataclass
class FAQMatch:
    id: str | None
    question: str | None
    content: str
    score: float | None
    source_url: str | None


@dataclass
class SupportResponse:
    text: str
    requires_human: bool
    faq_match: FAQMatch | None = None


class BaseVoiceAgent(IdentityMixin, SupportLoggingMixin, ABC):
    def __init__(self) -> None:
        self.human_escalation_message = get_env_str(
            "HUMAN_ESCALATION_MESSAGE",
            DEFAULT_HUMAN_ESCALATION_MESSAGE,
        )

    @property
    @abstractmethod
    def backend_name(self) -> str:
        raise NotImplementedError

    def find_faq_match(self, user_question: str) -> FAQMatch | None:
        faq = query_faq(user_question)
        if faq is None:
            return None

        return FAQMatch(
            id=faq.get("id"),
            question=faq.get("question"),
            content=faq.get("content", ""),
            score=faq.get("score"),
            source_url=faq.get("source_url"),
        )

    def decide_support_response(self, user_question: str) -> SupportResponse:
        faq_match = self.find_faq_match(user_question)
        if faq_match is None:
            response = SupportResponse(
                text=self.human_escalation_message,
                requires_human=True,
            )
            self.log_support_response(user_question, response)
            return response

        answer = generate_answer(user_question, faq_match.content)
        if HUMAN_ESCALATION_TOKEN in answer:
            response = SupportResponse(
                text=self.human_escalation_message,
                requires_human=True,
                faq_match=faq_match,
            )
            self.log_support_response(user_question, response)
            return response

        response = SupportResponse(
            text=answer,
            requires_human=False,
            faq_match=faq_match,
        )
        self.log_support_response(user_question, response)
        return response
