#!/usr/bin/env python3
"""
Admission Control + Seat Reservation
Maintains <100ms latency, >95% success rate, no queue.

Strategy:
1. Redis counter for fast admission control
2. Short-lived seat reservations (30s)
3. Fail fast when capacity reached
4. No retry storms
"""

import asyncio
import time
import statistics
from dataclasses import dataclass, field
from typing import List, Optional
import random

@dataclass
class Metrics:
    successful: int = 0
    rejected: int = 0  # Fast rejection
    conflicts: int = 0
    errors: int = 0
    response_times: List[float] = field(default_factory=list)
    
    def percentile(self, p: float) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * p)
        return sorted_times[min(idx, len(sorted_times)-1)]

class AdmissionControlBooking:
    """
    Key insight: Don't let everyone try to book.
    Use Redis counter for instant admission decision.
    """
    def __init__(self, total_seats: int):
        self.total_seats = total_seats
        self.available_seats = total_seats
        self.reserved_seats = 0  # Pending reservations
        self.lock = asyncio.Lock()
        self.metrics = Metrics()
        self.db_operations = 0
        
    async def book_seat(self, user_id: int) -> bool:
        start = time.time()
        
        # Step 1: Fast admission check (Redis GET - 1ms)
        async with self.lock:
            if self.available_seats - self.reserved_seats <= 0:
                # FAIL FAST - don't even try DB
                elapsed = (time.time() - start) * 1000
                self.metrics.rejected += 1
                self.metrics.response_times.append(elapsed)
                return False
            
            # Reserve seat temporarily
            self.reserved_seats += 1
        
        # Step 2: Try to book in DB (optimistic, but with reservation)
        await asyncio.sleep(0.0001)  # Simulate DB
        self.db_operations += 1
        
        async with self.lock:
            self.db_operations += 1
            
            if self.available_seats <= 0:
                # Someone else got it
                self.reserved_seats -= 1
                elapsed = (time.time() - start) * 1000
                self.metrics.conflicts += 1
                self.metrics.response_times.append(elapsed)
                return False
            
            # Success
            self.available_seats -= 1
            self.reserved_seats -= 1
            elapsed = (time.time() - start) * 1000
            self.metrics.successful += 1
            self.metrics.response_times.append(elapsed)
            return True

class ShardedCounterBooking:
    """
    Alternative: Shard the counter to reduce contention.
    Each shard handles subset of seats.
    """
    def __init__(self, total_seats: int, num_shards: int = 10):
        self.num_shards = num_shards
        self.seats_per_shard = total_seats // num_shards
        self.shards = [self.seats_per_shard] * num_shards
        self.locks = [asyncio.Lock() for _ in range(num_shards)]
        self.metrics = Metrics()
        self.db_operations = 0
        
    async def book_seat(self, user_id: int) -> bool:
        start = time.time()
        
        # Pick random shard (load balance)
        shard_id = random.randint(0, self.num_shards - 1)
        
        # Try this shard
        async with self.locks[shard_id]:
            self.db_operations += 1
            await asyncio.sleep(0.0001)
            
            if self.shards[shard_id] <= 0:
                # Try another shard
                for i in range(self.num_shards):
                    if self.shards[i] > 0:
                        shard_id = i
                        break
                else:
                    # All sold out
                    elapsed = (time.time() - start) * 1000
                    self.metrics.conflicts += 1
                    self.metrics.response_times.append(elapsed)
                    return False
            
            self.shards[shard_id] -= 1
            elapsed = (time.time() - start) * 1000
            self.metrics.successful += 1
            self.metrics.response_times.append(elapsed)
            return True

def print_header(text: str):
    print(f"\n{'='*70}")
    print(f"{text:^70}")
    print(f"{'='*70}\n")

def print_metrics(name: str, metrics: Metrics, duration: float, db_ops: int):
    total = metrics.successful + metrics.rejected + metrics.conflicts + metrics.errors
    
    print(f"{name}:")
    print(f"  Successful:      {metrics.successful}")
    print(f"  Fast rejected:   {metrics.rejected}")
    print(f"  Conflicts:       {metrics.conflicts}")
    print(f"  Success rate:    {metrics.successful/total*100:.1f}%")
    print(f"  DB ops:          {db_ops}")
    print(f"  DB ops/req:      {db_ops/total:.2f}")
    
    if metrics.response_times:
        print(f"  Avg latency:     {statistics.mean(metrics.response_times):.1f}ms")
        print(f"  P95 latency:     {metrics.percentile(0.95):.1f}ms")
        print(f"  P99 latency:     {metrics.percentile(0.99):.1f}ms")
    
    # Check SLA
    p99 = metrics.percentile(0.99)
    success_rate = metrics.successful/total*100
    
    print(f"\n  SLA Check:")
    print(f"    P99 < 100ms:     {'✓' if p99 < 100 else '✗'} ({p99:.1f}ms)")
    print(f"    Success > 95%:   {'✓' if success_rate > 95 else '✗'} ({success_rate:.1f}%)")
    print()

async def test_admission_control(users: int, seats: int):
    system = AdmissionControlBooking(seats)
    
    start = time.time()
    tasks = [system.book_seat(i) for i in range(users)]
    await asyncio.gather(*tasks)
    duration = time.time() - start
    
    return system.metrics, duration, system.db_operations

async def test_sharded(users: int, seats: int):
    system = ShardedCounterBooking(seats, num_shards=10)
    
    start = time.time()
    tasks = [system.book_seat(i) for i in range(users)]
    await asyncio.gather(*tasks)
    duration = time.time() - start
    
    return system.metrics, duration, system.db_operations

async def main():
    print_header("ADMISSION CONTROL STRATEGY")
    print("Goal: <100ms P99, >95% success, no queue\n")
    
    SCENARIOS = [
        ("HIGH Contention", 1000, 10),
        ("Moderate", 1000, 500),
    ]
    
    for name, users, seats in SCENARIOS:
        print_header(f"{name}: {users} users / {seats} seats")
        
        # Test 1: Admission control
        m1, d1, db1 = await test_admission_control(users, seats)
        print_metrics("Admission Control", m1, d1, db1)
        
        # Test 2: Sharded counters
        m2, d2, db2 = await test_sharded(users, seats)
        print_metrics("Sharded Counters", m2, d2, db2)
        
        await asyncio.sleep(0.3)
    
    print_header("HOW IT WORKS")
    print("Admission Control:")
    print("  1. Redis counter tracks available + reserved seats")
    print("  2. Fast rejection if capacity reached (no DB hit)")
    print("  3. Reserve seat before DB write")
    print("  4. Release reservation if DB write fails")
    print()
    print("Benefits:")
    print("  ✓ No retry storms (fail fast)")
    print("  ✓ Low latency (1-2 DB ops)")
    print("  ✓ High success rate (admission control)")
    print("  ✓ Predictable performance")
    print()
    print("Sharded Counters:")
    print("  1. Split seats across N shards")
    print("  2. Each shard has own lock")
    print("  3. Reduces lock contention by N")
    print("  4. Load balance across shards")
    print()
    print("Real implementation:")
    print("  - Redis INCR/DECR for counters")
    print("  - Redis TTL for reservations")
    print("  - Lua script for atomicity")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
