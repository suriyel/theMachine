"""Qdrant async client wrapper."""

from qdrant_client import AsyncQdrantClient


class QdrantClientWrapper:
    """Thin wrapper around AsyncQdrantClient with connect/health/close interface."""

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("url must not be empty")
        self._url = url
        self._client: AsyncQdrantClient | None = None

    async def connect(self) -> None:
        """Initialize the Qdrant client connection."""
        self._client = AsyncQdrantClient(url=self._url)

    async def health_check(self) -> bool:
        """Check if Qdrant server is reachable."""
        if self._client is None:
            return False
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Qdrant client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
