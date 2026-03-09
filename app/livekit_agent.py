import os
import inspect
import asyncio
import re

from dotenv import load_dotenv

from app.agent_identity import (
    AGENT_COMPANY_NAME,
    AGENT_IDENTITY_NAME,
    AGENT_IDENTITY_ROLE,
    AGENT_IDENTITY_TONE,
    build_voice_greeting,
)
from app.support import (
    HUMAN_ESCALATION_MESSAGE,
    decide_support_response,
)

load_dotenv()

try:
    from livekit import api
    from livekit.agents import (
        Agent,
        AgentServer,
        AgentSession,
        ChatMessage,
        JobContext,
        JobProcess,
        RoomOutputOptions,
        StopResponse,
        get_job_context,
        inference,
        cli,
    )
    from livekit.plugins import silero
except ImportError as exc:
    raise RuntimeError(
        "LiveKit dependencies are not installed. Install livekit-agents with required plugins."
    ) from exc


LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "wise-support-agent").strip()
LIVEKIT_STT_MODEL = os.getenv("LIVEKIT_STT_MODEL", "deepgram/nova-2-phonecall").strip()
LIVEKIT_STT_LANGUAGE = os.getenv("LIVEKIT_STT_LANGUAGE", "en").strip()
LIVEKIT_TTS_MODEL = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-3").strip()
LIVEKIT_TTS_VOICE = os.getenv(
    "LIVEKIT_TTS_VOICE",
    "f786b574-daa5-4673-aa0c-cbe3e8534c02",
).strip()
LIVEKIT_ALLOW_INTERRUPTIONS = os.getenv("LIVEKIT_ALLOW_INTERRUPTIONS", "false").strip()
LIVEKIT_MIN_INTERRUPTION_DURATION = os.getenv("LIVEKIT_MIN_INTERRUPTION_DURATION", "1.0").strip()
LIVEKIT_MIN_ENDPOINTING_DELAY = os.getenv("LIVEKIT_MIN_ENDPOINTING_DELAY", "1.2").strip()
LIVEKIT_MAX_ENDPOINTING_DELAY = os.getenv("LIVEKIT_MAX_ENDPOINTING_DELAY", "3.0").strip()
LIVEKIT_REPROMPT_ON_LOW_SIGNAL = os.getenv("LIVEKIT_REPROMPT_ON_LOW_SIGNAL", "true").strip()
LIVEKIT_CLARIFY_BEFORE_DEFLECTION = os.getenv("LIVEKIT_CLARIFY_BEFORE_DEFLECTION", "true").strip()

LOW_SIGNAL_WORDS = {
    "hey",
    "hi",
    "hello",
    "yo",
    "um",
    "uh",
    "hmm",
    "huh",
    "okay",
    "ok",
}


def parse_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def parse_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_message_text(message: ChatMessage) -> str:
    text_content = getattr(message, "text_content", "")
    if callable(text_content):
        return (text_content() or "").strip()
    return (text_content or "").strip()


def is_low_signal_input(user_text: str) -> bool:
    words = re.findall(r"[a-zA-Z']+", user_text.lower())
    if not words:
        return True

    meaningful = [word for word in words if word not in LOW_SIGNAL_WORDS]
    return len(meaningful) == 0


async def _say_and_wait(session: AgentSession, text: str) -> None:
    say_result = session.say(text)
    speech_handle = await say_result if inspect.isawaitable(say_result) else say_result

    wait_for_playout = getattr(speech_handle, "wait_for_playout", None)
    if callable(wait_for_playout):
        wait_result = wait_for_playout()
        if inspect.isawaitable(wait_result):
            await wait_result
        return

    # Fallback for future API variations when no speech handle is exposed.
    await asyncio.sleep(0.75)


async def hangup_call() -> None:
    ctx = get_job_context()
    if ctx is None:
        return

    await ctx.api.room.delete_room(
        api.DeleteRoomRequest(room=ctx.room.name)
    )


class WiseSupportLiveKitAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                f"You are {AGENT_IDENTITY_NAME}, a {AGENT_IDENTITY_ROLE} at {AGENT_COMPANY_NAME}. "
                f"Your tone is {AGENT_IDENTITY_TONE}. "
                "Give concise but complete phone-call answers, and use as much detail as needed. "
                "Speak in first person as the support representative. "
                "Only answer from the verified FAQ context inserted in the conversation. "
                "If context is missing or irrelevant, respond exactly with: "
                f"{HUMAN_ESCALATION_MESSAGE}"
            ),
        )
        self.clarification_prompted = False

    async def on_enter(self) -> None:
        self.clarification_prompted = False
        await _say_and_wait(
            self.session,
            build_voice_greeting(),
        )

    async def on_user_turn_completed(
        self,
        _turn_ctx,
        new_message: ChatMessage,
    ) -> None:
        user_text = _extract_message_text(new_message)
        if not user_text:
            return

        if parse_bool(LIVEKIT_REPROMPT_ON_LOW_SIGNAL, True) and is_low_signal_input(user_text):
            await _say_and_wait(
                self.session,
                "I can help with transfer status questions. Please tell me your transfer question.",
            )
            return

        support_response = decide_support_response(user_text)

        if support_response.faq_match is None:
            print("[LIVEKIT][RAG] no matching faq found")
        else:
            faq_match = support_response.faq_match
            print(
                "[LIVEKIT][RAG] "
                f"faq_id={faq_match.id} score={faq_match.score} source={faq_match.source_url}"
            )

        if support_response.requires_human:
            if parse_bool(LIVEKIT_CLARIFY_BEFORE_DEFLECTION, True) and not self.clarification_prompted:
                self.clarification_prompted = True
                await _say_and_wait(
                    self.session,
                    "I can help with transfer tracking questions like where your money is. "
                    "Could you ask your transfer question again?",
                )
                return

            await _say_and_wait(self.session, support_response.text)
            await hangup_call()
            raise StopResponse()

        self.clarification_prompted = False
        await _say_and_wait(self.session, support_response.text)
        return


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


def build_tts_model():
    if LIVEKIT_TTS_VOICE:
        return inference.TTS(model=LIVEKIT_TTS_MODEL, voice=LIVEKIT_TTS_VOICE)
    return inference.TTS(model=LIVEKIT_TTS_MODEL)


server = AgentServer(setup_fnc=prewarm)


@server.rtc_session(agent_name=LIVEKIT_AGENT_NAME)
async def entrypoint(ctx: JobContext):
    await ctx.connect()

    allow_interruptions = parse_bool(LIVEKIT_ALLOW_INTERRUPTIONS, False)
    min_interruption_duration = parse_float(LIVEKIT_MIN_INTERRUPTION_DURATION, 1.0)
    min_endpointing_delay = parse_float(LIVEKIT_MIN_ENDPOINTING_DELAY, 1.2)
    max_endpointing_delay = parse_float(LIVEKIT_MAX_ENDPOINTING_DELAY, 3.0)

    session = AgentSession(
        stt=inference.STT(model=LIVEKIT_STT_MODEL, language=LIVEKIT_STT_LANGUAGE),
        tts=build_tts_model(),
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=allow_interruptions,
        min_interruption_duration=min_interruption_duration,
        min_endpointing_delay=min_endpointing_delay,
        max_endpointing_delay=max_endpointing_delay,
    )

    await session.start(
        room=ctx.room,
        agent=WiseSupportLiveKitAgent(),
        room_output_options=RoomOutputOptions(
            transcription_enabled=False,
            sync_transcription=False,
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
