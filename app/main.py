from fastapi import FastAPI, Request
from fastapi.responses import Response
from urllib.parse import parse_qs

from twilio.twiml.voice_response import VoiceResponse, Gather

from app.rag import query_faq
from app.llm import generate_answer

app = FastAPI()


def extract_speech_result(body: bytes) -> str | None:
    if not body:
        return None

    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    speech_values = parsed.get("SpeechResult")

    return speech_values[0] if speech_values else None


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

        gather = Gather(
            input="speech",
            action="/voice",
            speechTimeout="auto",
            timeout=8,
            language="en-IN",
            speechModel="phone_call"
        )

        gather.say(
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
    gather = Gather(
        input="speech",
        action="/voice",
        speechTimeout="auto",
        timeout=8,
        language="en-IN",
        speechModel="phone_call"
    )

    gather.say(answer)

    response.append(gather)

    return Response(
        content=str(response),
        media_type="application/xml"
    )
