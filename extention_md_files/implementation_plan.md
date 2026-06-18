# Implementation Plan: Container Orchestration, Caching, and Background Tasks

This plan covers the implementation of Projects 1 through 7 for environmental separation, containerization, database seeding automation, health check enhancements, Redis caching, and Celery background task processing.

## User Review Required

> [!WARNING]
> **PostgreSQL & Neo4j Health Check Python Script Execution**
> The original design proposed running `python skeleton/health_check.py` inside the `postgres` database container. Since the standard `pgvector/pgvector:pg16` database image does not have Python installed, running a Python script inside it will fail and cause the database service to be marked unhealthy.
> **Correction:** We will keep database container health checks limited to native CLI tools (`pg_isready` for Postgres, `cypher-shell` for Neo4j), and run the Python `health_check.py` script inside the `ui`, `celery`, and `celery-beat` containers (which have Python and all requirements installed).

> [!IMPORTANT]
> **Windows Seeding & Seeding Compatibility**
> Running `.sh` shell scripts inside containers on Windows systems often causes execution failures due to CRLF carriage return characters.
> **Correction:** We will implement the seeding orchestration and model pull scripts in Python (`scripts/init_db.py` and `scripts/pull_ollama_models.py`), which are inherently platform-independent and fully compatible with all environments.

> [!NOTE]
> **Mock Database Functions for Celery Tasks**
> The background Celery tasks import `delete_old_sessions` and `send_notification` from `databases/relational/queries.py`, but these tables and functions do not exist in the current codebase.
> **Correction:** We will implement clean mock functions in `queries.py` so that imports succeed and these background tasks run without crashing.

---

## Proposed Changes

### 1. Build and Environment Orchestration

#### [MODIFY] [docker-compose.yml](file:///c:/Users/user/Linux_final/docker-compose.yml)
Update the base compose configuration to include the Redis, Ollama, Gradio UI, Celery worker, Celery beat, and initialization services.

#### [NEW] [docker-compose.dev.yml](file:///c:/Users/user/Linux_final/docker-compose.dev.yml)
Dev overlay defining exposed ports for PostgreSQL (5433), Neo4j (7475, 7688), Redis (6379), Ollama (11434), pgAdmin (5051), and a loose restart policy (`no`).

#### [NEW] [docker-compose.test.yml](file:///c:/Users/user/Linux_final/docker-compose.test.yml)
Test overlay without exposed database ports, standard resource limits (PostgreSQL/Neo4j capped at 2GB RAM, 1.5 CPUs), and an `unless-stopped` restart policy.

#### [NEW] [docker-compose.prod.yml](file:///c:/Users/user/Linux_final/docker-compose.prod.yml)
Prod overlay without exposed database ports, strict resource limits (PostgreSQL/Neo4j capped at 4GB RAM, 2 CPUs), and an `always` restart policy.

#### [NEW] [.env.dev](file:///c:/Users/user/Linux_final/.env.dev)
Development variables defining log level `DEBUG`, database initialization enabled, local Ollama endpoints, and exposed service profiles.

#### [NEW] [.env.test](file:///c:/Users/user/Linux_final/.env.test)
Testing variables defining log level `INFO`, database initialization enabled, rate limits set to 100/s, and backup schedule set to daily.

#### [NEW] [.env.prod](file:///c:/Users/user/Linux_final/.env.prod)
Production variables (ignored from git) defining log level `WARNING`, using Gemini as the default LLM provider, disabled auto database initialization, rate limits set to 1000/s, and backup schedule set to hourly.

#### [MODIFY] [.gitignore](file:///c:/Users/user/Linux_final/.gitignore)
Ignore `.env.prod` to ensure sensitive production credentials are never committed.

---

### 2. UI Containerization & Automation

#### [NEW] [Dockerfile](file:///c:/Users/user/Linux_final/skeleton/Dockerfile)
Create a Python 3.11 slim image containing postgresql-client, copying requirements, installing dependencies, exposing UI port 7860, and setting up health checks.

#### [NEW] [init_db.py](file:///c:/Users/user/Linux_final/scripts/init_db.py)
Platform-independent Python initialization script that waits for PostgreSQL and Neo4j, then sequentially triggers the database seeding scripts.

#### [NEW] [pull_ollama_models.py](file:///c:/Users/user/Linux_final/scripts/pull_ollama_models.py)
Python orchestration script to trigger Ollama pulls for `llama3.2:1b` and `nomic-embed-text` models in the running Ollama container.

---

### 3. Application Enhancements (Cache, Health, Tasks)

#### [NEW] [health_check.py](file:///c:/Users/user/Linux_final/skeleton/health_check.py)
App-level health check script checking Postgres connection, Neo4j connection, and Selected LLM Provider (Ollama API tags or Gemini endpoint connectivity).

#### [NEW] [cache.py](file:///c:/Users/user/Linux_final/skeleton/cache.py)
Redis caching manager using `redis` client with fault-tolerant fallbacks (if Redis is offline, database queries run as normal).

#### [NEW] [tasks.py](file:///c:/Users/user/Linux_final/skeleton/tasks.py)
Initialize the Celery application bound to Redis, scheduling periodic beat jobs (`generate_daily_report` daily at midnight, `cleanup_old_sessions` daily at 2 AM) and bulk update tasks.

#### [MODIFY] [queries.py](file:///c:/Users/user/Linux_final/databases/relational/queries.py)
- Integrate Redis caching in `query_employee_operations_summary`, `query_admin_system_stats`, and `query_admin_top_passengers`.
- Add mock `delete_old_sessions` and `send_notification` functions to satisfy background Celery task imports.

#### [MODIFY] [config.py](file:///c:/Users/user/Linux_final/skeleton/config.py)
Add Redis and log level config parameters loading from environment variables.

#### [MODIFY] [ui.py](file:///c:/Users/user/Linux_final/skeleton/ui.py)
- Add a "Clear Cache" button under System Statistics.
- Add a "Task Progress" tracker tab under the Admin Dashboard using Celery's AsyncResult.

#### [MODIFY] [agent.py](file:///c:/Users/user/Linux_final/skeleton/agent.py)
- Register `admin_generate_report` in the agent tools.
- Implement the asynchronous Celery trigger for generating report tasks in `_execute_tool`.

#### [MODIFY] [requirements.txt](file:///c:/Users/user/Linux_final/requirements.txt)
Add dependencies: `celery>=5.3.0` and `redis>=5.0.0`.

---

## Verification Plan

### Automated Tests
1. **Container Start validation:**
   - Execute docker-compose for dev, test, and prod to confirm containers build and coordinate.
   - Command: `docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev up -d`
2. **Database Initialization validation:**
   - Verify `init-db` runs and triggers the seed scripts.
3. **Application Verification:**
   - Inspect the logs of the `ui` and `celery` containers to ensure clean startup.

### Manual Verification
1. Access Gradio UI on `http://localhost:7860`.
2. Login as Admin and load the Admin Dashboard statistics. Press "Clear Cache" and verify cache invalidation.
3. Call the `admin_generate_report` tool via the chat (e.g., "Generate administrative report") and check the resulting Task ID in the UI "Task Progress" tab.
