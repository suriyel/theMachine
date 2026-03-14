# Code Context Retrieval — Worker Session Guide

Project-specific workflow guide for implementing features through TDD with quality gates.

## Orient

Each session starts by understanding current state:

1. **Load environment** — activate the project environment:
   ```bash
   # Windows
   .venv\Scripts\activate
   # Unix/macOS
   source .venv/bin/activate
   ```

2. **Read progress** — `task-progress.md` `## Current State` section for stats, last completed feature, next feature

3. **Read features** — `feature-list.json` for constraints, assumptions, required_configs, feature statuses

4. **Read design overview** — `docs/plans/2026-03-14-code-context-retrieval-design.md` Section 1 (Design Drivers)

5. **Check recent commits** — `git log --oneline -10`

6. **Pick next feature** — highest-priority `"failing"` feature with all dependencies `"passing"`

7. **For UI features** (`"ui": true`) — read UCD: `docs/plans/2026-03-14-code-context-retrieval-ucd.md`

## Bootstrap

1. **Environment setup** — if `init.sh` / `init.ps1` not yet run, execute once

2. **Verify test commands**:
   ```bash
   python scripts/get_tool_commands.py feature-list.json
   ```

3. **Smoke test** — run tests to verify previously passing features still work:
   ```bash
   pytest
   ```

4. **Services** — do NOT start services during Bootstrap; services are managed by `long-task-feature-st` during ST Acceptance testing

## Config Gate

Before planning any feature with external dependencies:

```bash
python scripts/check_configs.py feature-list.json --feature <id>
```

**If configs missing:**
1. For each missing `env`-type config, use `AskUserQuestion` to ask for the value
2. Save to `.env` file in project root (format: `KEY=value`)
3. Re-run check to confirm

**Block until all configs pass.**

## TDD Red

Write failing tests FIRST. Tests define expected behavior.

1. **Read spec** — extract `{srs_section}` and `{design_section}` via Document Lookup Protocol (read full subsections, not grep snippets)

2. **Write unit tests** covering all verification_steps:
   - Happy path scenarios
   - Error handling scenarios
   - Boundary conditions
   - Security scenarios (if auth-related)
   - Negative test ratio >= 40%
   - Low-value assertion ratio <= 20%

3. **For UI features** (`"ui": true`): write `[devtools]` functional tests using EXPECT/REJECT format:
   ```
   [devtools] /search | EXPECT: search input, language filter chips, result cards | REJECT: console errors, broken images, placeholder "TODO"
   ```

4. **Run tests** — ALL must FAIL (no implementation yet):
   ```bash
   pytest
   ```

## TDD Green

Write minimal code to make ALL tests pass.

1. **Implement** — write the minimum code necessary to pass tests

2. **Run full suite**:
   ```bash
   pytest
   ```
   All tests must pass, no regressions.

## Coverage Gate

After TDD Green, verify test coverage:

```bash
pytest --cov=src --cov-branch --cov-report=term-missing
```

**Thresholds:**
- Line coverage >= 90%
- Branch coverage >= 80%

**If below threshold:**
- Identify uncovered lines from report
- Write additional tests for those paths
- Re-run coverage

**Evidence required:** Full coverage report output showing line % and branch %.

## TDD Refactor

Clean up code while keeping tests green:

1. **Refactor** — improve code structure, remove duplication, enhance readability

2. **Re-run tests**:
   ```bash
   pytest
   ```
   Must still all pass.

## Mutation Gate

After refactor, verify test effectiveness:

```bash
# Incremental (changed files only)
mutmut run --paths-to-mutate=src/module_name.py
```

**Threshold:** Mutation score >= 80%

**If below threshold:**
- Run `mutmut results` to see surviving mutants
- Run `mutmut show <id>` to inspect each
- Improve test assertions to kill mutants
- Re-run mutation testing

**Evidence required:** Mutation report showing killed/survived/total and score %.

## Verification Enforcement

Before marking any feature as passing, run fresh verification:

```
1. IDENTIFY → Get commands via get_tool_commands.py
2. RUN → Execute each command fresh (not cached)
3. READ → Full output for each
4. VERIFY → Does ALL output confirm the claim?
5. THEN CLAIM → Mark feature "passing"
```

**Red flag words that mean STOP and re-verify:**
- "should pass", "probably works", "seems to be working"
- "I believe this is correct", "this looks good"
- "coverage is probably fine", "mutation score should be high enough"

## Code Review (Spec & Design Compliance)

After quality gates pass, run compliance review via `long-task:long-task-review`:

- **Spec Compliance** — Does implementation match verification_steps and SRS?
- **Design Compliance** — Does implementation follow class diagrams, sequence flows, dependency versions?
- **UCD Compliance** (ui:true only) — Do style tokens match UCD guide?

## ST Test Cases

After quality gates pass, run ST Acceptance Testing via `long-task:long-task-feature-st`:

**Purpose:** Black-box acceptance testing per feature, ISO/IEC/IEEE 29119 compliant.

**Process:**
1. Invoke `long-task:long-task-feature-st` skill
2. Skill manages environment lifecycle (start/stop services)
3. Execute all `[devtools]` verification steps via Chrome DevTools MCP
4. Generate test case document: `docs/test-cases/feature-{id}-{slug}.md`

**Test case document includes:**
- Test case ID and traceability (FR-xxx, verification_steps)
- Preconditions and test data
- Test procedure (step-by-step)
- Expected results
- Actual results (from execution)
- Pass/Fail verdict

**Hard Gate:** Any execution failure must be reported to user. No bypass allowed.

## Examples

Create runnable example in `examples/` for user-facing features:

- API features → Python script calling the endpoint
- UI features → Markdown walkthrough or demo script
- Name pattern: `<NN>-<short-name>.<ext>`

Update `examples/README.md` index.

## Persist

Save state for next session:

1. **Git commit** implementation + tests + examples:
   ```bash
   git add .
   git commit -m "feat(#id): feature description"
   ```

2. **Update RELEASE_NOTES.md** (Keep a Changelog format)

3. **Update task-progress.md**:
   - Update `## Current State` header
   - Append session entry

4. **Mark feature `"status": "passing"`** in feature-list.json

5. **Validate**:
   ```bash
   python scripts/validate_features.py feature-list.json
   ```

6. **Commit progress files**:
   ```bash
   git add feature-list.json task-progress.md RELEASE_NOTES.md
   git commit -m "progress: mark feature #id passing"
   ```

## Critical Rules

- **One feature per cycle** — prevents context exhaustion
- **Strict step order** — no skipping, no reordering
- **Sub-skills are non-negotiable** — TDD, Quality, ST, Review MUST be invoked via Skill tool
- **Config gate before planning** — never plan when configs missing
- **Never mark "passing" without fresh evidence** — run tests, read output
- **Never remove or edit verification_steps** — use increment skill for changes
- **Systematic debugging only** — trace root cause, never guess-and-fix
- **Update RELEASE_NOTES.md after every commit**
- **Always commit + update progress before ending session**
- **Never leave broken code** — revert incomplete work

## Environment Commands

| Action | Command |
|--------|---------|
| Activate environment (Windows) | `.venv\Scripts\activate` |
| Activate environment (Unix/macOS) | `source .venv/bin/activate` |
| Run all tests | `pytest` |
| Run specific test file | `pytest tests/test_module.py` |
| Run with coverage | `pytest --cov=src --cov-branch --cov-report=term-missing` |
| Run mutation (incremental) | `mutmut run --paths-to-mutate=src/module.py` |
| Run mutation (full) | `mutmut run` |
| View mutation results | `mutmut results` |
| View specific mutant | `mutmut show <id>` |

## Service Commands

This project has two main services. See `env-guide.md` for authoritative start/stop/restart commands.

**Services:**
| Service | Port | Health Check |
|---------|------|--------------|
| Query Service | 8000 | `GET /api/v1/health` |
| Indexing Service | 8001 | (Celery worker, no HTTP) |

**Restart Protocol (4 steps):**
1. **Kill** — Stop services using env-guide.md commands
2. **Verify dead** — Poll ports, confirm no response
3. **Start** — Run start commands from env-guide.md, capture output, record PID
4. **Verify alive** — Poll health endpoints, confirm response

**Important:** Services are started during ST acceptance testing by `long-task-feature-st`, not during Bootstrap.

## Config Management

This project uses `.env` file for configuration.

**To add/update a config value:**
1. Open `.env` in project root (create if not exists)
2. Add or update line: `KEY=value`
3. Save file
4. Config is loaded automatically by `python-dotenv`

**Config priority:**
1. System environment variables (highest)
2. `.env` file
3. Default values in code (lowest)

**Required configs are listed in `feature-list.json` under `required_configs`.**

## Real Test Convention

**Identification method:** Marker-based (`@pytest.mark.real_test`)

**Run only real tests:**
```bash
pytest -m real_test
```

**Example real test:**
```python
import pytest

@pytest.mark.real_test
async def test_query_retrieval_real():
    """Real test: Query returns results from actual Qdrant/ES."""
    from src.query.handler import QueryHandler
    from src.query.models import QueryRequest

    handler = QueryHandler()
    response = await handler.handle(QueryRequest(
        text="WebClient timeout",
        query_type="natural_language"
    ))

    assert response.results is not None
    assert len(response.results) <= 3
    assert all(r.score >= 0.6 for r in response.results)
```

**Mock patterns to avoid in real tests:**
- `@patch`, `Mock()`, `MagicMock()`, `AsyncMock()`
- `monkeypatch.setattr` for dependencies
- `unittest.mock.*`

**Real tests MUST hit actual services (Qdrant, ES, PG, Redis) using testcontainers or local instances.**

## Chrome DevTools MCP Testing (UI Features)

This project has UI features. When implementing `"ui": true` features:

**DevTools Gate (before planning):**
```bash
python scripts/check_devtools.py feature-list.json --feature <id>
```

**`[devtools]` verification step format:**
```
[devtools] /path | EXPECT: <positive criteria> | REJECT: <negative criteria>
```

**Test sequence:**
1. `navigate_page(url)` — navigate to page
2. `wait_for(text)` — wait for page load
3. `evaluate_script(ui_error_detector)` — automated error detection (HARD FAIL if errors)
4. `take_snapshot()` — capture initial state
5. Verify EXPECT criteria in snapshot
6. Verify REJECT criteria NOT present
7. `click(uid)` / `fill(uid, value)` — perform user action
8. `wait_for(text)` — wait for response
9. `evaluate_script(ui_error_detector)` — error detection again
10. `take_snapshot()` / `take_screenshot()` — capture result
11. Verify expected outcome
12. `list_console_messages(types=["error"])` — HARD FAIL if console errors

**Three-layer error detection:**
1. Automated error detection script via `evaluate_script()`
2. EXPECT/REJECT format verification
3. Console error gate via `list_console_messages()`

## UCD Style Reference

For UI features, reference the UCD style guide:

**Theme:** Developer Dark
**Key tokens:**
- Primary color: `#58A6FF`
- Background: `#0D1117` (primary), `#161B22` (secondary)
- Text: `#E6EDF3` (primary), `#8B949E` (secondary)
- Code font: JetBrains Mono, 13px
- UI font: System sans-serif, 14px body

**Components:** Search Input, Language Filter, Result Card, Score Badge, Empty State, Error Alert, Login Form

**Pages:** Search Page (`/search`), Login Page (`/login`)

See `docs/plans/2026-03-14-code-context-retrieval-ucd.md` for full style tokens and component prompts.


*by long task skill*
