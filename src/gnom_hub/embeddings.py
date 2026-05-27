# embeddings.py — Local embeddings / semantic retrieval helper (Singleton)
import gnom_hub.smr_retrieve as sr
import logging

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

_search_cache = {}
_logger = logging.getLogger("embeddings")

class SoulEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", db_path: str = None):
        from gnom_hub.db import DB_PATH
        self.db_path, self.helper = str(db_path or DB_PATH), None
        if HAS_LIBS:
            from gnom_hub.emb_faiss import FaissEmbeddingHelper
            self.helper = FaissEmbeddingHelper(model_name, self.db_path)

    def add_fact(self, fact_id: str, key: str, value: str):
        _search_cache.clear()
        if self.helper: self.helper.add_fact(fact_id, key, value)

    def search_sync(self, query: str, top_k: int = 8, raw: bool = False) -> list:
        k = (query, top_k, raw)
        if k in _search_cache: return _search_cache[k]
        res = self.helper.search(query, top_k, raw=raw) if self.helper else sr.retrieve_similar_sync(query, top_k, raw=raw)
        _search_cache[k] = res
        return res

    def has_similar(self, text: str, threshold: float = 0.92) -> bool:
        if not self.helper or self.helper.index.ntotal == 0: return False
        results = self.search_sync(text, top_k=1, raw=True)
        if not results: return False
        try:
            import numpy as np
            from .emb_cache import get_emb
            val_text = text.split(": ", 1)[1] if ": " in text else text
            res_val = results[0].split(": ", 1)[1] if ": " in results[0] else results[0]
            v1 = get_emb(self.helper.model, val_text).flatten()
            v2 = get_emb(self.helper.model, res_val).flatten()
            cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
            return cos > threshold
        except Exception:
            return False

# ── Singleton ──────────────────────────────────────────────
_instance = None

def get_embedder() -> SoulEmbedder:
    global _instance
    if _instance is None:
        _instance = SoulEmbedder()
        _logger.info("SoulEmbedder singleton initialized (FAISS=%s)", _instance.helper is not None)
    return _instance
