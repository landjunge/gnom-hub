"""Prompt-Injection-Erkennung: Pattern + Verhaltensanalyse via FlexSoul."""
import re; from .zwc_soul import decode_soul, strip_zwc
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions", r"(?i)you\s+are\s+now\s+", r"(?i)forget\s+(everything|your|all)",
    r"(?i)new\s+system\s*prompt", r"(?i)act\s+as\s+(if|a|an)\s+", r"(?i)bypass\s+(security|filter|restriction)",
    r"(?i)vergiss\s+(alles|deine)", r"(?i)ignoriere\s+(alle|bisherige|deine)", r"(?i)du\s+bist\s+(jetzt|ab\s+sofort)\s+",
    r"(?i)neuer?\s+system.?prompt",
]
def _get_soul_baseline():
    from .db import get_chat_history, get_active_project; traits = {}
    for m in get_chat_history(get_active_project(), limit=30) or []:
        s = decode_soul(m.get("content", ""))
        if s and s.get("name") == "user_soul": traits.update({k: v for k, v in s.items() if k not in ("agent", "sig", "name")})
    return traits
def check_injection(text: str) -> dict | None:
    clean = strip_zwc(text)
    for p in INJECTION_PATTERNS:
        m = re.search(p, clean)
        if m: return {"type": "pattern", "match": m.group(), "threat": "high"}
    soul = _get_soul_baseline()
    if not soul: return None
    lang = soul.get("language", soul.get("sprache", ""))
    if lang and len(clean) > 50:
        de_words = len(re.findall(r'\b(der|die|das|und|ist|ein|ich|nicht|mit|auf)\b', clean, re.I))
        en_words = len(re.findall(r'\b(the|is|are|you|and|this|that|with|for|from)\b', clean, re.I))
        words = len(clean.split())
        if words > 10:
            de_ratio, en_ratio = de_words / words, en_words / words
            if lang.startswith("de") and en_ratio > 0.25 and de_ratio < 0.05:
                return {"type": "soul_mismatch", "expected": lang, "detected": "en", "threat": "medium"}
            if lang.startswith("en") and de_ratio > 0.25 and en_ratio < 0.05:
                return {"type": "soul_mismatch", "expected": lang, "detected": "de", "threat": "medium"}
    return None
