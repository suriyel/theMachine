"""Redis async client wrapper."""

import redis.asyncio as aioredis


class RedisClient:
    """Thin wrapper around redis.asyncio.Redis with connect/health/close interface."""

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("url must not be empty")
        self._url = url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Initialize the Redis client connection."""
        self._client = aioredis.from_url(self._url)

    async def health_check(self) -> bool:
        """Check if Redis server is reachable."""
        if self._client is None:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Redis client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
