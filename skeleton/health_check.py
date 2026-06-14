# skeleton/health_check.py
import sys
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

def check_postgres():
    try:
        conn = psycopg2.connect(PG_DSN)
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        conn.close()
        print("PostgreSQL connection check passed.")
        return True
    except Exception as e:
        print(f"PostgreSQL connection check failed: {e}")
        return False

def check_neo4j():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) AS total")
            _ = result.single()["total"]
        driver.close()
        print("Neo4j connection check passed.")
        return True
    except Exception as e:
        print(f"Neo4j connection check failed: {e}")
        return False

def check_llm_provider():
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        if "models" in data:
            print("Ollama ready check passed.")
            return True
        else:
            print("Ollama check failed: 'models' not found in response.")
            return False
    except Exception as e:
        print(f"Ollama check failed to connect: {e}")
        return False

if __name__ == "__main__":
    checks = {
        "postgres": check_postgres(),
        "neo4j": check_neo4j(),
        "llm": check_llm_provider(),
    }
    
    if all(checks.values()):
        print("All application health checks passed.")
        sys.exit(0)
    else:
        print(f"Application health check failed! Status: {checks}")
        sys.exit(1)
