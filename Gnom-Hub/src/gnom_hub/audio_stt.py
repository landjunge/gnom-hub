"""STT Engine — Whisper lokal, OpenAI API Fallback."""
import os, io, tempfile

def stt_local(audio_bytes: bytes) -> str | None:
    """Lokales faster-whisper STT."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny", compute_type="int8")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(audio_bytes); tmp.close()
        segs, _ = model.transcribe(tmp.name, language="de")
        os.unlink(tmp.name)
        return " ".join(s.text for s in segs).strip()
    except: return None

def stt_cloud(audio_bytes: bytes) -> str | None:
    """OpenAI Whisper API Fallback."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key: return None
    try:
        import requests
        r = requests.post("https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": ("audio.wav", io.BytesIO(audio_bytes), "audio/wav")},
            data={"model": "whisper-1", "language": "de"}, timeout=30)
        return r.json().get("text") if r.status_code == 200 else None
    except: return None

def transcribe(audio_bytes: bytes) -> str:
    """Versucht lokal, dann Cloud. Gibt '' bei totalem Fehler zurück."""
    return stt_local(audio_bytes) or stt_cloud(audio_bytes) or ""
