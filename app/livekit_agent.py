from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, TypeAlias

from app.base_agent import BaseVoiceAgent
from app.utils import (
    extract_livekit_message_text,
    get_env_optional,
    get_env_str,
    is_low_signal_input,
    parse_bool,
    parse_float,
    say_and_wait,
)

try:
    from livekit import api
    from livekit.agents import (
        Agent,
        AgentServer,
        AgentSession,
        RoomOutputOptions,
        StopResponse,
        cli,
        get_job_context,
        inference,
    )
    from livekit.plugins import silero
except ImportError:
    api = None  # type: ignore[assignment]
    Agent = object  # type: ignore[assignment,misc]
    AgentServer = object  # type: ignore[assignment,misc]
    AgentSession = object  # type: ignore[assignment,misc]
    RoomOutputOptions = object  # type: ignore[assignment,misc]
    StopResponse = RuntimeError  # type: ignore[assignment,misc]
    cli = None  # type: ignore[assignment]
    get_job_context = None  # type: ignore[assignment]
    inference = None  # type: ignore[assignment]
    silero = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from livekit.agents import ChatMessage as LiveKitChatMessage
    from livekit.agents import JobContext as LiveKitJobContext
    from livekit.agents import JobProcess as LiveKitJobProcess
else:
    LiveKitChatMessage = Any
    LiveKitJobContext = Any
    LiveKitJobProcess = Any

ChatMessageT: TypeAlias = LiveKitChatMessage
JobContextT: TypeAlias = LiveKitJobContext
JobProcessT: TypeAlias = LiveKitJobProcess


def _require_livekit_dependencies() -> None:
    if api is None or cli is None or inference is None or silero is None:
        raise RuntimeError(
            "LiveKit dependencies are not installed. "
            "Install livekit-agents with required plugins."
        )


class LiveKitVoiceAgent(BaseVoiceAgent):
    @property
    def backend_name(self) -> str:
        return "livekit"

    @property
    def agent_name(self) -> str:
        return get_env_str("LIVEKIT_AGENT_NAME", "wise-support-agent")

    @property
    def stt_model(self) -> str:
        return get_env_str("LIVEKIT_STT_MODEL", "deepgram/nova-2-phonecall")

    @property
    def stt_language(self) -> str:
        return get_env_str("LIVEKIT_STT_LANGUAGE", "en")

    @property
    def tts_model(self) -> str:
        return get_env_str("LIVEKIT_TTS_MODEL", "cartesia/sonic-3")

    @property
    def tts_voice(self) -> str:
        return get_env_optional("LIVEKIT_TTS_VOICE", "f786b574-daa5-4673-aa0c-cbe3e8534c02")

    @property
    def allow_interruptions(self) -> bool:
        return parse_bool(get_env_str("LIVEKIT_ALLOW_INTERRUPTIONS", "false"), False)

    @property
    def min_interruption_duration(self) -> float:
        return parse_float(get_env_str("LIVEKIT_MIN_INTERRUPTION_DURATION", "1.0"), 1.0)

    @property
    def min_endpointing_delay(self) -> float:
        return parse_float(get_env_str("LIVEKIT_MIN_ENDPOINTING_DELAY", "1.2"), 1.2)

    @property
    def max_endpointing_delay(self) -> float:
        return parse_float(get_env_str("LIVEKIT_MAX_ENDPOINTING_DELAY", "3.0"), 3.0)

    @property
    def reprompt_on_low_signal(self) -> bool:
        return parse_bool(get_env_str("LIVEKIT_REPROMPT_ON_LOW_SIGNAL", "true"), True)

    @property
    def clarify_before_deflection(self) -> bool:
        return parse_bool(get_env_str("LIVEKIT_CLARIFY_BEFORE_DEFLECTION", "true"), True)

    def runtime_instructions(self) -> str:
        return (
            f"You are {self.identity_name}, a {self.identity_role} at {self.company_name}. "
            f"Your tone is {self.identity_tone}. "
            "Give concise but complete phone-call answers, and use as much detail as needed. "
            "Speak in first person as the support representative. "
            "Only answer from the verified FAQ context inserted in the conversation. "
            f"If context is missing or irrelevant, respond exactly with: {self.human_escalation_message}"
        )

    async def hangup_call(self) -> None:
        if get_job_context is None:
            return
        ctx = get_job_context()
        if ctx is None:
            return
        await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))

    def build_tts(self):
        if self.tts_voice:
            return inference.TTS(model=self.tts_model, voice=self.tts_voice)
        return inference.TTS(model=self.tts_model)

    def build_server(self):
        _require_livekit_dependencies()
        server = AgentServer(setup_fnc=_livekit_prewarm)
        server.rtc_session(agent_name=self.agent_name)(_livekit_entrypoint)
        return server

    def run_cli(self) -> None:
        _require_livekit_dependencies()
        cli.run_app(self.build_server())


class _LiveKitRuntimeAgent(Agent):
    def __init__(self, owner: LiveKitVoiceAgent) -> None:
        super().__init__(instructions=owner.runtime_instructions())
        self.owner = owner
        self.clarification_prompted = False

    async def on_enter(self) -> None:
        self.clarification_prompted = False
        await say_and_wait(self.session, self.owner.greeting_message())

    async def on_user_turn_completed(self, _turn_ctx: Any, new_message: ChatMessageT) -> None:
        user_text = extract_livekit_message_text(new_message)
        if not user_text:
            return

        if self.owner.reprompt_on_low_signal and is_low_signal_input(user_text):
            await say_and_wait(
                self.session,
                "I can help with transfer status questions. Please tell me your transfer question.",
            )
            return

        support_response = self.owner.decide_support_response(user_text)
        if support_response.faq_match is None:
            print("[LIVEKIT][RAG] no matching faq found")
        else:
            faq_match = support_response.faq_match
            print(
                "[LIVEKIT][RAG] "
                f"faq_id={faq_match.id} score={faq_match.score} source={faq_match.source_url}"
            )

        if support_response.requires_human:
            if self.owner.clarify_before_deflection and not self.clarification_prompted:
                self.clarification_prompted = True
                await say_and_wait(
                    self.session,
                    "I can help with transfer tracking questions like where your money is. "
                    "Could you ask your transfer question again?",
                )
                return

            await say_and_wait(self.session, support_response.text)
            await self.owner.hangup_call()
            raise StopResponse()

        self.clarification_prompted = False
        await say_and_wait(self.session, support_response.text)


def _livekit_prewarm(proc: JobProcessT) -> None:
    _require_livekit_dependencies()
    proc.userdata["vad"] = silero.VAD.load()


async def _livekit_entrypoint(ctx: JobContextT) -> None:
    _require_livekit_dependencies()
    owner = LiveKitVoiceAgent()

    await ctx.connect()
    session = AgentSession(
        stt=inference.STT(model=owner.stt_model, language=owner.stt_language),
        tts=owner.build_tts(),
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=owner.allow_interruptions,
        min_interruption_duration=owner.min_interruption_duration,
        min_endpointing_delay=owner.min_endpointing_delay,
        max_endpointing_delay=owner.max_endpointing_delay,
    )

    await session.start(
        room=ctx.room,
        agent=_LiveKitRuntimeAgent(owner),
        room_output_options=RoomOutputOptions(
            transcription_enabled=False,
            sync_transcription=False,
        ),
    )


def run_livekit_cli() -> None:
    LiveKitVoiceAgent().run_cli()


def run_livekit_server(devmode: bool = False) -> None:
    agent = LiveKitVoiceAgent()
    _require_livekit_dependencies()
    server = agent.build_server()
    run_result = server.run(devmode=devmode)
    if inspect.isawaitable(run_result):
        asyncio.run(run_result)


if __name__ == "__main__":
    run_livekit_cli()
