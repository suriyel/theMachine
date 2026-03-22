"""LanguageFilter — validates and normalizes programming language filter values."""

from __future__ import annotations

from src.shared.exceptions import ValidationError

SUPPORTED_LANGUAGES: frozenset[str] = frozenset(
    {"java", "python", "typescript", "javascript", "c", "c++"}
)


class LanguageFilter:
    """Validates language filter values against the supported set (CON-001)."""

    def validate(self, languages: list[str] | None) -> list[str] | None:
        """Validate and normalize language filter values.

        Args:
            languages: List of language strings, or None.

        Returns:
            Normalized (lowercased, stripped) list if all valid, or None if
            input is None or empty.

        Raises:
            ValidationError: If any language is not in SUPPORTED_LANGUAGES.
        """
        if languages is None:
            return None
        if not languages:
            return None

        normalized = [lang.lower().strip() for lang in languages]

        unsupported = [lang for lang in normalized if lang not in SUPPORTED_LANGUAGES]
        if unsupported:
            raise ValidationError(
                f"Unsupported language(s): {unsupported}. "
                f"Supported: {sorted(SUPPORTED_LANGUAGES)}"
            )

        return normalized

    def apply_filter(self, languages: list[str] | None) -> list[str] | None:
        """Pass-through for validated language list.

        The Retriever already constructs ES/Qdrant filter clauses from the
        languages list. This method exists for interface compliance with the
        design class diagram.
        """
        return languages
