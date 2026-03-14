# Service Lifecycle Guide — Code Context Retrieval

> User-editable. Claude reads this file before managing services. Update when ports change or new services are added.

## Services Table

| Service Name | Port | Start Command | Stop Command | Verify URL |
|--------------|------|---------------|--------------|------------|
| Query Service | 8000 | `uvicorn src.query.main:app --host 0.0.0.0 --port 8000` | `kill <PID>` or by port | `GET http://localhost:8000/api/v1/health` |
| Indexing Service (Celery Worker) | — | `celery -A src.indexing.worker worker --loglevel=info` | `kill <PID>` | (no HTTP endpoint) |
| Indexing Scheduler (Celery Beat) | — | `celery -A src.indexing.worker beat --loglevel=info` | `kill <PID>` | (no HTTP endpoint) |
| PostgreSQL | 5432 | (managed externally or Docker) | (managed externally) | `pg_isready -h localhost -p 5432` |
| Redis | 6379 | `redis-server` | `redis-cli shutdown` | `redis-cli ping` |
| Qdrant | 6333 | `qdrant` or Docker | `kill <PID>` or Docker stop | `GET http://localhost:6333/health` |
| Elasticsearch | 9200 | `elasticsearch` or Docker | `kill <PID>` or Docker stop | `GET http://localhost:9200/_cluster/health` |

## Start All Services

### Windows (PowerShell)

```powershell
# 1. Start storage services (assume Docker or local installs)
# PostgreSQL, Redis, Qdrant, Elasticsearch - start via Docker or local services

# 2. Start Query Service
cmd /c "start /b uvicorn src.query.main:app --host 0.0.0.0 --port 8000 > %TEMP%\svc-query-start.log 2>&1"
timeout /t 3 /nobreak >nul
powershell "Get-Content $env:TEMP\svc-query-start.log -TotalCount 30"
# → Extract PID and port from output; record both in task-progress.md

# 3. Start Celery Worker
cmd /c "start /b celery -A src.indexing.worker worker --loglevel=info > %TEMP%\svc-worker-start.log 2>&1"
timeout /t 3 /nobreak >nul
powershell "Get-Content $env:TEMP\svc-worker-start.log -TotalCount 30"

# 4. Start Celery Beat (optional, for scheduled indexing)
cmd /c "start /b celery -A src.indexing.worker beat --loglevel=info > %TEMP%\svc-beat-start.log 2>&1"
timeout /t 3 /nobreak >nul
powershell "Get-Content $env:TEMP\svc-beat-start.log -TotalCount 30"
```

### Unix/macOS (Bash)

```bash
# 1. Start storage services (assume Docker or local installs)
# PostgreSQL, Redis, Qdrant, Elasticsearch - start via Docker or local services

# 2. Start Query Service
uvicorn src.query.main:app --host 0.0.0.0 --port 8000 > /tmp/svc-query-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-query-start.log
# → Extract PID and port from output; record both in task-progress.md

# 3. Start Celery Worker
celery -A src.indexing.worker worker --loglevel=info > /tmp/svc-worker-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-worker-start.log

# 4. Start Celery Beat (optional, for scheduled indexing)
celery -A src.indexing.worker beat --loglevel=info > /tmp/svc-beat-start.log 2>&1 &
sleep 3
head -30 /tmp/svc-beat-start.log
```

## Verify Services Running

```bash
# Query Service
curl -f http://localhost:8000/api/v1/health

# PostgreSQL
pg_isready -h localhost -p 5432

# Redis
redis-cli ping
# Expected: PONG

# Qdrant
curl -f http://localhost:6333/health

# Elasticsearch
curl -f http://localhost:9200/_cluster/health
```

## Stop All Services

### By PID (preferred — use PID recorded in task-progress.md)

```bash
# Unix/macOS
kill <PID>

# Windows
taskkill /F /PID <PID>
```

### By Port (fallback)

```bash
# Unix/macOS — Query Service
lsof -ti :8000 | xargs kill -9

# Windows — Query Service
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %a
```

## Verify Services Stopped

```bash
# Unix/macOS — expect no output
lsof -i :8000
lsof -i :5432
lsof -i :6379
lsof -i :6333
lsof -i :9200

# Windows — expect no output
netstat -ano | findstr :8000
netstat -ano | findstr :5432
netstat -ano | findstr :6379
netstat -ano | findstr :6333
netstat -ano | findstr :9200
```

## Restart Protocol (4 Steps)

1. **Kill** — Stop All Services (by PID from task-progress.md, or by port fallback)

2. **Verify dead** — Run "Verify Services Stopped" commands; poll ports max 5 seconds — must not respond

3. **Start** — Run "Start All Services" with output capture → `head -30` / `Get-Content -TotalCount 30` → extract new PID/port → update task-progress.md

4. **Verify alive** — Run "Verify Services Running"; poll health endpoints max 10 seconds — must respond

## Docker Compose (Alternative)

If using Docker Compose for storage services:

```bash
# Start storage stack
docker compose up -d

# Verify
docker compose ps

# Stop
docker compose down
```

## Notes

- **Query Service** is stateless and can be scaled horizontally
- **Celery Worker** handles indexing tasks asynchronously
- **Celery Beat** triggers scheduled index refresh (FR-016)
- **Storage services** (PG, Redis, Qdrant, ES) are typically managed via Docker or cloud services
- Record all PIDs in `task-progress.md` when starting services for proper cleanup
