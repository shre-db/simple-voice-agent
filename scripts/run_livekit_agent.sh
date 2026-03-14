#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export VOICE_BACKEND="${VOICE_BACKEND:-livekit}"
uv run python -m app.main dev
