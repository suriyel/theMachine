"""EvalCorpusBuilder — builds evaluation corpus from representative repos.

Clones repos from eval/repos.json and runs the full indexing pipeline
(ContentExtractor → Chunker → EmbeddingEncoder → IndexWriter) into
eval_-prefixed ES/Qdrant namespaces.  Idempotent — skips already-indexed repos.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.indexing.content_extractor import ContentType
from src.indexing.exceptions import EmbeddingModelError, IndexWriteError
from src.shared.exceptions import CloneError

logger = logging.getLogger(__name__)

EVAL_ES_INDEX = "eval_code_chunks"
EVAL_QDRANT_COLLECTION = "eval_code_embeddings"


@dataclass
class EvalRepo:
    """Metadata for a single evaluation repository."""

    name: str
    url: str
    language: str
    branch: str


@dataclass
class RepoResult:
    """Result of processing a single repo."""

    name: str
    status: str  # "indexed", "skipped", "failed"
    chunk_count: int = 0
    error: str = ""


@dataclass
class CorpusSummary:
    """Summary of the entire corpus build operation."""

    total: int
    indexed: int
    skipped: int
    failed: int
    details: list[RepoResult] = field(default_factory=list)


class EvalCorpusBuilder:
    """Orchestrates evaluation corpus building."""

    def __init__(
        self,
        git_cloner,
        content_extractor,
        chunker,
        embedding_encoder,
        index_writer,
        es_client,
    ) -> None:
        self._git_cloner = git_cloner
        self._content_extractor = content_extractor
        self._chunker = chunker
        self._embedding_encoder = embedding_encoder
        self._index_writer = index_writer
        self._es_client = es_client

    async def build(self, repos_json_path: str) -> CorpusSummary:
        """Build the evaluation corpus from repos listed in the JSON file.

        Raises:
            FileNotFoundError: If repos_json_path does not exist.
            ValueError: If JSON is malformed or repos have missing/invalid fields.
        """
        repos = self._load_repos(repos_json_path)

        indexed = 0
        skipped = 0
        failed = 0
        details: list[RepoResult] = []

        for repo in repos:
            try:
                if await self._is_already_indexed(repo.name):
                    skipped += 1
                    details.append(RepoResult(repo.name, "skipped"))
                    logger.info("Skipping already-indexed repo: %s", repo.name)
                    continue

                clone_path = self._clone_repo(repo)
                chunk_count = await self._index_repo(repo, clone_path)
                indexed += 1
                details.append(RepoResult(repo.name, "indexed", chunk_count))
                logger.info("Indexed repo: %s (%d chunks)", repo.name, chunk_count)
            except (CloneError, EmbeddingModelError, IndexWriteError) as e:
                failed += 1
                details.append(RepoResult(repo.name, "failed", error=str(e)))
                logger.error("Failed to process repo %s: %s", repo.name, e)

        return CorpusSummary(
            total=len(repos),
            indexed=indexed,
            skipped=skipped,
            failed=failed,
            details=details,
        )

    def _load_repos(self, repos_json_path: str) -> list[EvalRepo]:
        """Load and validate the repo list from JSON file."""
        path = Path(repos_json_path)
        if not path.exists():
            raise FileNotFoundError(f"repos file not found: {repos_json_path}")

        try:
            raw = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"repos.json must contain valid JSON: {e}") from e

        if not isinstance(raw, list):
            raise ValueError("repos.json must contain a JSON array")

        required = {"name", "url", "language", "branch"}
        repos: list[EvalRepo] = []
        for entry in raw:
            missing = required - set(entry.keys())
            if missing:
                raise ValueError(f"repo entry missing fields: {missing}")
            if not entry["name"]:
                raise ValueError("repo entry has empty name")
            repos.append(
                EvalRepo(
                    name=entry["name"],
                    url=entry["url"],
                    language=entry["language"],
                    branch=entry["branch"],
                )
            )

        return repos

    async def _is_already_indexed(self, repo_name: str) -> bool:
        """Check if repo is already indexed in eval ES index.

        Returns False on any ES error (safe fallback: re-index).
        """
        try:
            result = await self._es_client._client.count(
                index=EVAL_ES_INDEX,
                body={"query": {"term": {"repo_id": repo_name}}},
            )
            return result["count"] > 0
        except Exception as e:
            logger.warning(
                "Idempotency check failed for %s, will re-index: %s",
                repo_name,
                e,
            )
            return False

    def _clone_repo(self, repo: EvalRepo) -> str:
        """Clone or update the repo via GitCloner."""
        return self._git_cloner.clone_or_update(repo.name, repo.url, repo.branch)

    async def _index_repo(self, repo: EvalRepo, clone_path: str) -> int:
        """Run the full indexing pipeline for a single repo.

        Returns the number of code chunks indexed.
        """
        files = self._content_extractor.extract(clone_path)
        code_files = [f for f in files if f.content_type == ContentType.CODE]

        all_chunks = []
        for code_file in code_files:
            chunks = self._chunker.chunk(code_file, repo.name, repo.branch)
            all_chunks.extend(chunks)

        if not all_chunks:
            logger.warning("No code chunks for repo %s", repo.name)
            return 0

        texts = [chunk.content for chunk in all_chunks]
        embeddings = self._embedding_encoder.encode_batch(texts)

        await self._index_writer.write_code_chunks(
            all_chunks,
            embeddings,
            repo.name,
            es_index=EVAL_ES_INDEX,
            qdrant_collection=EVAL_QDRANT_COLLECTION,
        )

        return len(all_chunks)
