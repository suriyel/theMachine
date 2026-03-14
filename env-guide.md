# Service Lifecycle Guide — Code Context Retrieval

> User-editable. Claude reads this file before managing services. Update when ports change or new services are added.

## Environment Variables (.env)

```bash
# === Database ===
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres

# === Cache & Broker ===
REDIS_URL=redis://localhost:6379/0

# === Vector Store ===
QDRANT_URL=http://localhost:6333

# === Keyword Index ===
ELASTICSEARCH_URL=http://localhost:9200

# === ML Models ===
EMBEDDING_MODEL=BAAI/bge-code-v1
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# === Security ===
API_KEY_SECRET=dev-secret-key-change-in-production

# === Optional ===
QUERY_SERVICE_PORT=8000
SEMANTIC_THRESHOLD=0.6
INDEX_REFRESH_SCHEDULE=0 0 * * 0
```

## Services Table

| Service | Port | Docker Command | Verify |
|---------|------|----------------|--------|
| PostgreSQL | 5432 | `docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16` | `pg_isready -h localhost -p 5432` |
| Redis | 6379 | `docker run -d --name redis -p 6379:6379 redis:7` | `redis-cli ping` |
| Qdrant | 6333 | `docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest` | `GET http://localhost:6333/health` |
| Elasticsearch | 9200 | `docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e "discovery.type=single-node" -e "xpack.security.enabled=false" docker.elastic.co/elasticsearch/elasticsearch:8.12.2` | `GET http://localhost:9200/_cluster/health` |
| Kibana | 5601 | `docker run -d --name kibana -p 5601:5601 --link elasticsearch:elasticsearch docker.elastic.co/kibana/kibana:8.12.2` | `GET http://localhost:5601/api/status` |
| Query Service | 8000 | `uvicorn src.query.main:app --host 0.0.0.0 --port 8000` | `GET http://localhost:8000/api/v1/health` |

## Docker Quick Start

```bash
# Start all storage services
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16
docker run -d --name redis -p 6379:6379 redis:7
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.12.2

# Optional: Kibana dashboard
docker run -d --name kibana -p 5601:5601 \
  --link elasticsearch:elasticsearch \
  docker.elastic.co/kibana/kibana:8.12.2

# Stop all
docker stop postgres redis qdrant elasticsearch kibana

# Remove containers
docker rm postgres redis qdrant elasticsearch kibana
```

## Verify Services Running

```powershell
# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/api/v1/health -UseBasicParsing
Invoke-WebRequest -Uri http://localhost:6333/health -UseBasicParsing
Invoke-WebRequest -Uri http://localhost:9200/_cluster/health -UseBasicParsing
redis-cli ping  # Expected: PONG
pg_isready -h localhost -p 5432  # Expected: accepting connections
```

## Stop All Services

```bash
# Stop by container name
docker stop postgres redis qdrant elasticsearch kibana

# Stop Query Service by port (Windows)
for /f "tokens=5" %a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %a

# Stop Query Service by port (Unix/macOS)
lsof -ti :8000 | xargs kill -9
```

## Application Services

### Start Query Service

```powershell
# Windows (PowerShell)
cd d:/03PyDemo/theMachine
.venv/Scripts/activate
uvicorn src.query.main:app --host 0.0.0.0 --port 8000

# Unix/macOS
cd /path/to/theMachine
source .venv/bin/activate
uvicorn src.query.main:app --host 0.0.0.0 --port 8000
```

### Start Indexing Service (Future)

```bash
# Celery Worker
celery -A src.indexing.worker worker --loglevel=info

# Celery Beat (scheduled tasks)
celery -A src.indexing.worker beat --loglevel=info
```

## Restart Protocol (4 Steps)

1. **Kill** — Stop services by container name or PID
2. **Verify dead** — Check ports not responding
3. **Start** — Run Docker commands or application startup
4. **Verify alive** — Check health endpoints

## Notes

- **Query Service** is stateless and can be scaled horizontally
- **Elasticsearch 8.x** required (client pinned to `>=8.17.0,<9.0.0`)
- **PostgreSQL 16** recommended (tested with asyncpg driver)
- **Redis 7** recommended (tested with redis-py 5.x)
- **Qdrant latest** recommended
- Record all PIDs in `task-progress.md` for proper cleanup
