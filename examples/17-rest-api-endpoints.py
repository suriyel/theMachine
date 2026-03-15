"""Example: REST API Endpoints (Feature #17)

This example demonstrates how to use the REST API endpoints for querying.

The Query Service exposes:
1. POST /api/v1/query - Submit query via JSON body
2. GET /api/v1/query - Submit query via query parameters
3. GET /api/v1/health - Health check (no auth required)
4. GET /api/v1/metrics - Prometheus metrics (no auth required)
"""

import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "your-api-key-here"  # Replace with a valid API key


def example_post_query():
    """Example: POST /api/v1/query with JSON body."""
    print("=== POST /api/v1/query ===\n")

    url = f"{BASE_URL}/api/v1/query"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    # Natural language query
    payload = {
        "query": "how to use spring WebClient timeout",
        "query_type": "natural_language",
        "top_k": 3
    }

    response = requests.post(url, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

    # With repository filter
    payload_with_repo = {
        "query": "timeout configuration",
        "repo": "spring-framework",
        "language": "Java"
    }

    response = requests.post(url, json=payload_with_repo, headers=headers)
    print(f"Status (with repo filter): {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def example_get_query():
    """Example: GET /api/v1/query with query parameters."""
    print("=== GET /api/v1/query ===\n")

    url = f"{BASE_URL}/api/v1/query"
    headers = {"X-API-Key": API_KEY}
    params = {
        "query": "WebClient timeout",
        "query_type": "natural_language",
        "top_k": 3
    }

    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

    # Symbol query
    params_symbol = {
        "query": "org.springframework.web.client.RestTemplate",
        "query_type": "symbol"
    }

    response = requests.get(url, headers=headers, params=params_symbol)
    print(f"Status (symbol query): {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def example_health_check():
    """Example: GET /api/v1/health (no auth required)."""
    print("=== GET /api/v1/health ===\n")

    url = f"{BASE_URL}/api/v1/health"
    # No X-API-Key header needed

    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def example_metrics():
    """Example: GET /api/v1/metrics (no auth required)."""
    print("=== GET /api/v1/metrics ===\n")

    url = f"{BASE_URL}/api/v1/metrics"
    # No X-API-Key header needed

    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"First 500 chars of metrics:\n{response.text[:500]}")
    print()


def example_error_cases():
    """Example: Error handling."""
    print("=== Error Cases ===\n")

    url = f"{BASE_URL}/api/v1/query"

    # Missing API key
    print("1. Missing API key:")
    response = requests.post(url, json={"query": "test"})
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json()}")
    print()

    # Invalid API key
    print("2. Invalid API key:")
    headers = {"X-API-Key": "invalid-key"}
    response = requests.post(url, json={"query": "test"}, headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json()}")
    print()

    # Empty query
    print("3. Empty query:")
    headers = {"X-API-Key": API_KEY}
    response = requests.post(url, json={"query": ""}, headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Error: {response.json()}")
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("REST API Endpoints Example")
    print("=" * 60 + "\n")

    # Note: Service must be running
    # Start with: uvicorn src.query.main:app --reload

    try:
        example_health_check()
        example_metrics()
        example_post_query()
        example_get_query()
        example_error_cases()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Query Service")
        print("Make sure the service is running on http://localhost:8000")
        print("Start with: uvicorn src.query.main:app --reload")


if __name__ == "__main__":
    main()
