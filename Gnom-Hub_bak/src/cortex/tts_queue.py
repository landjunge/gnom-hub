#!/usr/bin/env python3
"""
TTS QUEUE — Serieller Vorleser
==============================
Nur EINE Ausgabe gleichzeitig. Hermes wartet bis fertig.
Nutzt macOS `say` Befehl. Kein externes Paket nötig.

API:
  q = TTSQueue()
  q.enqueue("Hallo Welt", priority=0)
  q.enqueue("Nächster Gedanke", priority=1)  # wartet
  q.is_speaking()   # True wenn gerade läuft
  q.stop()
"""

import subprocess
import threading
import json
import os
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
QUEUE_FILE = os.path.join(BASE_DIR, ".cortex", "queues", "tts_queue.json")
FLAG_FILE  = os.path.join(BASE_DIR, ".cortex", "queues", "tts_speaking.flag")

VOICE      = "Anna"   # macOS deutsche Stimme
RATE       = 175      # Wörter pro Minute (normal ~180)


class TTSQueue:
    def __init__(self):
        self._lock      = threading.Lock()
        self._queue     = []
        self._speaking  = False
        self._stop_flag = False
        self._proc      = None
        self._thread    = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ── PUBLIC ──────────────────────────

    def enqueue(self, text: str, source: str = "system", priority: int = 0):
        """Text in die Queue einreihen."""
        item = {
            "id":        f"tts_{datetime.utcnow().strftime('%H%M%S%f')[:-3]}",
            "text":      text,
            "source":    source,
            "priority":  priority,
            "queued_at": datetime.utcnow().isoformat() + "Z",
        }
        with self._lock:
            self._queue.append(item)
            self._queue.sort(key=lambda x: x["priority"])
        self._persist()
        return item["id"]

    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self):
        """Aktuelle Ausgabe sofort stoppen."""
        self._stop_flag = True
        if self._proc:
            try:
                self._proc.terminate()
            except:
                pass
        self._speaking = False
        self._remove_flag()

    def clear(self):
        """Queue leeren."""
        self.stop()
        with self._lock:
            self._queue.clear()
        self._persist()

    def queue_length(self) -> int:
        with self._lock:
            return len(self._queue)

    # ── INTERNAL ────────────────────────

    def _worker(self):
        while True:
            item = None
            with self._lock:
                if self._queue:
                    item = self._queue.pop(0)
            if item:
                self._speak(item)
                self._persist()
            else:
                threading.Event().wait(0.3)

    def _speak(self, item: dict):
        self._speaking  = True
        self._stop_flag = False
        self._set_flag(item)
        try:
            text = item["text"][:1000]  # Max 1000 Zeichen
            self._proc = subprocess.Popen(
                ["say", "-v", VOICE, "-r", str(RATE), text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._proc.wait()
        except Exception as e:
            pass
        finally:
            self._speaking = False
            self._proc     = None
            self._remove_flag()

    def _set_flag(self, item: dict):
        os.makedirs(os.path.dirname(FLAG_FILE), exist_ok=True)
        with open(FLAG_FILE, "w") as f:
            json.dump({"speaking": True, "item": item}, f)

    def _remove_flag(self):
        try:
            os.remove(FLAG_FILE)
        except:
            pass

    def _persist(self):
        os.makedirs(os.path.dirname(QUEUE_FILE), exist_ok=True)
        with self._lock:
            data = list(self._queue)
        with open(QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Singleton für Import
_instance = None

def get_queue() -> TTSQueue:
    global _instance
    if _instance is None:
        _instance = TTSQueue()
    return _instance


def is_tts_speaking() -> bool:
    """Ohne Queue-Instanz prüfen (nur Flag lesen). Für Hermes."""
    return os.path.exists(FLAG_FILE)


if __name__ == "__main__":
    # Test
    q = get_queue()
    print("TTS Queue Test...")
    q.enqueue("Erster Gedanke von Hermes.", source="hermes")
    q.enqueue("Zweiter Gedanke, wartet bis erster fertig.", source="hermes")
    q.enqueue("Und jetzt die Antwort.", source="hermes")
    print(f"Queue: {q.queue_length()} Items")
    import time
    while q.is_speaking() or q.queue_length() > 0:
        print(f"  speaking={q.is_speaking()} queue={q.queue_length()}")
        time.sleep(1)
    print("Fertig.")
