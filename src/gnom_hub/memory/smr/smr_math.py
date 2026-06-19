# smr_math.py
import math
import re
from typing import List

def tokenize(text: str) -> List[str]:
    if not text: return []
    return re.findall(r'\w+', text.lower())

def cosine_similarity(text1: str, text2: str) -> float:
    t1, t2 = tokenize(text1), tokenize(text2)
    if not t1 or not t2: return 0.0
    f1, f2 = {}, {}
    for t in t1: f1[t] = f1.get(t, 0) + 1
    for t in t2: f2[t] = f2.get(t, 0) + 1
    dot = sum(f1[t] * f2[t] for t in f1 if t in f2)
    n1 = math.sqrt(sum(f * f for f in f1.values()))
    n2 = math.sqrt(sum(f * f for f in f2.values()))
    return dot / (n1 * n2) if (n1 > 0 and n2 > 0) else 0.0
