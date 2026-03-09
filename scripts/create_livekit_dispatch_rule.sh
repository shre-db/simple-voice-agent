#!/usr/bin/env bash
set -euo pipefail

if ! command -v lk >/dev/null 2>&1; then
  echo "Missing 'lk' CLI. Install it first: https://docs.livekit.io/home/cli/" >&2
  exit 1
fi

AGENT_NAME="${LIVEKIT_AGENT_NAME:-wise-support-agent-2}"
ROOM_PREFIX="${LIVEKIT_ROOM_PREFIX:-call-}"
DISPATCH_NAME="${LIVEKIT_DISPATCH_NAME:-wise-support-dispatch-2}"
DISPATCH_METADATA="${LIVEKIT_DISPATCH_METADATA:-job dispatch metadata}"
LIVEKIT_INBOUND_NUMBER_1="${LIVEKIT_INBOUND_NUMBER_PRIMARY:-"+14843985037"}"

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

cat >"$TMP_FILE" <<EOF
{
  "dispatch_rule": {
    "rule": {
      "dispatchRuleIndividual": {
        "roomPrefix": "${ROOM_PREFIX}"
      }
    },
    "name": "${DISPATCH_NAME}",
    "roomConfig": {
      "agents": [
        {
          "agentName": "${AGENT_NAME}",
          "metadata": "${DISPATCH_METADATA}"
        }
      ]
    }
  }
}
EOF

echo "Creating LiveKit dispatch rule '${DISPATCH_NAME}' for agent '${AGENT_NAME}' with room prefix '${ROOM_PREFIX}'..."
lk sip dispatch create "$TMP_FILE"
echo "Dispatch rule created."
echo "Check your LiveKit dashboard to verify the new dispatch rule. Telephony -> Dispatch rules"
