from fastapi import FastAPI, Request
from fastapi.responses import Response

from twilio.twiml.voice_response import VoiceResponse, Gather

from app.rag import query_faq
from app.llm import generate_answer

app = FastAPI()


@app.post("/voice")
async def voice(request: Request):

    form = await request.form()

    user_speech = form.get("SpeechResult")

    response = VoiceResponse()

    # First interaction (no speech yet)
    if not user_speech:

        gather = Gather(
            input="speech",
            action="/voice",
            speechTimeout="auto",
            timeout=1,
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
        timeout=1,
        speechModel="phone_call"
    )

    gather.say(answer)

    response.append(gather)

    return Response(
        content=str(response),
        media_type="application/xml"
    )
