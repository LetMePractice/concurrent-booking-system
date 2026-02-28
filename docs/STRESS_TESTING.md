# Elite Stress Testing Guide

## What Makes This Project Strong

Not that it runs. That it:
1. **Never overbooks** under any load
2. **Doesn't crash** when things fail
3. **Maintains latency** under pressure
4. **Handles bad input** gracefully
5. **Documents tradeoffs** honestly

---

## Test Suite Overview

### 1. Concurrency Test (Most Critical)
**Goal:** Prove no overbooking under extreme contention

**Scenario:**
- 100 users
- 10 seats available
- All book simultaneously

**Expected:**
- Exactly 10 successful bookings
- 90 conflicts (409)
- 0 overbookings
- No negative seats

**Run:**
```bash
# Quick test (no backend needed)
python3 experiments/production_stress_test.py

# Full Locust test
locust -f backend/locust/locustfile.py --tags concurrency -u 100 -r 50 --run-time 30s

# Verify in database
./verify_no_overbooking.sh
```

**What to check:**
```sql
SELECT COUNT(*) FROM bookings WHERE event_id = X;
-- Must be ≤ 10

SELECT available_seats FROM events WHERE id = X;
-- Must be ≥ 0
```

---

### 2. Throughput Test
**Goal:** Measure cache effectiveness

**Scenario A - With Redis:**
```bash
locust -f backend/locust/locustfile.py --tags throughput -u 100 -r 20 --run-time 60s
```

**Scenario B - Without Redis:**
```bash
docker compose -f backend/docker/docker-compose.yml stop redis
# Run same test
docker compose -f backend/docker/docker-compose.yml start redis
```

**Compare:**
| Metric | With Cache | Without Cache |
|--------|------------|---------------|
| Avg latency | ~40ms | ~220ms |
| P95 latency | ~80ms | ~450ms |
| Requests/sec | ~900 | ~180 |
| Error rate | 0% | 0% |

---

### 3. Database Bottleneck Test
**Goal:** Find query/index problems

**Run:**
```bash
locust -f backend/locust/locustfile.py --tags throughput -u 500 -r 50 --run-time 60s
```

**Monitor:**
```bash
# Watch DB CPU
docker stats

# Check slow queries
docker compose -f backend/docker/docker-compose.yml exec db psql -U postgres -d event_booking -c "
SELECT query, calls, mean_exec_time, max_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"
```

**If DB maxes out CPU:**
- Check missing indexes
- Analyze query plans
- Add composite indexes

---

### 4. Edge Case Test
**Goal:** System doesn't crash on bad input

**Run:**
```bash
locust -f backend/locust/locustfile.py --tags edge -u 20 -r 5 --run-time 30s
```

**Tests:**
- Invalid event_id → 404
- Negative seats → 400/422
- Zero seats → 400/422
- Malformed JSON → 400/422
- Missing auth → 401
- Huge payload → 400/413

**All should return proper errors, not crash.**

---

### 5. Failure Simulation

#### Test A: Kill Redis During Load
```bash
# Start load test
locust -f backend/locust/locustfile.py -u 100 &

# Kill Redis
docker compose -f backend/docker/docker-compose.yml stop redis

# Watch logs - should NOT crash
# Should fallback to DB gracefully
```

**Expected:** Higher latency, but no crashes.

#### Test B: Kill DB During Load
```bash
docker compose -f backend/docker/docker-compose.yml stop db
```

**Expected:** Clean 500 errors, not hanging requests.

---

### 6. Realistic Workload
**Goal:** Mixed traffic pattern

**Run:**
```bash
locust -f backend/locust/locustfile.py -u 200 -r 20 --run-time 120s
```

**Traffic mix:**
- 60% browsing events
- 25% viewing details
- 12% booking
- 3% creating events

**Metrics to track:**
- P95/P99 latency
- Error rate
- Throughput
- Resource usage

---

## Running All Tests

### Quick (No Backend)
```bash
python3 experiments/production_stress_test.py
```

### Full Suite (Requires Backend)
```bash
# Start backend
cd backend/docker && docker compose up -d

# Run all tests
./run_stress_tests.sh

# Verify no overbooking
./verify_no_overbooking.sh
```

---

## Metrics That Matter

### Response Time
- **Avg:** Overall performance
- **P95:** What most users experience
- **P99:** Worst case (still acceptable?)

### Throughput
- **Requests/sec:** System capacity
- **Error rate:** Reliability

### Resource Usage
- **CPU:** Bottleneck indicator
- **Memory:** Leak detection
- **Connections:** Pool sizing

---

## What Good Results Look Like

### Concurrency Test
```
✓ 10 successful bookings
✓ 90 conflicts (expected)
✓ 0 overbookings
✓ Avg response: <50ms
✓ P99 response: <200ms
```

### Throughput Test
```
✓ >500 req/s with cache
✓ Cache hit rate >70%
✓ P95 latency <100ms
✓ 0% error rate
```

### Edge Cases
```
✓ All bad inputs rejected
✓ Proper error codes
✓ No crashes
✓ No 500 errors
```

---

## When Tests Fail

### Overbooking Detected
**Problem:** Race condition in booking logic

**Fix:**
1. Add optimistic locking (version field)
2. Use SELECT FOR UPDATE
3. Add DB constraint: `CHECK (available_seats >= 0)`

### High Latency
**Problem:** Missing indexes or cache

**Fix:**
1. Check query plans: `EXPLAIN ANALYZE`
2. Add indexes on filtered/sorted columns
3. Enable Redis caching
4. Increase connection pool

### Crashes Under Load
**Problem:** Unhandled exceptions

**Fix:**
1. Add try/catch blocks
2. Set timeouts
3. Implement circuit breakers
4. Add graceful degradation

### Cache Not Helping
**Problem:** Cache misses or wrong TTL

**Fix:**
1. Check cache hit rate
2. Adjust TTL
3. Warm cache on startup
4. Use cache-aside pattern

---

## Performance Findings Template

Add this to your README after testing:

```markdown
## Performance Findings

### What Broke First
At 500 concurrent users, connection pool exhausted.
Increased from 5 → 20 connections.

### What Improved Performance Most
Adding composite index on (available_seats, date):
- Before: 220ms avg
- After: 15ms avg
- 14x improvement

### Tradeoffs Made
Chose optimistic locking over pessimistic:
- Pro: 5x better throughput
- Con: 15% retry rate at high contention
- Decision: Acceptable for our scale

### What Would Break at 10,000 Users
1. Single DB instance (need read replicas)
2. Redis single node (need cluster)
3. Optimistic locking retries (need queue)
4. Gunicorn workers (need horizontal scaling)
```

---

## Elite Move: Document Everything

Your README should show:
1. **Test results** (actual numbers)
2. **What broke** (be honest)
3. **What you fixed** (show improvement)
4. **What would break next** (show you understand limits)

This makes you look like an engineer, not a coder.

---

## Quick Reference

```bash
# Run all tests
./run_stress_tests.sh

# Verify no overbooking
./verify_no_overbooking.sh

# Quick mock test
python3 experiments/production_stress_test.py

# Individual tests
locust -f backend/locust/locustfile.py --tags concurrency
locust -f backend/locust/locustfile.py --tags throughput
locust -f backend/locust/locustfile.py --tags edge

# Monitor resources
docker stats
watch -n 1 'curl -s http://localhost:8000/health | jq'
```
