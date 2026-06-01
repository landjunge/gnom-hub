import json, base64, logging
Z, R = {'0': '\u200b', '1': '\u200c'}, {'\u200b': '0', '\u200c': '1'}
def soul_to_bits(d: dict) -> str: return ''.join(format(ord(c), '08b') for c in base64.b64encode(json.dumps(d, separators=(',', ':')).encode()).decode())
def bits_to_zwc(b: str) -> str: return ''.join(Z[bit] for bit in ''.join(bit * 3 for bit in b))
def extract_zwc(t: str) -> str: return ''.join(R.get(c, '') for c in t if c in R)
def strip_zwc(t: str) -> str: return ''.join(c for c in t if c not in R)
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
    try: return json.loads(base64.b64decode(''.join(chr(int(cb[i:i+8], 2)) for i in range(0, len(cb), 8))).decode())
    except Exception:
        logging.getLogger(__name__).debug('ZWC decode failed for input length %d', len(t))
        return None
def add_agent_metadata(agent_name: str, message: str) -> str:
    return message + bits_to_zwc(soul_to_bits({"agent": agent_name}))
