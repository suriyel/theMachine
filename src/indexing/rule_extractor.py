"""Rule Extractor — extracts rule chunks from configuration and guide files."""

import os
import re
from dataclasses import dataclass

from src.indexing.content_extractor import ExtractedFile


@dataclass
class RuleChunk:
    """A chunk of rules/configuration extracted from a repository."""

    chunk_id: str
    repo_id: str
    file_path: str
    rule_type: str  # "agent_rules" / "contribution_guide" / "linter_config" / "editor_config"
    content: str


class RuleExtractor:
    """Extracts rule chunks from agent rules, contribution guides, and configs."""

    def extract_rules(
        self, file: ExtractedFile, repo_id: str, branch: str
    ) -> list[RuleChunk]:
        """Extract rule chunks from an ExtractedFile."""
        filename = os.path.basename(file.path).lower()
        normalized = file.path.replace(os.sep, "/")

        if filename == "claude.md":
            rule_type = "agent_rules"
        elif filename == "contributing.md":
            rule_type = "contribution_guide"
        elif filename == ".editorconfig":
            rule_type = "editor_config"
        elif normalized.startswith(".cursor/rules/"):
            rule_type = "agent_rules"
        else:
            rule_type = "linter_config"

        chunk_id = f"{repo_id}:{branch}:{file.path}"
        return [
            RuleChunk(
                chunk_id=chunk_id,
                repo_id=repo_id,
                file_path=file.path,
                rule_type=rule_type,
                content=file.content,
            )
        ]

    def parse_claude_md(self, content: str) -> list[str]:
        """Parse CLAUDE.md content into rule sections."""
        return self._split_by_headings(content)

    def parse_contributing(self, content: str) -> list[str]:
        """Parse CONTRIBUTING.md content into guide sections."""
        return self._split_by_headings(content)

    def parse_cursor_rules(self, content: str) -> list[str]:
        """Parse .cursor/rules content into rule sections."""
        return self._split_by_headings(content)

    def _split_by_headings(self, content: str) -> list[str]:
        """Split content by markdown headings into rule strings."""
        if not content.strip():
            return []
        sections = re.split(r"\n(?=##?\s)", content)
        return [s.strip() for s in sections if s.strip()]
