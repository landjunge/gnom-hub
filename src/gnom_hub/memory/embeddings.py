# embeddings.py — Local embeddings / semantic retrieval helper (Singleton)
import gnom_hub.memory.smr.smr_retrieve as sr
import logging
import threading

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
        from gnom_hub.core.config import Config
        DB_PATH = Config.DB_PATH
        self.model_name = model_name
        self.db_path = str(db_path or DB_PATH)
        self.helpers = {}

    def get_helper(self, scope: str = "global"):
        if not HAS_LIBS:
            return None
        import time
        now = time.time()
        # Evict inactive helpers (except global scope) after 120s of inactivity
        expired = [s for s, (_, ts) in self.helpers.items() if s != "global" and now - ts > 120]
        for s in expired:
            del self.helpers[s]
            
        if scope not in self.helpers:
            from gnom_hub.memory.emb_faiss import FaissEmbeddingHelper
            helper = FaissEmbeddingHelper(self.model_name, self.db_path, scope)
            self.helpers[scope] = (helper, now)
        else:
            helper, _ = self.helpers[scope]
            self.helpers[scope] = (helper, now)
        return helper

    def add_fact(self, fact_id: str, key: str, value: str, scope: str = "global"):
        _search_cache.clear()
        helper = self.get_helper(scope)
        if helper:
            helper.add_fact(fact_id, key, value)

    def search_sync(self, query: str, agent_name: str = None, top_k: int = 8, raw: bool = False) -> list:
        k = (query, agent_name, top_k, raw)
        if k in _search_cache:
            return _search_cache[k]
        
        g_helper = self.get_helper("global")
        global_results = g_helper.search(query, top_k, raw=raw) if g_helper else []
        
        agent_scope = agent_name.lower() if agent_name else None
        if agent_scope and agent_scope in ["coderag", "researcherag", "writerag", "editorag"]:
            a_helper = self.get_helper(agent_scope)
            agent_results = a_helper.search(query, top_k, raw=raw) if a_helper else []
            seen = set()
            merged = []
            for r in agent_results + global_results:
                content = r.split(": ", 1)[1] if ": " in r else r
                if content not in seen:
                    seen.add(content)
                    merged.append(r)
            res = merged[:top_k]
        elif agent_scope == "generalag":
            # GeneralAG orchestrates the entire swarm and must see facts for all agents
            all_results = []
            for scope in ["global", "coderag", "researcherag", "writerag", "editorag"]:
                helper = self.get_helper(scope)
                if helper:
                    all_results += helper.search(query, top_k, raw=raw)
            seen = set()
            merged = []
            for r in all_results:
                content = r.split(": ", 1)[1] if ": " in r else r
                if content not in seen:
                    seen.add(content)
                    merged.append(r)
            res = merged[:top_k]
        else:
            res = global_results
            
        if not g_helper:
            res = sr.retrieve_similar_sync(query, top_k=top_k, agent_name=agent_name, raw=raw)
            
        _search_cache[k] = res
        return res

    def has_similar(self, text: str, threshold: float = 0.92) -> bool:
        helper = self.get_helper("global")
        if not helper or helper.index.ntotal == 0: return False
        results = self.search_sync(text, top_k=1, raw=True)
        if not results: return False
        try:
            import numpy as np
            from gnom_hub.memory.emb_cache import get_emb
            val_text = text.split(": ", 1)[1] if ": " in text else text
            res_val = results[0].split(": ", 1)[1] if ": " in results[0] else results[0]
            v1 = get_emb(helper.model, val_text).flatten()
            v2 = get_emb(helper.model, res_val).flatten()
            cos = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
            return cos > threshold
        except Exception:
            return False

# ── Singleton ──────────────────────────────────────────────
_instance = None
_instance_lock = threading.Lock()

def get_embedder() -> SoulEmbedder:
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:  # Double-check locking
                _instance = SoulEmbedder()
                _logger.info("SoulEmbedder singleton initialized (FAISS=%s)", _instance.get_helper("global") is not None)
    return _instance
