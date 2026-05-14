"""Gnom-Hub Tests — DB, Pulse, Audio, Rollen, Chat-Dispatch."""
import json, os, sys, tempfile, shutil
from pathlib import Path
from datetime import datetime, timedelta

TMP = tempfile.mkdtemp()
os.environ["GNOM_HUB_HOME"] = TMP
Path(TMP, "data").mkdir(); Path(TMP, "run").mkdir()
sys.path.insert(0, str(Path(__file__).parent / "src"))

passed, failed = 0, 0
def test(name, cond):
    global passed, failed
    if cond: passed += 1; print(f"  ✅ {name}")
    else: failed += 1; print(f"  ❌ {name}")

print("\n=== DB Tests ===")
from gnom_hub.db import get_db, save_db
test("get_db empty", get_db("test") == [])
save_db("test", [{"id": "1"}]); test("save/load", get_db("test") == [{"id": "1"}])

print("\n=== Pulse Janitor Tests ===")
from gnom_hub.hub_pulse import pulse_janitor
old = (datetime.utcnow() - timedelta(seconds=200)).isoformat() + "Z"
save_db("agents", [{"id":"a1","name":"Passive","port":0,"status":"online","last_seen":old}])
pulse_janitor(); test("port-0 bleibt online", get_db("agents")[0]["status"] == "online")
save_db("agents", [{"id":"a2","name":"Dead","port":59999,"status":"online","last_seen":old}])
pulse_janitor(); test("unerreichbar bleibt online (kein auto-offline)", get_db("agents")[0]["status"] == "online")

print("\n=== Audio Tests ===")
from gnom_hub.audio_tts import tts
from gnom_hub.audio_stt import transcribe
test("tts ohne Key → None", tts("test") is None)
test("transcribe leer → leer", transcribe(b"") == "")

print("\n=== Rollen Tests ===")
from gnom_hub.routes_chat import _role, _parse
save_db("agents", [
    {"id":"r1","name":"Alpha","status":"online","port":0},
    {"id":"r2","name":"Beta","status":"online","port":0},
    {"id":"r3","name":"Gamma","status":"online","port":0}
])
# General zuweisen
_role("Alpha", "general")
test("Alpha ist General", get_db("agents")[0].get("role") == "general")

# Zweiter General → Alpha verliert Rolle
_role("Beta", "general")
agents = get_db("agents")
test("Beta ist neuer General", next(a for a in agents if a["name"]=="Beta").get("role") == "general")
test("Alpha wurde normal", next(a for a in agents if a["name"]=="Alpha").get("role") == "normal")

# Summarizer — ebenfalls einzigartig
_role("Gamma", "summarizer")
_role("Alpha", "summarizer")
agents = get_db("agents")
test("Alpha ist Summarizer", next(a for a in agents if a["name"]=="Alpha").get("role") == "summarizer")
test("Gamma wurde normal", next(a for a in agents if a["name"]=="Gamma").get("role") == "normal")

# Normal-Rolle kann mehrfach existieren
_role("Beta", "normal"); _role("Gamma", "normal")
normals = [a for a in get_db("agents") if a.get("role") == "normal"]
test("Mehrere normals erlaubt", len(normals) >= 2)

print("\n=== Chat-Parser Tests ===")
q, t, r = _parse("@general @Hermes")
test("@general @Hermes → role=general", r == "general" and t == "Hermes")
q, t, r = _parse("@summarizer @Anki")
test("@summarizer @Anki → role=summarizer", r == "summarizer" and t == "Anki")
q, t, r = _parse("@bs Was meint ihr?")
test("@bs → cmd=bs, kein Target", t is None and r == "bs")
q, t, r = _parse("@Hermes Wie geht's?")
test("@Hermes → target=Hermes", t == "Hermes" and r is None)
q, t, r = _parse("Normaler Text")
test("Kein @ → alles None", t is None and r is None)

print(f"\n{'='*40}")
print(f"  Ergebnis: {passed} passed, {failed} failed")
print(f"{'='*40}")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if failed else 0)
