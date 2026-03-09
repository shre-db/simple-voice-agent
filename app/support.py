from dataclasses import dataclass

from app.llm import generate_answer
from app.rag import query_faq

HUMAN_ESCALATION_MESSAGE = (
    "I'm sorry, this question requires a human support agent. Please contact Wise support."
)


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


def _single_line(text: str) -> str:
    return " ".join(text.split())


def _log_support_response(user_question: str, response: SupportResponse) -> None:
    faq_id = response.faq_match.id if response.faq_match else None
    faq_score = response.faq_match.score if response.faq_match else None
    faq_source = response.faq_match.source_url if response.faq_match else None
    print(
        "[SUPPORT] "
        f"question={_single_line(user_question)} | "
        f"requires_human={response.requires_human} | "
        f"faq_id={faq_id} | "
        f"score={faq_score} | "
        f"source={faq_source} | "
        f"response={_single_line(response.text)}"
    )


def find_faq_match(user_question: str) -> FAQMatch | None:
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


def decide_support_response(user_question: str) -> SupportResponse:
    faq_match = find_faq_match(user_question)

    if faq_match is None:
        response = SupportResponse(
            text=HUMAN_ESCALATION_MESSAGE,
            requires_human=True,
        )
        _log_support_response(user_question, response)
        return response

    answer = generate_answer(user_question, faq_match.content)
    if "HUMAN_ESCALATION" in answer:
        response = SupportResponse(
            text=HUMAN_ESCALATION_MESSAGE,
            requires_human=True,
            faq_match=faq_match,
        )
        _log_support_response(user_question, response)
        return response

    response = SupportResponse(
        text=answer,
        requires_human=False,
        faq_match=faq_match,
    )
    _log_support_response(user_question, response)
    return response
