# Event Booking System

> Concurrency-safe booking API preventing overbooking under high load.

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-red.svg)](https://redis.io/)

## Problem

When 1000 users try to book the last 10 seats simultaneously:
- **Overbook** - Sell more than available
- **Crash** - Connection pool exhausted
- **Timeout** - Retry storms

This system prevents overbooking with optimistic locking and Redis caching.

---

## Architecture

```
┌─────────────┐
│   Clients   │  (1000 concurrent users)
└──────┬──────┘
       │
┌──────▼──────────────────────────────┐
│   Load Balancer / API Gateway       │
└──────┬──────────────────────────────┘
       │
       ├─────────────┬─────────────┐
       │             │             │
┌──────▼──────┐ ┌───▼───┐  ┌─────▼──────┐
│  FastAPI    │ │FastAPI│  │  FastAPI   │
│  Instance 1 │ │   2   │  │  Instance N│
└──────┬──────┘ └───┬───┘  └─────┬──────┘
       │            │             │
       └────────────┼─────────────┘
                    │
       ┌────────────┴────────────┐
       │                         │
┌──────▼──────┐         ┌────────▼────────┐
│    Redis    │         │   PostgreSQL    │
│  (Admission │         │  (Source of     │
│   Control)  │         │    Truth)       │
└─────────────┘         └─────────────────┘
```

**Key Design:**
- **Redis** - Fast admission control (1ms check)
- **PostgreSQL** - Transactional booking with optimistic locking
- **Horizontal scaling** - Stateless API instances

---

## Concurrency Strategies Compared

| Strategy | Success Rate | P99 Latency | DB Ops/Req | Breaks At | Use Case |
|----------|--------------|-------------|------------|-----------|----------|
| **Optimistic Locking** | 0.5% | 44ms | 9.76 | 500 users | Normal load |
| **Queue-based** | 100% | 1228ms | 1.00 | Memory limit | Guaranteed delivery |
| **Admission Control** | 100%* | 2.7ms | 0.02 | Redis capacity | High contention |

*100% of admitted requests. Fast-rejects 99% before DB hit.

**Key Insight:** Optimistic locking creates **10x load amplification** from retry storms under high contention.

---

## Load Amplification Problem

```
Scenario: 1000 users → 10 seats

Optimistic Locking:
  1000 requests
  → 4 avg retries per request
  → 1000 × (1 + 4×2) DB operations
  → 9,000 DB ops
  → Connection pool exhausted
  → 99.5% error rate

Admission Control:
  1000 requests
  → 990 rejected in Redis (1ms)
  → 10 reach DB
  → 20 DB ops total
  → 0% error rate
```

**Approach:** Early admission control reduces write amplification and protects the primary database.

---

## Performance Results

### Test: 1000 Concurrent Users / 10 Seats

**Optimistic Locking:**
```
Success rate:     0.5%
P99 latency:      44ms
DB operations:    9,980
Error rate:       99.5%
Status:           BREAKS ✗
```

**Admission Control:**
```
Success rate:     100% (of admitted)
P99 latency:      2.7ms
DB operations:    20
Error rate:       0%
Status:           SCALES ✓
```

### Cache Performance

| Metric | With Redis | Without Redis | Improvement |
|--------|-----------|---------------|-------------|
| Avg Latency | 40ms | 220ms | **5.5x faster** |
| Throughput | 900 req/s | 180 req/s | **5x higher** |
| P95 Latency | 80ms | 450ms | **5.6x faster** |

---

## Quick Start

```bash
# Start backend
cd backend/docker
docker compose up -d
docker compose exec api alembic upgrade head

# API: http://localhost:8000/docs

# Run stress test
python3 experiments/production_stress_test.py
```

---

## Features

### ✓ Concurrency Control
- Optimistic locking with version field
- Admission control with Redis
- Database constraints as safety net

### ✓ Performance Optimization
- Redis caching (5.5x faster)
- Composite database indexes (14.7x faster queries)
- Connection pool tuning

### ✓ Production Patterns
- Circuit breakers for Redis failures
- Graceful degradation
- Metrics exposure (`/metrics`)
- Structured logging

### ✓ Comprehensive Testing
- Unit tests (pytest)
- Load tests (Locust)
- Stress tests (1000 concurrent users)
- SQL verification scripts

---

## Production Limitations

### ✓ Ready For
- Up to 100 concurrent users per event
- Up to 1,000 total concurrent users
- Read-heavy workloads
- Normal booking scenarios

### ✗ NOT Ready For
- Viral flash sales (1000+ concurrent users per event)
- Multi-region deployment (clock drift, replication lag not handled)
- 10,000+ concurrent users without horizontal scaling

### Known Operational Gaps
- No rate limiting per user
- No distributed tracing
- Redis desync requires manual reconciliation
- Single-region only (no cross-region consistency)
- Circuit breaker is basic (no half-open state)

### To Scale Further
1. Implement admission control (see `experiments/admission_control.py`)
2. Add read replicas for database
3. Deploy Redis cluster
4. Horizontal scaling with load balancer
5. Add rate limiting per user

**Honest assessment:** Suitable for moderate single-region workloads with defined scaling boundaries.

---

## Transaction Model

- **Isolation Level:** READ COMMITTED (PostgreSQL default)
- **Concurrency Guard:** Version column with optimistic locking
- **Safety Net:** Database constraint `CHECK (available_seats >= 0)`
- **Failure Mode:** Retry on version conflict, fail after 3 attempts

---

## Documentation

- [Architecture Overview](docs/OVERVIEW.md) - System design and decisions
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Copy-paste patterns
- [Performance Analysis](docs/PERFORMANCE_FINDINGS.md) - Stress test results
- [Stress Testing](docs/STRESS_TESTING.md) - Testing methodology

---

## Tech Stack

- FastAPI 0.115 + SQLAlchemy 2.0
- PostgreSQL 15 + Redis 7
- Docker + Alembic migrations
- pytest + Locust load testing

---

## Metrics & Observability

System exposes operational metrics at `/metrics`:

```
booking_attempts_total       # Total booking attempts
booking_success_total        # Successful bookings
booking_conflicts_total      # Conflicts (sold out)
admission_rejected_total     # Fast rejections
db_retry_attempts_total      # Retry attempts due to version conflicts
db_connection_pool_size      # Connection pool size
db_connection_pool_overflow  # Pool overflow count
cache_hit_rate              # Redis cache effectiveness
redis_connection_errors_total # Redis failures
redis_circuit_breaker_open   # Circuit breaker state (1=open, 0=closed)
```

---

## Use Cases

- Event ticketing (concerts, conferences)
- Restaurant reservations
- Hotel/flight bookings
- Appointment scheduling
- Limited inventory sales

---

## Key Learnings

- Optimistic locking fails catastrophically under high contention
- Load amplification from retries kills systems
- Fail fast > retry storm
- Test at scale, not just correctness
- Document limitations honestly

---

## License

MIT
