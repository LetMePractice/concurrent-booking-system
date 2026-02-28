#!/bin/bash
# Elite Stress Test Runner
# Run all critical tests and generate report

set -e

API_URL="${API_URL:-http://localhost:8000}"
RESULTS_DIR="stress_test_results"

echo "========================================"
echo "ELITE STRESS TEST SUITE"
echo "========================================"
echo ""
echo "API: $API_URL"
echo "Results: $RESULTS_DIR"
echo ""

# Check if API is running
if ! curl -s "$API_URL/health" > /dev/null; then
    echo "❌ API not responding at $API_URL"
    echo "Start backend first: cd backend/docker && docker compose up -d"
    exit 1
fi

echo "✓ API is running"
echo ""

mkdir -p "$RESULTS_DIR"

# Test 1: Concurrency
echo "========================================"
echo "TEST 1: CONCURRENCY (100 users → 10 seats)"
echo "========================================"
echo ""

locust -f backend/elite_locustfile.py \
    --host="$API_URL" \
    --tags concurrency \
    --headless \
    -u 100 \
    -r 50 \
    --run-time 30s \
    --csv="$RESULTS_DIR/concurrency" \
    --html="$RESULTS_DIR/concurrency.html"

echo ""
echo "✓ Concurrency test complete"
echo "Check: $RESULTS_DIR/concurrency.html"
echo ""

# Test 2: Throughput (with cache)
echo "========================================"
echo "TEST 2: THROUGHPUT (with Redis cache)"
echo "========================================"
echo ""

locust -f backend/elite_locustfile.py \
    --host="$API_URL" \
    --tags throughput \
    --headless \
    -u 100 \
    -r 20 \
    --run-time 60s \
    --csv="$RESULTS_DIR/throughput_cached" \
    --html="$RESULTS_DIR/throughput_cached.html"

echo ""
echo "✓ Throughput test complete"
echo "Check: $RESULTS_DIR/throughput_cached.html"
echo ""

# Test 3: Edge cases
echo "========================================"
echo "TEST 3: EDGE CASES (bad input)"
echo "========================================"
echo ""

locust -f backend/elite_locustfile.py \
    --host="$API_URL" \
    --tags edge \
    --headless \
    -u 20 \
    -r 5 \
    --run-time 30s \
    --csv="$RESULTS_DIR/edge_cases" \
    --html="$RESULTS_DIR/edge_cases.html"

echo ""
echo "✓ Edge case test complete"
echo "Check: $RESULTS_DIR/edge_cases.html"
echo ""

# Test 4: Realistic workload
echo "========================================"
echo "TEST 4: REALISTIC WORKLOAD (mixed traffic)"
echo "========================================"
echo ""

locust -f backend/elite_locustfile.py \
    --host="$API_URL" \
    --headless \
    -u 200 \
    -r 20 \
    --run-time 120s \
    --csv="$RESULTS_DIR/realistic" \
    --html="$RESULTS_DIR/realistic.html"

echo ""
echo "✓ Realistic workload test complete"
echo "Check: $RESULTS_DIR/realistic.html"
echo ""

# Summary
echo "========================================"
echo "ALL TESTS COMPLETE"
echo "========================================"
echo ""
echo "Results saved to: $RESULTS_DIR/"
echo ""
echo "Next steps:"
echo "  1. Check HTML reports for metrics"
echo "  2. Verify no overbooking in database"
echo "  3. Compare cached vs uncached performance"
echo "  4. Document findings in README"
echo ""
