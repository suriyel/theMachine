"""Example: Language Filter usage.

This example demonstrates how to use the LanguageFilter class
to validate and filter query results by programming language.
"""

from src.query.language_filter import LanguageFilter


def main():
    filter = LanguageFilter()

    # Validate supported languages (case-insensitive)
    print("=== Language Validation ===")
    print(f"Java: {filter.validate('Java')}")  # -> 'java'
    print(f"Python: {filter.validate('python')}")  # -> 'python'
    print(f"TypeScript: {filter.validate('typescript')}")  # -> 'typescript'
    print(f"C++: {filter.validate('C++')}")  # -> 'cpp'
    print(f"None: {filter.validate(None)}")  # -> None
    print(f"all: {filter.validate('all')}")  # -> None

    # Validate unsupported language
    print("\n=== Unsupported Language ===")
    try:
        filter.validate("Ruby")
    except ValueError as e:
        print(f"Error: {e}")

    # Filter candidates by language
    print("\n=== Filtering Candidates ===")

    # Mock candidate data
    class MockCandidate:
        def __init__(self, repo, file_path, language):
            self.repo_name = repo
            self.file_path = file_path
            self.language = language

        def __repr__(self):
            return f"Candidate({self.file_path}, {self.language})"

    candidates = [
        MockCandidate("repo1", "Main.java", "java"),
        MockCandidate("repo1", "Helper.java", "java"),
        MockCandidate("repo2", "main.py", "python"),
        MockCandidate("repo3", "index.ts", "typescript"),
    ]

    # Filter to Java only
    java_results = filter.apply(candidates, "java")
    print(f"Java results: {java_results}")

    # Filter to Python
    python_results = filter.apply(candidates, "python")
    print(f"Python results: {python_results}")

    # No filter (None)
    all_results = filter.apply(candidates, None)
    print(f"All results: {all_results}")


if __name__ == "__main__":
    main()
