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

## Architecture

- **FastAPI** - Async Python web framework
- **PostgreSQL** - Optimistic locking with version field
- **Redis** - Caching layer (5.5x faster)
- **Docker** - Containerized deployment

## Performance

**Tested with 1000 concurrent users:**
- ✓ Zero overbookings
- ✓ <100ms P99 latency
- ✓ 5.5x faster with Redis caching

**Key finding:** Optimistic locking creates 10x load amplification from retry storms. See [Performance Analysis](docs/PERFORMANCE_FINDINGS.md) for details.

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

## Features

- Optimistic locking with version field
- Redis caching (5.5x faster)
- Database indexes (14.7x faster queries)
- Prometheus metrics at `/metrics`
- Stress tested with 1000 concurrent users
- Zero overbookings verified

## Documentation

- [Architecture Overview](docs/OVERVIEW.md)
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md)
- [Performance Analysis](docs/PERFORMANCE_FINDINGS.md)
- [Stress Testing](docs/STRESS_TESTING.md)

## Tech Stack

- FastAPI 0.115 + SQLAlchemy 2.0
- PostgreSQL 15 + Redis 7
- Docker + Alembic migrations
- pytest + Locust load testing

## Use Cases

- Event ticketing (concerts, conferences)
- Restaurant reservations
- Hotel/flight bookings
- Appointment scheduling
- Limited inventory sales

## License

MIT
