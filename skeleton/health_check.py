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
    LLM_PROVIDER,
    GEMINI_API_KEY
)

def check_postgres():
    try:
        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()
        cur.execute("SELECT 1")
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
        driver.close()
        print("Neo4j connection check passed.")
        return True
    except Exception as e:
        print(f"Neo4j connection check failed: {e}")
        return False

def check_llm_provider():
    if LLM_PROVIDER == "gemini":
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
            print("Gemini API key is missing or not configured.")
            return False
        try:
            # Check if Gemini endpoint is reachable
            response = requests.get("https://generativelanguage.googleapis.com/", timeout=5)
            print("Gemini connectivity check passed.")
            return True
        except Exception as e:
            print(f"Gemini connectivity check failed: {e}")
            return False
    else: # ollama
        try:
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                print("Ollama ready check passed.")
                return True
            else:
                print(f"Ollama check failed with status code: {response.status_code}")
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
