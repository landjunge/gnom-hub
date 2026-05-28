# run_benchmarks.py — Benchmark caching and database index optimizations
import sys, os, time
# Add project root and src directory to PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import gnom_hub.db
from gnom_hub.memory.embeddings import SoulEmbedder
from gnom_hub.agents.capability_manager import request_capability, check_capability, cleanup_expired, _cache

def run_benchmarks():
    print("============================================================")
    print(" 📈 RUNNING GNOM-HUB PERFORMANCE BENCHMARKS")
    print("============================================================")
    
    gnom_hub.db.init_db()
    
    # 1. Benchmark Capability Checking
    print("\n--- 🔐 CAPABILITY CHECK BENCHMARK ---")
    request_capability("BenchmarkAgent", "WRITE", "test_file.txt", "SecurityAG", ttl_min=10)
    
    # Cold check (first time, hits SQLite DB)
    _cache.clear()  # Clear local cache first
    t0 = time.perf_counter()
    cold_res = check_capability("BenchmarkAgent", "WRITE", "test_file.txt")
    t_cold_cap = (time.perf_counter() - t0) * 1000
    
    # Warm checks (subsequent times, hits O(1) Memory Cache)
    warm_times = []
    for _ in range(100):
        t0 = time.perf_counter()
        check_capability("BenchmarkAgent", "WRITE", "test_file.txt")
        warm_times.append((time.perf_counter() - t0) * 1000)
    t_warm_cap = sum(warm_times) / len(warm_times)
    
    print(f"Cold Check (Database Query): {t_cold_cap:.4f} ms")
    print(f"Warm Check (Memory Cache):   {t_warm_cap:.4f} ms")
    print(f"Speedup Factor:              {t_cold_cap / t_warm_cap:.1f}x")

    # 2. Benchmark Semantic Embeddings Retrieval
    print("\n--- 🧠 SEMANTIC EMBEDDINGS SEARCH BENCHMARK ---")
    # Save a test fact to update index
    fact_id = gnom_hub.db.save_soul_fact("benchmark_test", "Die bevorzugte Programmiersprache fuer Spielentwicklung ist C#.", agent="Benchmark")
    embedder = SoulEmbedder()
    
    # Query sentence
    query = "Welche Programmiersprache fuer Spiele?"
    
    # Cold search (first time, might generate embedding/query)
    # We clear the search cache to simulate first lookup
    from gnom_hub.memory.embeddings import _search_cache
    _search_cache.clear()
    
    t0 = time.perf_counter()
    cold_results = embedder.search_sync(query, top_k=2)
    t_cold_search = (time.perf_counter() - t0) * 1000
    
    # Warm search (subsequent lookups, hits module-level search cache)
    search_times = []
    for _ in range(100):
        t0 = time.perf_counter()
        embedder.search_sync(query, top_k=2)
        search_times.append((time.perf_counter() - t0) * 1000)
    t_warm_search = sum(search_times) / len(search_times)
    
    print(f"Cold Search (Embedding + FAISS): {t_cold_search:.4f} ms")
    print(f"Warm Search (Query Cache):      {t_warm_search:.4f} ms")
    print(f"Speedup Factor:                 {t_cold_search / t_warm_search:.1f}x")

    print("\n============================================================")
    print(" ✅ BENCHMARKS COMPLETE")
    print("============================================================")

if __name__ == "__main__":
    run_benchmarks()
