# scripts/init_db.py
import time
import sys
import os
import psycopg2
from neo4j import GraphDatabase
import subprocess

# Ensure project root is in path
sys.path.insert(0, ".")

from skeleton.config import PG_DSN, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# Respect AUTO_INIT_DB flag
auto_init = os.getenv("AUTO_INIT_DB", "yes").lower()
if auto_init != "yes":
    print(f"AUTO_INIT_DB is set to '{auto_init}'. Skipping database seeding.")
    sys.exit(0)

print("Starting database initialization check...")

# 1. Wait for PostgreSQL
print("Waiting for PostgreSQL to become ready...")
for i in range(30):
    try:
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        conn.close()
        print("PostgreSQL is ready!")
        break
    except Exception as e:
        print(f"PostgreSQL not ready yet ({e}). Retrying in 2 seconds...")
        time.sleep(2)
else:
    print("Error: PostgreSQL did not become ready in time.")
    sys.exit(1)

# 2. Wait for Neo4j
print("Waiting for Neo4j to become ready...")
for i in range(30):
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        driver.close()
        print("Neo4j is ready!")
        break
    except Exception as e:
        print(f"Neo4j not ready yet ({e}). Retrying in 2 seconds...")
        time.sleep(2)
else:
    print("Error: Neo4j did not become ready in time.")
    sys.exit(1)

# 3. Seed PostgreSQL
print("Seeding PostgreSQL database...")
try:
    subprocess.run([sys.executable, "skeleton/seed_postgres.py"], check=True)
    print("PostgreSQL database seeding complete.")
except subprocess.CalledProcessError as e:
    print(f"Failed to seed PostgreSQL: {e}")
    sys.exit(1)

# 4. Seed Neo4j
print("Seeding Neo4j graph database...")
try:
    subprocess.run([sys.executable, "skeleton/seed_neo4j.py"], check=True)
    print("Neo4j database seeding complete.")
except subprocess.CalledProcessError as e:
    print(f"Failed to seed Neo4j: {e}")
    sys.exit(1)

# 5. Seed vectors
print("Seeding vector embeddings...")
try:
    subprocess.run([sys.executable, "skeleton/seed_vectors.py"], check=True)
    print("Vector embedding database seeding complete.")
except subprocess.CalledProcessError as e:
    print(f"Failed to seed vector embeddings: {e}")
    sys.exit(1)

print("All databases successfully initialized and seeded!")
