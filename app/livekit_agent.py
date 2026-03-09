import os

from dotenv import load_dotenv

from app.support import HUMAN_ESCALATION_MESSAGE, find_faq_match

load_dotenv()

try:
    from livekit.agents import (
        Agent,
        AgentServer,
        AgentSession,
        ChatContext,
        ChatMessage,
        JobContext,
        JobProcess,
        StopResponse,
        cli,
    )
    from livekit.plugins import google, inference, silero
except ImportError as exc:
    raise RuntimeError(
        "LiveKit dependencies are not installed. Install livekit-agents with plugins."
    ) from exc


LIVEKIT_AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "wise-support-agent").strip()
LIVEKIT_LLM_MODEL = os.getenv("LIVEKIT_LLM_MODEL", "gemini-3.1-flash-lite-preview").strip()
LIVEKIT_STT_MODEL = os.getenv("LIVEKIT_STT_MODEL", "deepgram/nova-2-phonecall").strip()
LIVEKIT_STT_LANGUAGE = os.getenv("LIVEKIT_STT_LANGUAGE", "en").strip()
LIVEKIT_TTS_MODEL = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-3").strip()
LIVEKIT_TTS_VOICE = os.getenv(
    "LIVEKIT_TTS_VOICE",
    "f786b574-daa5-4673-aa0c-cbe3e8534c02",
).strip()


def _extract_message_text(message: ChatMessage) -> str:
    text_content = getattr(message, "text_content", "")
    if callable(text_content):
        return (text_content() or "").strip()
    return (text_content or "").strip()


class WiseSupportLiveKitAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a Wise customer support voice agent. "
                "Answer in 1 or 2 short sentences suitable for a phone call. "
                "Only answer from the verified FAQ context inserted in the conversation. "
                "If context is missing or irrelevant, respond exactly with: "
                f"{HUMAN_ESCALATION_MESSAGE}"
            ),
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=(
                "Greet the caller and ask how you can help with a transfer status question."
            )
        )

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        user_text = _extract_message_text(new_message)
        if not user_text:
            raise StopResponse()

        faq_match = find_faq_match(user_text)
        if faq_match is None:
            await self.session.generate_reply(
                instructions=(
                    "Respond with exactly this sentence and nothing else: "
                    f"{HUMAN_ESCALATION_MESSAGE}"
                )
            )
            raise StopResponse()

        print(
            "[LIVEKIT][RAG] "
            f"faq_id={faq_match.id} score={faq_match.score} source={faq_match.source_url}"
        )

        turn_ctx.add_message(
            role="assistant",
            content=(
                "Verified FAQ context (authoritative, use only this context): "
                f"{faq_match.content}"
            ),
        )


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


def build_tts_model():
    if LIVEKIT_TTS_VOICE:
        return inference.TTS(model=LIVEKIT_TTS_MODEL, voice=LIVEKIT_TTS_VOICE)
    return inference.TTS(model=LIVEKIT_TTS_MODEL)


server = AgentServer(prewarm_fnc=prewarm)


@server.rtc_session(agent_name=LIVEKIT_AGENT_NAME)
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=inference.STT(model=LIVEKIT_STT_MODEL, language=LIVEKIT_STT_LANGUAGE),
        llm=google.LLM(model=LIVEKIT_LLM_MODEL),
        tts=build_tts_model(),
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(
        room=ctx.room,
        agent=WiseSupportLiveKitAgent(),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
