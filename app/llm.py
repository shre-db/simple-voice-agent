import os
import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Use fast model
model = genai.GenerativeModel("gemini-1.5-flash")


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

    response = model.generate_content(
        SYSTEM_PROMPT + prompt
    )

    return response.text.strip()