# Simple Voice Agent

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-%3E%3D0.135.1-009688)
![Twilio](https://img.shields.io/badge/Twilio-%3E%3D9.10.2-F22F46)
![LiveKit Agents](https://img.shields.io/badge/LiveKit%20Agents-%3E%3D1.2.8-1A1A1A)
![Qdrant Client](https://img.shields.io/badge/Qdrant%20Client-%3E%3D1.17.0-EA4335)
![Google GenAI](https://img.shields.io/badge/Google%20GenAI-%3E%3D1.66.0-4285F4)
![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v2-2496ED)

A simple voice agent for incoming support calls.

The agent:
- Answers only [Wise](https://wise.com/help/topics/5bVKT0uQdBrDp6T62keyfz/sending-money) "Where is my money" FAQ-style questions from the local dataset.
- Deflects unrelated questions to a human agent and ends the call.
- Supports two voice backends: `twilio` and `livekit` (selected by `VOICE_BACKEND`).

## Architecture

- [System architecture and technical details](docs/architecture.md)

## App Layout

- `app/main.py` - shared entrypoint; switches backend using `VOICE_BACKEND`
- `app/rag.py` - FAQ retrieval from Qdrant/FastEmbed
- `app/llm.py` - Gemini setup, system prompt, retry/fallback handling
- `app/base_agent.py` - abstract base class and shared support decision flow
- `app/mixins.py` - identity and logging mixins
- `app/twilio_agent.py` - Twilio implementation (webhook/TwiML flow)
- `app/livekit_agent.py` - LiveKit implementation (worker/session flow)
- `app/utils.py` - shared helpers/utilities for both backends

## Stack

- FastAPI (voice webhook)
- Twilio Voice (`<Gather>` for speech input, `<Say>` for speech output)
- LiveKit Agents (real-time STT/LLM/TTS pipeline, LiveKit Cloud compatible)
- Qdrant (vector store)
- FastEmbed (embeddings)
- Gemini API (final answer generation with escalation fallback)
- Docker + Docker Compose (local reproducible runtime)

## Prerequisites

- Docker Engine + Docker Compose v2
- `ngrok` (for exposing local webhook to Twilio)
- Twilio account + phone number
- LiveKit Cloud project (for LiveKit backend)
- Google API key for Gemini

## Environment

Create `.env` from `.env.example` and fill required values.

```bash
cp .env.example .env
```

Required for app behavior:
- `GOOGLE_API_KEY`
- `VOICE_BACKEND` (`twilio` or `livekit`)

Required for Twilio backend:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `USER_PHONE_NUMBER`

Required for LiveKit backend:
- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`

Optional (defaults shown):
- `AGENT_IDENTITY_NAME=Wise Support Assistant`
- `AGENT_IDENTITY_ROLE=transfer tracking specialist`
- `AGENT_COMPANY_NAME=Wise`
- `AGENT_IDENTITY_TONE=calm, confident, and practical`
- `GOOGLE_MODEL_NAME=gemini-3.1-flash-lite-preview`
- `GOOGLE_MODEL_FALLBACK=gemini-2.5-flash`
- `GOOGLE_MODEL_RETRY_COUNT=2`
- `GOOGLE_MODEL_RETRY_BACKOFF_SECONDS=0.6`
- `LIVEKIT_AGENT_NAME=wise-support-agent`
- `LIVEKIT_ROOM_PREFIX=call-`
- `LIVEKIT_STT_MODEL=deepgram/nova-2-phonecall`
- `LIVEKIT_STT_LANGUAGE=en`
- `LIVEKIT_TTS_MODEL=cartesia/sonic-3`
- `LIVEKIT_TTS_VOICE=f786b574-daa5-4673-aa0c-cbe3e8534c02`
- `LIVEKIT_ALLOW_INTERRUPTIONS=false`
- `LIVEKIT_MIN_INTERRUPTION_DURATION=1.0`
- `LIVEKIT_MIN_ENDPOINTING_DELAY=1.2`
- `LIVEKIT_MAX_ENDPOINTING_DELAY=3.0`
- `LIVEKIT_REPROMPT_ON_LOW_SIGNAL=true`
- `LIVEKIT_CLARIFY_BEFORE_DEFLECTION=true`
- `TWILIO_GATHER_LANGUAGE=en-IN`
- `TWILIO_GATHER_SPEECH_MODEL=googlev2_telephony`
- `TWILIO_GATHER_SPEECH_TIMEOUT=3`
- `TWILIO_GATHER_TIMEOUT=8`
- `TWILIO_GATHER_HINTS=`
- `TWILIO_TTS_VOICE=Polly.Joanna-Neural`
- `TWILIO_TTS_LANGUAGE=`
- `QDRANT_HOST=localhost`
- `QDRANT_PORT=6333`

Identity behavior:
- Greeting and LLM answer style follow the identity variables above.
- This applies consistently to both `twilio` and `livekit` backends.

## Backend Selection

Set backend in `.env`:

```bash
VOICE_BACKEND=twilio   # or livekit
```

- `twilio`: run FastAPI webhook (`/voice`) and point Twilio phone number to it.
- `livekit`: run LiveKit agent worker and assign a LiveKit phone number to the agent.

Single entrypoint:
- `uv run python -m app.main` starts Twilio webhook mode when `VOICE_BACKEND=twilio`.
- `uv run python -m app.main` starts LiveKit worker mode when `VOICE_BACKEND=livekit`.
- `uv run python -m app.main dev` keeps LiveKit CLI dev mode (hot reload/watcher behavior).
- Optional: set `LIVEKIT_DEVMODE=true` to run LiveKit default mode with `devmode` when no CLI subcommand is passed.

## Quick Start (Docker)
Run the setup script:
```bash
./scripts/setup.sh
```

What it does:
1. Starts Qdrant
2. Waits for Qdrant readiness
3. Ingests FAQ data into Qdrant
4. Starts the app on `http://localhost:8000`

This path is for `VOICE_BACKEND=twilio`.

## LiveKit Quick Start

1. Set `VOICE_BACKEND=livekit` and add LiveKit Cloud credentials in `.env`.
2. Ensure Qdrant has FAQ data (run `./scripts/setup.sh` once or ingest manually).
3. Start LiveKit worker:

```bash
./scripts/run_livekit_agent.sh
```

4. Create a SIP dispatch rule that routes calls to your agent:

```bash
./scripts/create_livekit_dispatch_rule.sh
```

5. In LiveKit Cloud, assign your phone number to that dispatch rule.

Deflection behavior in LiveKit backend:
- Out-of-scope questions are spoken with a human-agent deflection message.
- Call then ends by deleting the active LiveKit room.

LiveKit LLM note:
- LiveKit backend reuses the same FAQ + Gemini answer path as Twilio backend for consistent behavior.
- Configure Gemini key via `GOOGLE_API_KEY` (model is defined in `app/llm.py`).
- If primary model returns transient errors (`503/429`), the app retries and falls back to `GOOGLE_MODEL_FALLBACK`.

LiveKit telephony truncation note:
- Agent replies are streamed and can be interrupted by caller speech/noise.
- Defaults in `.env.example` now disable interruptions for call stability.
- To re-enable barge-in later, set `LIVEKIT_ALLOW_INTERRUPTIONS=true` and tune interruption delays.
- Greeting-only utterances (like "hey") are reprompted instead of immediate deflection.
- Deflection now includes one clarification attempt before ending the call.

## Manual Docker Commands

If you want full control:

```bash
docker compose up -d qdrant
docker compose run --rm app uv run python scripts/ingest_faq.py
docker compose up -d app
```

Stop services:

```bash
docker compose down
```

Stop and delete Qdrant persisted data:

```bash
docker compose down -v
```

## Twilio Webhook Wiring (POST URL)

1. Start tunnel:

```bash
ngrok http 8000
```

2. Copy HTTPS forwarding URL from ngrok, for example:
   `https://abc123.ngrok-free.app`

3. In Twilio Console (Twilio provides a free trial with a test number):
   - Go to Develop > # Phone Numbers > Manage > Active numbers > [Your Number] > Voice Configuration.
   - Under "A call comes in", choose `Webhook`.
   - Set URL to (example): `https://abc123.ngrok-free.app/voice`
   - Set method to: `HTTP POST`
   - Save.

4. Call your Twilio number and test.

Important:
- Free ngrok URLs change when ngrok restarts. Update Twilio webhook each time URL changes.
- If app is in Docker and ngrok runs on host, `ngrok http 8000` is correct because Compose publishes `8000:8000`.

## Google STT v2 Experiment Notes

- `TWILIO_GATHER_SPEECH_MODEL` is now environment configurable.
- Current `.env.example` uses `googlev2_telephony`.
- Other common values you can try:
  - `googlev2_telephony_short`
  - `googlev2_short`
  - `phone_call` (Twilio default style fallback)
- After changing `.env`, restart app container:

```bash
docker compose up -d --build app
```

## Neural TTS Experiment Notes

- `TWILIO_TTS_VOICE` controls the Twilio `<Say>` voice.
- Current `.env.example` uses `Polly.Joanna-Neural`.
- If a voice is unavailable for your account or locale, switch to another supported voice or set:
  - `TWILIO_TTS_VOICE=` (empty value) to use Twilio default voice.
- `TWILIO_TTS_LANGUAGE` is optional and usually can stay empty when voice already implies language.

## Verify Assignment Behavior

Expected:
- In-scope "Where is my money" style question -> agent responds from FAQ context.
- Unrelated question -> agent says human-agent deflection message and hangs up.

## Troubleshooting

- `RAG lookup failed`:
  - Check Qdrant is running: `docker compose ps`
  - Re-run ingestion: `docker compose run --rm app uv run python scripts/ingest_faq.py`

- Twilio says webhook error:
  - Confirm ngrok is running.
  - Confirm Twilio webhook is exactly `POST https://<ngrok-domain>/voice`.
  - Check app logs: `docker compose logs -f app`

- LiveKit call is not reaching agent:
  - Confirm `VOICE_BACKEND=livekit`.
  - Confirm worker is running: `./scripts/run_livekit_agent.sh`
  - Confirm dispatch rule exists: `lk sip dispatch list`
  - Confirm phone number is attached to the dispatch rule in LiveKit Cloud.

## License
MIT License. See [LICENSE](LICENSE) file for details.

## Author
**Shreyas Bangera**
- [GitHub](https://github.com/shre-db) 
- shreyasdb99@gmail.com
