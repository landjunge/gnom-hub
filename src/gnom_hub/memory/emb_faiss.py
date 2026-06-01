# emb_faiss.py — FAISS index and sentence embeddings logic helper
import os, json, sqlite3, logging, numpy as np, faiss; from sentence_transformers import SentenceTransformer; from gnom_hub.memory.emb_cache import get_emb
class FaissEmbeddingHelper:
    def __init__(self, model_name: str, db_path: str, scope: str = "global"):
        self.scope = scope
        self.db_path, self.model, self.index, self.fact_ids = db_path, SentenceTransformer(model_name), None, []
        os.makedirs("data", exist_ok=True)
        self.index_path = f"data/soul_embeddings_{scope}.index"
        self.json_path = f"data/soul_fact_ids_{scope}.json"
        if not os.path.exists(self.index_path): self._create()
        else:
            self.index = faiss.read_index(self.index_path)
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.fact_ids = json.load(f)
            except Exception as e: logging.getLogger(__name__).error('Fehler beim Laden der fact_ids: %s', e)
    def _create(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                if self.scope == "global":
                    facts = conn.execute("SELECT id, key, value FROM soul_memory WHERE agent IS NULL OR LOWER(agent) NOT IN ('coderag', 'researcherag', 'writerag', 'editorag')").fetchall()
                else:
                    facts = conn.execute("SELECT id, key, value FROM soul_memory WHERE LOWER(agent) = ?", (self.scope.lower(),)).fetchall()
        except Exception: facts = []
        embs = np.vstack([get_emb(self.model, f[2]) for f in facts]) if facts else []
        dim = embs.shape[1] if len(embs) > 0 else 384
        self.index = faiss.IndexFlatL2(dim)
        if len(embs) > 0: self.index.add(embs)
        self.fact_ids = [f[0] for f in facts]
        faiss.write_index(self.index, self.index_path)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.fact_ids, f)
    def add_fact(self, fact_id: str, key: str, value: str):
        self.index.add(get_emb(self.model, value)); self.fact_ids.append(fact_id)
        faiss.write_index(self.index, self.index_path)
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.fact_ids, f)
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
                except Exception as e: logging.getLogger(__name__).error('Fehler in search (raw DB-Lookup): %s', e)
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
        except Exception as e:
            logging.getLogger(__name__).error('Fehler in search (scored DB-Lookup): %s', e)

        if not res_scored:
            return []

        res_scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in res_scored[:top_k]]
