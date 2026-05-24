import json, re as _re
def _sanitize_json(raw):
    """Robust JSON parser for LLM-generated Showbox content."""
    raw = raw.strip()
    try: return json.loads(raw)
    except Exception: pass
    match = _re.search(r'\[\s*(.*)\s*\]', raw, _re.DOTALL)
    if not match: raise ValueError("Could not find JSON array")
    parts = _re.split(r'(?<!\\)"\s*,\s*(?=\s*(?:"|\[|\{))', match.group(1).strip())
    slides = []
    for p in parts:
        p = p.strip()
        if p.startswith('"'): p = p[1:]
        if p.endswith('"') and not p.endswith('\\"'): p = p[:-1]
        escaped = []
        i = 0
        while i < len(p):
            if p[i] == '"':
                bs = 0; j = i - 1
                while j >= 0 and p[j] == '\\': bs += 1; j -= 1
                escaped.append('\\"' if bs % 2 == 0 else '"')
            elif p[i] == '\n': escaped.append('\\n')
            elif p[i] == '\t': escaped.append('\\t')
            else: escaped.append(p[i])
            i += 1
        slides.append(json.loads('"' + "".join(escaped) + '"'))
    return {"slides": slides}
