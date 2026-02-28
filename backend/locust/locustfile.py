"""
Locust Load Test Suite

Run scenarios:
  locust -f locustfile.py --tags concurrency  # Test overbooking
  locust -f locustfile.py --tags throughput   # Test cache
  locust -f locustfile.py --tags edge         # Test bad input
  locust -f locustfile.py                     # All tests
"""

import random
import string
from locust import HttpUser, task, between, tag, events
from datetime import datetime, timezone, timedelta

# Shared state
EVENT_IDS = []
TOKENS = []
CONCURRENCY_EVENT_ID = None

def random_email():
    return f"load_{random.randint(10000, 99999)}@test.com"

def random_username():
    return "u_" + "".join(random.choices(string.ascii_lowercase, k=8))


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Setup: Create event with limited seats for concurrency test."""
    print("\n" + "="*60)
    print("SETUP: Creating concurrency test event...")
    print("="*60)


class ConcurrencyUser(HttpUser):
    """
    TEST 1: Concurrency - 100 users → 10 seats
    
    Run: locust -f locustfile.py --tags concurrency -u 100 -r 50 --run-time 30s
    
    After test, verify:
      SELECT COUNT(*) FROM bookings WHERE event_id = X;
    Should be ≤ 10
    """
    wait_time = between(0, 0.1)
    
    def on_start(self):
        email = random_email()
        username = random_username()
        
        self.client.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": "test123"
        })
        
        resp = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "test123"
        })
        
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
            
            # Create event with limited seats
            if not CONCURRENCY_EVENT_ID:
                future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                resp = self.client.post("/api/v1/events/", 
                    json={
                        "title": "Concurrency Test Event",
                        "description": "10 seats only",
                        "date": future,
                        "location": "Test",
                        "seat_count": 10
                    },
                    headers=self.headers
                )
                if resp.status_code == 201:
                    globals()["CONCURRENCY_EVENT_ID"] = resp.json()["id"]
                    print(f"\n✓ Created event {CONCURRENCY_EVENT_ID} with 10 seats\n")
        else:
            self.headers = {}
    
    @tag("concurrency")
    @task
    def book_limited_seats(self):
        """All users fight for same 10 seats."""
        if not CONCURRENCY_EVENT_ID or not self.headers:
            return
        
        with self.client.post("/api/v1/bookings/",
            json={"event_id": CONCURRENCY_EVENT_ID, "seat_count": 1},
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code == 201:
                resp.success()
            elif resp.status_code == 409:
                resp.success()  # Expected: sold out
            else:
                resp.failure(f"Unexpected: {resp.status_code}")


class ThroughputUser(HttpUser):
    """
    TEST 2: Throughput - Cache effectiveness
    
    Run twice:
      1. With Redis: locust -f locustfile.py --tags throughput -u 100 -r 20 --run-time 60s
      2. Without Redis: Stop Redis, run again
    
    Compare:
      - Avg response time
      - Requests/sec
      - P95/P99 latency
    """
    wait_time = between(0.1, 0.5)
    
    @tag("throughput", "read")
    @task(10)
    def list_events_cached(self):
        """Hammer the cached endpoint."""
        page = random.randint(1, 5)
        self.client.get(f"/api/v1/events/?page={page}&page_size=20",
            name="/api/v1/events/ [cached]")
    
    @tag("throughput", "read")
    @task(3)
    def get_event_detail(self):
        """Read individual events."""
        if EVENT_IDS:
            event_id = random.choice(EVENT_IDS)
            self.client.get(f"/api/v1/events/{event_id}",
                name="/api/v1/events/{id}")
    
    @tag("throughput")
    @task(1)
    def health_check(self):
        """Monitor system health."""
        self.client.get("/health")


class EdgeCaseUser(HttpUser):
    """
    TEST 3: Edge cases - Bad input handling
    
    Run: locust -f locustfile.py --tags edge -u 20 -r 5 --run-time 30s
    
    System should NOT crash, return proper error codes.
    """
    wait_time = between(0.5, 1.5)
    
    def on_start(self):
        email = random_email()
        resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "username": random_username(),
            "password": "test123"
        })
        
        resp = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "test123"
        })
        
        if resp.status_code == 200:
            self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        else:
            self.headers = {}
    
    @tag("edge")
    @task
    def invalid_event_id(self):
        """Book non-existent event."""
        with self.client.post("/api/v1/bookings/",
            json={"event_id": 999999, "seat_count": 1},
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code in [404, 400]:
                resp.success()
            else:
                resp.failure(f"Expected 404/400, got {resp.status_code}")
    
    @tag("edge")
    @task
    def negative_seats(self):
        """Try to book negative seats."""
        with self.client.post("/api/v1/bookings/",
            json={"event_id": 1, "seat_count": -5},
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code in [400, 422]:
                resp.success()
            else:
                resp.failure(f"Expected 400/422, got {resp.status_code}")
    
    @tag("edge")
    @task
    def zero_seats(self):
        """Try to book zero seats."""
        with self.client.post("/api/v1/bookings/",
            json={"event_id": 1, "seat_count": 0},
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code in [400, 422]:
                resp.success()
            else:
                resp.failure(f"Expected 400/422, got {resp.status_code}")
    
    @tag("edge")
    @task
    def huge_seats(self):
        """Try to book absurd number of seats."""
        with self.client.post("/api/v1/bookings/",
            json={"event_id": 1, "seat_count": 999999},
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code in [400, 409, 422]:
                resp.success()
            else:
                resp.failure(f"Expected 400/409/422, got {resp.status_code}")
    
    @tag("edge")
    @task
    def malformed_json(self):
        """Send garbage data."""
        with self.client.post("/api/v1/bookings/",
            data="not json at all",
            headers=self.headers,
            catch_response=True
        ) as resp:
            if resp.status_code in [400, 422]:
                resp.success()
            else:
                resp.failure(f"Expected 400/422, got {resp.status_code}")
    
    @tag("edge")
    @task
    def missing_auth(self):
        """Try booking without auth."""
        with self.client.post("/api/v1/bookings/",
            json={"event_id": 1, "seat_count": 1},
            catch_response=True
        ) as resp:
            if resp.status_code == 401:
                resp.success()
            else:
                resp.failure(f"Expected 401, got {resp.status_code}")


class RealisticUser(HttpUser):
    """
    TEST 4: Realistic mixed workload
    
    Run: locust -f locustfile.py -u 200 -r 20 --run-time 120s
    
    Simulates real traffic:
      - Mostly browsing (80%)
      - Some bookings (15%)
      - Rare creates (5%)
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        email = random_email()
        self.client.post("/api/v1/auth/register", json={
            "email": email,
            "username": random_username(),
            "password": "test123"
        })
        
        resp = self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "test123"
        })
        
        if resp.status_code == 200:
            self.headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        else:
            self.headers = {}
    
    @task(50)
    def browse_events(self):
        """Most common: browsing."""
        resp = self.client.get("/api/v1/events/?page=1&page_size=20")
        if resp.status_code == 200:
            for event in resp.json().get("events", []):
                if event["id"] not in EVENT_IDS:
                    EVENT_IDS.append(event["id"])
    
    @task(20)
    def view_event(self):
        """View details."""
        if EVENT_IDS:
            self.client.get(f"/api/v1/events/{random.choice(EVENT_IDS)}")
    
    @task(10)
    def book_seats(self):
        """Occasional booking."""
        if EVENT_IDS and self.headers:
            self.client.post("/api/v1/bookings/",
                json={"event_id": random.choice(EVENT_IDS), "seat_count": random.randint(1, 3)},
                headers=self.headers)
    
    @task(3)
    def create_event(self):
        """Rare: create new event."""
        if self.headers:
            future = (datetime.now(timezone.utc) + timedelta(days=random.randint(1, 90))).isoformat()
            resp = self.client.post("/api/v1/events/",
                json={
                    "title": f"Event {random.randint(1, 10000)}",
                    "description": "Test event",
                    "date": future,
                    "location": "Venue",
                    "seat_count": random.randint(10, 500)
                },
                headers=self.headers)
            if resp.status_code == 201:
                EVENT_IDS.append(resp.json()["id"])
