# embeddings.py — Local embeddings / semantic retrieval helper (Singleton)
# Try to import FAISS + sentence-transformers, but gracefully degrade to TF-IDF if unavailable
import gnom_hub.memory.smr.smr_retrieve as sr
import logging
import threading

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_FAISS = True
    _log_faiss = "available"
except ImportError:
    HAS_FAISS = False
    _log_faiss = "NOT installed (using TF-IDF fallback)"

_search_cache = {}
_search_cache_ttl = {}
_search_cache_max_age = 60.0
_logger = logging.getLogger("embeddings")


class SoulEmbedder:
    """Semantic embedder with graceful FAISS→TF-IDF fallback.
    
    If sentence-transformers or faiss-cpu are not installed (via optional 'memory' extra),
    all search operations automatically delegate to TF-IDF (pure Python, no compilation).
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", db_path: str = None):
        from gnom_hub.core.config import Config
        DB_PATH = Config.DB_PATH
        self.model_name = model_name
        self.db_path = str(db_path or DB_PATH)
        self.helpers = {}
        self.has_faiss = HAS_FAISS
        
        if not HAS_FAISS:
            _logger.warning(
                "⚠️  sentence-transformers or faiss-cpu not installed. "
                "Falling back to TF-IDF semantic search (pure Python, no C dependencies). "
                "For faster search, run: pip install -e '.[memory]'"
            )

    def get_helper(self, scope: str = "global"):
        """Get or create a FAISS helper for the given scope.
        Returns None if FAISS is not available (fallback to TF-IDF).
        """
        if not HAS_FAISS:
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
        """Add a fact to the semantic index (FAISS only, TF-IDF is read-only)."""
        _search_cache.clear()
        helper = self.get_helper(scope)
        if helper:
            try:
                helper.add_fact(fact_id, key, value)
            except Exception as e:
                _logger.error(f"Failed to add fact to FAISS index: {e}. Continuing without index.")

    def search_sync(self, query: str, agent_name: str = None, top_k: int = 8, raw: bool = False) -> list:
        """Search for relevant facts using FAISS (if available) or TF-IDF fallback."""
        k = (query, agent_name, top_k, raw)
        import time as _time
        now = _time.time()
        if k in _search_cache and now - _search_cache_ttl.get(k, 0) < _search_cache_max_age:
            return _search_cache[k]
        
        # Try FAISS first (if available)
        if HAS_FAISS:
            try:
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
                
                if res:
                    _search_cache[k] = res
                    _search_cache_ttl[k] = now
                    return res
            except Exception as e:
                _logger.warning(f"FAISS search failed: {e}. Falling back to TF-IDF.")
        
        # Fallback: TF-IDF (pure Python)
        res = sr.retrieve_similar_sync(query, top_k=top_k, agent_name=agent_name, raw=raw)
        _search_cache[k] = res
        _search_cache_ttl[k] = now
        return res

    def has_similar(self, text: str, threshold: float = 0.92) -> bool:
        """Check if similar text exists (FAISS only, returns False if not available)."""
        if not HAS_FAISS:
            return False
            
        try:
            helper = self.get_helper("global")
            if not helper or helper.index.ntotal == 0:
                return False
            results = self.search_sync(text, top_k=1, raw=True)
            if not results:
                return False
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
    """Get or create the singleton SoulEmbedder instance."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:  # Double-check locking
                _instance = SoulEmbedder()
                backend = "FAISS" if _instance.has_faiss else "TF-IDF (fallback)"
                _logger.info(f"✓ SoulEmbedder initialized (backend: {backend})")
    return _instance
