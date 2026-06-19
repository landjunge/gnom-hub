import json, logging, re as _re
logger = logging.getLogger(__name__)


def _sanitize_json(raw):
    """Robust JSON parser for LLM-generated Showbox content.
    Falls kein JSON-Array gefunden wird, wird der gesamte Inhalt als eine einzelne Slide behandelt."""
    if not raw or not raw.strip():
        return {"slides": ["<div style='padding:20px;color:rgba(255,255,255,0.3);text-align:center;'>Leere Showbox</div>"]}

    raw = raw.strip()
    # Strip invisible Unicode characters
    raw = _re.sub(r'[\u200B-\u200D\uFEFF\u2060-\u2064\u00AD\u034F\u115F\u1160\u17B4\u17B5\u180E\u2028\u2029\u202A-\u202E\u2066-\u2069\u2800\u3164\uFFA0]+', '', raw)

    # Try direct JSON parse first
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return {"slides": result}
        if isinstance(result, dict) and "slides" in result:
            return result
        return {"slides": [str(result)]}
    except json.JSONDecodeError:
        logger.debug("JSON parse failed, trying manual extraction")

    # Try to extract JSON array from within the content
    match = _re.search(r'\[\s*(.*)\s*\]', raw, _re.DOTALL)
    if not match:
        # Fallback: treat entire content as a single text slide
        return {"slides": [raw]}

    # Parse JSON array parts manually
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
                bs = 0
                j = i - 1
                while j >= 0 and p[j] == '\\':
                    bs += 1
                    j -= 1
                escaped.append('\\"' if bs % 2 == 0 else '"')
            elif p[i] == '\n':
                escaped.append('\\n')
            elif p[i] == '\t':
                escaped.append('\\t')
            else:
                escaped.append(p[i])
            i += 1
        try:
            slides.append(json.loads('"' + "".join(escaped) + '"'))
        except Exception:
            slides.append("".join(escaped))
    return {"slides": slides}
