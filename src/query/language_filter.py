"""LanguageFilter — validates and normalizes programming language filter values."""

from __future__ import annotations

from src.shared.exceptions import ValidationError

# Canonical language identifiers — must match values stored in ES/Qdrant
# by chunker.EXT_TO_LANGUAGE (the indexing-time source of truth).
SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {"java", "python", "typescript", "javascript", "c", "cpp"}
)

# Alias mapping: common user-facing names → canonical index values.
# Covers: display names, file extensions, abbreviations, Pygments aliases.
_LANGUAGE_ALIASES: dict[str, str] = {
    "c++": "cpp",
    "cxx": "cpp",
    "cc": "cpp",
    "hpp": "cpp",
    "ts": "typescript",
    "tsx": "typescript",
    "js": "javascript",
    "jsx": "javascript",
    "py": "python",
}


class LanguageFilter:
    """Validates language filter values against the supported set (CON-001)."""

    def validate(self, languages: list[str] | None) -> list[str] | None:
        """Validate and normalize language filter values.

        Args:
            languages: List of language strings, or None.

        Returns:
            Normalized list mapped to canonical index identifiers if all valid,
            or None if input is None or empty.

        Raises:
            ValidationError: If any language is not in SUPPORTED_LANGUAGES
                and has no known alias.
        """
        if languages is None:
            return None
        if not languages:
            return None

        normalized = []
        for lang in languages:
            key = lang.lower().strip()
            key = _LANGUAGE_ALIASES.get(key, key)
            normalized.append(key)

        unsupported = [lang for lang in normalized if lang not in SUPPORTED_LANGUAGES]
        if unsupported:
            raise ValidationError(
                f"Unsupported language(s): {unsupported}. "
                f"Supported: {sorted(SUPPORTED_LANGUAGES)}. "
                f"Aliases: {sorted(_LANGUAGE_ALIASES.keys())}"
            )

        return normalized

    def apply_filter(self, languages: list[str] | None) -> list[str] | None:
        """Pass-through for validated language list.

        The Retriever already constructs ES/Qdrant filter clauses from the
        languages list. This method exists for interface compliance with the
        design class diagram.
        """
        return languages
