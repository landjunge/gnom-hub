from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from gnom_hub.core.utils.audio_tts import tts
from gnom_hub.core.utils.audio_stt import transcribe
from gnom_hub.db.agent_repo import SQLiteAgentRepository

router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    agent_id: str = ""

@router.post("/api/audio/tts")
async def do_tts(req: TTSRequest):
    voice = ""
    if req.agent_id:
        agent = SQLiteAgentRepository().get_by_id(req.agent_id)
        if agent: voice = getattr(agent, 'voice_id', '') or dict(agent.__dict__).get('voice_id', '')
    path = tts(req.text, voice)
    if path and path.exists():
        return FileResponse(str(path), media_type="audio/mpeg")
    return {"fallback": "web_speech", "text": req.text}

@router.post("/api/audio/stt")
async def do_stt(file: UploadFile = File(...)):
    data = await file.read()
    text = transcribe(data)
    if text: return {"text": text}
    return {"text": "", "fallback": "web_speech"}
