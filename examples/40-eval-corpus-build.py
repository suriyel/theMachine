#!/usr/bin/env python3
"""Example: Evaluation Corpus Builder (Feature #40).

Demonstrates how to instantiate and run EvalCorpusBuilder with mocked
pipeline dependencies.  In production use, real GitCloner, ContentExtractor,
Chunker, EmbeddingEncoder, IndexWriter, and ElasticsearchClient instances
would be injected.

Usage:
    python examples/40-eval-corpus-build.py
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import numpy as np

from src.eval.corpus_builder import EvalCorpusBuilder
from src.indexing.chunker import CodeChunk
from src.indexing.content_extractor import ContentType, ExtractedFile


def _make_chunk(chunk_id: str, repo_id: str) -> CodeChunk:
    return CodeChunk(
        chunk_id=chunk_id,
        repo_id=repo_id,
        branch="main",
        file_path="main.py",
        language="python",
        chunk_type="function",
        symbol="main",
        signature="def main():",
        doc_comment="",
        parent_class="",
        content="def main(): print('hello')",
        line_start=1,
        line_end=1,
    )


async def main():
    # Create a temp repos.json
    repos = [
        {"name": "demo-repo-1", "url": "https://github.com/example/repo1", "language": "python", "branch": "main"},
        {"name": "demo-repo-2", "url": "https://github.com/example/repo2", "language": "java", "branch": "main"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(repos, f)
        repos_path = f.name

    # Mock all pipeline dependencies
    git_cloner = MagicMock()
    git_cloner.clone_or_update = MagicMock(return_value="/tmp/clone")

    content_extractor = MagicMock()
    content_extractor.extract = MagicMock(return_value=[
        ExtractedFile(path="main.py", content_type=ContentType.CODE, content="def main(): pass", size=16),
    ])

    chunker = MagicMock()
    chunker.chunk = MagicMock(return_value=[_make_chunk("c1", "demo")])

    embedding_encoder = MagicMock()
    embedding_encoder.encode_batch = MagicMock(return_value=[np.zeros(1024)])

    index_writer = MagicMock()
    index_writer.write_code_chunks = AsyncMock()

    es_client = MagicMock()
    es_client._client = AsyncMock()
    es_client._client.count = AsyncMock(return_value={"count": 0})

    builder = EvalCorpusBuilder(
        git_cloner=git_cloner,
        content_extractor=content_extractor,
        chunker=chunker,
        embedding_encoder=embedding_encoder,
        index_writer=index_writer,
        es_client=es_client,
    )

    print("Building evaluation corpus...")
    summary = await builder.build(repos_path)

    print(f"\nCorpus Build Summary:")
    print(f"  Total repos:   {summary.total}")
    print(f"  Indexed:       {summary.indexed}")
    print(f"  Skipped:       {summary.skipped}")
    print(f"  Failed:        {summary.failed}")
    print(f"\nPer-repo details:")
    for detail in summary.details:
        print(f"  - {detail.name}: {detail.status} ({detail.chunk_count} chunks)")

    # Verify eval_ prefix was used
    for call in index_writer.write_code_chunks.call_args_list:
        assert call.kwargs["es_index"] == "eval_code_chunks"
        assert call.kwargs["qdrant_collection"] == "eval_code_embeddings"
    print("\n✓ Eval prefix isolation verified (eval_code_chunks, eval_code_embeddings)")

    Path(repos_path).unlink()


if __name__ == "__main__":
    asyncio.run(main())
