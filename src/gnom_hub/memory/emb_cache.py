# emb_cache.py — LRU-bounded caching for sentence embeddings
import json
import logging
import os
import threading
from collections import OrderedDict

import numpy as np

from gnom_hub.core.config import DATA_DIR

_MAX_CACHE_SIZE = 5000
_CACHE_PATH = os.path.join(str(DATA_DIR), "emb_cache.json")

_cache = OrderedDict()
_cache_lock = threading.Lock()
_dirty_count = 0
_SAVE_EVERY = 50  # Save to disk every N new embeddings
try:
    if os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH, encoding="utf-8") as f:
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
    global _dirty_count
    with _cache_lock:
        if txt in _cache:
            _cache.move_to_end(txt)
            return _cache[txt]
    emb = model.encode([txt])
    with _cache_lock:
        _cache[txt] = emb
        while len(_cache) > _MAX_CACHE_SIZE:
            _cache.popitem(last=False)
        _dirty_count += 1
        if _dirty_count >= _SAVE_EVERY:
            _save_cache()
            _dirty_count = 0
    return emb
