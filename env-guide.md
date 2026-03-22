# Code Context Retrieval — Service Lifecycle Guide

> User-editable. Claude reads this file before managing services. Update when ports change or new services are added.

## Services

| Service Name | Port | Start Command | Stop Command | Verify URL |
|---|---|---|---|---|
| query-api | 8000 | `uvicorn --factory src.query.app:create_app --host 0.0.0.0 --port 8000` | kill PID | `http://localhost:8000/api/v1/health` |
| mcp-server | 3000 | `python -m src.query.mcp` | kill PID | `http://localhost:3000/health` |
| index-worker | — | `celery -A src.indexing.celery_app worker --loglevel=info` | kill PID | N/A (check celery inspect active) |
| celery-beat | — | `celery -A src.indexing.celery_app beat --loglevel=info` | kill PID | N/A |

## External Dependencies (must be running before services)

All external dependencies run as Docker containers. Start them with:
```bash
docker start postgres redis qdrant elasticsearch rabbitmq
```

| Service | Port | Verify |
|---|---|---|
| PostgreSQL | 5432 | `pg_isready -h localhost -p 5432` |
| Elasticsearch | 9200 | `curl -f http://localhost:9200/_cluster/health` |
| Qdrant | 6333 | `curl -f http://localhost:6333/healthz` |
| Redis | 6379 | `redis-cli ping` |
| RabbitMQ | 5672 | `docker exec rabbitmq rabbitmqctl status` |

## Start All Services

```bash
# Ensure environment is activated and .env is sourced
source .venv/bin/activate
set -a && source .env && set +a

# Start query-api
uvicorn --factory src.query.app:create_app --host 0.0.0.0 --port 8000 > /tmp/svc-query-api-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-query-api-start.log
# → Record PID in task-progress.md

# Start mcp-server
python -m src.query.mcp > /tmp/svc-mcp-server-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-mcp-server-start.log
# → Record PID in task-progress.md

# Start index-worker
celery -A src.indexing.celery_app worker --loglevel=info > /tmp/svc-index-worker-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-index-worker-start.log
# → Record PID in task-progress.md

# Start celery-beat (scheduler)
celery -A src.indexing.celery_app beat --loglevel=info > /tmp/svc-celery-beat-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-celery-beat-start.log
# → Record PID in task-progress.md
```

### Windows Alternative

```powershell
# Start query-api
cmd /c "start /b uvicorn src.query.main:app --host 0.0.0.0 --port 8000 > %TEMP%\svc-query-api-start.log 2>&1"
timeout /t 3 /nobreak >nul
powershell "Get-Content $env:TEMP\svc-query-api-start.log -TotalCount 30"
```

## Verify Services Running

```bash
curl -f http://localhost:8000/api/v1/health    # query-api
curl -f http://localhost:3000/health            # mcp-server
celery -A src.indexing.celery_app inspect ping  # index-worker
```

## Stop All Services

```bash
# By PID (preferred — use PID recorded in task-progress.md)
kill <query-api-PID>
kill <mcp-server-PID>
kill <index-worker-PID>
kill <celery-beat-PID>

# By port (fallback)
lsof -ti :8000 | xargs kill -9    # query-api
lsof -ti :3000 | xargs kill -9    # mcp-server
```

### Windows Alternative

```powershell
taskkill /F /PID <PID>
# or by port
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %a
```

## Verify Services Stopped

```bash
lsof -i :8000    # expect no output
lsof -i :3000    # expect no output
```

### Windows Alternative

```powershell
netstat -ano | findstr :8000    # expect no output
netstat -ano | findstr :3000    # expect no output
```

## Restart Protocol (4 steps)

1. **Kill** — Stop All Services (by PID from task-progress.md, or by port)
2. **Verify dead** — run Verify Services Stopped; poll port max 5 seconds — must not respond
3. **Start** — run Start All Services with output capture → `head -30` → extract new PID/port → update task-progress.md
4. **Verify alive** — run Verify Services Running; poll health endpoint max 10 seconds — must respond

---

## Proxy Configuration

This machine has system-level HTTP/SOCKS proxy (`ALL_PROXY`, `HTTP_PROXY`, `HTTPS_PROXY`). Localhost services are **not** reachable through the proxy.

**For real integration tests** (connecting to localhost ES/Qdrant/Redis/PostgreSQL):
- The `.env` file includes `NO_PROXY=localhost,127.0.0.1`
- `aiohttp` (used by elasticsearch-py async) ignores `NO_PROXY` when `ALL_PROXY` (SOCKS) is set
- **Solution**: Clear `ALL_PROXY` before running real tests:
  ```bash
  # In test file (module level, before imports):
  import os
  for k in ("ALL_PROXY", "all_proxy"):
      os.environ.pop(k, None)

  # Or from shell:
  env -u ALL_PROXY -u all_proxy pytest -m real tests/
  ```
- The `conftest.py` autouse fixture `_clear_proxy_env` clears proxy for non-`@pytest.mark.real` tests. Real tests that connect to localhost must handle proxy clearing themselves.

## Elasticsearch Operational Notes

### Disk Watermark (Critical)

ES refuses to allocate shards when disk usage exceeds the high watermark (default 90%). Symptoms:
- `indices.create()` returns `acknowledged=true, shards_acknowledged=false`
- Subsequent `index()` calls timeout or return `503 unavailable_shards_exception`
- Cluster status: **red**

**Diagnosis**:
```bash
curl -s http://localhost:9200/_cluster/allocation/explain | python3 -m json.tool | grep -A3 disk_threshold
```

**Fix**: Free disk space or lower watermarks:
```bash
curl -XPUT http://localhost:9200/_cluster/settings -H 'Content-Type: application/json' -d '{
  "persistent": {
    "cluster.routing.allocation.disk.watermark.low": "95%",
    "cluster.routing.allocation.disk.watermark.high": "98%",
    "cluster.routing.allocation.disk.watermark.flood_stage": "99%"
  }
}'
```

### Test Index Cleanup (Mandatory)

**Every real test that creates ES indices MUST clean them up in fixture teardown.** Leaked indices cause:
1. Unassigned shards → cluster goes red/yellow
2. Disk space waste → triggers watermark → blocks ALL new index creation

**Test index rules**:
- Always use `number_of_shards=1, number_of_replicas=0` (single-node cluster)
- Always delete in fixture teardown: `await es.indices.delete(index=name, ignore=[404])`
- Use unique index names with UUID suffix to avoid collisions: `f"test_{uuid.uuid4().hex[:8]}"`

**Manual cleanup** (if leaked indices exist):
```bash
# List test indices
curl -s http://localhost:9200/_cat/indices?v | grep test_

# Delete one by one (wildcard may be disabled)
curl -s http://localhost:9200/_cat/indices?v | grep test_ | awk '{print $3}' | while read idx; do
  curl -s -XDELETE "http://localhost:9200/$idx"
  echo " deleted $idx"
done

# Check health recovers
curl -s http://localhost:9200/_cat/health
```

**Before running ES real tests**, always verify:
```bash
curl -s http://localhost:9200/_cat/health  # Must be green or yellow (NOT red)
curl -s http://localhost:9200/_cat/shards | grep UNASSIGNED  # Must be empty
```

---

## Mutation Testing (mutmut 3.2.0)

### Known Issue: `src` as top-level package

mutmut 3.2.0 has一个 hardcoded `strip_prefix(prefix='src.')` on `__main__.py:261`, designed for [src-layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) projects where `src/` is NOT importable. This project uses `src` as the top-level package itself, causing a name mismatch:

| Source | Mutant key (from file path) | Stats key (from `orig.__module__`) |
|---|---|---|
| Before patch | `shared.database.x_get_engine` | `src.shared.database.x_get_engine` |
| After patch | `src.shared.database.x_get_engine` | `src.shared.database.x_get_engine` |

The mismatch makes all mutants report "no tests" (🫥, exit code 33) even though tests DO kill them.

### Applied Patch

**File**: `.venv/lib/python3.12/site-packages/mutmut/__main__.py` line 261

```python
# BEFORE (broken for src-as-package):
module_name = strip_prefix(str(filename)[:-len(filename.suffix)].replace(os.sep, '.'), prefix='src.')

# AFTER (preserves src. prefix):
module_name = str(filename)[:-len(filename.suffix)].replace(os.sep, '.')
```

**WARNING**: This patch lives inside `.venv/` and will be lost on `pip install mutmut` or venv recreation. Re-apply after:
```bash
pip install mutmut==3.2.0
# Then patch line 261 of .venv/lib/python3.12/site-packages/mutmut/__main__.py
sed -i "s/module_name = strip_prefix(str(filename)\[:-len(filename.suffix)\].replace(os.sep, '.'), prefix='src.')/module_name = str(filename)[:-len(filename.suffix)].replace(os.sep, '.')/" \
  .venv/lib/python3.12/site-packages/mutmut/__main__.py
```

### Patch 2: Stats KeyError on third-party `__init__`

**File**: `.venv/lib/python3.12/site-packages/mutmut/__main__.py` line 702

```python
# BEFORE (crashes on third-party __init__ calls in stats):
mutmut.tests_by_mangled_function_name[function].add(...)

# AFTER (skip unknown functions):
if function in mutmut.tests_by_mangled_function_name:
    mutmut.tests_by_mangled_function_name[function].add(...)
```

This also causes `__init__` methods in project classes to report "no tests" (🫥). These are a tooling limitation — verify manually that tests cover the `__init__` behavior.

### conftest.py Hook

`tests/conftest.py` includes a hook for when `MUTANT_UNDER_TEST` is set — it prepends CWD to `sys.path` and clears stale `src.*` module cache so trampolined code in `mutants/` takes priority over the editable install.

### Run Commands

```bash
source .venv/bin/activate

# Full mutation run
mutmut run

# Check results
mutmut results

# Show specific mutant diff
mutmut show <mutant-name>
```

### Equivalent Mutants (expected survivors)

| Mutant | Why equivalent |
|---|---|
| `echo=False` → `echo=True` or removed | SQLAlchemy `create_async_engine` defaults to `echo=False` |
| `version="0.1.0"` removed | FastAPI defaults to `version="0.1.0"` |
