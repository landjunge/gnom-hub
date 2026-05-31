import hmac, hashlib, os
from gnom_hub.core.config import DATA_DIR

SECRET_FILE = DATA_DIR / ".hub_secret"

def _get_or_create_secret() -> bytes:
    if not SECRET_FILE.exists():
        SECRET_FILE.write_bytes(os.urandom(32))
    return SECRET_FILE.read_bytes()

def generate_signature(agent: str, content: str) -> str:
    return hmac.new(_get_or_create_secret(), f"{agent}:{content}".encode('utf-8'), hashlib.sha256).hexdigest()

def verify_signature(agent: str, content: str, signature: str) -> bool:
    """Timing-safe Verifizierung einer HMAC-Signatur."""
    expected = generate_signature(agent, content)
    return hmac.compare_digest(expected, signature)
