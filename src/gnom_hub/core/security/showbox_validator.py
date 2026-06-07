"""Showbox-Validierung für Chat-Ausgaben — 3-Layer-System."""
import re

USER_LAYER_PATTERN = re.compile(r'<SHOWBOX:\s*user\s*>(.*?)</SHOWBOX>', re.IGNORECASE | re.DOTALL)
BLOCKED_WARNING = '<SHOWBOX:system>["<div style=\'padding:20px;color:#f44;text-align:center;\'>🚫 <b>User-Layer blockiert</b><br><span style=\'font-size:0.7rem;color:rgba(255,255,255,0.4);\'>Agenten dürfen nicht in <b>&lt;SHOWBOX:user&gt;</b> schreiben. Das ist exklusiv für den User.</span></div>"]</SHOWBOX>'


def sanitize_showboxes(content, sender: str = ""):
    """
    Validiert SHOWBOX-Tags nach dem 3-Layer-System.
    - Agenten dürfen NIEMALS in <SHOWBOX:user> schreiben → wird geblockt
    """
    if sender and sender.lower() != "user":
        content = USER_LAYER_PATTERN.sub(BLOCKED_WARNING, content)
    return content


def enforce_agent_layer(content: str, sender: str) -> str:
    """
    Harte Durchsetzung der Layer-Regeln für Agenten-Nachrichten.
    Wird vor dem Speichern aufgerufen.
    """
    if sender.lower() == "user":
        return content
    return sanitize_showboxes(content, sender)

