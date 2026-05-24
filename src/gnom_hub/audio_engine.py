"""Audio Engine Facade — importiert TTS + STT Module."""
from .audio_tts import tts
from .audio_stt import transcribe, stt_local, stt_cloud
