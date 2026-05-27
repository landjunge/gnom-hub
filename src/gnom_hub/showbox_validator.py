"""Showbox-Signatur-Validierung für Chat-Ausgaben."""
import json, re
from agents.securityAG import generate_signature
from gnom_hub.soul.zwc_soul import strip_zwc

def sanitize_showboxes(content):
    """Prüft SHOWBOX-Signaturen, blockiert manipulierte."""
    def repl(m):
        idx = m.group(1) or ""
        idx_str = f":{idx}" if idx else ""
        json_str = m.group(2)
        try:
            data = json.loads(strip_zwc(json_str))
            sig = data.pop("sig", None)
            if not sig: raise ValueError("No signature")
            clean_json = json.dumps(data, separators=(',', ':'), sort_keys=True)
            expected_sig = generate_signature("Gnom", clean_json)
            if sig != expected_sig: raise ValueError("Invalid signature")
            data["sig"] = sig
            return f"<SHOWBOX{idx_str}>{json.dumps(data)}</SHOWBOX>"
        except Exception:
            return "[Blockiert: Manipulierte Showbox entfernt]"
    return re.sub(r"<SHOWBOX(?::([a-zA-Z0-9_\-]+))?>(.+?)</SHOWBOX>", repl, content, flags=re.DOTALL)
