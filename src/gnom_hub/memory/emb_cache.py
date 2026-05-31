# emb_cache.py — LRU-bounded caching for sentence embeddings
import os, json, logging, numpy as np
from collections import OrderedDict
from gnom_hub.core.config import DATA_DIR

_MAX_CACHE_SIZE = 5000
_CACHE_PATH = os.path.join(str(DATA_DIR), "emb_cache.json")

_cache = OrderedDict()
try:
    if os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for k, v in raw.items():
                _cache[k] = np.array(v, dtype=np.float32)
except Exception as e:
    logging.getLogger(__name__).error('Fehler beim Laden des Embedding-Cache: %s', e)

def _save_cache():
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        serializable = {k: v.tolist() for k, v in _cache.items()}
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(serializable, f)
    except Exception as e:
        logging.getLogger(__name__).error('Fehler in _save_cache: %s', e)

def get_emb(model, txt: str):
    if txt in _cache:
        _cache.move_to_end(txt)
        return _cache[txt]
    emb = model.encode([txt])
    _cache[txt] = emb
    # Evict oldest entries if over limit
    while len(_cache) > _MAX_CACHE_SIZE:
        _cache.popitem(last=False)
    _save_cache()
    return emb
