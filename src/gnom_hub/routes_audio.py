from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .audio_tts import tts
from .audio_stt import transcribe
from .db import get_db
router = APIRouter()
class TTSRequest(BaseModel):
    text: str
    agent_id: str = ""
@router.post("/api/audio/tts")
async def do_tts(req: TTSRequest):
    voice = ""
    if req.agent_id:
        agent = next((a for a in get_db("agents") if a.get("id") == req.agent_id), None)
        if agent: voice = agent.get("voice_id", "")
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
