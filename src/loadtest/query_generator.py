"""Query payload generator for load testing."""

import random

NL_QUERIES = [
    {"query": "how to authenticate users", "query_type": "nl", "repo_id": None},
    {"query": "database connection pooling", "query_type": "nl", "repo_id": None},
    {"query": "error handling best practices", "query_type": "nl", "repo_id": None},
    {"query": "implement caching strategy", "query_type": "nl", "repo_id": None},
    {"query": "parse JSON configuration", "query_type": "nl", "repo_id": None},
    {"query": "logging and monitoring setup", "query_type": "nl", "repo_id": None},
    {"query": "async task processing", "query_type": "nl", "repo_id": None},
    {"query": "REST API pagination", "query_type": "nl", "repo_id": None},
    {"query": "file upload handling", "query_type": "nl", "repo_id": None},
    {"query": "unit testing patterns", "query_type": "nl", "repo_id": None},
]

SYMBOL_QUERIES = [
    {"query": "QueryHandler", "query_type": "symbol", "repo_id": None},
    {"query": "Repository.create", "query_type": "symbol", "repo_id": None},
    {"query": "AuthMiddleware", "query_type": "symbol", "repo_id": None},
    {"query": "ElasticsearchClient.search", "query_type": "symbol", "repo_id": None},
    {"query": "RankFusion.fuse", "query_type": "symbol", "repo_id": None},
    {"query": "Reranker.rerank", "query_type": "symbol", "repo_id": None},
    {"query": "ResponseBuilder.build", "query_type": "symbol", "repo_id": None},
    {"query": "IndexWriter.write_batch", "query_type": "symbol", "repo_id": None},
    {"query": "GitCloner.clone", "query_type": "symbol", "repo_id": None},
    {"query": "Chunker.chunk_code", "query_type": "symbol", "repo_id": None},
]


class QueryGenerator:
    """Generates diverse query payloads for load testing."""

    def generate_payloads(
        self, count: int, mix_ratio: float = 0.7
    ) -> list[dict]:
        """Generate query payloads with a configurable NL/symbol mix.

        Args:
            count: Number of payloads to generate. Must be > 0.
            mix_ratio: Fraction of NL queries (0.0 to 1.0). Default 0.7.

        Returns:
            List of query payload dicts, each with 'query' and 'query_type' keys.

        Raises:
            ValueError: If count <= 0 or mix_ratio outside [0.0, 1.0].
        """
        if count <= 0:
            raise ValueError("count must be > 0")
        if mix_ratio < 0.0 or mix_ratio > 1.0:
            raise ValueError("mix_ratio must be in [0.0, 1.0]")

        nl_count = round(count * mix_ratio)
        sym_count = count - nl_count

        payloads = []
        for i in range(nl_count):
            payloads.append(dict(NL_QUERIES[i % len(NL_QUERIES)]))
        for i in range(sym_count):
            payloads.append(dict(SYMBOL_QUERIES[i % len(SYMBOL_QUERIES)]))

        random.shuffle(payloads)
        return payloads
