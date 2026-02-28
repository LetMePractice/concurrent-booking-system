#!/usr/bin/env python3
"""
Mock stress test - simulates concurrent booking without backend.
Demonstrates optimistic locking behavior.
"""

import asyncio
import time
import random
from dataclasses import dataclass
from typing import List

@dataclass
class Event:
    id: int
    available_seats: int
    version: int = 0

class MockBookingSystem:
    def __init__(self, total_seats: int):
        self.event = Event(id=1, available_seats=total_seats)
        self.lock = asyncio.Lock()
        self.successful_bookings = []
        self.conflicts = 0
        self.response_times = []

    async def book_seat_optimistic(self, user_id: int) -> bool:
        """Optimistic locking - read, then conditional update."""
        start = time.time()
        max_retries = 3
        
        for attempt in range(max_retries):
            # Read current state
            current_version = self.event.version
            current_seats = self.event.available_seats
            
            # Simulate network delay
            await asyncio.sleep(random.uniform(0.001, 0.005))
            
            # Try to update (with lock to simulate DB transaction)
            async with self.lock:
                # Check if someone else modified it
                if self.event.version != current_version:
                    continue  # Retry
                
                # Check if seats available
                if self.event.available_seats <= 0:
                    self.conflicts += 1
                    elapsed = (time.time() - start) * 1000
                    self.response_times.append(elapsed)
                    return False
                
                # Book the seat
                self.event.available_seats -= 1
                self.event.version += 1
                self.successful_bookings.append(user_id)
                elapsed = (time.time() - start) * 1000
                self.response_times.append(elapsed)
                return True
        
        # Max retries exceeded
        self.conflicts += 1
        elapsed = (time.time() - start) * 1000
        self.response_times.append(elapsed)
        return False

    async def book_seat_pessimistic(self, user_id: int) -> bool:
        """Pessimistic locking - lock first, then update."""
        start = time.time()
        
        async with self.lock:
            await asyncio.sleep(random.uniform(0.001, 0.005))
            
            if self.event.available_seats <= 0:
                self.conflicts += 1
                elapsed = (time.time() - start) * 1000
                self.response_times.append(elapsed)
                return False
            
            self.event.available_seats -= 1
            self.successful_bookings.append(user_id)
            elapsed = (time.time() - start) * 1000
            self.response_times.append(elapsed)
            return True

    async def book_seat_broken(self, user_id: int) -> bool:
        """Broken implementation - no locking (demonstrates race condition)."""
        start = time.time()
        
        # Read
        current_seats = self.event.available_seats
        await asyncio.sleep(random.uniform(0.001, 0.005))
        
        # Check and update (RACE CONDITION HERE)
        if current_seats > 0:
            self.event.available_seats -= 1
            self.successful_bookings.append(user_id)
            elapsed = (time.time() - start) * 1000
            self.response_times.append(elapsed)
            return True
        
        self.conflicts += 1
        elapsed = (time.time() - start) * 1000
        self.response_times.append(elapsed)
        return False

async def run_test(strategy: str, users: int, seats: int):
    """Run stress test with specified strategy."""
    print(f"\n{'='*60}")
    print(f"Strategy: {strategy.upper()}")
    print(f"Users: {users} | Seats: {seats}")
    print(f"{'='*60}\n")
    
    system = MockBookingSystem(seats)
    
    # Choose booking method
    if strategy == "optimistic":
        book_method = system.book_seat_optimistic
    elif strategy == "pessimistic":
        book_method = system.book_seat_pessimistic
    else:
        book_method = system.book_seat_broken
    
    # Run concurrent bookings
    start_time = time.time()
    tasks = [book_method(i) for i in range(users)]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Results
    successful = sum(results)
    times = sorted(system.response_times)
    
    print(f"Time:        {total_time:.3f}s")
    print(f"Successful:  {successful}")
    print(f"Conflicts:   {system.conflicts}")
    print(f"Final seats: {system.event.available_seats}")
    
    if times:
        print(f"\nResponse times:")
        print(f"  Avg: {sum(times)/len(times):.1f}ms")
        print(f"  P95: {times[int(len(times)*0.95)]:.1f}ms")
        print(f"  Max: {max(times):.1f}ms")
    
    # Verify
    print(f"\n{'='*60}")
    if successful <= seats and system.event.available_seats >= 0:
        print(f"✓ PASS: No overbooking")
    else:
        print(f"✗ FAIL: OVERBOOKING! {successful} bookings > {seats} seats")
    print(f"{'='*60}")

async def main():
    USERS = 100
    SEATS = 10
    
    print("\n" + "="*60)
    print("CONCURRENT BOOKING STRESS TEST")
    print("="*60)
    
    # Test 1: Optimistic locking (what the project uses)
    await run_test("optimistic", USERS, SEATS)
    await asyncio.sleep(0.5)
    
    # Test 2: Pessimistic locking (alternative approach)
    await run_test("pessimistic", USERS, SEATS)
    await asyncio.sleep(0.5)
    
    # Test 3: Broken (no locking - shows the problem)
    await run_test("broken", USERS, SEATS)
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("Optimistic:  Fast, handles contention with retries")
    print("Pessimistic: Slower, serializes all bookings")
    print("Broken:      Fast but ALLOWS OVERBOOKING")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
