"""Example 01: Health Check Endpoint.

Demonstrates starting the FastAPI app and hitting the /api/v1/health endpoint.

Usage:
    python examples/01-health-check.py
"""

from fastapi.testclient import TestClient

from src.query.app import create_app


def main():
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Body:   {response.json()}")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "code-context-retrieval"}
    print("\nHealth check passed!")


if __name__ == "__main__":
    main()
