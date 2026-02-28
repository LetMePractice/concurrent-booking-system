#!/usr/bin/env python3
"""
Simple stress test for the Event Booking API.
Tests concurrent booking to verify overbooking prevention.
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict

API_URL = "http://localhost:8000"
CONCURRENT_USERS = 50
SEATS_AVAILABLE = 10

class StressTest:
    def __init__(self):
        self.results = {
            "successful_bookings": 0,
            "failed_bookings": 0,
            "conflicts": 0,
            "errors": 0,
            "response_times": []
        }
        self.event_id = None
        self.tokens = []

    async def register_and_login(self, session: aiohttp.ClientSession, user_num: int) -> str:
        """Register a user and return auth token."""
        email = f"stress_test_{user_num}_{int(time.time())}@test.com"
        username = f"stress_{user_num}_{int(time.time())}"
        password = "test123"

        # Register
        await session.post(f"{API_URL}/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": password
        })

        # Login
        async with session.post(f"{API_URL}/api/v1/auth/login", json={
            "email": email,
            "password": password
        }) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["access_token"]
        return None

    async def create_test_event(self, session: aiohttp.ClientSession, token: str):
        """Create an event with limited seats."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        headers = {"Authorization": f"Bearer {token}"}
        async with session.post(f"{API_URL}/api/v1/events/", 
            json={
                "title": f"Stress Test Event {int(time.time())}",
                "description": "Testing concurrent bookings",
                "date": future_date,
                "location": "Test Venue",
                "seat_count": SEATS_AVAILABLE
            },
            headers=headers
        ) as resp:
            if resp.status == 201:
                data = await resp.json()
                self.event_id = data["id"]
                print(f"✓ Created event {self.event_id} with {SEATS_AVAILABLE} seats")

    async def book_seat(self, session: aiohttp.ClientSession, token: str, user_num: int):
        """Attempt to book a seat."""
        if not self.event_id:
            return

        headers = {"Authorization": f"Bearer {token}"}
        start = time.time()
        
        try:
            async with session.post(f"{API_URL}/api/v1/bookings/",
                json={"event_id": self.event_id, "seat_count": 1},
                headers=headers
            ) as resp:
                elapsed = (time.time() - start) * 1000
                self.results["response_times"].append(elapsed)
                
                if resp.status == 201:
                    self.results["successful_bookings"] += 1
                    print(f"✓ User {user_num} booked seat ({elapsed:.0f}ms)")
                elif resp.status == 409:
                    self.results["conflicts"] += 1
                    print(f"✗ User {user_num} conflict - sold out ({elapsed:.0f}ms)")
                else:
                    self.results["failed_bookings"] += 1
                    print(f"✗ User {user_num} failed: {resp.status} ({elapsed:.0f}ms)")
        except Exception as e:
            self.results["errors"] += 1
            print(f"✗ User {user_num} error: {e}")

    async def run(self):
        """Execute the stress test."""
        print(f"\n{'='*60}")
        print(f"STRESS TEST: {CONCURRENT_USERS} users → {SEATS_AVAILABLE} seats")
        print(f"{'='*60}\n")

        async with aiohttp.ClientSession() as session:
            # Setup phase
            print("Phase 1: Setting up users...")
            setup_tasks = [self.register_and_login(session, i) for i in range(CONCURRENT_USERS)]
            self.tokens = await asyncio.gather(*setup_tasks)
            self.tokens = [t for t in self.tokens if t]
            print(f"✓ Created {len(self.tokens)} users\n")

            if not self.tokens:
                print("✗ Failed to create users")
                return

            # Create event
            print("Phase 2: Creating test event...")
            await self.create_test_event(session, self.tokens[0])
            if not self.event_id:
                print("✗ Failed to create event")
                return
            print()

            # Stress test phase
            print(f"Phase 3: {CONCURRENT_USERS} users booking simultaneously...")
            print("-" * 60)
            start_time = time.time()
            
            booking_tasks = [self.book_seat(session, token, i) for i, token in enumerate(self.tokens)]
            await asyncio.gather(*booking_tasks)
            
            total_time = time.time() - start_time

            # Results
            print("\n" + "="*60)
            print("RESULTS")
            print("="*60)
            print(f"Total time:          {total_time:.2f}s")
            print(f"Successful bookings: {self.results['successful_bookings']}")
            print(f"Conflicts (409):     {self.results['conflicts']}")
            print(f"Failed bookings:     {self.results['failed_bookings']}")
            print(f"Errors:              {self.results['errors']}")
            
            if self.results["response_times"]:
                times = sorted(self.results["response_times"])
                print(f"\nResponse times:")
                print(f"  Avg: {sum(times)/len(times):.0f}ms")
                print(f"  P50: {times[len(times)//2]:.0f}ms")
                print(f"  P95: {times[int(len(times)*0.95)]:.0f}ms")
                print(f"  P99: {times[int(len(times)*0.99)]:.0f}ms")

            # Verify no overbooking
            print("\n" + "="*60)
            if self.results["successful_bookings"] <= SEATS_AVAILABLE:
                print(f"✓ PASS: No overbooking detected!")
                print(f"  {self.results['successful_bookings']} bookings ≤ {SEATS_AVAILABLE} seats")
            else:
                print(f"✗ FAIL: OVERBOOKING DETECTED!")
                print(f"  {self.results['successful_bookings']} bookings > {SEATS_AVAILABLE} seats")
            print("="*60 + "\n")

if __name__ == "__main__":
    test = StressTest()
    asyncio.run(test.run())
