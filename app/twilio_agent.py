from fastapi import Request
from fastapi.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from app.base_agent import BaseVoiceAgent
from app.utils import (
    extract_speech_result,
    get_env_optional,
    get_env_str,
    parse_positive_int,
    parse_speech_timeout,
)


class TwilioVoiceAgent(BaseVoiceAgent):
    @property
    def backend_name(self) -> str:
        return "twilio"

    @property
    def gather_language(self) -> str:
        return get_env_str("TWILIO_GATHER_LANGUAGE", "en-IN")

    @property
    def gather_speech_model(self) -> str:
        return get_env_str("TWILIO_GATHER_SPEECH_MODEL", "googlev2_telephony")

    @property
    def gather_timeout(self) -> int:
        return parse_positive_int(get_env_str("TWILIO_GATHER_TIMEOUT", "8"), 8)

    @property
    def gather_speech_timeout(self) -> int:
        return parse_speech_timeout(get_env_str("TWILIO_GATHER_SPEECH_TIMEOUT", "3"))

    @property
    def gather_hints(self) -> str:
        return get_env_optional("TWILIO_GATHER_HINTS", "")

    @property
    def tts_voice(self) -> str:
        return get_env_optional("TWILIO_TTS_VOICE", "Polly.Joanna-Neural")

    @property
    def tts_language(self) -> str:
        return get_env_optional("TWILIO_TTS_LANGUAGE", "")

    def _say_with_config(self, target: Gather | VoiceResponse, text: str) -> None:
        say_kwargs = {}
        if self.tts_voice:
            say_kwargs["voice"] = self.tts_voice
        if self.tts_language:
            say_kwargs["language"] = self.tts_language

        print(
            "[DEBUG][TTS] "
            f"voice={say_kwargs.get('voice', 'default')} "
            f"language={say_kwargs.get('language', 'default')}"
        )
        target.say(text, **say_kwargs)

    def _build_gather(self, prompt: str) -> Gather:
        gather_kwargs = {
            "input": "speech",
            "action": "/voice",
            "speechTimeout": self.gather_speech_timeout,
            "timeout": self.gather_timeout,
            "language": self.gather_language,
            "speechModel": self.gather_speech_model,
        }
        if self.gather_hints:
            gather_kwargs["hints"] = self.gather_hints

        print(
            "[DEBUG][STT] "
            f"speechModel={gather_kwargs['speechModel']} "
            f"language={gather_kwargs['language']} "
            f"speechTimeout={gather_kwargs['speechTimeout']} "
            f"timeout={gather_kwargs['timeout']} "
            f"hints={'set' if 'hints' in gather_kwargs else 'none'}"
        )

        gather = Gather(**gather_kwargs)
        self._say_with_config(gather, prompt)
        return gather

    def _xml_response(self, response: VoiceResponse) -> Response:
        return Response(content=str(response), media_type="application/xml")

    def backend_disabled_response(self, active_backend: str) -> Response:
        response = VoiceResponse()
        response.say(
            "Twilio voice webhook is disabled. "
            f"This deployment is configured for {active_backend} backend."
        )
        response.hangup()
        return self._xml_response(response)

    async def handle_voice_request(self, request: Request) -> Response:
        if request.method == "POST":
            body = await request.body()
            user_speech = extract_speech_result(body)
        else:
            user_speech = request.query_params.get("SpeechResult")

        response = VoiceResponse()
        if not user_speech:
            response.append(self._build_gather(self.greeting_message()))
            return self._xml_response(response)

        print("User said:", user_speech)
        support_response = self.decide_support_response(user_speech)

        if support_response.requires_human:
            self._say_with_config(response, support_response.text)
            response.hangup()
            return self._xml_response(response)

        response.append(self._build_gather(support_response.text))
        return self._xml_response(response)
