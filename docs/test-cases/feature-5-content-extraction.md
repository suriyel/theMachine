# Test Case Document — Feature #5: Content Extraction (FR-003)

**Feature ID**: 5
**Feature Title**: Content Extraction (FR-003)
**Related Requirements**: FR-003
**Date**: 2026-03-15
**Standard**: ISO/IEC/IEEE 29119-3

## Summary

| Category | Count |
|----------|-------|
| Functional | 2 |
| Boundary | 1 |
| Security | 0 |
| Accessibility | 0 |
| Performance | 0 |
| **Total** | **3** |

## Test Cases

### ST-FUNC-005-001: Extract Multiple Content Types

| Field | Value |
|-------|-------|
| **Test Case ID** | ST-FUNC-005-001 |
| **Category** | Functional |
| **Feature** | Content Extraction (FR-003) |
| **Verification Step** | Given a cloned repository containing README.md, source files, and a CHANGELOG.md, when content extraction runs, then all three content types are identified and queued for chunking |
| **Priority** | High |
| **Preconditions** | 1. ContentExtractor module is importable<br>2. Test repository structure created with README.md, src/main.java, CHANGELOG.md |
| **Test Data** | Repository with mixed content types: README.md, main.java, CHANGELOG.md |
| **Test Type** | Real |

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create temp directory with README.md, src/main.java, CHANGELOG.md | Files created successfully |
| 2 | Instantiate ContentExtractor | Object created without error |
| 3 | Call extract(repo_path, ["Java"]) | Returns list of RawContent objects |
| 4 | Verify README content type present | ContentType.README found in results |
| 5 | Verify SOURCE content type present | ContentType.SOURCE found in results |
| 6 | Verify CHANGELOG content type present | ContentType.CHANGELOG found in results |
| 7 | Verify all three content types returned | Exactly 3 items with distinct content types |

**Actual Results:** All 3 content types (README, SOURCE, CHANGELOG) identified and extracted correctly.

**Result:** PASS

---

### ST-FUNC-005-002: Extract Zero Content from Binary-Only Repository

| Field | Value |
|-------|-------|
| **Test Case ID** | ST-FUNC-005-002 |
| **Category** | Functional |
| **Feature** | Content Extraction (FR-003) |
| **Verification Step** | Given a cloned repository containing only binary files, when content extraction runs, then warning is logged and job completes with zero chunks |
| **Priority** | High |
| **Preconditions** | 1. ContentExtractor module is importable<br>2. Test repository contains only binary files |
| **Test Data** | Repository with .png, .jpg, .exe files only |
| **Test Type** | Real |

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create temp directory with binary files only (image.png, archive.zip) | Files created successfully |
| 2 | Instantiate ContentExtractor | Object created without error |
| 3 | Call extract(repo_path, ["Java"]) | Returns empty list or list with no SOURCE/README/CHANGELOG |
| 4 | Verify no indexable content extracted | Results contain zero items with content_type in [SOURCE, README, CHANGELOG] |

**Actual Results:** Empty list returned when only binary files present.

**Result:** PASS

---

### ST-BNDRY-005-001: Extract 100 Source Files

| Field | Value |
|-------|-------|
| **Test Case ID** | ST-BNDRY-005-001 |
| **Category** | Boundary |
| **Feature** | Content Extraction (FR-003) |
| **Verification Step** | Given a cloned repository with 100 source files, when content extraction runs, then all 100 files are identified by language extension |
| **Priority** | High |
| **Preconditions** | 1. ContentExtractor module is importable<br>2. Test repository contains 100 Java source files |
| **Test Data** | Repository with exactly 100 .java files |
| **Test Type** | Real |

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create temp directory with 100 Java files | 100 files created |
| 2 | Instantiate ContentExtractor | Object created without error |
| 3 | Call extract(repo_path, ["Java"]) | Returns list of RawContent objects |
| 4 | Count Java source files extracted | Exactly 100 items with language="Java" |
| 5 | Verify all have SOURCE content type | All 100 items have ContentType.SOURCE |

**Actual Results:** All 100 Java files extracted successfully with correct content type.

**Result:** PASS

---

## Traceability Matrix

| Test Case ID | Requirement | Verification Step | Automated Test | Result |
|--------------|-------------|-------------------|----------------|--------|
| ST-FUNC-005-001 | FR-003 | VS-1: README, source, CHANGELOG extraction | tests/test_content_extractor.py::TestContentExtractorExtraction::test_extract_identifies_readme, test_extract_identifies_source_file, test_extract_identifies_changelog | PASS |
| ST-FUNC-005-002 | FR-003 | VS-2: Binary-only repo warning | tests/test_content_extractor.py::TestContentExtractorExtraction::test_extract_empty_repo_warns | PASS |
| ST-BNDRY-005-001 | FR-003 | VS-3: 100 source files | tests/test_content_extractor.py::TestContentExtractorExtraction::test_extract_many_source_files | PASS |

## Real Test Case Execution Summary

| Metric | Value |
|--------|-------|
| Total Real Test Cases | 3 |
| Passed | 3 |
| Failed | 0 |
| Pending | 0 |

## Execution Notes

- This is a backend-only feature (not UI) - no Chrome DevTools MCP testing required
- Test cases verify ContentExtractor behavior through direct Python API calls
- All tests use real file system operations (no mocks at the primary interface level)
- The TDD unit tests already provide comprehensive coverage; ST adds integration-level verification
