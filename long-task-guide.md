# Code Context Retrieval — Worker Session Guide

## Environment Commands

```bash
# Activate environment
source .venv/bin/activate

# Run tests
pytest --cov=src --cov-branch --cov-report=term-missing tests/

# Run specific test file
pytest tests/test_<module>.py -v

# Coverage report
pytest --cov=src --cov-branch --cov-report=term-missing

# Mutation testing (ALWAYS scope to feature files — never run unscoped)
mutmut run --paths-to-mutate=src/<changed_module1>.py,src/<changed_module2>.py
# WARNING: `mutmut run` without --paths-to-mutate generates 4000+ mutants and will timeout

# Mutation results
mutmut results
mutmut show <mutant-id>
```

## Service Commands

Refer to `env-guide.md` as the authoritative source for start/stop/restart commands.

**Services**:
- **query-api** (FastAPI): port 8000, health check: `http://localhost:8000/api/v1/health`
- **mcp-server**: port 3000
- **index-worker** (Celery): no port (background worker)

**Restart Protocol** (4 steps): Kill → Verify dead → Start with output capture → Verify alive. See `env-guide.md` for exact commands.

## Config Management

This project uses `.env` file for configuration (loaded via python-dotenv or os.environ).

To add/update a config value:
1. Append `KEY=value` to `.env` in project root
2. Ensure `.env` is in `.gitignore`
3. Update `.env.example` with the new key (no secret values)
4. Source the `.env` before running: `set -a && source .env && set +a`

## Real Test Convention

**Identification method**: pytest marker `@pytest.mark.real`

**Run command** (real tests only):
```bash
pytest -m real tests/
```

**Mock patterns to avoid in real tests**: `Mock`, `MagicMock`, `patch`, `mocker`, `monkeypatch.setattr`

**Example real test**:
```python
import pytest

@pytest.mark.real
def test_repository_model_create(db_session):
    """Real test: creates a Repository record in actual test database."""
    from src.shared.models.repository import Repository
    repo = Repository(name="test-repo", url="https://github.com/test/repo")
    db_session.add(repo)
    db_session.commit()
    assert repo.id is not None
    assert repo.status == "pending"
```

## Orient

1. Activate environment: `source .venv/bin/activate`
2. Source config: `set -a && source .env && set +a`
3. Read `task-progress.md` — current state, last feature, next up
4. Read `feature-list.json` — constraints, assumptions, feature statuses
5. Read design doc Section 1 — architecture overview
6. Run `git log --oneline -10`
7. Pick next `"failing"` feature by priority → array position (skip deprecated)
8. Check dependency satisfaction before starting

## Bootstrap

1. If environment not ready: run `bash init.sh`
2. Verify: `python3 scripts/get_tool_commands.py feature-list.json`
3. Smoke-test passing features: `pytest tests/ -v --tb=short`

## Config Gate

```bash
python3 scripts/check_configs.py feature-list.json --feature <id>
```

If missing configs: prompt user for values → append to `.env` → re-run check.

## TDD Red

1. Read the feature's design section (Document Lookup Protocol — read full `### 4.N` subsection)
2. Read the SRS FR-xxx section for acceptance criteria
3. Write failing test(s) first — one test per acceptance criterion
4. Verify tests fail: `pytest tests/test_<module>.py -v`

## TDD Green

1. Implement minimum code to pass all tests
2. Run: `pytest tests/test_<module>.py -v`
3. All tests must pass before proceeding

## Coverage Gate

```bash
pytest --cov=src --cov-branch --cov-report=term-missing tests/
```
- Line coverage >= 90%
- Branch coverage >= 80%

If below threshold: add tests for uncovered lines/branches.

## TDD Refactor

1. Clean up implementation code (no behavior changes)
2. Re-run tests to confirm nothing broke
3. Re-check coverage

## Mutation Gate

```bash
mutmut run --paths-to-mutate=src/<changed_files>
mutmut results
```
- Mutation score >= 80% (surviving mutants < 20%)

If below threshold: strengthen assertions, add edge case tests.

## Verification Enforcement

Before marking any feature as "passing":
1. All tests pass: `pytest tests/ -v`
2. Coverage gate met
3. Mutation gate met
4. All verification_steps from feature-list.json are covered by tests

## ST Test Cases

After quality gates pass, generate ISO/IEC/IEEE 29119 compliant test case documents:
- Save to `docs/test-cases/feature-<id>-<slug>.md`
- Each test case traces to SRS acceptance criteria and verification_steps
- Include preconditions, test steps, expected results, and actual results

## Chrome DevTools MCP

For UI features (`"ui": true`), use Chrome DevTools MCP for black-box functional testing:
1. Start the application using `env-guide.md` "Start All Services"
2. Navigate to the UI entry point specified in the feature's `ui_entry` field
3. Execute each `[devtools]`-prefixed verification step:
   - Navigate to URL → verify page elements render correctly
   - Interact with inputs/buttons → verify state changes
   - Check for console errors → reject if any present
4. Capture screenshots for evidence
5. Stop services using `env-guide.md` "Stop All Services"

## Code Review

After quality gates pass, invoke `long-task:long-task-review` for spec & design compliance.

## Examples

After each feature passes, create/update `examples/<NN>-<feature-slug>.py` with a runnable demonstration.

## Persist

1. Update `feature-list.json`: set feature status to `"passing"`
2. Update `task-progress.md`: append session entry with feature completed
3. Update `RELEASE_NOTES.md`: add entry under current version
4. Git commit all changes

## Critical Rules

- **Never skip TDD**: Write tests first, then implement
- **Never skip quality gates**: Coverage AND mutation must pass
- **Never skip review**: Run compliance review after every feature
- **One feature per cycle**: Complete the full pipeline before starting the next
- **Follow design doc**: Implementation must match approved class diagrams and sequence flows
- **Environment activation**: Always activate venv before running any command
- **Service lifecycle**: Services managed by long-task-feature-st, not during TDD


*by long task skill*
