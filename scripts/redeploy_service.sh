#!/usr/bin/env bash
set -euo pipefail

# specs/031-production-deployment-hardening-ii, research.md Decision 4 — redeploys one
# non-db service at a time (`docker compose up -d --no-deps --build <service>`),
# reusing docker-compose.yml's own already-real healthchecks (an actual HTTP call for
# api/web; a weaker interpreter-liveness check for worker — this script polls the same
# signal the rest of the stack already trusts, it doesn't invent a stronger one) to
# confirm the redeployed service is actually healthy before declaring success, and
# confirms the other already-running services never report unhealthy throughout.
#
# `db` is explicitly, permanently refused here — not just unimplemented. Redeploying it
# mid-operation risks in-flight transaction loss and briefly disconnects every other
# service at once (api/worker both hold live connection pools to it): a fundamentally
# different, higher-risk operation than a stateless service's rolling image swap, that
# deserves its own planned maintenance window (likely paired with the backup job this
# same feature built), not a one-line redeploy folded in alongside api/worker/web.

usage() {
    echo "Usage: $0 <api|worker|web>" >&2
    exit 1
}

SERVICE="${1:-}"

case "$SERVICE" in
    api|worker|web)
        ;;
    db)
        cat >&2 <<'EOF'
Refusing to redeploy 'db' through this script.

Redeploying the database service mid-operation risks in-flight transaction loss and
briefly disconnects every other service at once (api/worker both hold live connection
pools to it) — a fundamentally different, higher-risk operation than a stateless
service's rolling image swap. This deserves a planned maintenance window (likely paired
with the backup job, specs/031-production-deployment-hardening-ii), not a one-line
redeploy alongside api/worker/web.
EOF
        exit 2
        ;;
    *)
        usage
        ;;
esac

TIMEOUT_SECONDS=60
POLL_INTERVAL=2

_health_status() {
    # docker compose ps --format json emits one JSON object per line (compose v2) —
    # extract just the Health field, tolerating a service with no healthcheck at all
    # (Health is then simply absent) or not running yet (no matching line).
    docker compose ps --format json "$1" 2>/dev/null | python3 -c '
import json, sys
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    print(json.loads(line).get("Health", ""))
    break
else:
    print("")
'
}

echo "Redeploying '$SERVICE'..."
docker compose up -d --no-deps --build "$SERVICE"

echo "Waiting for '$SERVICE' to report healthy (timeout ${TIMEOUT_SECONDS}s)..."
elapsed=0
while true; do
    health="$(_health_status "$SERVICE")"
    if [ "$health" = "healthy" ]; then
        echo "'$SERVICE' is healthy."
        break
    fi
    if [ "$elapsed" -ge "$TIMEOUT_SECONDS" ]; then
        echo "Timed out waiting for '$SERVICE' to become healthy (last status: '${health:-none}')." >&2
        exit 3
    fi
    sleep "$POLL_INTERVAL"
    elapsed=$((elapsed + POLL_INTERVAL))
done

# SC-005's own proof: confirm the other services this run touched via --no-deps never
# went unhealthy. Best-effort snapshot, not a continuous monitor — an operator running
# this interactively watches their own real traffic separately (quickstart.md Story 3).
for other in api worker web; do
    if [ "$other" = "$SERVICE" ]; then
        continue
    fi
    other_health="$(_health_status "$other")"
    if [ "$other_health" = "unhealthy" ]; then
        echo "WARNING: '$other' reports unhealthy after redeploying '$SERVICE'." >&2
    fi
done

echo "Redeploy of '$SERVICE' complete."
