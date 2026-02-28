#!/bin/bash
# Load testing script with result collection
# Runs Locust in headless mode and saves CSV results

set -e

HOST="${1:-http://localhost:8000}"
USERS="${2:-100}"
SPAWN_RATE="${3:-10}"
DURATION="${4:-60s}"
RESULTS_DIR="results"

mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "========================================"
echo "Event Booking API - Load Test"
echo "========================================"
echo "Host:       $HOST"
echo "Users:      $USERS"
echo "Spawn Rate: $SPAWN_RATE/s"
echo "Duration:   $DURATION"
echo "Results:    $RESULTS_DIR/"
echo "========================================"

# Run with Redis (default)
echo ""
echo "--- Test 1: WITH Redis Cache ---"
locust -f locustfile.py \
  --host="$HOST" \
  --headless \
  -u "$USERS" \
  -r "$SPAWN_RATE" \
  --run-time "$DURATION" \
  --csv="$RESULTS_DIR/with_redis_${TIMESTAMP}" \
  --html="$RESULTS_DIR/with_redis_${TIMESTAMP}.html" \
  2>&1 | tee "$RESULTS_DIR/with_redis_${TIMESTAMP}.log"

echo ""
echo "--- Test 2: WITHOUT Redis Cache ---"
echo "(Disable Redis by setting REDIS_ENABLED=false on the API)"
echo "Skipping automated no-cache test - run manually with:"
echo "  REDIS_ENABLED=false uvicorn app.main:app"
echo "  then re-run this script"

echo ""
echo "========================================"
echo "Results saved to: $RESULTS_DIR/"
echo "Open HTML reports for visual analysis."
echo "========================================"

# Print summary
if [ -f "$RESULTS_DIR/with_redis_${TIMESTAMP}_stats.csv" ]; then
  echo ""
  echo "--- Summary ---"
  cat "$RESULTS_DIR/with_redis_${TIMESTAMP}_stats.csv" | column -t -s','
fi
