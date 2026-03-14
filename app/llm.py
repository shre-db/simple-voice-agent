import time

from dotenv import load_dotenv
from google import genai

from app.utils import get_env_str, parse_float, parse_positive_int

load_dotenv()

HUMAN_ESCALATION_TOKEN = "HUMAN_ESCALATION"

GOOGLE_API_KEY = get_env_str("GOOGLE_API_KEY", "")
PRIMARY_MODEL_NAME = get_env_str("GOOGLE_MODEL_NAME", "gemini-3.1-flash-lite-preview")
FALLBACK_MODEL_NAME = get_env_str("GOOGLE_MODEL_FALLBACK", "gemini-2.5-flash")
MODEL_RETRY_COUNT = parse_positive_int(get_env_str("GOOGLE_MODEL_RETRY_COUNT", "2"), 2)
MODEL_RETRY_BACKOFF_SECONDS = parse_float(
    get_env_str("GOOGLE_MODEL_RETRY_BACKOFF_SECONDS", "0.6"),
    0.6,
)

AGENT_IDENTITY_NAME = get_env_str("AGENT_IDENTITY_NAME", "Wise Support Assistant")
AGENT_IDENTITY_ROLE = get_env_str("AGENT_IDENTITY_ROLE", "transfer tracking specialist")
AGENT_COMPANY_NAME = get_env_str("AGENT_COMPANY_NAME", "Wise")
AGENT_IDENTITY_TONE = get_env_str("AGENT_IDENTITY_TONE", "calm, confident, and practical")

SYSTEM_PROMPT = """
You are handling a live customer support call.

Identity:
- You are {agent_name}.
- You work as a {agent_role} at {company}.
- Your speaking style is: {agent_tone}.

Answer the caller's question using ONLY the provided context.

Rules:
- Speak in first person as the support representative.
- Start with a direct answer.
- Keep the reply concise for voice, but include all important details from context.
- Choose response length based on complexity of the question and context.
- Include concrete next steps the caller can do now, when available.
- Include practical details from context that help resolve the issue.
- Do not add information that is not in context.
- Do not mention "context", "article", or that you are an AI model.
- Do not use markdown or bullet points.
- If the question is unrelated to the context, respond exactly with: HUMAN_ESCALATION.
""".format(
    agent_name=AGENT_IDENTITY_NAME,
    agent_role=AGENT_IDENTITY_ROLE,
    company=AGENT_COMPANY_NAME,
    agent_tone=AGENT_IDENTITY_TONE,
)

client = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None


def is_retryable_llm_error(exc: Exception) -> bool:
    error_text = str(exc).upper()
    retryable_markers = (
        "429",
        "500",
        "503",
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "DEADLINE_EXCEEDED",
        "INTERNAL",
    )
    return any(marker in error_text for marker in retryable_markers)


def selected_models() -> list[str]:
    models: list[str] = []
    for model_name in (PRIMARY_MODEL_NAME, FALLBACK_MODEL_NAME):
        if model_name and model_name not in models:
            models.append(model_name)
    return models


def generate_answer(user_question: str, faq_context: str) -> str:
    if client is None:
        print("GOOGLE_API_KEY is not configured.")
        return HUMAN_ESCALATION_TOKEN

    prompt = f"""
Context:
{faq_context}

Caller question:
{user_question}

Answer:
"""

    models = selected_models()
    if not models:
        print("No Gemini model configured (GOOGLE_MODEL_NAME/GOOGLE_MODEL_FALLBACK).")
        return HUMAN_ESCALATION_TOKEN

    for model_name in models:
        for attempt in range(1, MODEL_RETRY_COUNT + 2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=SYSTEM_PROMPT + prompt,
                )
                answer = (response.text or "").strip()
                if answer:
                    print(f"[LLM] model={model_name} answer={answer}")
                    return answer
                print(f"LLM returned empty response: model={model_name}, attempt={attempt}")
            except Exception as exc:
                retryable = is_retryable_llm_error(exc)
                print(
                    "LLM generation failed: "
                    f"model={model_name}, attempt={attempt}, retryable={retryable}, error={exc}"
                )
                if retryable and attempt <= MODEL_RETRY_COUNT:
                    sleep_seconds = MODEL_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    time.sleep(sleep_seconds)
                    continue
            break

    return HUMAN_ESCALATION_TOKEN
