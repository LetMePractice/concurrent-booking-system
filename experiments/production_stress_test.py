#!/usr/bin/env python3
"""
Production-Grade Stress Test
Tests what actually breaks in production.
"""

import asyncio
import time
import statistics
from dataclasses import dataclass, field
from typing import List
import random

@dataclass
class Metrics:
    successful: int = 0
    conflicts: int = 0
    errors: int = 0
    retries: List[int] = field(default_factory=list)
    response_times: List[float] = field(default_factory=list)
    
    def percentile(self, p: float) -> float:
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        idx = int(len(sorted_times) * p)
        return sorted_times[min(idx, len(sorted_times)-1)]
    
    def avg_retries(self) -> float:
        return statistics.mean(self.retries) if self.retries else 0

@dataclass
class Event:
    id: int
    available_seats: int
    version: int = 0

class ProductionBookingSystem:
    def __init__(self, total_seats: int):
        self.event = Event(id=1, available_seats=total_seats)
        self.lock = asyncio.Lock()
        self.metrics = Metrics()
        self.db_operations = 0
        
    async def book_with_optimistic_locking(self, user_id: int, max_retries: int = 5):
        """Real optimistic locking with retry tracking."""
        start = time.time()
        retry_count = 0
        
        for attempt in range(max_retries):
            retry_count = attempt
            self.db_operations += 1
            
            # Read current version
            current_version = self.event.version
            current_seats = self.event.available_seats
            
            # Simulate network/DB delay (reduced)
            await asyncio.sleep(random.uniform(0.0001, 0.0005))
            
            # Conditional UPDATE (atomic)
            async with self.lock:
                self.db_operations += 1
                
                # Check version hasn't changed (someone else modified)
                if self.event.version != current_version:
                    continue  # Retry
                
                # Check seats available
                if self.event.available_seats <= 0:
                    elapsed = (time.time() - start) * 1000
                    self.metrics.conflicts += 1
                    self.metrics.response_times.append(elapsed)
                    self.metrics.retries.append(retry_count)
                    return False
                
                # Book seat
                self.event.available_seats -= 1
                self.event.version += 1
                
                elapsed = (time.time() - start) * 1000
                self.metrics.successful += 1
                self.metrics.response_times.append(elapsed)
                self.metrics.retries.append(retry_count)
                return True
        
        # Max retries exceeded
        elapsed = (time.time() - start) * 1000
        self.metrics.errors += 1
        self.metrics.response_times.append(elapsed)
        self.metrics.retries.append(retry_count)
        return False

def print_header(text: str):
    print(f"\n{'='*70}")
    print(f"{text:^70}")
    print(f"{'='*70}\n")

def print_metrics(metrics: Metrics, duration: float, db_ops: int):
    total = metrics.successful + metrics.conflicts + metrics.errors
    
    print(f"Duration:              {duration:.2f}s")
    print(f"Total requests:        {total}")
    print(f"Throughput:            {total/duration:.1f} req/s")
    print()
    print(f"✓ Successful:          {metrics.successful}")
    print(f"✗ Conflicts (409):     {metrics.conflicts}")
    print(f"✗ Errors (timeout):    {metrics.errors}")
    print()
    print(f"Conflict rate:         {metrics.conflicts/total*100:.1f}%")
    print(f"Error rate:            {metrics.errors/total*100:.1f}%")
    print()
    
    if metrics.response_times:
        print(f"Response times:")
        print(f"  Avg:  {statistics.mean(metrics.response_times):>8.1f}ms")
        print(f"  P50:  {metrics.percentile(0.50):>8.1f}ms")
        print(f"  P95:  {metrics.percentile(0.95):>8.1f}ms")
        print(f"  P99:  {metrics.percentile(0.99):>8.1f}ms")
        print(f"  Max:  {max(metrics.response_times):>8.1f}ms")
    
    print()
    if metrics.retries:
        print(f"Retries:")
        print(f"  Avg:  {metrics.avg_retries():>8.2f}")
        print(f"  Max:  {max(metrics.retries):>8}")
        retry_0 = sum(1 for r in metrics.retries if r == 0)
        retry_1 = sum(1 for r in metrics.retries if r == 1)
        retry_2 = sum(1 for r in metrics.retries if r == 2)
        retry_3plus = sum(1 for r in metrics.retries if r >= 3)
        print(f"  0 retries: {retry_0:>4} ({retry_0/len(metrics.retries)*100:.1f}%)")
        print(f"  1 retry:   {retry_1:>4} ({retry_1/len(metrics.retries)*100:.1f}%)")
        print(f"  2 retries: {retry_2:>4} ({retry_2/len(metrics.retries)*100:.1f}%)")
        print(f"  3+ retries:{retry_3plus:>4} ({retry_3plus/len(metrics.retries)*100:.1f}%)")
    
    print()
    print(f"DB operations:         {db_ops}")
    print(f"DB ops per request:    {db_ops/total:.2f}")

async def test_scenario(name: str, users: int, seats: int):
    print_header(name)
    print(f"Users: {users} | Seats: {seats} | Contention: {users/seats:.1f}x\n")
    
    system = ProductionBookingSystem(seats)
    
    start_time = time.time()
    tasks = [system.book_with_optimistic_locking(i) for i in range(users)]
    await asyncio.gather(*tasks)
    duration = time.time() - start_time
    
    print_metrics(system.metrics, duration, system.db_operations)
    
    # Verify
    print()
    print(f"Final seats:           {system.event.available_seats}")
    
    overbooking = system.metrics.successful > seats
    negative = system.event.available_seats < 0
    
    if not overbooking and not negative:
        print(f"\n✓ PASS: No overbooking ({system.metrics.successful} ≤ {seats})")
    else:
        print(f"\n✗ FAIL: OVERBOOKING DETECTED!")
        if overbooking:
            print(f"  {system.metrics.successful} bookings > {seats} seats")
        if negative:
            print(f"  Negative seats: {system.event.available_seats}")
    
    return system.metrics

async def main():
    print_header("PRODUCTION-GRADE STRESS TEST")
    print("Testing real production scenarios:\n")
    print("  1. Moderate contention (100 users / 10 seats)")
    print("  2. HIGH contention (1000 users / 10 seats)")
    print("  3. Low contention (1000 users / 500 seats)")
    
    # Test 1: Moderate contention (your original test)
    await test_scenario(
        "TEST 1: MODERATE CONTENTION",
        users=100,
        seats=10
    )
    await asyncio.sleep(0.5)
    
    # Test 2: HIGH contention - this is where things break
    await test_scenario(
        "TEST 2: HIGH CONTENTION (The Real Test)",
        users=1000,
        seats=10
    )
    await asyncio.sleep(0.5)
    
    # Test 3: Low contention - optimistic should shine
    await test_scenario(
        "TEST 3: LOW CONTENTION",
        users=1000,
        seats=500
    )
    
    # Summary
    print_header("ANALYSIS")
    print("What to look for:\n")
    print("HIGH CONTENTION (1000/10):")
    print("  - High retry rate (>50%) = expected")
    print("  - P99 latency spike = retry storm")
    print("  - DB ops per request >2 = inefficient")
    print()
    print("LOW CONTENTION (1000/500):")
    print("  - Low retry rate (<10%) = good")
    print("  - Consistent latency = efficient")
    print("  - DB ops per request ~2 = optimal")
    print()
    print("If HIGH contention causes:")
    print("  - >3 avg retries → need queue-based system")
    print("  - P99 >500ms → need better strategy")
    print("  - Errors >5% → connection pool too small")
    print()
    print("Production-ready means knowing WHEN it breaks.")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
