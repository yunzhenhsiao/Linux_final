import time
import os
import psycopg2
import redis

# Configuration
PG_HOST = os.getenv("PG_HOST", "postgres")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "transitflow")
PG_PASSWORD = os.getenv("PG_PASSWORD", "transitflow")
PG_DB = os.getenv("PG_DB", "transitflow")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

ITERATIONS = 50

def run_benchmark():
    print("=======================================================")
    print("  TransitFlow Cache Performance Benchmark")
    print(f"  Iterations per test: {ITERATIONS}")
    print("=======================================================\n")

    # 1. Setup Connections
    print("[*] Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname=PG_DB
        )
        pg_conn.autocommit = True
    except Exception as e:
        print(f"[-] PostgreSQL Connection failed: {e}")
        return

    print("[*] Connecting to Redis...")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
        r.ping()
    except Exception as e:
        print(f"[-] Redis Connection failed: {e}")
        return

    print("\n[+] Both databases connected successfully.\n")

    # 2. Benchmark PostgreSQL (Simulating Admin Dashboard Query)
    # We will simulate a query that calculates total bookings and revenue
    complex_query = """
        SELECT 
            COUNT(*) as total_bookings,
            SUM(amount_usd) as total_revenue
        FROM national_rail_bookings
        WHERE status = 'confirmed';
    """
    
    print("[*] Benchmarking PostgreSQL Aggregation Query...")
    db_times = []
    with pg_conn.cursor() as cur:
        for _ in range(ITERATIONS):
            start_time = time.time()
            cur.execute(complex_query)
            result = cur.fetchone()
            end_time = time.time()
            db_times.append((end_time - start_time) * 1000) # in ms
            
    avg_db_time = sum(db_times) / len(db_times)
    print(f"    -> Average DB Query Time: {avg_db_time:.2f} ms")
    print(f"    -> Min DB Time: {min(db_times):.2f} ms | Max DB Time: {max(db_times):.2f} ms\n")

    # 3. Benchmark Redis (Simulating Cache Hit)
    cache_key = "benchmark:admin:revenue"
    r.set(cache_key, str(result), ex=60)

    print("[*] Benchmarking Redis Cache Read...")
    redis_times = []
    for _ in range(ITERATIONS):
        start_time = time.time()
        val = r.get(cache_key)
        end_time = time.time()
        redis_times.append((end_time - start_time) * 1000) # in ms

    avg_redis_time = sum(redis_times) / len(redis_times)
    print(f"    -> Average Redis Read Time: {avg_redis_time:.2f} ms")
    print(f"    -> Min Redis Time: {min(redis_times):.2f} ms | Max Redis Time: {max(redis_times):.2f} ms\n")

    # 4. Result Summary
    if avg_redis_time > 0:
        speedup = avg_db_time / avg_redis_time
        print("=======================================================")
        print("  Benchmark Results Summary")
        print("=======================================================")
        print(f"  PostgreSQL Time : {avg_db_time:.2f} ms")
        print(f"  Redis Time      : {avg_redis_time:.2f} ms")
        print(f"  Speedup Ratio   : {speedup:.1f}x faster")
        print("=======================================================")

    pg_conn.close()

if __name__ == "__main__":
    run_benchmark()
