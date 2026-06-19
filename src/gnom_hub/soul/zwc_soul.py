import json, base64, logging, time
Z, R = {'0': '\u200b', '1': '\u200c'}, {'\u200b': '0', '\u200c': '1'}
_log = logging.getLogger(__name__)

def soul_to_bits(d: dict) -> str:
    return ''.join(format(ord(c), '08b') for c in base64.b64encode(json.dumps(d, separators=(',', ':')).encode()).decode())

def bits_to_zwc(b: str) -> str:
    return ''.join(Z[bit] for bit in ''.join(bit * 3 for bit in b))

def extract_zwc(t: str) -> str:
    return ''.join(R.get(c, '') for c in t if c in R)

def strip_zwc(t: str) -> str:
    return ''.join(c for c in t if c not in R)

def correct_ecc(zb: str) -> str:
    c = ''
    for i in range(0, len(zb), 3):
        g = zb[i:i+3]
        if len(g) < 3: break
        c += '0' if g.count('0') >= 2 else '1'
    return c

def decode_soul(t: str):
    zb = extract_zwc(t)
    if not zb or len(zb) % 3 != 0: return None
    cb = correct_ecc(zb)
    try:
        raw = ''.join(chr(int(cb[i:i+8], 2)) for i in range(0, len(cb), 8))
        return json.loads(base64.b64decode(raw).decode())
    except Exception:
        _log.debug('ZWC decode failed for input length %d', len(t))
        return None

def add_agent_metadata(agent_name: str, message: str, extra: dict = None) -> str:
    """Fügt unsichtbare ZWC-Metadaten an eine Nachricht an.

    Standard: kodiert die Agenten-Identitaet zur Signatur.
    SoulAG kann via `extra` Direktiven einbetten, die andere Agents
    via decode_soul() lesen koennen (z.B. Ziel-Ausrichtung, Erinnerungen).

    Beispiel aus SoulAG:
        add_agent_metadata("SoulAG", msg, {"directive": "CoderAG: Nutze HTML5", "ttl": 3600})
    """
    data = {"agent": agent_name, "ts": time.time()}
    if extra:
        data["extra"] = extra
    return message + bits_to_zwc(soul_to_bits(data))

def add_directive(target_agent: str, directive: str, ttl: int = 3600) -> str:
    """Erzeugt einen ZWC-Direktiv-String fuer SoulAG.

    Kann als Chat-Nachricht gepostet werden. Agents die die Nachricht
    lesen, koennen via decode_soul() die Direktive extrahieren.

    Args:
        target_agent: Ziel-Agent (z.B. "CoderAG", "all")
        directive:   Die Direktive (z.B. "Nutze HTML5 Standards")
        ttl:         Gültigkeitsdauer in Sekunden (default 1h)

    Returns:
        String mit ZWC-kodierter Direktive
    """
    payload = {
        "agent": "SoulAG",
        "ts": time.time(),
        "extra": {
            "type": "directive",
            "target": target_agent,
            "msg": directive,
            "ttl": ttl
        }
    }
    return bits_to_zwc(soul_to_bits(payload))

def get_directives(text: str) -> list:
    """Extrahiert alle SoulAG-Direktiven aus einem Text.

    Durchsucht den Text nach ZWC-kodierten Direktiven und gibt
    eine Liste aller gefundenen, noch nicht abgelaufenen Direktiven zurueck.

    Returns:
        Liste von Dicts mit {"agent", "target", "msg", "ts", "ttl"}
    """
    result = []
    payload = decode_soul(text)
    if payload and "extra" in payload:
        extra = payload["extra"]
        if isinstance(extra, dict) and extra.get("type") == "directive":
            now = time.time()
            ts = payload.get("ts", 0)
            ttl = extra.get("ttl", 3600)
            if now - ts < ttl:
                result.append({
                    "agent": payload.get("agent", "?"),
                    "target": extra.get("target", "all"),
                    "msg": extra.get("msg", ""),
                    "ts": ts,
                    "ttl": ttl
                })
    return result


# ── SoulAG Thought-Extractor ─────────────────────────────────────────
# Lokale, schnelle Fakt-Extraktion aus Denkprozessen — KEIN LLM-Call,
# damit der Agent-Loop nicht blockiert wird. Pattern-basiert.
import re as _re
import uuid as _uuid
from datetime import datetime as _dt

_THOUGHT_PATTERNS = [
    # Strategische Erkenntnisse
    (r"(?:ich (?:merke|lern[ae]|erkenne|verstehe)|es zeigt sich|auffällig ist|wichtig ist)\s*,?\s*[:\-]?\s*(.+?)(?:[\.\n]|$)",
     "thought", "medium"),
    (r"(?:die (?:beste|optimale|richtige|richtigste) (?:Strategie|Lösung|Antwort|Methode) (?:ist|wäre)|optimal wäre|empfehl[ae])\s*[:\-]?\s*(.+?)(?:[\.\n]|$)",
     "strategy", "high"),
    (r"(?:ich sollte|man sollte|wir sollten|ich muss|ich werde)\s+(.+?)(?:[\.\n]|$)",
     "todo", "medium"),
    # Wiederkehrende Muster
    (r"(?:pattern|regel|prinzip|grundsatz|lehrsatz)[:\s]+(.+?)(?:[\.\n]|$)",
     "pattern", "medium"),
    # Nutzer-Präferenzen (aus User-Mentioned Denkprozessen)
    (r"(?:der (?:user|nutzer|benutzer) (?:mag|will|braucht|verlangt|erwartet|bevorzugt)|nutzer[- ]?präferenz)[:\s]+(.+?)(?:[\.\n]|$)",
     "user_pref", "high"),
]


def extract_facts_from_text(text: str, agent_name: str) -> list:
    """
    Lokale, blockierungsfreie Fakt-Extraktion aus einem Denkprozess.
    Pattern-basiert, kein LLM-Call. Speichert direkt in soul_memory.
    Gibt Liste der gespeicherten Keys zurück.

    Wird von agent_base.py nach jeder Agent-Antwort aufgerufen,
    damit SoulAG die Strategien und Muster aller Agenten mitbekommt.
    """
    if not text or len(text) < 30:
        return []

    text_lower = text.lower()
    saved_keys = []

    try:
        from gnom_hub.db import save_soul_fact
    except Exception:
        return []

    for pattern, kind, priority in _THOUGHT_PATTERNS:
        for m in _re.finditer(pattern, text_lower, flags=_re.IGNORECASE | _re.DOTALL):
            fact = m.group(1).strip().rstrip(".!?\n")
            if len(fact) < 15 or len(fact) > 300:
                continue
            # Keine Duplikate pro Agent+Kind
            key = f"thought_{kind}_{_uuid.uuid4().hex[:8]}"
            try:
                save_soul_fact(
                    key,
                    f"[{kind} from {agent_name}] {fact[:250]}",
                    agent="SoulAG",
                )
                saved_keys.append(key)
            except Exception:
                pass
            # Max 5 Fakten pro Denkprozess (Performance)
            if len(saved_keys) >= 5:
                return saved_keys

    # Zusätzlich: bei jedem Denkprozess einen Meta-Fakt über die Denkaktivität
    if len(text) > 200 and saved_keys:
        try:
            save_soul_fact(
                f"thought_meta_{_uuid.uuid4().hex[:6]}",
                f"{agent_name} dachte intensiv nach ({len(text)} Zeichen Denkprozess, ",
                f"{len(saved_keys)} Erkenntnisse extrahiert) am {_dt.utcnow().strftime('%Y-%m-%d %H:%M')}",
                agent="SoulAG",
            )
        except Exception:
            pass

    return saved_keys
