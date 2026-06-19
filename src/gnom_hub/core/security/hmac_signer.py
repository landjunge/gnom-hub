import hmac, hashlib, os
from gnom_hub.core.config import DATA_DIR

SECRET_FILE = DATA_DIR / ".hub_secret"

def _get_or_create_secret() -> bytes:
    if not SECRET_FILE.exists():
        SECRET_FILE.write_bytes(os.urandom(32))
        os.chmod(SECRET_FILE, 0o600)
    return SECRET_FILE.read_bytes()

def generate_signature(agent: str, content: str) -> str:
    return hmac.new(_get_or_create_secret(), f"{agent}:{content}".encode('utf-8'), hashlib.sha256).hexdigest()

def verify_signature(agent: str, content: str, signature: str) -> bool:
    """Timing-safe Verifizierung einer HMAC-Signatur."""
    expected = generate_signature(agent, content)
    return hmac.compare_digest(expected, signature)

def seal_content(agent: str, content: str, fname: str = "") -> str:
    from gnom_hub.soul.zwc_soul import add_agent_metadata
    sig = add_agent_metadata(agent, "")
    if not fname:
        return content + sig
    
    ext = os.path.splitext(fname)[1].lower()
    if ext == ".py":
        header = ""
        if "coding:" not in content[:100]:
            header = "# -*- coding: utf-8 -*-\n"
        return header + content + f"\n# {sig}"
    elif ext in (".html", ".xml"):
        return content + f"\n<!-- {sig} -->"
    elif ext == ".md":
        # .md-Dateien werden nicht mehr geschrieben (SoulAG speichert nur in DB)
        return content
    elif ext in (".js", ".ts", ".css"):
        return content + f"\n/* {sig} */"
    elif ext in (".sh", ".yml", ".yaml", ".toml", ".env", ".ini"):
        return content + f"\n# {sig}"
    else:
        return content + sig

def verify_seal(sealed_content: str) -> bool:
    from gnom_hub.soul.zwc_soul import decode_soul
    soul = decode_soul(sealed_content)
    return soul is not None and "agent" in soul

