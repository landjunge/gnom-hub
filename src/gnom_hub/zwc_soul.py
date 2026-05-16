import json
import base64

ZERO_MAP = {'0': '\u200b', '1': '\u200c'}
REV_MAP = {'\u200b': '0', '\u200c': '1'}

def soul_to_bits(soul_dict: dict) -> str:
    """Soul → JSON → Base64 → Binary-Bits."""
    json_str = json.dumps(soul_dict, separators=(',', ':'))
    b64 = base64.b64encode(json_str.encode()).decode()
    return ''.join(format(ord(c), '08b') for c in b64)

def bits_to_zwc(bits: str) -> str:
    """Bits → Triple-Repetition → ZWC-Sequenz (ECC!)."""
    triple_bits = ''.join(bit * 3 for bit in bits)
    return ''.join(ZERO_MAP[bit] for bit in triple_bits)

def encode_soul(message: str, soul_dict: dict) -> str:
    """Hauptfunktion: Message + korrigierte Soul unsichtbar anhängen."""
    bits = soul_to_bits(soul_dict)
    zwc_payload = bits_to_zwc(bits)
    return message + zwc_payload

def extract_zwc(text: str) -> str:
    """Holt nur die ZWC-Sequenz raus."""
    return ''.join(REV_MAP.get(c, '') for c in text if c in REV_MAP)

def correct_ecc(zwc_bits: str) -> str:
    """Majority-Vote pro Triplet – repariert einzelne Bit-Fehler."""
    corrected = ''
    for i in range(0, len(zwc_bits), 3):
        group = zwc_bits[i:i+3]
        if len(group) < 3:
            break
        # Mehrheit entscheidet (robust gegen 1 Flip)
        if group.count('0') >= 2:
            corrected += '0'
        else:
            corrected += '1'
    return corrected

def decode_soul(text: str) -> dict | None:
    """ZWC + ECC → Soul-Dict zurück (für War-Room)."""
    zwc_bits = extract_zwc(text)
    if not zwc_bits or len(zwc_bits) % 3 != 0:
        return None
    corrected_bits = correct_ecc(zwc_bits)
    try:
        b64_chars = ''.join(chr(int(corrected_bits[i:i+8], 2)) for i in range(0, len(corrected_bits), 8))
        json_str = base64.b64decode(b64_chars).decode()
        return json.loads(json_str)
    except:
        return None
