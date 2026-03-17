# Implementation Plan — Feature #20: Language Filter

**Feature**: Language Filter (FR-015)
**Status**: Failing (needs implementation)
**Dependencies**: Feature #17 (REST API Endpoints) - passing

## Overview

Implement language filtering functionality to restrict retrieval results to specified programming languages. This includes a LanguageFilter class with validation and application logic, plus integration with the REST API and Web UI.

## What's Already Implemented

- `src/query/api/web.py`: Basic language filter validation in search page (lowercase)
- `src/query/handler.py`: Passes language filter to retrievers
- `src/query/retriever.py`: Applies language filter in ES/Qdrant queries
- `src/query/templates/search.html`: UI chips for language selection

## What's Missing

1. **LanguageFilter class** - validate() and apply() methods per design doc
2. **API validation** - Return 422 with supported language list for unsupported languages
3. **Unit tests** - Coverage for LanguageFilter class
4. **ST test cases** - DevTools-based acceptance tests

## Implementation Steps

### Step 1: Create LanguageFilter class

Create `src/query/language_filter.py`:

```python
class LanguageFilter:
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
        lang = language.lower()
        if lang not in self.SUPPORTED_LANGUAGES:
            supported = ", ".join(self.SUPPORTED_LANGUAGES_DISPLAY)
            raise ValueError(f"Unsupported language: {language}. Supported: {supported}")
        return lang

    def apply(self, candidates: list[Candidate], language: str) -> list[Candidate]:
        """Filter candidates by language.

        Args:
            candidates: List of Candidate objects
            language: Language to filter by (lowercase)

        Returns:
            Filtered list of candidates
        """
        if not language:
            return candidates
        return [c for c in candidates if c.language and c.language.lower() == language.lower()]
```

### Step 2: Integrate with REST API

Update `src/query/api/v1/endpoints/query.py`:

- Import LanguageFilter
- Add validation before creating QueryRequest
- Return 422 with supported languages on validation error

### Step 3: Integrate with Web UI

Update `src/query/api/web.py`:

- Import LanguageFilter
- Use it for validation (replace existing logic)
- Ensure error message matches specification

### Step 4: Add Unit Tests

Create `tests/test_language_filter.py`:

- Test validate() with valid languages (case-insensitive)
- Test validate() with unsupported language raises ValueError
- Test validate() with None returns None
- Test validate() with "all" returns None
- Test apply() filters correctly

### Step 5: Run TDD Cycle

- Write failing tests first (Red)
- Implement code to pass (Green)
- Refactor for clarity

### Step 6: Quality Gates

- Run coverage: `pytest --cov=src --cov-branch --cov-report=term-missing`
- Target: Line >= 90%, Branch >= 80%
- Run mutation: `mutmut run --paths-to-mutate=src/query/language_filter.py`

### Step 7: ST Acceptance

- Run DevTools test for language filter chips
- Verify chip selection works
- Verify error state displays correctly

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/query/language_filter.py` | Create |
| `src/query/api/v1/endpoints/query.py` | Modify |
| `src/query/api/web.py` | Modify |
| `tests/test_language_filter.py` | Create |

## UCD Reference

- Language Filter chips: default, selected, hover, error states
- Colors: Primary #58A6FF, Background #0D1117
- Error: "Unsupported language" alert with AlertCircle icon
