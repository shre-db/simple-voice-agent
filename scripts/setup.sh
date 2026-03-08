#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: $cmd" >&2
    exit 1
  fi
}

http_ready() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS "$url" >/dev/null 2>&1
    return $?
  fi

  if command -v wget >/dev/null 2>&1; then
    wget -q -O /dev/null "$url"
    return $?
  fi

  echo "Need curl or wget to check service readiness." >&2
  return 1
}

require_cmd docker

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose ...)." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example. Update GOOGLE_API_KEY and Twilio values before running calls."
fi

echo "Starting Qdrant..."
docker compose up -d qdrant

echo "Waiting for Qdrant to become ready..."
for _ in {1..45}; do
  if http_ready "http://localhost:6333/readyz"; then
    break
  fi
  sleep 1
done

if ! http_ready "http://localhost:6333/readyz"; then
  echo "Qdrant did not become ready in time." >&2
  exit 1
fi

echo "Ingesting FAQ data into Qdrant..."
docker compose run --rm app uv run python scripts/ingest_faq.py

echo "Starting app service..."
docker compose up -d app

echo "Setup complete."
echo "API endpoint: http://localhost:8000/voice"
echo "Next step: run ngrok on port 8000 and configure Twilio webhook to POST /voice."
