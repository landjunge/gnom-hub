# semantic_memory_retriever.py — Semantic similarity retrieval and memory pruning
from typing import List
import gnom_hub.memory.smr.smr_retrieve as sr
import gnom_hub.memory.smr.smr_prune as sp
import gnom_hub.memory.smr.smr_stats as ss

class LocalEmbedder:
    pass

class SemanticMemoryRetriever:
    def __init__(self, db=None, embedder=None):
        self.db = db
        self.embedder = embedder

    async def retrieve_similar(self, query: str, top_k: int = 8) -> List[str]:
        return await sr.retrieve_similar(query, top_k)

    async def retrieve_with_fallback(self, query: str, top_k: int = 8) -> List[str]:
        return await sr.retrieve_with_fallback(query, top_k)

    def prune_low_relevance(self, threshold: float = 0.15, min_age_days: int = 30):
        sp.prune_low_relevance(threshold, min_age_days)

    def get_memory_stats(self) -> dict:
        return ss.get_memory_stats()
