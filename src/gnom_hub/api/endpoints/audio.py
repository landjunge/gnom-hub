import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from gnom_hub.core.utils.audio_stt import transcribe
from gnom_hub.core.utils.audio_tts import tts
from gnom_hub.db.agent_repo import SQLiteAgentRepository

_log = logging.getLogger(__name__)

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    agent_id: str = ""

@router.post("/api/audio/tts")
async def do_tts(req: TTSRequest):
    voice = ""
    if req.agent_id:
        agent = SQLiteAgentRepository().get_by_id(req.agent_id)
        if agent:
            voice = getattr(agent, 'voice_id', '') or dict(agent.__dict__).get('voice_id', '')
    path = tts(req.text, voice)
    if path and path.exists():
        # Erfolg: MP3 als FileResponse. Frontend erkennt content-type=audio/mpeg.
        return FileResponse(str(path), media_type="audio/mpeg")
    # Kein Provider konnte liefern. Statt leerem Body oder 500 ein ehrliches
    # Fallback-JSON liefern, damit das Frontend sauber auf speechSynthesis
    # umschalten kann.
    _log.info(
        "TTS endpoint fallback → speech_synthesis (agent=%r, text_len=%d)",
        req.agent_id, len(req.text or ""),
    )
    return JSONResponse(
        status_code=200,
        content={
            "audio_url": None,
            "fallback": "speech_synthesis",
            "text": req.text,
            "reason": "no_tts_provider_available",
        },
    )

@router.post("/api/audio/stt")
async def do_stt(file: UploadFile = File(...)):
    data = await file.read()
    text = transcribe(data)
    if text: return {"text": text}
    return {"text": "", "fallback": "web_speech"}
