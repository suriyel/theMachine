# Code Context Retrieval — Service Lifecycle Guide

> User-editable. Claude reads this file before managing services. Update when ports change or new services are added.

## Services

| Service Name | Port | Start Command | Stop Command | Verify URL |
|---|---|---|---|---|
| query-api | 8000 | `uvicorn src.query.main:app --host 0.0.0.0 --port 8000` | kill PID | `http://localhost:8000/api/v1/health` |
| mcp-server | 3000 | `python -m src.query.mcp` | kill PID | `http://localhost:3000/health` |
| index-worker | — | `celery -A src.indexing.celery_app worker --loglevel=info` | kill PID | N/A (check celery inspect active) |
| celery-beat | — | `celery -A src.indexing.celery_app beat --loglevel=info` | kill PID | N/A |

## External Dependencies (must be running before services)

| Service | Port | Verify |
|---|---|---|
| PostgreSQL | 5432 | `pg_isready -h localhost -p 5432` |
| Elasticsearch | 9200 | `curl -f http://localhost:9200/_cluster/health` |
| Qdrant | 6333 | `curl -f http://localhost:6333/healthz` |
| Redis | 6379 | `redis-cli ping` |
| RabbitMQ | 5672 | `rabbitmqctl status` |

## Start All Services

```bash
# Ensure environment is activated and .env is sourced
source .venv/bin/activate
set -a && source .env && set +a

# Start query-api
uvicorn src.query.main:app --host 0.0.0.0 --port 8000 > /tmp/svc-query-api-start.log 2>&1 &
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
