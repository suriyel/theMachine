"""Prometheus metrics for code-context-retrieval."""

from prometheus_client import Counter, Gauge, Histogram

# Query latency histogram (seconds)
QUERY_LATENCY = Histogram(
    "ccr_query_latency_seconds",
    "Query latency in seconds",
    ["query_type", "status"],
)

# Query throughput counter
QUERY_THROUGHPUT = Counter(
    "ccr_query_throughput_total",
    "Total number of queries processed",
    ["query_type", "status"],
)

# Query errors counter
QUERY_ERRORS = Counter(
    "ccr_query_errors_total",
    "Total number of query errors",
    ["error_type"],
)

# Index size gauge (bytes)
INDEX_SIZE_BYTES = Gauge(
    "ccr_index_size_bytes",
    "Total size of indexed content in bytes",
)

# Active index jobs gauge
ACTIVE_INDEX_JOBS = Gauge(
    "ccr_active_index_jobs",
    "Number of currently running index jobs",
)

# Repository count gauge
REPOSITORY_COUNT = Gauge(
    "ccr_repository_count",
    "Total number of registered repositories",
    ["status"],
)


def record_query_latency(query_type: str, latency_seconds: float, status: str = "success"):
    """Record query latency."""
    QUERY_LATENCY.labels(query_type=query_type, status=status).observe(latency_seconds)


def increment_query_throughput(query_type: str, status: str = "success"):
    """Increment query throughput counter."""
    QUERY_THROUGHPUT.labels(query_type=query_type, status=status).inc()


def increment_query_errors(error_type: str):
    """Increment query errors counter."""
    QUERY_ERRORS.labels(error_type=error_type).inc()


def set_index_size(bytes_count: int):
    """Set index size gauge."""
    INDEX_SIZE_BYTES.set(bytes_count)


def set_active_index_jobs(count: int):
    """Set active index jobs gauge."""
    ACTIVE_INDEX_JOBS.set(count)


def set_repository_count(status: str, count: int):
    """Set repository count by status."""
    REPOSITORY_COUNT.labels(status=status).set(count)
