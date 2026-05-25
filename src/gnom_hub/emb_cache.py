# emb_cache.py — Caching helper for sentence embeddings
import os, pickle

_cache = {}
try:
    if os.path.exists("data/emb_cache.pkl"):
        with open("data/emb_cache.pkl", "rb") as f: _cache = pickle.load(f)
except Exception: pass

def get_emb(model, txt: str):
    if txt in _cache: return _cache[txt]
    emb = model.encode([txt])
    _cache[txt] = emb
    try:
        with open("data/emb_cache.pkl", "wb") as f: pickle.dump(_cache, f)
    except Exception: pass
    return emb
