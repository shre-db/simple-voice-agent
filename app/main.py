import os

from fastapi import FastAPI, Request
from fastapi.responses import Response
from urllib.parse import parse_qs

from twilio.twiml.voice_response import VoiceResponse, Gather

from app.rag import query_faq
from app.llm import generate_answer

app = FastAPI()


def parse_positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


DEFAULT_GATHER_LANGUAGE = os.getenv("TWILIO_GATHER_LANGUAGE", "en-IN")
DEFAULT_GATHER_SPEECH_MODEL = os.getenv("TWILIO_GATHER_SPEECH_MODEL", "phone_call")
DEFAULT_GATHER_TIMEOUT = parse_positive_int(os.getenv("TWILIO_GATHER_TIMEOUT", "8"), 8)
DEFAULT_GATHER_SPEECH_TIMEOUT = os.getenv("TWILIO_GATHER_SPEECH_TIMEOUT", "3")
DEFAULT_GATHER_HINTS = os.getenv("TWILIO_GATHER_HINTS", "").strip()


def extract_speech_result(body: bytes) -> str | None:
    if not body:
        return None

    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    speech_values = parsed.get("SpeechResult")

    return speech_values[0] if speech_values else None


def parse_speech_timeout(value: str) -> int:
    """
    Twilio only allows positive integers for speechTimeout when speechModel is set.
    """
    return parse_positive_int(value, 3)


def build_gather(prompt: str) -> Gather:
    gather_kwargs = {
        "input": "speech",
        "action": "/voice",
        "speechTimeout": parse_speech_timeout(DEFAULT_GATHER_SPEECH_TIMEOUT),
        "timeout": DEFAULT_GATHER_TIMEOUT,
        "language": DEFAULT_GATHER_LANGUAGE,
        "speechModel": DEFAULT_GATHER_SPEECH_MODEL,
    }

    # Debugging logs
    print(gather_kwargs["speechModel"])

    if DEFAULT_GATHER_HINTS:
        gather_kwargs["hints"] = DEFAULT_GATHER_HINTS

    gather = Gather(**gather_kwargs)
    gather.say(prompt)
    return gather


@app.api_route("/voice", methods=["GET", "POST"])
async def voice(request: Request):

    if request.method == "POST":
        body = await request.body()
        user_speech = extract_speech_result(body)
    else:
        user_speech = request.query_params.get("SpeechResult")

    response = VoiceResponse()

    # First interaction (no speech yet)
    if not user_speech:

        gather = build_gather(
            "Hello. You have reached Wise support. How can I help you today?"
        )

        response.append(gather)

        return Response(
            content=str(response),
            media_type="application/xml"
        )

    print("User said:", user_speech)

    # RAG retrieval
    faq = query_faq(user_speech)

    # Escalation if no match
    if faq is None:

        response.say(
            "I'm sorry, this question requires a human support agent. Please contact Wise support."
        )

        response.hangup()

        return Response(
            content=str(response),
            media_type="application/xml"
        )

    # Generate answer with Gemini
    answer = generate_answer(
        user_speech,
        faq["content"]
    )

    # LLM escalation
    if "HUMAN_ESCALATION" in answer:

        response.say(
            "I'm sorry, this question requires a human support agent. Please contact Wise support."
        )

        response.hangup()

        return Response(
            content=str(response),
            media_type="application/xml"
        )

    # Speak the answer
    gather = build_gather(answer)

    response.append(gather)

    return Response(
        content=str(response),
        media_type="application/xml"
    )
