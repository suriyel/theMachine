# Implementation Plan — Feature #29: NFR-004 Single Repository Size

**Date**: 2026-03-18
**Feature**: NFR-004: Single Repository Size
**Status**: Implementation In Progress

## Overview

Implement a test runner script to validate that the system can index repositories up to 1GB without failure.

## Verification Steps

- Given 1GB repository, when indexing job runs, then job completes successfully with all chunks indexed

## NFR Requirements

- **NFR-004**: System shall handle repositories up to size limit (Single repository ≤ 1 GB)
- **Pass Criteria**: 1 GB repository indexed successfully
- **Fail Criteria**: Indexing fails on 1 GB repository

## Implementation Approach

Following the pattern established by NFR-002 (Query Throughput) and NFR-003 (Repository Capacity), implement a test runner script that:

1. **Test Runner Script** (`scripts/run_repo_size_test.py`):
   - Accepts repository size threshold parameter
   - Validates file size limits during content extraction
   - Validates chunk processing handles large files
   - Supports `--validate` mode for pre-collected metrics

2. **Unit Tests** (for validation logic):
   - Test file size threshold validation
   - Test large file chunking boundaries
   - Test memory-efficient processing paths

3. **ST Test Cases** (per ISO/IEC/IEEE 29119):
   - Generate test case document for black-box acceptance

## Technical Details

### File Size Handling
- Threshold: 1GB per repository
- Must handle large files (>10MB already handled in ContentExtractor)
- Streaming/chunked processing for memory efficiency

### Related Components
- `src/indexing/services/content_extractor.py` - Already handles large file detection
- `src/indexing/services/code_chunker.py` - Multi-granularity chunking

## Files to Create/Modify

| File | Action |
|------|--------|
| `scripts/run_repo_size_test.py` | Create - Test runner script |
| `tests/test_repo_size.py` | Create - Unit tests for validation logic |
| `docs/test-cases/feature-29-nfr-004-single-repository-size.md` | Create - ST test cases |

## Implementation Order

1. Create test runner script with validation logic
2. Create unit tests for validation functions
3. Generate ST test case document
4. Create example script
