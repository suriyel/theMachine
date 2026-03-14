#!/usr/bin/env python3
"""
Example: Storage Client Health Checks

Demonstrates how to use the storage client health check functions
for PostgreSQL, Redis, Qdrant, and Elasticsearch.

Usage:
    # Set environment variables first
    export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
    export REDIS_URL=redis://localhost:6379/0
    export QDRANT_URL=http://localhost:6333
    export ELASTICSEARCH_URL=http://localhost:9200

    # Run the example
    python examples/01-storage-clients.py
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def check_all_services():
    """Check health of all storage services."""
    from src.shared.clients import (
        check_postgres_connection,
        check_redis_connection,
        check_qdrant_connection,
        check_elasticsearch_connection,
    )

    print("=" * 60)
    print("Storage Client Health Checks")
    print("=" * 60)

    # PostgreSQL
    print("\n📊 PostgreSQL:")
    try:
        result = await check_postgres_connection()
        print(f"   Status: {result['status']}")
        print(f"   Version: {result.get('version', 'N/A')}")
        print(f"   Latency: {result.get('latency_ms', 'N/A')}ms")
    except Exception as e:
        print(f"   Error: {e}")

    # Redis
    print("\n🔴 Redis:")
    try:
        result = await check_redis_connection()
        print(f"   Status: {result['status']}")
        print(f"   Ping: {result.get('ping', 'N/A')}")
        print(f"   Latency: {result.get('latency_ms', 'N/A')}ms")
    except Exception as e:
        print(f"   Error: {e}")

    # Qdrant
    print("\n🔍 Qdrant:")
    try:
        result = await check_qdrant_connection()
        print(f"   Status: {result['status']}")
        print(f"   Version: {result.get('version', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")

    # Elasticsearch
    print("\n📄 Elasticsearch:")
    try:
        result = await check_elasticsearch_connection()
        print(f"   Status: {result['status']}")
        print(f"   Cluster: {result.get('cluster_name', 'N/A')}")
        print(f"   Health: {result.get('cluster_health', 'N/A')}")
        print(f"   Version: {result.get('version', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Health checks complete!")
    print("=" * 60)


async def demonstrate_client_lifecycle():
    """Demonstrate client initialization and cleanup."""
    from src.shared.clients import init_clients, close_clients, get_redis, get_qdrant, get_elasticsearch

    print("\n📦 Client Lifecycle Demo:")
    print("-" * 40)

    # Initialize clients
    print("   Initializing clients...")
    await init_clients()
    print("   ✓ Clients initialized")

    # Use Redis client
    try:
        redis = get_redis()
        await redis.set("demo_key", "demo_value", ex=60)
        value = await redis.get("demo_key")
        print(f"   ✓ Redis SET/GET: {value}")
    except Exception as e:
        print(f"   Redis error: {e}")

    # Close clients
    print("   Closing clients...")
    await close_clients()
    print("   ✓ Clients closed")


async def main():
    """Main entry point."""
    print("\n🚀 Code Context Retrieval - Storage Clients Example\n")

    # Check all services
    await check_all_services()

    # Demonstrate lifecycle
    await demonstrate_client_lifecycle()


if __name__ == "__main__":
    asyncio.run(main())
