"""TTS Engine — ElevenLabs mit Web-Speech-Fallback."""
import os
from .config import DATA_DIR

AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVEN_VOICE = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

def tts(text: str, voice_id: str = ""):
    """ElevenLabs TTS → MP3 Pfad. None = Fallback auf Browser Web Speech."""
    if not ELEVEN_KEY: return None
    try:
        import requests
        vid = voice_id or ELEVEN_VOICE
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"}, timeout=15)
        if r.status_code != 200: return None
        out = AUDIO_DIR / f"tts_{hash(text) & 0xFFFFFFFF}.mp3"
        out.write_bytes(r.content); return out
    except: return None
