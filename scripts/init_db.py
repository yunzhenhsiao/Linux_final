# scripts/init_db.py
import time
import sys
import os
import psycopg2
from neo4j import GraphDatabase
import subprocess
from pathlib import Path

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from skeleton.config import PG_DSN, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Respect AUTO_INIT_DB flag
auto_init = os.getenv("AUTO_INIT_DB", "yes").lower()
if auto_init != "yes":
    print(f"AUTO_INIT_DB is set to '{auto_init}'. Skipping database seeding.")
    sys.exit(0)

print("Starting database initialization check...")


# ── Helpers ───────────────────────────────────────────────────────────────────

def wait_for_postgres(max_retries: int = 30, interval: int = 2) -> None:
    """Block until PostgreSQL accepts connections, or exit on timeout."""
    print("Waiting for PostgreSQL to become ready...")
    for _ in range(max_retries):
        try:
            conn = psycopg2.connect(PG_DSN)
            conn.cursor().execute("SELECT 1;")
            conn.close()
            print("PostgreSQL is ready!")
            return
        except Exception as e:
            print(f"PostgreSQL not ready yet ({e}). Retrying in {interval}s...")
            time.sleep(interval)
    print("Error: PostgreSQL did not become ready in time.")
    sys.exit(1)


def wait_for_neo4j(max_retries: int = 30, interval: int = 2) -> None:
    """Block until Neo4j accepts connections, or exit on timeout."""
    print("Waiting for Neo4j to become ready...")
    for _ in range(max_retries):
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            driver.verify_connectivity()
            driver.close()
            print("Neo4j is ready!")
            return
        except Exception as e:
            print(f"Neo4j not ready yet ({e}). Retrying in {interval}s...")
            time.sleep(interval)
    print("Error: Neo4j did not become ready in time.")
    sys.exit(1)


def run_seed(module: str, label: str) -> None:
    """Run a seed module via `python -m <module>` and exit on failure."""
    print(f"Seeding {label}...")
    try:
        subprocess.run([sys.executable, "-m", module], check=True, cwd=str(ROOT))
        print(f"{label} seeding complete.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to seed {label}: {e}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

wait_for_postgres()
wait_for_neo4j()

run_seed("skeleton.seed_postgres", "PostgreSQL database")
run_seed("skeleton.seed_neo4j",    "Neo4j graph database")
run_seed("skeleton.seed_vectors",  "vector embeddings")

print("All databases successfully initialized and seeded!")
