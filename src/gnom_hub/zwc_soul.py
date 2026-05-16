"""ZWC Soul-Steganografie."""
import json, base64
ZERO_MAP = {'0': '\u200b', '1': '\u200c'}
REV_MAP = {'\u200b': '0', '\u200c': '1'}
def soul_to_bits(soul_dict: dict) -> str:
    json_str = json.dumps(soul_dict, separators=(',', ':'))
    b64 = base64.b64encode(json_str.encode()).decode()
    return ''.join(format(ord(c), '08b') for c in b64)
def bits_to_zwc(bits: str) -> str:
    return ''.join(ZERO_MAP[b] for b in bits)
def encode_soul(msg: str, soul_dict: dict) -> str:
    return msg + bits_to_zwc(soul_to_bits(soul_dict))
def extract_zwc(text: str) -> str:
    return ''.join(REV_MAP.get(c, '') for c in text if c in REV_MAP)
def strip_zwc(text: str) -> str:
    return text.replace('\u200b', '').replace('\u200c', '')
def decode_soul(text: str) -> dict | None:
    zwc_str = extract_zwc(text)
    if not zwc_str or len(zwc_str) % 8 != 0: return None
    try:
        b64_chars = ''.join(chr(int(zwc_str[i:i+8], 2)) for i in range(0, len(zwc_str), 8))
        return json.loads(base64.b64decode(b64_chars).decode())
    except: return None
