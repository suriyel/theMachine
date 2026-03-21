"""Documentation Chunker — splits markdown files by heading structure."""

import re
from collections import namedtuple
from dataclasses import dataclass

from src.indexing.content_extractor import ExtractedFile


@dataclass
class CodeBlock:
    """A fenced code block extracted from markdown."""

    language: str
    code: str


@dataclass
class DocChunk:
    """A chunk of documentation extracted from a markdown file."""

    chunk_id: str
    repo_id: str
    file_path: str
    breadcrumb: str
    content: str
    code_examples: list  # list of CodeBlock
    content_tokens: int
    heading_level: int


Section = namedtuple("Section", ["heading_level", "heading_text", "body"])

# Regex patterns
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_TOKEN_LIMIT = 2000
_SMALL_FILE_TOKENS = 500
_H4_SPLIT_THRESHOLD = 1000
_SHORT_PARAGRAPH_TOKENS = 200


def _count_tokens(text: str) -> int:
    """Approximate token count using word count."""
    return len(text.split())


def _slugify(text: str) -> str:
    """Convert heading text to a URL-friendly slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


class DocChunker:
    """Splits markdown documentation files into section-level chunks."""

    def chunk_markdown(
        self, file: ExtractedFile, repo_id: str, branch: str
    ) -> list[DocChunk]:
        """Produce documentation chunks from a markdown file."""
        content = file.content

        # Empty file -> single chunk
        if not content.strip():
            chunk_id = f"{repo_id}:{branch}:{file.path}::0"
            return [
                DocChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    file_path=file.path,
                    breadcrumb=file.path,
                    content="",
                    code_examples=[],
                    content_tokens=0,
                    heading_level=0,
                )
            ]

        # Small file -> single chunk (if no real H2+ headings)
        total_tokens = _count_tokens(content)
        if total_tokens < _SMALL_FILE_TOKENS:
            sections = self.split_by_headings(content)
            has_real_headings = any(s.heading_level >= 2 for s in sections)
            if not has_real_headings:
                code_examples = self.extract_code_blocks(content)
                chunk_id = f"{repo_id}:{branch}:{file.path}::0"
                return [
                    DocChunk(
                        chunk_id=chunk_id,
                        repo_id=repo_id,
                        file_path=file.path,
                        breadcrumb=file.path,
                        content=content.strip(),
                        code_examples=code_examples,
                        content_tokens=total_tokens,
                        heading_level=0,
                    )
                ]

        sections = self.split_by_headings(content)

        # No H2/H3 headings -> paragraph fallback
        has_real_headings = any(s.heading_level >= 2 for s in sections)
        if not has_real_headings:
            return self._paragraph_fallback(content, file, repo_id, branch)

        chunks: list[DocChunk] = []
        section_index = 0
        heading_stack: list[str] = []

        for section in sections:
            level = section.heading_level
            heading = section.heading_text
            body = section.body.strip()

            if level == 0:
                # Content before first heading (intro)
                if body:
                    heading_stack = []
                    breadcrumb = file.path
                    code_examples = self.extract_code_blocks(body)
                    tokens = _count_tokens(body)
                    slug = "intro"
                    chunk_id = (
                        f"{repo_id}:{branch}:{file.path}:{slug}:"
                        f"{section_index}"
                    )
                    chunks.append(
                        DocChunk(
                            chunk_id=chunk_id,
                            repo_id=repo_id,
                            file_path=file.path,
                            breadcrumb=breadcrumb,
                            content=body,
                            code_examples=code_examples,
                            content_tokens=tokens,
                            heading_level=0,
                        )
                    )
                    section_index += 1
                continue

            if level == 1:
                # H1 is title, track but don't split
                heading_stack = [heading]
                if body:
                    breadcrumb = self.build_breadcrumb(
                        file.path, heading_stack
                    )
                    code_examples = self.extract_code_blocks(body)
                    tokens = _count_tokens(body)
                    slug = _slugify(heading)
                    chunk_id = (
                        f"{repo_id}:{branch}:{file.path}:{slug}:"
                        f"{section_index}"
                    )
                    chunks.append(
                        DocChunk(
                            chunk_id=chunk_id,
                            repo_id=repo_id,
                            file_path=file.path,
                            breadcrumb=breadcrumb,
                            content=body,
                            code_examples=code_examples,
                            content_tokens=tokens,
                            heading_level=1,
                        )
                    )
                    section_index += 1
                continue

            # H2 or H3 -- update heading stack
            if level == 2:
                if heading_stack and heading_stack[0]:
                    heading_stack = [heading_stack[0], heading]
                else:
                    heading_stack = [heading]
            elif level == 3:
                while len(heading_stack) > 2:
                    heading_stack.pop()
                heading_stack.append(heading)

            section_tokens = _count_tokens(body)

            # Check for H4 sub-split if H3 > threshold
            if level == 3 and section_tokens > _H4_SPLIT_THRESHOLD:
                sub_chunks = self._split_h4(
                    body,
                    heading,
                    heading_stack,
                    file,
                    repo_id,
                    branch,
                    section_index,
                )
                if sub_chunks:
                    chunks.extend(sub_chunks)
                    section_index += len(sub_chunks)
                    continue

            # Split large sections at paragraph boundaries
            if section_tokens > _TOKEN_LIMIT:
                sub_chunks = self._split_paragraphs(
                    body,
                    heading_stack,
                    file,
                    repo_id,
                    branch,
                    section_index,
                    level,
                )
                chunks.extend(sub_chunks)
                section_index += len(sub_chunks)
            else:
                breadcrumb = self.build_breadcrumb(
                    file.path, heading_stack
                )
                code_examples = self.extract_code_blocks(body)
                slug = _slugify(heading)
                chunk_id = (
                    f"{repo_id}:{branch}:{file.path}:{slug}:"
                    f"{section_index}"
                )
                chunks.append(
                    DocChunk(
                        chunk_id=chunk_id,
                        repo_id=repo_id,
                        file_path=file.path,
                        breadcrumb=breadcrumb,
                        content=body,
                        code_examples=code_examples,
                        content_tokens=section_tokens,
                        heading_level=level,
                    )
                )
                section_index += 1

        return chunks if chunks else [
            self._single_chunk(content, file, repo_id, branch)
        ]

    def split_by_headings(self, content: str) -> list[Section]:
        """Split markdown content into sections by headings."""
        if not content.strip():
            return [Section(heading_level=0, heading_text="", body="")]

        sections: list[Section] = []
        lines = content.split("\n")
        current_level = 0
        current_heading = ""
        current_body_lines: list[str] = []

        for line in lines:
            match = _HEADING_RE.match(line)
            if match:
                heading_level = len(match.group(1))
                # Only split on H1, H2, H3 — H4+ stay in parent body
                if heading_level <= 3:
                    body = "\n".join(current_body_lines).strip()
                    if body or sections:
                        sections.append(
                            Section(
                                heading_level=current_level,
                                heading_text=current_heading,
                                body=body,
                            )
                        )
                    current_level = heading_level
                    current_heading = match.group(2).strip()
                    current_body_lines = []
                else:
                    # H4+ kept inline
                    current_body_lines.append(line)
            else:
                current_body_lines.append(line)

        body = "\n".join(current_body_lines).strip()
        sections.append(
            Section(
                heading_level=current_level,
                heading_text=current_heading,
                body=body,
            )
        )

        return sections

    def build_breadcrumb(
        self, file_path: str, headings: list[str]
    ) -> str:
        """Build breadcrumb string from file path and heading chain."""
        parts = [file_path] + [h for h in headings if h]
        return " > ".join(parts)

    def extract_code_blocks(self, section: str) -> list[CodeBlock]:
        """Extract fenced code blocks from markdown text."""
        blocks: list[CodeBlock] = []
        for match in _CODE_BLOCK_RE.finditer(section):
            language = match.group(1) or ""
            code = match.group(2).strip()
            blocks.append(CodeBlock(language=language, code=code))
        return blocks

    def _paragraph_fallback(
        self,
        content: str,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
    ) -> list[DocChunk]:
        """Split content by paragraphs when no H2+ headings present."""
        # Strip H1 title if present
        lines = content.split("\n")
        body_lines: list[str] = []
        skip_title = False
        for line in lines:
            if not skip_title and _HEADING_RE.match(line):
                match = _HEADING_RE.match(line)
                if match and len(match.group(1)) == 1:
                    skip_title = True
                    continue
            body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if not body:
            body = content.strip()

        paragraphs = re.split(r"\n\n+", body)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        if not paragraphs:
            return [self._single_chunk(content, file, repo_id, branch)]

        # Merge short consecutive paragraphs
        merged: list[str] = []
        buf = ""
        for para in paragraphs:
            if buf:
                combined = buf + "\n\n" + para
                if _count_tokens(combined) < _SHORT_PARAGRAPH_TOKENS:
                    buf = combined
                else:
                    merged.append(buf)
                    buf = para
            else:
                buf = para
        if buf:
            merged.append(buf)

        # If everything merged into one chunk and small
        total_tokens = _count_tokens(content)
        if len(merged) == 1 and total_tokens < _SMALL_FILE_TOKENS:
            return [self._single_chunk(content, file, repo_id, branch)]

        chunks: list[DocChunk] = []
        for i, para in enumerate(merged):
            breadcrumb = f"{file.path} > [section {i + 1}]"
            code_examples = self.extract_code_blocks(para)
            tokens = _count_tokens(para)
            chunk_id = f"{repo_id}:{branch}:{file.path}:section-{i + 1}:{i}"
            chunks.append(
                DocChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    file_path=file.path,
                    breadcrumb=breadcrumb,
                    content=para,
                    code_examples=code_examples,
                    content_tokens=tokens,
                    heading_level=0,
                )
            )

        return chunks if chunks else [
            self._single_chunk(content, file, repo_id, branch)
        ]

    def _split_paragraphs(
        self,
        text: str,
        heading_stack: list[str],
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        base_index: int,
        level: int,
    ) -> list[DocChunk]:
        """Split text at paragraph boundaries to stay under token limit."""
        paragraphs = re.split(r"\n\n+", text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks: list[DocChunk] = []
        current_text = ""
        sub_idx = 0

        for para in paragraphs:
            if current_text:
                combined = current_text + "\n\n" + para
                if _count_tokens(combined) > _TOKEN_LIMIT:
                    breadcrumb = self.build_breadcrumb(
                        file.path, heading_stack
                    )
                    code_examples = self.extract_code_blocks(current_text)
                    slug = _slugify(
                        heading_stack[-1] if heading_stack else "section"
                    )
                    chunk_id = (
                        f"{repo_id}:{branch}:{file.path}:{slug}:"
                        f"{base_index + sub_idx}"
                    )
                    chunks.append(
                        DocChunk(
                            chunk_id=chunk_id,
                            repo_id=repo_id,
                            file_path=file.path,
                            breadcrumb=breadcrumb,
                            content=current_text,
                            code_examples=code_examples,
                            content_tokens=_count_tokens(current_text),
                            heading_level=level,
                        )
                    )
                    sub_idx += 1
                    current_text = para
                else:
                    current_text = combined
            else:
                current_text = para

        if current_text:
            # If still over limit (e.g., single giant paragraph), force-split
            if _count_tokens(current_text) > _TOKEN_LIMIT:
                forced = self._force_split_text(
                    current_text,
                    heading_stack,
                    file,
                    repo_id,
                    branch,
                    base_index + sub_idx,
                    level,
                )
                chunks.extend(forced)
            else:
                breadcrumb = self.build_breadcrumb(
                    file.path, heading_stack
                )
                code_examples = self.extract_code_blocks(current_text)
                slug = _slugify(
                    heading_stack[-1] if heading_stack else "section"
                )
                chunk_id = (
                    f"{repo_id}:{branch}:{file.path}:{slug}:"
                    f"{base_index + sub_idx}"
                )
                chunks.append(
                    DocChunk(
                        chunk_id=chunk_id,
                        repo_id=repo_id,
                        file_path=file.path,
                        breadcrumb=breadcrumb,
                        content=current_text,
                        code_examples=code_examples,
                        content_tokens=_count_tokens(current_text),
                        heading_level=level,
                    )
                )

        return chunks

    def _force_split_text(
        self,
        text: str,
        heading_stack: list[str],
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        base_index: int,
        level: int,
    ) -> list[DocChunk]:
        """Force-split oversized text into fixed-size token windows."""
        words = text.split()
        window_size = 1500
        overlap = 100
        chunks: list[DocChunk] = []
        start = 0
        sub_idx = 0

        while start < len(words):
            end = min(start + window_size, len(words))
            window_text = " ".join(words[start:end])
            breadcrumb = self.build_breadcrumb(file.path, heading_stack)
            slug = _slugify(
                heading_stack[-1] if heading_stack else "section"
            )
            chunk_id = (
                f"{repo_id}:{branch}:{file.path}:{slug}:"
                f"{base_index + sub_idx}"
            )
            chunks.append(
                DocChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    file_path=file.path,
                    breadcrumb=breadcrumb,
                    content=window_text,
                    code_examples=self.extract_code_blocks(window_text),
                    content_tokens=_count_tokens(window_text),
                    heading_level=level,
                )
            )
            if end >= len(words):
                break
            start = end - overlap
            sub_idx += 1

        return chunks

    def _split_h4(
        self,
        text: str,
        parent_heading: str,
        heading_stack: list[str],
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        base_index: int,
    ) -> list[DocChunk] | None:
        """Split at H4 boundaries if present in a large H3 section."""
        h4_pattern = re.compile(r"^####\s+(.+)$", re.MULTILINE)
        h4_matches = list(h4_pattern.finditer(text))
        if not h4_matches:
            return None

        chunks: list[DocChunk] = []
        # Content before first H4
        first_h4_pos = h4_matches[0].start()
        pre_h4 = text[:first_h4_pos].strip()
        if pre_h4:
            breadcrumb = self.build_breadcrumb(file.path, heading_stack)
            slug = _slugify(parent_heading)
            chunk_id = (
                f"{repo_id}:{branch}:{file.path}:{slug}:{base_index}"
            )
            chunks.append(
                DocChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    file_path=file.path,
                    breadcrumb=breadcrumb,
                    content=pre_h4,
                    code_examples=self.extract_code_blocks(pre_h4),
                    content_tokens=_count_tokens(pre_h4),
                    heading_level=3,
                )
            )

        for i, match in enumerate(h4_matches):
            h4_heading = match.group(1).strip()
            start = match.end()
            end = (
                h4_matches[i + 1].start()
                if i + 1 < len(h4_matches)
                else len(text)
            )
            body = text[start:end].strip()

            h4_stack = heading_stack + [h4_heading]
            breadcrumb = self.build_breadcrumb(file.path, h4_stack)
            slug = _slugify(h4_heading)
            idx = base_index + len(chunks)
            chunk_id = f"{repo_id}:{branch}:{file.path}:{slug}:{idx}"
            chunks.append(
                DocChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    file_path=file.path,
                    breadcrumb=breadcrumb,
                    content=body,
                    code_examples=self.extract_code_blocks(body),
                    content_tokens=_count_tokens(body),
                    heading_level=4,
                )
            )

        return chunks if chunks else None

    def _single_chunk(
        self,
        content: str,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
    ) -> DocChunk:
        """Create a single DocChunk for the entire file."""
        chunk_id = f"{repo_id}:{branch}:{file.path}::0"
        return DocChunk(
            chunk_id=chunk_id,
            repo_id=repo_id,
            file_path=file.path,
            breadcrumb=file.path,
            content=content.strip(),
            code_examples=self.extract_code_blocks(content),
            content_tokens=_count_tokens(content),
            heading_level=0,
        )
