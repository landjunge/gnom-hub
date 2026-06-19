"""Test: _kill_orphans_by_cmdline killt Waisen, die nicht in PID-Dateien stehen."""
import os
import subprocess
import sys
import time
from pathlib import Path

import psutil


def _spawn_dummy_agent(agent_name: str) -> int:
    """Startet einen Dummy-Prozess, der wie ein Agent aussieht (cmdline enthält 'agents.{name}')."""
    proc = subprocess.Popen(
        [sys.executable, "-u", "-c",
         f"import time, sys; sys.argv = ['agents.{agent_name}']; time.sleep(30)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.3)
    return proc.pid


def test_orphans_killed():
    """Waisen-Prozess mit 'agents.generalAG' im cmdline wird gefunden und gekillt."""
    from gnom_hub.infrastructure.process.process_manager import _kill_orphans_by_cmdline

    pid = _spawn_dummy_agent("generalAG")
    assert psutil.pid_exists(pid), "Dummy-Prozess nicht gestartet"

    _kill_orphans_by_cmdline("generalAG", already_killed=set())

    # Gebe dem System Zeit
    time.sleep(0.5)
    assert not psutil.pid_exists(pid), f"Orphan PID {pid} lebt noch"
    print(f"OK: Orphan {pid} (generalAG) gekillt")


def test_orphans_skipped_when_already_killed():
    """PID in already_killed wird nicht doppelt angefasst."""
    from gnom_hub.infrastructure.process.process_manager import _kill_orphans_by_cmdline

    pid = _spawn_dummy_agent("soulAG")
    assert psutil.pid_exists(pid)

    # Simuliere: wurde schon woanders gekillt
    _kill_orphans_by_cmdline("soulAG", already_killed={pid})

    # Prozess lebt noch, weil _kill_orphans ihn überspringt
    assert psutil.pid_exists(pid), "Prozess fälschlich gekillt"

    # Cleanup
    p = psutil.Process(pid)
    p.terminate()
    p.wait(timeout=3)
    print(f"OK: PID {pid} wurde korrekt übersprungen")


def test_orphans_does_not_kill_unrelated():
    """Prozesse OHNE 'agents.{name}' im cmdline bleiben unangetastet."""
    from gnom_hub.infrastructure.process.process_manager import _kill_orphans_by_cmdline

    # Eigener Subprozess mit anderem cmdline
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.3)

    try:
        _kill_orphans_by_cmdline("generalAG", already_killed=set())
        time.sleep(0.3)
        assert psutil.pid_exists(proc.pid), "Falscher Prozess gekillt"
        print(f"OK: unrelated PID {proc.pid} lebt noch")
    finally:
        proc.terminate()
        proc.wait(timeout=3)


def test_orphans_kill_only_target_agent():
    """generalAG-Kill darf nicht soulAG mitnehmen."""
    from gnom_hub.infrastructure.process.process_manager import _kill_orphans_by_cmdline

    pid_gen = _spawn_dummy_agent("generalAG")
    pid_soul = _spawn_dummy_agent("soulAG")

    try:
        _kill_orphans_by_cmdline("generalAG", already_killed=set())
        time.sleep(0.5)
        assert not psutil.pid_exists(pid_gen), "generalAG sollte tot sein"
        assert psutil.pid_exists(pid_soul), "soulAG fälschlich gekillt"
        print(f"OK: generalAG tot, soulAG lebt")
    finally:
        if psutil.pid_exists(pid_soul):
            psutil.Process(pid_soul).terminate()
            psutil.Process(pid_soul).wait(timeout=3)


if __name__ == "__main__":
    test_orphans_kill_only_target_agent()
    test_orphans_does_not_kill_unrelated()
    test_orphans_skipped_when_already_killed()
    test_orphans_killed()
    print("\nAlle Orphan-Kill-Tests bestanden.")
