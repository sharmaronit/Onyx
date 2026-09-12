#!/bin/zsh
# Onyx macOS heartbeat-only endpoint agent.
# It reports the Mac as a real connected endpoint; it does not collect security telemetry.

set -eu

API_URL="${ONYX_API_URL:-}"
API_KEY="${ONYX_INGEST_API_KEY:-}"
ENDPOINT_ID="${ONYX_ENDPOINT_ID:-}"
TOPOLOGY="${ONYX_TOPOLOGY:-enterprise_20n}"
POLL_SECONDS="${ONYX_POLL_SECONDS:-5}"

if [[ -z "$API_URL" || -z "$API_KEY" || -z "$ENDPOINT_ID" ]]; then
  print "Set ONYX_API_URL, ONYX_INGEST_API_KEY, and ONYX_ENDPOINT_ID before starting this agent."
  exit 1
fi

API_URL="${API_URL%/}"
HOSTNAME_VALUE="$(scutil --get ComputerName 2>/dev/null || hostname)"
IP_ADDRESS="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
PLATFORM_VALUE="$(sw_vers -productName 2>/dev/null || print macOS) $(sw_vers -productVersion 2>/dev/null || true)"

while true; do
  if /usr/bin/curl --fail --silent --show-error --connect-timeout 5 --max-time 15 \
    -X POST "$API_URL/api/endpoints/heartbeat" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    --data "{\"endpoint_id\":\"$ENDPOINT_ID\",\"hostname\":\"$HOSTNAME_VALUE\",\"ip_address\":\"$IP_ADDRESS\",\"topology\":\"$TOPOLOGY\",\"agent_version\":\"macos-heartbeat-1.0.0\",\"platform\":\"$PLATFORM_VALUE\",\"quarantined\":false,\"metadata\":{\"telemetry_mode\":\"heartbeat_only\",\"response_capable\":false}}" \
    >/dev/null; then
    print "[$(date '+%H:%M:%S')] Connected to Onyx"
  else
    print "[$(date '+%H:%M:%S')] Heartbeat failed; retrying."
  fi
  sleep "$POLL_SECONDS"
done
