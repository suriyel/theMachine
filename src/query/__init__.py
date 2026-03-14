"""Query Service - Online query handling and retrieval pipeline."""

try:
    from importlib.metadata import version
    __version__ = version("code-context-retrieval")
except Exception:
    __version__ = "0.1.0.dev"  # Fallback for development
