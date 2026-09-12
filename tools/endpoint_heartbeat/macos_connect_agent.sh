#!/bin/zsh
# Onyx macOS connection agent.
# Run with: /bin/zsh macos_connect_agent.sh

set -u

DEFAULT_API_URL="http://10.159.162.209:8020"
API_URL="${ONYX_API_URL:-$DEFAULT_API_URL}"
# Always prompt for the key. This intentionally ignores a previously exported
# ONYX_INGEST_API_KEY so an old value cannot silently cause HTTP 401.
API_KEY=""
ENDPOINT_ID="${ONYX_ENDPOINT_ID:-macbook-demo}"
TOPOLOGY="${ONYX_TOPOLOGY:-enterprise_20n}"
POLL_SECONDS="${ONYX_POLL_SECONDS:-5}"

read -rs "API_KEY?Paste the current Onyx telemetry key: "
print

# Remove carriage returns that can be introduced by copy/paste.
API_KEY="${API_KEY//$'\r'/}"

if [[ -z "$API_KEY" ]]; then
  print -u2 "ERROR: A telemetry key is required."
  exit 1
fi

if [[ "$ENDPOINT_ID" == *[^A-Za-z0-9_.-]* ]]; then
  print -u2 "ERROR: Endpoint ID may contain only letters, numbers, dot, dash, and underscore."
  exit 1
fi

API_URL="${API_URL%/}"
HOSTNAME_VALUE="$(/bin/hostname | /usr/bin/tr -cd 'A-Za-z0-9_.-')"
[[ -n "$HOSTNAME_VALUE" ]] || HOSTNAME_VALUE="macbook"
IP_ADDRESS="$(/usr/sbin/ipconfig getifaddr en0 2>/dev/null || /usr/sbin/ipconfig getifaddr en1 2>/dev/null || true)"
MACOS_VERSION="$(/usr/bin/sw_vers -productVersion 2>/dev/null || print unknown)"

print "Checking Onyx at $API_URL ..."
if ! /usr/bin/curl --fail --silent --show-error --connect-timeout 5 --max-time 10 \
  "$API_URL/api/health" >/dev/null; then
  print -u2 "ERROR: The Mac cannot reach $API_URL. Check Wi-Fi, server IP, port 8020, and firewall."
  exit 2
fi

PAYLOAD="{\"endpoint_id\":\"$ENDPOINT_ID\",\"hostname\":\"$HOSTNAME_VALUE\",\"ip_address\":\"$IP_ADDRESS\",\"topology\":\"$TOPOLOGY\",\"agent_version\":\"macos-connect-2.0.0\",\"platform\":\"macOS $MACOS_VERSION\",\"quarantined\":false,\"metadata\":{\"telemetry_mode\":\"heartbeat_only\",\"response_capable\":false}}"

print "Onyx agent started as $ENDPOINT_ID. Press Ctrl+C to stop."
while true; do
  HTTP_CODE="$(/usr/bin/curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --connect-timeout 5 --max-time 15 \
    -X POST "$API_URL/api/endpoints/heartbeat" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    --data "$PAYLOAD" 2>/dev/null)"
  CURL_EXIT=$?
  if (( CURL_EXIT != 0 )); then
    HTTP_CODE="network-error"
  fi

  case "$HTTP_CODE" in
    200) print "[$(/bin/date '+%H:%M:%S')] Connected to Onyx" ;;
    401) print -u2 "[$(/bin/date '+%H:%M:%S')] ERROR 401: telemetry key was rejected" ;;
    network-error|000) print -u2 "[$(/bin/date '+%H:%M:%S')] Network connection failed" ;;
    *) print -u2 "[$(/bin/date '+%H:%M:%S')] Server returned HTTP $HTTP_CODE" ;;
  esac

  /bin/sleep "$POLL_SECONDS"
done
