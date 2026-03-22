#!/usr/bin/env python3
"""Example: Language Filter validation and normalization.

Demonstrates how LanguageFilter validates language filter values
against the supported set (CON-001: Java, Python, TypeScript,
JavaScript, C, C++) before they reach the retrieval pipeline.
"""

from src.query.language_filter import SUPPORTED_LANGUAGES, LanguageFilter
from src.shared.exceptions import ValidationError


def main():
    lf = LanguageFilter()

    print(f"Supported languages: {sorted(SUPPORTED_LANGUAGES)}")
    print()

    # Valid single language
    result = lf.validate(["java"])
    print(f"validate(['java'])       -> {result}")

    # Case normalization
    result = lf.validate(["Python", "TYPESCRIPT"])
    print(f"validate(['Python', 'TYPESCRIPT']) -> {result}")

    # Special character language
    result = lf.validate(["c++"])
    print(f"validate(['c++'])        -> {result}")

    # Empty list = no filter
    result = lf.validate([])
    print(f"validate([])             -> {result}")

    # None = no filter
    result = lf.validate(None)
    print(f"validate(None)           -> {result}")

    # Unsupported language
    print()
    try:
        lf.validate(["rust"])
    except ValidationError as e:
        print(f"validate(['rust'])       -> ValidationError: {e}")

    # Mixed valid + invalid
    try:
        lf.validate(["java", "go"])
    except ValidationError as e:
        print(f"validate(['java', 'go']) -> ValidationError: {e}")


if __name__ == "__main__":
    main()
