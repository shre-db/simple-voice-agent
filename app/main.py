import os

from fastapi import FastAPI, Request
from fastapi.responses import Response
from urllib.parse import parse_qs

from twilio.twiml.voice_response import VoiceResponse, Gather

from app.backend import get_voice_backend
from app.support import decide_support_response

app = FastAPI()


def parse_positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


DEFAULT_GATHER_LANGUAGE = os.getenv("TWILIO_GATHER_LANGUAGE", "en-IN")
DEFAULT_GATHER_SPEECH_MODEL = os.getenv("TWILIO_GATHER_SPEECH_MODEL", "googlev2_telephony")
DEFAULT_GATHER_TIMEOUT = parse_positive_int(os.getenv("TWILIO_GATHER_TIMEOUT", "8"), 8)
DEFAULT_GATHER_SPEECH_TIMEOUT = os.getenv("TWILIO_GATHER_SPEECH_TIMEOUT", "3")
DEFAULT_GATHER_HINTS = os.getenv("TWILIO_GATHER_HINTS", "").strip()
DEFAULT_TTS_VOICE = os.getenv("TWILIO_TTS_VOICE", "Polly.Joanna-Neural").strip()
DEFAULT_TTS_LANGUAGE = os.getenv("TWILIO_TTS_LANGUAGE", "").strip()
VOICE_BACKEND = get_voice_backend()


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


def say_with_config(target: Gather | VoiceResponse, text: str) -> None:
    say_kwargs = {}
    if DEFAULT_TTS_VOICE:
        say_kwargs["voice"] = DEFAULT_TTS_VOICE
    if DEFAULT_TTS_LANGUAGE:
        say_kwargs["language"] = DEFAULT_TTS_LANGUAGE

    print(
        "[DEBUG][TTS] "
        f"voice={say_kwargs.get('voice', 'default')} "
        f"language={say_kwargs.get('language', 'default')}"
    )

    target.say(text, **say_kwargs)


def build_gather(prompt: str) -> Gather:
    gather_kwargs = {
        "input": "speech",
        "action": "/voice",
        "speechTimeout": parse_speech_timeout(DEFAULT_GATHER_SPEECH_TIMEOUT),
        "timeout": DEFAULT_GATHER_TIMEOUT,
        "language": DEFAULT_GATHER_LANGUAGE,
        "speechModel": DEFAULT_GATHER_SPEECH_MODEL,
    }

    if DEFAULT_GATHER_HINTS:
        gather_kwargs["hints"] = DEFAULT_GATHER_HINTS

    print(
        "[DEBUG][STT] "
        f"speechModel={gather_kwargs['speechModel']} "
        f"language={gather_kwargs['language']} "
        f"speechTimeout={gather_kwargs['speechTimeout']} "
        f"timeout={gather_kwargs['timeout']} "
        f"hints={'set' if 'hints' in gather_kwargs else 'none'}"
    )

    gather = Gather(**gather_kwargs)
    say_with_config(gather, prompt)
    return gather


@app.api_route("/voice", methods=["GET", "POST"])
async def voice(request: Request):
    if VOICE_BACKEND != "twilio":
        response = VoiceResponse()
        response.say(
            "Twilio voice webhook is disabled. This deployment is configured for LiveKit backend."
        )
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

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

    support_response = decide_support_response(user_speech)

    if support_response.requires_human:
        say_with_config(response, support_response.text)
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

    # Speak the answer
    gather = build_gather(support_response.text)

    response.append(gather)

    return Response(
        content=str(response),
        media_type="application/xml"
    )
