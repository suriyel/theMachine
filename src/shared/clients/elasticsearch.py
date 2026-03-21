"""Elasticsearch async client wrapper."""

from elasticsearch import AsyncElasticsearch


class ElasticsearchClient:
    """Thin wrapper around AsyncElasticsearch with connect/health/close interface."""

    def __init__(self, url: str) -> None:
        if not url:
            raise ValueError("url must not be empty")
        self._url = url
        self._client: AsyncElasticsearch | None = None

    async def connect(self) -> None:
        """Initialize the Elasticsearch client connection."""
        self._client = AsyncElasticsearch(hosts=[self._url])

    async def health_check(self) -> bool:
        """Check if Elasticsearch cluster is reachable."""
        if self._client is None:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Elasticsearch client connection."""
        if self._client is not None:
            await self._client.close()
            self._client = None
