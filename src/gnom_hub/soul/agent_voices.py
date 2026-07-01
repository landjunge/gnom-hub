"""TTS-Stimmen für Gnom-Hub Agenten — plattformunabhängig.

Verfügbare Engines (in dieser Reihenfolge geprüft):
- macOS:   `say` (eingebaut, viele Stimmen)
- Linux:   `espeak` oder `spd-say` (oft vorinstalliert)
- Windows: `SAPI` via PowerShell, oder `espeak`
- Fallback: pyttsx3 (pip install pyttsx3)

SoulAG weist jedem Agent eine Stimme zu basierend auf:
- Agent-Rolle (Worker/System)
- Prompt-Sprache (DE/EN)
- Verfügbare Stimmen auf der aktuellen Plattform

User kann manuell überschreiben via state['agent_voices'] dict.
"""
import logging
import platform
import re
import shutil
import subprocess

_log = logging.getLogger(__name__)


def _detect_engine() -> str:
    """Detect available TTS engine on this platform."""
    system = platform.system()
    # macOS hat `say` eingebaut
    if system == 'Darwin' and shutil.which('say'):
        return 'say'
    # Linux: espeak, spd-say, festival
    for engine in ['espeak', 'spd-say', 'festival']:
        if shutil.which(engine):
            return engine
    # Windows: PowerShell SAPI
    if system == 'Windows':
        return 'sapi'
    return 'none'


ENGINE = _detect_engine()
SYSTEM = platform.system()


def list_voices() -> list:
    """Return all available TTS voices on this platform."""
    if ENGINE == 'say':
        # macOS: `say -v ?`
        try:
            out = subprocess.run(['say', '-v', '?'], capture_output=True, text=True, timeout=5).stdout
        except Exception:
            return []
        voices = []
        for line in out.split('\n'):
            if not line.strip():
                continue
            parts = re.split(r'\s{2,}', line, maxsplit=2)
            if len(parts) >= 2:
                voices.append({'name': parts[0].strip(), 'lang': parts[1].strip()})
        return voices
    elif ENGINE == 'espeak':
        # espeak --voices gibt eine Liste mit Sprache + Name
        try:
            out = subprocess.run(['espeak', '--voices'], capture_output=True, text=True, timeout=5).stdout
        except Exception:
            return []
        voices = []
        for line in out.split('\n')[1:]:  # skip header
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                voices.append({'name': parts[3], 'lang': parts[1]})
        return voices
    return [{'name': 'default', 'lang': 'en'}]


# Default voice assignment by role + language
# macOS bevorzugt: 'Anna' (de), 'Daniel' (en)
# Linux espeak: 'de+f3' (de), 'en+f3' (en) — fallback
DEFAULT_VOICE_ASSIGNMENTS = {
    'SoulAG':       {'de': 'Anna',         'en': 'Daniel'},
    'WatchdogAG':   {'de': 'Eddy (Deutsch (Deutschland))', 'en': 'Eddy'},
    'GeneralAG':    {'de': 'Anna (Enhanced)', 'en': 'Daniel'},
    'SecurityAG':   {'de': 'Anna (Premium)',  'en': 'Bad News'},
    'WriterAG':     {'de': 'Anna',         'en': 'Samantha'},
    'CoderAG':      {'de': 'Reed (Deutsch (Deutschland))', 'en': 'Alex'},
    'ResearcherAG': {'de': 'Anna (Enhanced)', 'en': 'Daniel'},
    'EditorAG':     {'de': 'Anna',         'en': 'Karen'},
}

# Plattformunabhängige Fallback-Voices (für Linux/Windows)
PLATFORM_FALLBACK = {
    'Darwin':  {'de': 'Anna', 'en': 'Daniel'},
    'Linux':   {'de': 'de+f3', 'en': 'en+m3'},
    'Windows': {'de': 'de-DE', 'en': 'en-US'},
}


def get_voice_for_agent(agent_name: str, lang: str = 'de') -> str:
    """Get assigned voice for an agent. Falls back to platform default."""
    assign = DEFAULT_VOICE_ASSIGNMENTS.get(agent_name, {})
    voice = assign.get(lang)
    if not voice:
        voice = PLATFORM_FALLBACK.get(SYSTEM, {}).get(lang, 'default')
    return voice


def get_all_assignments() -> dict:
    """All default voice assignments."""
    return {agent: dict(voices) for agent, voices in DEFAULT_VOICE_ASSIGNMENTS.items()}


def speak(text: str, voice: str = None, rate: int = 180) -> bool:
    """Speak text using the platform's TTS engine. Returns True if dispatched."""
    if not text:
        return False
    if ENGINE == 'say':
        cmd = ['say']
        if voice:
            cmd += ['-v', voice]
        cmd += ['-r', str(rate), text]
        return _run_async(cmd)
    elif ENGINE == 'espeak':
        cmd = ['espeak']
        if voice:
            cmd += ['-v', voice]
        cmd += ['-s', str(rate), text]
        return _run_async(cmd)
    elif ENGINE == 'sapi':
        # Windows: PowerShell SAPI
        ps_cmd = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Speak('{text.replace(chr(39), chr(chr(39)+chr(39)))}')"
        )
        return _run_async(['powershell', '-Command', ps_cmd])
    _log.warning(f"No TTS engine available on {SYSTEM}")
    return False


def _run_async(cmd) -> bool:
    """Run TTS command asynchronously (non-blocking)."""
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        _log.error(f"TTS command failed: {e}")
        return False
