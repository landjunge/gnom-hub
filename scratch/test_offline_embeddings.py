# test_offline_embeddings.py — Test semantic offline embeddings
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gnom_hub.db
import gnom_hub.memory.soul_retrieval as soul_retrieval
from gnom_hub.memory.embeddings import SoulEmbedder

def test_offline_embeddings():
    print("--- STARTING OFFLINE EMBEDDINGS UNIT TESTS ---")
    gnom_hub.db.init_db()

    # Clear previous soul memory
    with gnom_hub.db.get_db_conn() as conn:
        with conn: conn.execute("DELETE FROM soul_memory WHERE agent = 'EmbeddingsTest'")

    # Seed facts
    gnom_hub.db.save_soul_fact("ui_color", "Das Farbschema der Anwendung ist Smaragdgrün.", agent="EmbeddingsTest")
    gnom_hub.db.save_soul_fact("db_type", "Als relationale Datenbank wird SQLite verwendet.", agent="EmbeddingsTest")

    # 1. Test semantic similarity search
    embedder = SoulEmbedder(db_path=None)
    res = embedder.search_sync("Das Farbschema der Anwendung", top_k=2)
    print(f"Embedding search color result: {res}")
    assert any("Smaragdgrün" in r for r in res), "Semantic search failed to match color!"

    # 2. Test retrieve_relevant_facts wrapper
    facts = soul_retrieval.retrieve_relevant_facts("Welche relationale Datenbank wird verwendet?")
    print(f"Relevant facts DB result: {facts}")
    assert any("SQLite" in f for f in facts), "Semantic retrieval wrapper failed to find SQLite!"

    # 3. Test fallback behavior (Apfelkuchen)
    fallback_res = soul_retrieval.retrieve_relevant_facts("Apfelkuchen")
    print(f"Fallback result: {fallback_res}")
    assert len(fallback_res) > 0, "Fallback should have returned recent facts!"

    print("Offline embeddings semantic retrieval verified successfully!")

if __name__ == "__main__":
    test_offline_embeddings()
