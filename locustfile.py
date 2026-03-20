"""
Locust load test for NFR-001 (Query Latency P95) and NFR-002 (Query Throughput)

Run with:
    locust -f locustfile.py --headless -u 1000 -r 100 -t 10m --host http://localhost:8000

Requirements:
    pip install locust
    Services running: PostgreSQL, Redis, Qdrant, Elasticsearch, Query Service
"""

from locust import HttpUser, task, between, events
import random
import json

# Sample queries for load testing
SAMPLE_QUERIES = [
    "how to configure spring WebClient timeout",
    "RestTemplate execute method",
    "WebClient builder responseTimeout",
    "Spring HttpMessageConverter",
    "Repository annotation Spring Data",
    "Bean configuration Java",
    "Dependency injection example",
    "AOP aspectj pointcut",
    "Transaction management Spring",
    "JPA entity mapping",
]


class QueryUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Simulate realistic think time

    def on_start(self):
        """Initialize user session"""
        # Query service may require auth - check if API key needed
        self.api_key = "test-api-key"  # Replace with valid key if needed

    @task(10)
    def query_natural_language(self):
        """Submit natural language query"""
        query_text = random.choice(SAMPLE_QUERIES)
        payload = {
            "query": query_text,
            "type": "natural_language"
        }
        headers = {"X-API-Key": self.api_key} if self.api_key else {}

        with self.client.post(
            "/api/v1/query",
            json=payload,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                # Check latency from response if available
                if "latency_ms" in data:
                    latency = data["latency_ms"]
                    if latency > 1000:
                        response.failure(f"P95 target missed: {latency}ms > 1000ms")
                    else:
                        response.success()
            else:
                response.failure(f"Status {response.status_code}")

    @task(5)
    def query_symbol(self):
        """Submit symbol query"""
        symbols = [
            "org.springframework.web.client.RestTemplate",
            "org.springframework.web.reactive.function.client.WebClient",
            "org.springframework.stereotype.Repository",
        ]
        payload = {
            "query": random.choice(symbols),
            "type": "symbol"
        }
        headers = {"X-API-Key": self.api_key} if self.api_key else {}

        self.client.post("/api/v1/query", json=payload, headers=headers, name="/api/v1/query [symbol]")

    @task(2)
    def health_check(self):
        """Check service health"""
        self.client.get("/api/v1/health", name="/api/v1/health")

    @task(1)
    def metrics_check(self):
        """Check metrics endpoint"""
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        self.client.get("/api/v1/metrics", headers=headers, name="/api/v1/metrics")


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("Starting load test for NFR-001/002...")
    print(f"Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - print summary"""
    print("\n=== Load Test Results ===")
    stats = environment.stats

    # Calculate P95 from request times
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures

    if total_requests > 0:
        print(f"Total Requests: {total_requests}")
        print(f"Failures: {total_failures}")
        print(f"Failure Rate: {total_failures/total_requests*100:.2f}%")

        # Get response times
        response_times = stats.total.get_response_time_percentile()
        if response_times:
            print(f"Median (50th): {response_times[0]:.2f}ms")
            print(f"75th percentile: {response_times[1]:.2f}ms")
            print(f"90th percentile: {response_times[2]:.2f}ms")
            p95 = response_times[3]
            print(f"95th percentile: {p95:.2f}ms")
            print(f"99th percentile: {response_times[4]:.2f}ms")

            # NFR-001 Check
            if p95 <= 1000:
                print(f"\n✓ NFR-001 PASS: P95 ({p95:.2f}ms) <= 1000ms")
            else:
                print(f"\n✗ NFR-001 FAIL: P95 ({p95:.2f}ms) > 1000ms")

        # NFR-002 Throughput check
        duration = stats.total.duration
        if duration > 0:
            rps = total_requests / duration
            print(f"\nThroughput: {rps:.2f} requests/second")
            if rps >= 1000:
                print(f"✓ NFR-002 PASS: {rps:.2f} QPS >= 1000 QPS")
            else:
                print(f"✗ NFR-002 FAIL: {rps:.2f} QPS < 1000 QPS")
