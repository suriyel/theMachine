"""Language filter for query results."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.query.retriever import Candidate


class LanguageFilter:
    """Filter query results by programming language."""

    SUPPORTED_LANGUAGES = {"java", "python", "typescript", "javascript", "c", "cpp"}
    SUPPORTED_LANGUAGES_DISPLAY = ["Java", "Python", "TypeScript", "JavaScript", "C", "C++"]

    def validate(self, language: str | None) -> str | None:
        """Validate language filter.

        Args:
            language: Language string (case-insensitive)

        Returns:
            Normalized lowercase language or None

        Raises:
            ValueError: If language is not supported
        """
        if language is None or language.lower() == "all":
            return None
        # Handle C++ specially - normalize "c++" to "cpp"
        lang = language.lower()
        if lang == "c++" or lang == "c++":
            lang = "cpp"
        if lang not in self.SUPPORTED_LANGUAGES:
            supported = ", ".join(self.SUPPORTED_LANGUAGES_DISPLAY)
            raise ValueError(f"Unsupported language: {language}. Supported: {supported}")
        return lang

    def apply(self, candidates: list["Candidate"], language: str) -> list["Candidate"]:
        """Filter candidates by language.

        Args:
            candidates: List of Candidate objects
            language: Language to filter by (lowercase)

        Returns:
            Filtered list of candidates
        """
        if not language:
            return candidates
        return [
            c for c in candidates
            if c.language and c.language.lower() == language.lower()
        ]
