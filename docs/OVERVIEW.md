# What Is This Project?

## Overview

This is a **production-grade event booking system** that demonstrates how to handle **concurrent seat reservations** without overbooking.

**Think:** Ticketmaster, Eventbrite, or any system where multiple people try to book limited seats simultaneously.

---

## Why Does This Exist?

### The Problem

When 1000 people try to book the last 10 seats at the same time:
- **Bad system:** Books 1000 seats (overbooking disaster)
- **This system:** Books exactly 10 seats, rejects 990

### What Makes It Special

Most "booking projects" just show CRUD operations.

This project shows:
- ✓ **Concurrency control** - No overbooking under any load
- ✓ **Performance testing** - Tested with 1000 concurrent users
- ✓ **Scaling analysis** - Documents exactly where it breaks
- ✓ **Production patterns** - Caching, indexing, admission control
- ✓ **Honest assessment** - Shows failures, not just successes

---

## Who Is This For?

### 1. **Job Seekers**
Use this to demonstrate:
- Backend engineering skills
- Distributed systems understanding
- Production thinking
- Performance optimization

### 2. **Students Learning Backend**
Learn:
- How to prevent race conditions
- How to test at scale
- How to optimize databases
- How to document tradeoffs

### 3. **Engineers Building Booking Systems**
Copy:
- Optimistic locking pattern
- Admission control pattern
- Stress testing approach
- Performance documentation

---

## How To Use This Project

### Quick Start (5 minutes)

```bash
# 1. Clone the repo
git clone <your-repo>
cd project1-api

# 2. Start backend
cd backend/docker
docker compose up -d
docker compose exec api alembic upgrade head

# 3. Open browser
# API: http://localhost:8000/docs
```

### Run Stress Tests (10 minutes)

```bash
# Quick test (no backend needed)
python3 mock_stress_test.py

# Full test suite (requires backend)
./run_stress_tests.sh

# Verify no overbooking
./verify_no_overbooking.sh
```

### Study The Code (30 minutes)

**Key files to read:**

1. **Concurrency logic:**
   - `backend/app/services/booking_service.py` - Optimistic locking
   - `experiments/admission_control.py` - Admission control pattern

2. **Performance tests:**
   - `production_stress_test.py` - Load testing
   - `backend/locust/locustfile.py` - Locust scenarios

3. **Documentation:**
   - `PERFORMANCE_FINDINGS.md` - Test results & analysis
   - `backend/README.md` - Architecture details
   - `STRESS_TESTING.md` - Testing guide

---

## What Can Others Learn From This?

### 1. **Concurrency Patterns**

**Optimistic Locking:**
```python
# Read with version
event = db.get(Event, event_id)  # version = 5

# Conditional update
UPDATE events 
SET available_seats = available_seats - 1,
    version = version + 1
WHERE id = :id 
  AND version = 5  -- Only if unchanged
  AND available_seats >= 1
```

**When to use:** Low/medium contention (<100 concurrent users)

---

**Admission Control:**
```python
# Fast check in Redis (1ms)
if available_seats - reserved_seats <= 0:
    return 409  # Fail fast

# Reserve seat
reserved_seats += 1

# Try DB write
if db.book_seat():
    available_seats -= 1
    reserved_seats -= 1
```

**When to use:** High contention (1000+ concurrent users)

---

### 2. **Performance Testing Methodology**

**Don't just test if it works. Test:**
- ✓ Where it breaks (500 users? 1000?)
- ✓ How it breaks (errors? latency? crashes?)
- ✓ Resource usage (CPU, memory, connections)
- ✓ Load amplification (retries multiply load)

**Example from this project:**
```
Test: 1000 users → 10 seats

Optimistic locking:
- 99.5% error rate ✗
- 10x load amplification ✗
- Connection pool exhausted ✗

Admission control:
- 0% error rate ✓
- 0.02x load amplification ✓
- Constant latency ✓
```

---

### 3. **Database Optimization**

**Before optimization:**
```sql
SELECT * FROM events WHERE date > NOW() ORDER BY date;
-- Sequential scan: 220ms
```

**After adding composite index:**
```sql
CREATE INDEX ix_events_available_date 
ON events(available_seats, date);
-- Index scan: 15ms (14.7x faster)
```

**Lesson:** Indexes matter. Measure before/after.

---

### 4. **Caching Strategy**

**What to cache:**
- ✓ Event listings (changes rarely)
- ✓ Read-heavy endpoints

**What NOT to cache:**
- ✗ Available seat counts (changes constantly)
- ✗ Data used in write operations

**Results:**
- With Redis: 40ms avg, 900 req/s
- Without Redis: 220ms avg, 180 req/s
- **5.5x improvement**

---

### 5. **Honest Documentation**

**Bad documentation:**
> "This system handles high concurrency."

**Good documentation (from this project):**
> "Handles up to 100 concurrent users per event. Breaks at 1000+ users with 99% error rate. Fix: Admission control or queue-based system."

**Why this matters:** Shows you understand limits and can architect solutions.

---

## How To Adapt This For Your Use Case

### For E-commerce (Product Inventory)
Replace:
- `events` → `products`
- `available_seats` → `stock_quantity`
- Same concurrency patterns apply

### For Restaurant Reservations
Replace:
- `events` → `time_slots`
- `available_seats` → `table_capacity`
- Add time-based expiry

### For Hotel Bookings
Replace:
- `events` → `rooms`
- `available_seats` → `room_availability`
- Add date range logic

**Core pattern stays the same:** Prevent overbooking under concurrent access.

---

## Key Takeaways

### What This Project Proves

1. **Correctness:** 0 overbookings in all tests
2. **Performance:** <100ms P99 latency at normal load
3. **Scalability:** Documented breaking points (500, 1000, 2000 users)
4. **Production thinking:** Caching, indexing, monitoring, tradeoffs

### What Makes It Interview-Ready

- ✓ Real concurrency problem solved
- ✓ Quantified performance (not just "it's fast")
- ✓ Tested at scale (1000 concurrent users)
- ✓ Honest about limitations
- ✓ Shows architectural evolution

### What Makes It Production-Ready

- ✓ No overbooking (correctness)
- ✓ Database constraints (safety net)
- ✓ Caching (performance)
- ✓ Error handling (reliability)
- ✓ Documented tradeoffs (maintainability)

**For normal scale:** Production-ready  
**For viral scale:** Needs admission control or queue system (documented in PERFORMANCE_FINDINGS.md)

---

## Next Steps

### To Use This Project

1. **Clone and run** - See Quick Start above
2. **Read the code** - Focus on booking_service.py
3. **Run stress tests** - See what breaks
4. **Read PERFORMANCE_FINDINGS.md** - Understand tradeoffs

### To Learn From This Project

1. **Study concurrency patterns** - Optimistic vs pessimistic vs admission control
2. **Study testing methodology** - How to stress test properly
3. **Study documentation** - How to document performance honestly

### To Build Your Own

1. **Start simple** - Basic CRUD first
2. **Add concurrency control** - Optimistic locking
3. **Test at scale** - Find breaking points
4. **Optimize** - Caching, indexing
5. **Document honestly** - What works, what breaks, why

---

## Questions?

**Q: Is this production-ready?**  
A: For normal scale (100 concurrent users per event), yes. For viral scale (1000+), needs admission control.

**Q: Can I use this code?**  
A: Yes, MIT license. Copy patterns, adapt to your use case.

**Q: What's the most important lesson?**  
A: Test at scale. "Works" ≠ "Works at scale". Document where it breaks.

**Q: How do I show this to employers?**  
A: Link to GitHub. Highlight PERFORMANCE_FINDINGS.md. Explain tradeoffs in interviews.

---

## License

MIT - Use freely, adapt to your needs.

## Author

Built to demonstrate production-grade backend engineering and distributed systems thinking.
