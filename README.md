# simple-voice-agent

A simple voice agent for incoming support calls.

The agent:
- Answers only Wise "Where is my money" FAQ-style questions from the local dataset.
- Deflects unrelated questions to a human agent and ends the call.

## Stack

- FastAPI (voice webhook)
- Twilio Voice (`<Gather>` for speech input, `<Say>` for speech output)
- Qdrant (vector store)
- FastEmbed (embeddings)
- Gemini API (final answer generation with escalation fallback)
- Docker + Docker Compose (local reproducible runtime)

## Prerequisites

- Docker Engine + Docker Compose v2
- `ngrok` (for exposing local webhook to Twilio)
- Twilio account + phone number
- Google API key for Gemini

## Environment

Create `.env` from `.env.example` and fill required values.

```bash
cp .env.example .env
```

Required for app behavior:
- `GOOGLE_API_KEY`

Required for Twilio call flow setup/testing:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `USER_PHONE_NUMBER`

Optional (defaults shown):
- `TWILIO_GATHER_LANGUAGE=en-IN`
- `TWILIO_GATHER_SPEECH_MODEL=googlev2_telephony`
- `TWILIO_GATHER_SPEECH_TIMEOUT=3`
- `TWILIO_GATHER_TIMEOUT=8`
- `TWILIO_GATHER_HINTS=`
- `QDRANT_HOST=localhost`
- `QDRANT_PORT=6333`

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

3. In Twilio Console:
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
