# embeddings.py — Local embeddings / semantic retrieval helper
from gnom_hub.semantic_memory_retriever import SemanticMemoryRetriever
import gnom_hub.smr_retrieve as sr

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_LIBS = True
except ImportError:
    HAS_LIBS = False

_search_cache = {}

class SoulEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", db_path: str = "gnomhub.db"):
        self.db_path, self.smr, self.helper = db_path, SemanticMemoryRetriever(), None
        if HAS_LIBS:
            from gnom_hub.emb_faiss import FaissEmbeddingHelper
            self.helper = FaissEmbeddingHelper(model_name, db_path)

    def add_fact(self, fact_id: str, key: str, value: str):
        _search_cache.clear()
        if self.helper: self.helper.add_fact(fact_id, key, value)

    def search_sync(self, query: str, top_k: int = 8) -> list:
        k = (query, top_k)
        if k in _search_cache: return _search_cache[k]
        res = self.helper.search(query, top_k) if self.helper else sr.retrieve_similar_sync(query, top_k)
        _search_cache[k] = res
        return res

    async def search(self, query: str, top_k: int = 8) -> list:
        return self.search_sync(query, top_k)
