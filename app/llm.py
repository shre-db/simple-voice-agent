import os
from dotenv import load_dotenv

from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GOOGLE_API_KEY")
)

# print([model for model in client.models.list() if "gemini" in model.name])
# exit()

MODEL_NAME = "gemini-3.1-flash-lite-preview"

SYSTEM_PROMPT = """
You are a Wise customer support voice agent.

Answer the caller's question using ONLY the provided context.

Rules:
- Respond in 1 or 2 short sentences suitable for a phone call.
- Do not add extra information.
- If the question is unrelated to the context, respond exactly with: HUMAN_ESCALATION.
"""


def generate_answer(user_question: str, faq_context: str):

    prompt = f"""
Context:
{faq_context}

Caller question:
{user_question}

Answer:
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=SYSTEM_PROMPT + prompt,
    )

    return response.text.strip()