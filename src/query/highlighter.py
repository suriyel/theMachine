"""CodeHighlighter — Pygments-based syntax highlighting with UCD dark theme."""

from __future__ import annotations

from pygments import highlight as pygments_highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.style import Style
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Token,
)
from pygments.util import ClassNotFound


# Language alias mapping for Pygments compatibility
_LANGUAGE_ALIASES: dict[str, str] = {
    "c++": "cpp",
    "typescript": "ts",
    "javascript": "js",
}


class UCDDarkStyle(Style):
    """Pygments style using UCD Developer Dark theme syntax token colors."""

    background_color = "#0d1117"
    default_style = ""

    styles = {
        Token: "#e6edf3",  # --color-text-primary
        Comment: "#8b949e",  # --syntax-comment
        Comment.Single: "#8b949e",
        Comment.Multiline: "#8b949e",
        Keyword: "#ff7b72",  # --syntax-keyword
        Keyword.Type: "#79c0ff",  # --syntax-type
        Keyword.Namespace: "#ff7b72",
        Name: "#e6edf3",
        Name.Function: "#d2a8ff",  # --syntax-function
        Name.Class: "#79c0ff",  # --syntax-type
        Name.Decorator: "#d2a8ff",
        Name.Builtin: "#79c0ff",
        Name.Variable: "#ffa657",  # --syntax-variable
        Name.Other: "#ffa657",
        String: "#a5d6ff",  # --syntax-string
        String.Doc: "#8b949e",
        Number: "#79c0ff",  # --syntax-number
        Operator: "#ff7b72",  # --syntax-operator
        Operator.Word: "#ff7b72",
    }


class DarkThemeFormatter(HtmlFormatter):
    """Custom Pygments HtmlFormatter with UCD Developer Dark theme colors."""

    def __init__(self, **options):
        options.setdefault("noclasses", True)
        options.setdefault("nowrap", False)
        options.setdefault("style", UCDDarkStyle)
        super().__init__(**options)


class CodeHighlighter:
    """Highlights code using Pygments with UCD dark theme."""

    def __init__(self) -> None:
        self._formatter = DarkThemeFormatter(
            noclasses=True,
            nowrap=False,
        )

    def highlight(self, code: str, language: str | None) -> str:
        """Highlight code with syntax coloring.

        Args:
            code: Source code string (may be empty).
            language: Pygments lexer alias, None, or empty string.

        Returns:
            HTML string with syntax-highlighted code. Falls back to
            plain text (TextLexer) for unknown or missing languages.
        """
        lexer = self._resolve_lexer(language)
        return pygments_highlight(code, lexer, self._formatter)

    @staticmethod
    def _resolve_lexer(language: str | None):
        """Resolve a Pygments lexer, falling back to TextLexer."""
        if language is not None and language != "":
            alias = _LANGUAGE_ALIASES.get(language.lower(), language.lower())
            try:
                return get_lexer_by_name(alias)
            except ClassNotFound:
                return TextLexer()
        return TextLexer()
