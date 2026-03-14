import os
import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.twilio_agent import TwilioVoiceAgent
from app.utils import get_env_str, get_voice_backend, parse_bool, parse_positive_int

app = FastAPI(title="Simple Voice Agent")
twilio_agent = TwilioVoiceAgent()


@app.get("/health")
async def health():
    return JSONResponse(
        {
            "status": "ok",
            "voice_backend": get_voice_backend(),
        }
    )


@app.api_route("/voice", methods=["GET", "POST"])
async def voice(request: Request):
    active_backend = get_voice_backend()
    if active_backend != twilio_agent.backend_name:
        return twilio_agent.backend_disabled_response(active_backend)
    return await twilio_agent.handle_voice_request(request)


def run_twilio_webhook_server() -> None:
    host = os.getenv("APP_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = parse_positive_int(os.getenv("APP_PORT", "8000"), 8000)
    uvicorn.run("app.main:app", host=host, port=port)


def run_selected_backend() -> None:
    backend = get_voice_backend()
    if backend == "livekit":
        # With no explicit subcommand, run a default worker so this works:
        # VOICE_BACKEND=livekit uv run python -m app.main
        if len(sys.argv) <= 1:
            from app.livekit_agent import run_livekit_server

            devmode = parse_bool(get_env_str("LIVEKIT_DEVMODE", "false"), False)
            run_livekit_server(devmode=devmode)
            return

        from app.livekit_agent import run_livekit_cli

        run_livekit_cli()
        return

    run_twilio_webhook_server()


if __name__ == "__main__":
    run_selected_backend()
