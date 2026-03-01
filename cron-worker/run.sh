#!/bin/sh
set -e

API_URL="${API_URL:-https://cascade-production-d270.up.railway.app}"

echo "=== Cron tick: $(date -u) ==="

echo "Calling /api/cron/daily ..."
curl -sf -X POST "$API_URL/api/cron/daily" \
  -H "X-Cron-Secret: $CRON_SECRET" \
  -H "Content-Type: application/json" \
  && echo " -> daily OK" \
  || echo " -> daily FAILED (exit $?)"

echo "Calling /api/cron/trial-check ..."
curl -sf -X POST "$API_URL/api/cron/trial-check" \
  -H "X-Cron-Secret: $CRON_SECRET" \
  -H "Content-Type: application/json" \
  && echo " -> trial-check OK" \
  || echo " -> trial-check FAILED (exit $?)"

echo "=== Done ==="
