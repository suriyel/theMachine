# Implementation Plan — Feature #4: Git Clone or Update (FR-002)

## Overview

**Feature**: Git Clone or Update (FR-002)
**Priority**: High (P1)
**Dependencies**: Feature #3 (Repository Registration) - PASSING

## Design Reference

From design doc Section 4.1.2 (Class Diagram):
```
GitCloner {
    -workspace_dir: Path
    +clone_or_update(repo: Repository): Path
    -_full_clone(url: str, dest: Path): void
    -_fetch_updates(dest: Path): void
}
```

From SRS FR-002:
- Given a registered repository not yet cloned → full git clone to workspace
- Given a previously cloned repository → git fetch retrieves only latest changes
- Given invalid credentials → job marked failed with error, existing index preserved
- Given network timeout → job marked failed after retry attempts exhausted

## Implementation Details

### 1. GitCloner Class

**Location**: `src/indexing/git_cloner.py`

**Public API**:
- `clone_or_update(repo: Repository) -> Path`: Main entry point
- `_full_clone(url: str, dest: Path) -> None`: Perform full clone
- `_fetch_updates(dest: Path) -> None`: Fetch latest changes

**Behavior**:
1. Check if repository already cloned in workspace (`{workspace_dir}/{repo_id}`)
2. If not exists → `_full_clone()`
3. If exists → `_fetch_updates()`
4. On any failure → raise `GitCloneError` with descriptive message

### 2. Workspace Management

**Configuration**:
- `WORKSPACE_DIR`: Path to store cloned repositories
- Set via `WORKSPACE_DIR` env var, default: `./workspace`

### 3. Error Handling

**Custom Exceptions**:
- `GitCloneError`: Base exception for all git operations
- `GitCloneFailedError`: For clone failures (network, auth)
- `GitFetchError`: For fetch failures

**Retry Logic**:
- 3 retry attempts for network operations
- Exponential backoff: 1s, 2s, 4s
- On auth failure: Do NOT retry, fail immediately

## Files to Create

| File | Purpose |
|------|---------|
| `src/indexing/git_cloner.py` | GitCloner class |
| `src/indexing/exceptions.py` | Custom exceptions |
| `tests/test_git_cloner.py` | Unit tests |

## Test Scenarios

### Happy Path
1. Full clone of new repository
2. Fetch updates for existing repository

### Error Handling
1. Network timeout → retry → fail after 3 attempts
2. Invalid credentials → fail immediately
3. Repository URL not found → clear error message

### Edge Cases
1. Workspace directory doesn't exist → create it
2. Disk full during clone → graceful error
3. Interrupted clone → cleanup partial files

## Implementation Steps

1. Create `src/indexing/__init__.py`
2. Create `src/indexing/exceptions.py` with custom exceptions
3. Create `src/indexing/git_cloner.py` with GitCloner class
4. Create `tests/test_git_cloner.py` with unit tests
5. Run TDD cycle (Red → Green → Refactor)
6. Run Quality Gates (Coverage + Mutation)
7. Create ST test cases
8. Run Compliance Review

## Dependencies

- `GitPython` (>= 3.1.40) — pure Python git operations
- Add to `pyproject.toml`

## Acceptance Criteria (from SRS FR-002)

- [ ] Given registered repo not yet cloned → full clone performed
- [ ] Given previously cloned repo → git fetch retrieves only latest
- [ ] Given invalid credentials → job marked failed, existing index preserved
- [ ] Given network timeout → job marked failed after retries exhausted
