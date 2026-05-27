# emb_faiss.py — FAISS index and sentence embeddings logic helper
import os, pickle, sqlite3, numpy as np, faiss; from sentence_transformers import SentenceTransformer; from .emb_cache import get_emb
class FaissEmbeddingHelper:
    def __init__(self, model_name: str, db_path: str):
        self.db_path, self.model, self.index, self.fact_ids = db_path, SentenceTransformer(model_name), None, []
        os.makedirs("data", exist_ok=True)
        if not os.path.exists("data/soul_embeddings.index"): self._create()
        else:
            self.index = faiss.read_index("data/soul_embeddings.index")
            try: self.fact_ids = pickle.load(open("data/soul_fact_ids.pkl", "rb"))
            except Exception: pass
    def _create(self):
        try:
            with sqlite3.connect(self.db_path) as conn: facts = conn.execute("SELECT id, key, value FROM soul_memory").fetchall()
        except Exception: facts = []
        embs = np.vstack([get_emb(self.model, f[2]) for f in facts]) if facts else []
        dim = embs.shape[1] if len(embs) > 0 else 384
        if len(embs) >= 256:
            self.index = faiss.IndexIVFPQ(faiss.IndexFlatL2(dim), dim, 100, 8, 8)
            self.index.train(embs); self.index.add(embs)
        else:
            self.index = faiss.IndexFlatL2(dim)
            if len(embs) > 0: self.index.add(embs)
        self.fact_ids = [f[0] for f in facts]; faiss.write_index(self.index, "data/soul_embeddings.index")
        pickle.dump(self.fact_ids, open("data/soul_fact_ids.pkl", "wb"))
    def add_fact(self, fact_id: str, key: str, value: str):
        self.index.add(get_emb(self.model, value)); self.fact_ids.append(fact_id)
        faiss.write_index(self.index, "data/soul_embeddings.index")
        pickle.dump(self.fact_ids, open("data/soul_fact_ids.pkl", "wb"))
    def search(self, query: str, top_k: int = 8, raw: bool = False) -> list:
        if self.index is None or self.index.ntotal == 0: return []
        if raw:
            _, indices = self.index.search(get_emb(self.model, query), top_k)
            res = []
            for idx in [i for i in indices[0] if 0 <= i < len(self.fact_ids)]:
                try:
                    with sqlite3.connect(self.db_path) as conn:
                        r = conn.execute("SELECT key, value FROM soul_memory WHERE id = ?", (self.fact_ids[idx],)).fetchone()
                        if r: res.append(f"{r[0]}: {r[1]}")
                except Exception: pass
            return res

        candidate_k = max(top_k * 3, 24)
        # Ensure we don't query more than the total number of vectors in index
        candidate_k = min(candidate_k, self.index.ntotal)
        
        distances, indices = self.index.search(get_emb(self.model, query), candidate_k)
        candidates = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.fact_ids):
                candidates.append((float(dist), self.fact_ids[idx]))

        res_scored = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                for dist, fact_id in candidates:
                    r = conn.execute("SELECT key, value, priority FROM soul_memory WHERE id = ?", (fact_id,)).fetchone()
                    if r:
                        # Cosine similarity approximation from L2 distance (since vectors are normalized):
                        # similarity = 1 - 0.5 * L2_squared
                        base_sim = 1.0 - 0.5 * dist
                        if base_sim < 0.70:
                            continue
                        priority = (r['priority'] or 'medium').lower()
                        if priority == 'high':
                            weight = 1.3
                        elif priority == 'low':
                            weight = 0.7
                        else:
                            weight = 1.0
                        boosted_score = base_sim * weight
                        res_scored.append((boosted_score, f"{r['key']}: {r['value']}"))
        except Exception:
            pass

        if not res_scored:
            return []

        res_scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in res_scored[:top_k]]
