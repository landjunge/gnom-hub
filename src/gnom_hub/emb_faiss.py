# emb_faiss.py — FAISS index and sentence embeddings logic helper
import os, pickle, sqlite3, numpy as np; import faiss; from sentence_transformers import SentenceTransformer; from .emb_cache import get_emb
class FaissEmbeddingHelper:
    def __init__(self, model_name: str, db_path: str):
        self.db_path, self.model, self.index, self.fact_ids = db_path, SentenceTransformer(model_name), None, []
        os.makedirs("data", exist_ok=True)
        if not os.path.exists("data/soul_embeddings.index"): self._create()
        else:
            self.index = faiss.read_index("data/soul_embeddings.index")
            try:
                with open("data/soul_fact_ids.pkl", "rb") as f: self.fact_ids = pickle.load(f)
            except Exception: pass
    def _create(self):
        try:
            with sqlite3.connect(self.db_path) as conn: facts = conn.execute("SELECT id, key, value FROM soul_memory").fetchall()
        except Exception: facts = []
        embs = np.vstack([get_emb(self.model, f"{f[1]}: {f[2]}") for f in facts]) if facts else []
        self.index = faiss.IndexFlatL2(embs.shape[1]) if len(embs) > 0 else faiss.IndexFlatL2(384)
        if len(embs) > 0: self.index.add(embs)
        self.fact_ids = [f[0] for f in facts]
        faiss.write_index(self.index, "data/soul_embeddings.index")
        with open("data/soul_fact_ids.pkl", "wb") as f: pickle.dump(self.fact_ids, f)
    def add_fact(self, fact_id: str, key: str, value: str):
        self.index.add(get_emb(self.model, f"{key}: {value}"))
        self.fact_ids.append(fact_id)
        faiss.write_index(self.index, "data/soul_embeddings.index")
        with open("data/soul_fact_ids.pkl", "wb") as f: pickle.dump(self.fact_ids, f)
    def search(self, query: str, top_k: int = 8) -> list:
        if self.index is None or self.index.ntotal == 0: return []
        _, indices = self.index.search(get_emb(self.model, query), top_k)
        res = []
        for idx in [i for i in indices[0] if 0 <= i < len(self.fact_ids)]:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    row = conn.execute("SELECT key, value FROM soul_memory WHERE id = ?", (self.fact_ids[idx],)).fetchone()
                    if row: res.append(f"{row[0]}: {row[1]}")
            except Exception: pass
        return res
