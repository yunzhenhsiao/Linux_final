# scripts/smoke_test.py
"""
TransitFlow Smoke Test
======================
快速驗證系統核心功能是否正常運作。
在容器環境中執行：
    docker compose run --rm ui python scripts/smoke_test.py

在本機執行（需設定好環境變數）：
    python scripts/smoke_test.py
"""
import sys
import time
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
import requests
from neo4j import GraphDatabase

from skeleton.config import (
    PG_DSN,
    NEO4J_URI,
    NEO4J_USER,
    NEO4J_PASSWORD,
    OLLAMA_BASE_URL,
)
from skeleton.cache import get_cache, set_cache

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = {}


# ── Individual test functions ──────────────────────────────────────────────────

def test_postgres() -> bool:
    """Verify PostgreSQL is reachable and seed data exists."""
    try:
        conn = psycopg2.connect(PG_DSN)
        with conn.cursor() as cur:
            # Basic connectivity
            cur.execute("SELECT 1;")
            assert cur.fetchone()[0] == 1

            # Verify seed data was injected
            cur.execute("SELECT COUNT(*) FROM users;")
            user_count = cur.fetchone()[0]
            assert user_count > 0, f"users table is empty (count={user_count})"

            cur.execute("SELECT COUNT(*) FROM metro_stations;")
            station_count = cur.fetchone()[0]
            assert station_count > 0, f"metro_stations table is empty"

        conn.close()
        print(f"  {PASS} PostgreSQL — users={user_count}, stations={station_count}")
        return True
    except Exception as e:
        print(f"  {FAIL} PostgreSQL — {e}")
        return False


def test_neo4j() -> bool:
    """Verify Neo4j is reachable and graph data exists."""
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        with driver.session() as session:
            # Basic Cypher execution
            result = session.run("RETURN 1 AS x")
            assert result.single()["x"] == 1

            # Verify seed data was injected
            result = session.run("MATCH (n) RETURN count(n) AS total")
            total = result.single()["total"]
            assert total > 0, f"Graph is empty (nodes={total})"

        driver.close()
        print(f"  {PASS} Neo4j — graph nodes={total}")
        return True
    except Exception as e:
        print(f"  {FAIL} Neo4j — {e}")
        return False


def test_redis() -> bool:
    """Verify Redis cache layer can set and get values."""
    try:
        test_key = "smoke:test"
        test_val = {"smoke": True, "ts": time.time()}

        ok = set_cache(test_key, test_val, ttl_seconds=30)
        assert ok is True, "set_cache returned False"

        retrieved = get_cache(test_key)
        assert retrieved is not None, "get_cache returned None"
        assert retrieved["smoke"] is True, "Cached value mismatch"

        print(f"  {PASS} Redis — set/get round-trip successful")
        return True
    except Exception as e:
        print(f"  {FAIL} Redis — {e}")
        return False


def test_ollama() -> bool:
    """Verify Ollama API is reachable and returns model list."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        assert "models" in data, "'models' key not found in Ollama response"

        model_names = [m.get("name", "") for m in data["models"]]
        print(f"  {PASS} Ollama — available models: {model_names}")
        return True
    except Exception as e:
        print(f"  {FAIL} Ollama — {e}")
        return False


def test_pgvector() -> bool:
    """Verify pgvector extension and policy_documents embeddings exist."""
    try:
        conn = psycopg2.connect(PG_DSN)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM policy_documents WHERE embedding IS NOT NULL;")
            count = cur.fetchone()[0]
            assert count > 0, f"No vector embeddings found in policy_documents"
        conn.close()
        print(f"  {PASS} pgvector — {count} policy documents with embeddings")
        return True
    except Exception as e:
        print(f"  {FAIL} pgvector — {e}")
        return False


def test_celery_task() -> bool:
    """Verify Celery worker is running and can execute a task."""
    try:
        from skeleton.tasks import generate_daily_report

        task = generate_daily_report.delay()
        # Wait up to 30 seconds for the worker to pick up and complete the task
        result = task.get(timeout=30)

        assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
        assert result.get("status") == "completed", f"Task status: {result.get('status')}"

        print(f"  {PASS} Celery — task completed, status={result['status']}")
        return True
    except Exception as e:
        print(f"  {FAIL} Celery — {e}")
        print("       (Is the Celery worker running? Try: docker compose up celery)")
        return False


# ── Runner ─────────────────────────────────────────────────────────────────────

TESTS = [
    ("PostgreSQL connectivity + seed data", test_postgres),
    ("Neo4j connectivity + graph data",     test_neo4j),
    ("Redis cache set/get",                 test_redis),
    ("Ollama API availability",             test_ollama),
    ("pgvector embeddings",                 test_pgvector),
    ("Celery task dispatch + execution",    test_celery_task),
]

if __name__ == "__main__":
    print("=" * 55)
    print("  TransitFlow Smoke Test")
    print("=" * 55)

    passed = 0
    failed = 0

    for name, fn in TESTS:
        print(f"\n[{name}]")
        if fn():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 55)
    print(f"  Results: {passed} passed / {failed} failed")
    print("=" * 55)

    if failed > 0:
        print("\n⚠️  Some smoke tests failed. Check the output above.")
        sys.exit(1)
    else:
        print("\n🎉 All smoke tests passed — system is operational.")
        sys.exit(0)
