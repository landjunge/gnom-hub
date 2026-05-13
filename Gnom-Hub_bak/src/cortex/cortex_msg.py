#!/usr/bin/env python3
"""
CORTEX MSG — Bidirektionale Message-Pipe: Hermes ↔ Antigravity
==============================================================
Nutzt die Cortex-DB als zuverlässigen Shared Blackboard.
Kein HTTP, kein requests, keine Ports — nur JSON-Dateien.

USAGE:
  python3 cortex_msg.py send <von> <an> "<nachricht>"
  python3 cortex_msg.py read <empfaenger>
  python3 cortex_msg.py read <empfaenger> --unread
  python3 cortex_msg.py ack <msg_id>
  python3 cortex_msg.py list

BEISPIELE:
  python3 cortex_msg.py send hermes antigravity "Hallo Antigravity!"
  python3 cortex_msg.py send antigravity hermes "Antwort von Antigravity"
  python3 cortex_msg.py read antigravity --unread
  python3 cortex_msg.py read hermes
"""

import json
import os
import sys
from datetime import datetime


# ── Pfade ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR   = os.path.join(BASE_DIR, ".cortex", "db")
MSG_FILE = os.path.join(DB_DIR, "messages.json")

AGENTS = ["hermes", "antigravity", "openclaw", "paperclip", "cortex"]


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _gen_id() -> str:
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]
    return f"msg_{ts}"


def _read() -> list:
    if not os.path.exists(MSG_FILE):
        return []
    try:
        with open(MSG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write(data: list):
    os.makedirs(DB_DIR, exist_ok=True)
    with open(MSG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════

def cmd_send(sender: str, recipient: str, content: str) -> dict:
    """Nachricht senden."""
    msg = {
        "id":        _gen_id(),
        "from":      sender,
        "to":        recipient,
        "content":   content,
        "timestamp": _now(),
        "read":      False,
    }
    data = _read()
    data.append(msg)
    _write(data)
    print(f"✅ Nachricht gesendet: {msg['id']}")
    print(f"   {sender} → {recipient}: {content[:80]}")
    return msg


def cmd_read(recipient: str, unread_only: bool = False) -> list:
    """Nachrichten für einen Empfänger lesen."""
    data = _read()
    msgs = [m for m in data if m.get("to") == recipient]
    if unread_only:
        msgs = [m for m in msgs if not m.get("read")]

    if not msgs:
        print(f"📭 Keine {'ungelesenen ' if unread_only else ''}Nachrichten für {recipient}.")
        return []

    print(f"📬 {len(msgs)} Nachricht(en) für {recipient}:")
    print("─" * 60)
    for m in msgs:
        status = "🆕" if not m.get("read") else "✓ "
        print(f"{status} [{m['id']}] {m['from']} → {m['to']}  ({m['timestamp'][:19]})")
        print(f"   {m['content']}")
        print()

    # Alle als gelesen markieren
    now = _now()
    for m in data:
        if m.get("to") == recipient and not m.get("read"):
            m["read"] = True
            m["read_at"] = now
    _write(data)
    return msgs


def cmd_ack(msg_id: str):
    """Einzelne Nachricht als gelesen markieren."""
    data = _read()
    for m in data:
        if m["id"] == msg_id:
            m["read"] = True
            m["read_at"] = _now()
            _write(data)
            print(f"✅ Nachricht {msg_id} als gelesen markiert.")
            return
    print(f"❌ Nachricht {msg_id} nicht gefunden.")


def cmd_list():
    """Alle Nachrichten anzeigen."""
    data = _read()
    if not data:
        print("📭 Keine Nachrichten.")
        return
    print(f"📬 {len(data)} Nachricht(en) gesamt:")
    print("─" * 60)
    for m in data:
        status = "🆕" if not m.get("read") else "✓ "
        print(f"{status} [{m['id']}] {m['from']} → {m['to']}  ({m['timestamp'][:19]})")
        print(f"   {m['content'][:100]}")


def cmd_clear(agent: str = ""):
    """Gelesene Nachrichten löschen. Optional: nur für einen Agenten."""
    data = _read()
    if agent:
        new = [m for m in data if not (m.get("to") == agent and m.get("read"))]
    else:
        new = [m for m in data if not m.get("read")]
    removed = len(data) - len(new)
    _write(new)
    print(f"🧹 {removed} gelesene Nachricht(en) gelöscht.")


# ══════════════════════════════════════
# MAIN
# ══════════════════════════════════════

def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "help"):
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "send":
        if len(args) < 4:
            print("Usage: cortex_msg.py send <von> <an> <nachricht>")
            sys.exit(1)
        cmd_send(sender=args[1], recipient=args[2], content=args[3])

    elif cmd == "read":
        if len(args) < 2:
            print("Usage: cortex_msg.py read <empfaenger> [--unread]")
            sys.exit(1)
        unread = "--unread" in args
        cmd_read(recipient=args[1], unread_only=unread)

    elif cmd == "ack":
        if len(args) < 2:
            print("Usage: cortex_msg.py ack <msg_id>")
            sys.exit(1)
        cmd_ack(args[1])

    elif cmd == "list":
        cmd_list()

    elif cmd == "clear":
        agent = args[1] if len(args) > 1 else ""
        cmd_clear(agent)

    else:
        print(f"❌ Unbekannter Befehl: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
