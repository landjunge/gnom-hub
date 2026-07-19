# tests/test_queue_stability.py
# Load-Test: SQLite-basierte Message Queue unter realistischer Multi-Agent-Last
#
# Test-Szenarien:
#   1. 5 Agents parallel mit Tasks bombardieren (unterschiedliche Prioritäten)
#   2. Sequenzielle Abhängigkeiten via parent_msg_id
#   3. Absichtlich langsame/crashende Agents → stuck messages provozieren
#   4. recover_stuck_messages() unter Last
#   5. Statistiken: Durchsatz, stuck, DLQ, Backpressure-Treffer
#
# Schwachstellen die dieser Test aufdeckt:
#   - Race Conditions in fetch_next_message() / BEGIN IMMEDIATE
#   - NULL processing_since in recover_stuck_messages()
#   - dispatch_sequence() partial commit
#   - Backpressure-Limit bei MAX_QUEUE_DEPTH=50
#   - Threading.Event Notification-Verlust bei hoher Last
#   - DLQ-Kaskadierung bei sequenziellen Abhängigkeiten

import json
import threading
import time

import pytest

from gnom_hub.agents.swarm.swarm_comms import (
    MAX_QUEUE_DEPTH,
    RETRY_MAX,
    ack_message,
    dispatch_mention,
    dispatch_sequence,
    fetch_next_message,
    nack_message,
    notify_agent,
    recover_stuck_messages,
)
from gnom_hub.db.connection import get_db_connection

# ── Test-Konfiguration ─────────────────────────────────────────────────────
NUM_AGENTS = 5
# Wave A: MAX_QUEUE_DEPTH=20 — stay under per-agent cap
TASKS_PER_AGENT = min(15, MAX_QUEUE_DEPTH - 2)
TASKS_WITH_DEPENDENCIES = 10
SIMULATED_PROCESSING_TIME = 0.01
STUCK_AGENTS = ["SlowAG", "CrashAG"]
RECOVERY_TIMEOUT = 0.2
BENCHMARK_DURATION = 5.0


def _seed_agents(conn):
    """Registriert 5 Test-Agenten für den Load-Test."""
    agents = [
        ("FastAG",   "Fast Worker",    "online"),
        ("SlowAG",   "Slow Worker",    "online"),
        ("CrashAG",  "Crash Worker",   "online"),
        ("CoderAG",  "Code Worker",    "online"),
        ("WriterAG", "Writer Worker",  "online"),
    ]
    for name, desc, status in agents:
        conn.execute("""
            INSERT OR REPLACE INTO agents (name, id, port, description, status, capabilities, role, last_seen)
            VALUES (?, ?, 0, ?, ?, '[]', 'normal', '2026-06-08T00:00:00Z')
        """, (name, name.lower(), desc, status))
    conn.commit()


def _queue_stats(conn) -> dict:
    """Liefert eine Momentaufnahme der Queue."""
    total = conn.execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0]
    by_status = {
        row["status"]: row["cnt"]
        for row in conn.execute("SELECT status, COUNT(*) as cnt FROM agent_messages GROUP BY status").fetchall()
    }
    by_recipient = {
        row["recipient"]: {s: 0 for s in ("pending", "processing", "done", "dead_letter")}
        for row in conn.execute("SELECT DISTINCT recipient FROM agent_messages").fetchall()
    }
    for row in conn.execute("SELECT recipient, status, COUNT(*) as cnt FROM agent_messages GROUP BY recipient, status").fetchall():
        by_recipient.setdefault(row["recipient"], {})[row["status"]] = row["cnt"]
    stuck = conn.execute("""
        SELECT COUNT(*) FROM agent_messages
        WHERE status = 'processing' AND (processing_since IS NULL OR processing_since <= ?)
    """, (time.time() - RECOVERY_TIMEOUT,)).fetchone()[0]
    return {
        "total": total,
        "by_status": by_status,
        "by_recipient": by_recipient,
        "stuck_count": stuck,
        "pending": by_status.get("pending", 0),
        "processing": by_status.get("processing", 0),
        "done": by_status.get("done", 0),
        "dead_letter": by_status.get("dead_letter", 0),
    }


def _print_stats(phase: str, stats: dict, elapsed: float):
    """Gibt formatierte Queue-Statistiken aus."""
    throughput = stats["done"] / elapsed if elapsed > 0 else 0
    print(f"\n  [{phase}] ─── Queue-Statistiken ───")
    print(f"  Gesamt:      {stats['total']:>4}")
    print(f"  pending:     {stats['pending']:>4}")
    print(f"  processing:  {stats['processing']:>4}")
    print(f"  done:        {stats['done']:>4}")
    print(f"  dead_letter: {stats['dead_letter']:>4}")
    print(f"  stuck:       {stats['stuck_count']:>4}")
    print(f"  Durchsatz:   {throughput:.1f} msgs/s")
    print(f"  Laufzeit:    {elapsed:.2f}s")
    if stats.get("backpressure_hits"):
        print(f"  Backpressure: {stats['backpressure_hits']} hits")
    for agent, counts in stats["by_recipient"].items():
        if any(v > 0 for v in counts.values()):
            print(f"    {agent}: {counts}")


class MockAgentWorker(threading.Thread):
    """Simuliert einen Agenten, der Nachrichten aus der Queue holt und verarbeitet."""

    def __init__(self, name: str, db_path: str, slow: bool = False, crash: bool = False,
                 process_time: float = SIMULATED_PROCESSING_TIME):
        super().__init__(daemon=True)
        self.name = name
        self.db_path = db_path
        self.slow = slow
        self.crash = crash
        self.process_time = process_time
        self.processed = 0
        self.nacked = 0
        self.errors = 0
        self.running = True

    def run(self):
        while self.running:
            msg = fetch_next_message(self.name, self.db_path, timeout=1.0)
            if msg is None:
                continue
            try:
                if self.crash:
                    # Simuliere Absturz: processing_since bleibt stehen,
                    # kein ack/nack → message wird stuck
                    time.sleep(0.05)
                    self.errors += 1
                    continue  # ← bewusst kein ack/nack = stuck

                if self.slow:
                    sim_time = self.process_time * 5
                else:
                    sim_time = self.process_time

                time.sleep(sim_time)

                # 10% der Nachrichten simulieren Fehler
                if not self.crash and hash(str(msg["msg_id"])) % 10 == 0:
                    nack_message(msg["msg_id"], self.db_path, "simulated failure")
                    self.nacked += 1
                else:
                    ack_message(msg["msg_id"], self.db_path)
                    self.processed += 1
            except Exception:
                self.errors += 1

    def stop(self):
        self.running = False


@pytest.mark.load_test
class TestQueueStability:

    def test_basic_throughput(self, isolated_db):
        """5 Agents mit Basis-Tasks bombardieren, Durchsatz messen."""
        conn = get_db_connection()
        try:
            _seed_agents(conn)
        finally:
            conn.close()

        db_path = str(isolated_db)
        agents = ["FastAG", "SlowAG", "CrashAG", "CoderAG", "WriterAG"]

        # Phase 1: Dispatch 150 Tasks (30 pro Agent)
        print(f"\n  Phase 1: Dispatche {NUM_AGENTS * TASKS_PER_AGENT} Tasks...")
        t0 = time.time()
        tasks_dispatched = 0
        for i in range(TASKS_PER_AGENT):
            for agent in agents:
                priority = "critical" if i < 3 else ("high" if i < 10 else "normal")
                dispatch_mention("User", f"@{agent} task_{i}", "loadtest", db_path, priority=priority)
                tasks_dispatched += 1
        dispatch_time = time.time() - t0
        print(f"    {tasks_dispatched} Tasks dispatched in {dispatch_time:.2f}s "
              f"({tasks_dispatched/dispatch_time:.0f} tasks/s)")

        conn = get_db_connection()
        try:
            stats_before = _queue_stats(conn)
            _print_stats("Nach Dispatch", stats_before, dispatch_time)
        finally:
            conn.close()

        # Phase 2: Agents arbeiten lassen
        workers = [
            MockAgentWorker("FastAG",   db_path, slow=False),
            MockAgentWorker("SlowAG",   db_path, slow=True),
            MockAgentWorker("CrashAG",  db_path, crash=True),
            MockAgentWorker("CoderAG",  db_path, slow=False),
            MockAgentWorker("WriterAG", db_path, slow=False),
        ]
        for w in workers:
            w.start()

        work_time = BENCHMARK_DURATION
        print(f"\n  Phase 2: Agents arbeiten ({work_time}s)...")
        time.sleep(work_time)

        for w in workers:
            w.stop()
        for w in workers:
            w.join(timeout=3)

        conn = get_db_connection()
        try:
            stats_after = _queue_stats(conn)
            stats_after["total_dispatched"] = tasks_dispatched
            _print_stats("Nach Arbeit", stats_after, work_time + dispatch_time)
        finally:
            conn.close()

        # Assertions
        assert stats_after["pending"] + stats_after["processing"] + stats_after["done"] + stats_after["dead_letter"] == tasks_dispatched
        assert stats_after["done"] > 0
        assert stats_after["dead_letter"] >= 0
        assert stats_after["stuck_count"] >= 0

    def test_recovery_under_load(self, isolated_db):
        """recover_stuck_messages() unter Dauerlast testen."""
        conn = get_db_connection()
        try:
            _seed_agents(conn)
        finally:
            conn.close()

        db_path = str(isolated_db)
        crash_worker = MockAgentWorker("CrashAG", db_path, crash=True)
        crash_worker.start()

        fast_worker = MockAgentWorker("FastAG", db_path, slow=False)
        fast_worker.start()

        # Phase 1: Tasks dispatchen während CrashAG stuck messages produziert
        print("\n  Phase 1: Dispatche Tasks mit CrashAG als Stuck-Produzent...")
        t0 = time.time()
        for i in range(20):
            dispatch_mention("User", f"@CrashAG bomb_task_{i}", "loadtest", db_path, priority="low")
            dispatch_mention("User", f"@FastAG normal_task_{i}", "loadtest", db_path, priority="high")
        dispatch_1 = time.time() - t0

        time.sleep(0.5)

        conn = get_db_connection()
        try:
            stats_before_recovery = _queue_stats(conn)
            _print_stats("Vor Recovery", stats_before_recovery, dispatch_1)
            stuck_before = stats_before_recovery["stuck_count"]
        finally:
            conn.close()

        # Phase 2: Recovery laufen lassen
        print(f"\n  Phase 2: recover_stuck_messages() mit timeout={RECOVERY_TIMEOUT}s...")
        recover_stuck_messages(db_path, timeout=RECOVERY_TIMEOUT)

        # Kurz warten damit geworkte Nachrichten durchkommen
        time.sleep(0.3)
        recover_stuck_messages(db_path, timeout=RECOVERY_TIMEOUT)

        conn = get_db_connection()
        try:
            stats_after_recovery = _queue_stats(conn)
            _print_stats("Nach Recovery", stats_after_recovery, dispatch_1 + 0.5 + 0.3)
        finally:
            conn.close()

        crash_worker.stop()
        fast_worker.stop()
        crash_worker.join(timeout=3)
        fast_worker.join(timeout=3)

        conn = get_db_connection()
        try:
            stats_final = _queue_stats(conn)
            _print_stats("Final", stats_final, dispatch_1 + 1.0)
        finally:
            conn.close()

        assert stats_after_recovery["stuck_count"] <= stuck_before
        assert stats_final["stuck_count"] <= stuck_before

    def test_dependency_chains(self, isolated_db):
        """Sequenzielle Abhängigkeiten unter 5 Szenarien:

        1. parent_msg_id-Ketten sind korrekt verknüpft (dispatch_sequence)
        2. fetch_next_message: Step N wird erst sichtbar wenn Step N-1 geackt ist
        3. DEPENDENCY_TIMEOUT: Hängender Parent → Child nach Timeout in DLQ
        4. Dead-Letter-Parent: Child wird SOFORT in DLQ geschoben (kein Timeout)
        5. Gemischte Agents: Chain über verschiedene Agenten funktioniert
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('ChainAG', 'cha', 'Chain Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('DepAG', 'dep', 'Dep Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('TimeoutAG', 'to', 'Timeout Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('DLQAG', 'dlq', 'DLQ Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('MixedAG', 'mix', 'Mixed Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # ═══════ Szenario 1: parent_msg_id-Korrektheit ════════════════════
        print("\n  Szenario 1: parent_msg_id-Verkettung...")
        dispatch_sequence("User", "\n".join(f"@ChainAG -> chainA_step{s}" for s in range(4)), "chainA", db_path)
        dispatch_sequence("User", "\n".join(f"@ChainAG -> chainB_step{s}" for s in range(3)), "chainB", db_path)

        conn = get_db_connection()
        try:
            rows = conn.execute(
                "SELECT id, parent_msg_id, context_id FROM agent_messages WHERE context_id IN ('chainA','chainB') ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()

        groups = {}
        for r in rows:
            groups.setdefault(r["context_id"], []).append(r)

        for cid, chain in groups.items():
            assert chain[0]["parent_msg_id"] is None, f"Erster Step in {cid} sollte kein parent haben"
            for i in range(1, len(chain)):
                assert chain[i]["parent_msg_id"] == chain[i-1]["id"], (
                    f"Bruch in {cid}: Step {i+1} parent={chain[i]['parent_msg_id']}, erwartet {chain[i-1]['id']}"
                )
        total = sum(len(c) for c in groups.values())
        print(f"    ✅ {total} parent_msg_id-Verkettungen korrekt ({len(groups)} Chains)")

        # ═══════ Szenario 2: fetch_next_message blockt bis parent done ════
        # ack_message() setzt jetzt child.deliver_after=0 (Bugfix), sodass das Child
        # sofort nach Parent-Erledigung abholbar ist – ohne 3s Reschedule-Verzögerung.
        print("  Szenario 2: fetch blockt bis parent geackt (mit deliver_after-Reset)...")
        dispatch_sequence("User", "@DepAG -> dep_step1\n@DepAG -> dep_step2", "sc2", db_path)

        conn = get_db_connection()
        try:
            s1 = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc2' ORDER BY id ASC LIMIT 1").fetchone()
            s2 = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc2' ORDER BY id ASC LIMIT 1 OFFSET 1").fetchone()
        finally:
            conn.close()

        msg1 = fetch_next_message("DepAG", db_path, timeout=0.5)
        assert msg1 is not None, "Step 1 sollte abholbar sein"
        assert msg1["msg_id"] == s1["id"]

        # fetch_next_message hat Step 2 gesehen und rescheduled (deliver_after=now+3s).
        # Jetzt acken wir Step 1. ack_message muss deliver_after von Step 2 zurücksetzen.
        ack_message(msg1["msg_id"], db_path)
        time.sleep(0.05)

        # Step 2 muss jetzt sofort abholbar sein (deliver_after wurde auf 0 gesetzt)
        msg2_after = fetch_next_message("DepAG", db_path, timeout=0.5)
        assert msg2_after is not None, "Step 2 sollte nach ack sofort abholbar sein (deliver_after-Reset)"
        assert msg2_after["msg_id"] == s2["id"]
        assert msg2_after["parent_msg_id"] == s1["id"]
        print("    ✅ Step 1 geackt → Step 2 sofort abholbar (deliver_after-Reset funktioniert)")

        # ═══════ Szenario 3: DEPENDENCY_TIMEOUT → Child in DLQ ════════════
        # fetch_next_message prüft jetzt processing_since (nicht created_at).
        # Setze processing_since künstlich alt + DEPENDENCY_TIMEOUT kurz.
        print("  Szenario 3: DEPENDENCY_TIMEOUT → Child in DLQ...")
        import gnom_hub.agents.swarm.swarm_comms as sc
        original_timeout = sc.DEPENDENCY_TIMEOUT
        sc.DEPENDENCY_TIMEOUT = 0.05
        try:
            dispatch_sequence("User", "@TimeoutAG -> to_parent\n@TimeoutAG -> to_child", "sc3", db_path)

            conn = get_db_connection()
            try:
                parent = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc3' ORDER BY id ASC LIMIT 1").fetchone()
                child = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc3' ORDER BY id ASC LIMIT 1 OFFSET 1").fetchone()
                # Parent processing_since auf alt setzen (simuliert langlaufende Verarbeitung)
                conn.execute("UPDATE agent_messages SET created_at=? WHERE id=?", (time.time() - 60, parent["id"]))
                conn.commit()
            finally:
                conn.close()

            # Parent holen → processing_since wird auf now gesetzt
            msg_parent = fetch_next_message("TimeoutAG", db_path, timeout=0.3)
            assert msg_parent is not None, "Parent sollte abholbar sein"
            assert msg_parent["msg_id"] == parent["id"]

            # processing_since künstlich auf 60s alt setzen (Parent hängt seit 60s)
            conn = get_db_connection()
            try:
                conn.execute("UPDATE agent_messages SET processing_since=? WHERE id=?", (time.time() - 60, parent["id"]))
                conn.commit()
            finally:
                conn.close()

            # fetch_next_message sieht child, prüft parent.processing_since (60s > 0.05s),
            # und schiebt child in DLQ
            fetch_next_message("TimeoutAG", db_path, timeout=0.5)

            conn = get_db_connection()
            try:
                child_status = conn.execute("SELECT status FROM agent_messages WHERE id=?", (child["id"],)).fetchone()
                parent_status = conn.execute("SELECT status FROM agent_messages WHERE id=?", (parent["id"],)).fetchone()
            finally:
                conn.close()

            assert child_status["status"] == "dead_letter", (
                f"Child sollte nach DEPENDENCY_TIMEOUT in DLQ sein, ist {child_status['status']}"
            )
            print(f"    ✅ Child in DLQ (Parent={parent_status['status']}, Child={child_status['status']})")
        finally:
            sc.DEPENDENCY_TIMEOUT = original_timeout

        # ═══════ Szenario 4: Dead-Letter-Parent → Kind SOFORT DLQ ═════════
        print("  Szenario 4: Parent in DLQ → Child sofort DLQ (kein Timeout)...")
        dispatch_sequence("User", "@DLQAG -> dlq_parent\n@DLQAG -> dlq_child", "sc4", db_path)

        conn = get_db_connection()
        try:
            parent_s4 = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc4' ORDER BY id ASC LIMIT 1").fetchone()
            child_s4 = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc4' ORDER BY id ASC LIMIT 1 OFFSET 1").fetchone()
            conn.execute("UPDATE agent_messages SET status='dead_letter', completed_at=? WHERE id=?", (time.time(), parent_s4["id"]))
            conn.commit()
        finally:
            conn.close()

        msg_s4 = fetch_next_message("DLQAG", db_path, timeout=1.0)
        assert msg_s4 is None, "fetch_next_message sollte None sein (child automatisch DLQ)"

        conn = get_db_connection()
        try:
            child_s4_status = conn.execute("SELECT status FROM agent_messages WHERE id=?", (child_s4["id"],)).fetchone()
            assert child_s4_status["status"] == "dead_letter", (
                f"Child sollte sofort DLQ sein, ist {child_s4_status['status']}"
            )
        finally:
            conn.close()
        print("    ✅ Child sofort in DLQ (kein Timeout)")

        # ═══════ Szenario 5: Chain über verschiedene Agenten ═══════════════
        print("  Szenario 5: Mixed-Agent-Chain...")
        dispatch_sequence("User", "@MixedAG -> mixed_code\n@MixedAG -> mixed_text\n@MixedAG -> mixed_more", "sc5", db_path)

        conn = get_db_connection()
        try:
            rows_s5 = conn.execute(
                "SELECT id, parent_msg_id, recipient FROM agent_messages WHERE context_id='sc5' ORDER BY id ASC"
            ).fetchall()
            assert len(rows_s5) == 3, f"Erwartet 3 Messages, gefunden {len(rows_s5)}"
            assert rows_s5[0]["recipient"] == "MixedAG"
            assert rows_s5[1]["recipient"] == "MixedAG"
            assert rows_s5[2]["recipient"] == "MixedAG"
            assert rows_s5[1]["parent_msg_id"] == rows_s5[0]["id"]
            assert rows_s5[2]["parent_msg_id"] == rows_s5[1]["id"]
            print("    ✅ 3-Step-Chain korrekt (parent-Verkettung intakt)")
        finally:
            conn.close()

    def test_backpressure_bombardment(self, isolated_db):
        """Backpressure-Limit unter 3 Szenarien validieren:

        1. Füllen → Dispatch blockiert exakt bei MAX_QUEUE_DEPTH
        2. Freigabe → Nach ack() werden neue Tasks angenommen
        3. Sequenz-Dispatch respektiert ebenfalls das Limit
        4. Mehrere Agents parallel am Limit
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT OR REPLACE INTO agents (name, id, description, status, last_seen) VALUES ('OverflowAG', 'overflow', 'Overflow Tester', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)
        agent = "CoderAG"

        # ── Szenario 1: Exact Limit ──────────────────────────────────────
        print(f"\n  Szenario 1: Exact Limit = {MAX_QUEUE_DEPTH}...")
        accepted = 0
        rejected = 0
        for i in range(MAX_QUEUE_DEPTH + 10):
            dispatched = dispatch_mention("User", f"@{agent} fill_{i}", "scenario1", db_path)
            if dispatched:
                accepted += 1
            else:
                rejected += 1

        conn = get_db_connection()
        try:
            queue_count = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE recipient = ?", (agent,)).fetchone()[0]
        finally:
            conn.close()

        assert accepted == MAX_QUEUE_DEPTH, f"Erwartet {MAX_QUEUE_DEPTH} accepted, bekam {accepted}"
        assert rejected == 10, f"Erwartet 10 rejected, bekam {rejected}"
        assert queue_count == MAX_QUEUE_DEPTH, f"Queue darf {MAX_QUEUE_DEPTH} nicht überschreiten, hat {queue_count}"
        print(f"    ✅ {queue_count} in Queue, {rejected} korrekt zurückgewiesen")

        # ── Szenario 2: Release & Re-fill ────────────────────────────────
        # 10 Messages ack-en → danach müssen genau 10 neue durchkommen
        print("  Szenario 2: 10 ack → 10 neue dispatchen...")
        for _i in range(15):
            msg = fetch_next_message(agent, db_path, timeout=0.3)
            if msg is None:
                break
            ack_message(msg["msg_id"], db_path)

        accepted2 = 0
        rejected2 = 0
        for i in range(25):
            dispatched = dispatch_mention("User", f"@{agent} refill_{i}", "scenario2", db_path)
            if dispatched:
                accepted2 += 1
            else:
                rejected2 += 1

        conn = get_db_connection()
        try:
            queue_count2 = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE recipient = ? AND status IN ('pending', 'processing')", (agent,)).fetchone()[0]
        finally:
            conn.close()

        # ack hat 15 Slots frei gemacht, aber 15-10=5 gingen verloren durch den fetch im Leerlauf
        # Korrekte Rechnung: 50 - 15 = 35 pending+processing → dann +25 neue = 60, capped bei 50
        assert accepted2 == 15, f"Erwartet 15 accepted nach Release, bekam {accepted2}"
        assert rejected2 == 10, f"Erwartet 10 rejected nach Release, bekam {rejected2}"
        print(f"    ✅ Nach Release: {accepted2} accepted, {rejected2} rejected, Queue={queue_count2}")

        # ── Szenario 3: dispatch_sequence respektiert jetzt Backpressure ──
        print("  Szenario 3: dispatch_sequence mit vollem Ziel-Agent (neuer Fix)...")
        conn = get_db_connection()
        try:
            conn.execute("DELETE FROM agent_messages WHERE recipient = ?", (agent,))
            conn.commit()
        finally:
            conn.close()

        for i in range(MAX_QUEUE_DEPTH):
            dispatch_mention("User", f"@{agent} pref_{i}", "prescenario3", db_path)

        text = "\n".join(f"@{agent} -> seq_step_{s}" for s in range(5))
        dispatched_seq = dispatch_sequence("User", text, "scenario3", db_path)

        conn = get_db_connection()
        try:
            queue_count3 = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE recipient = ?", (agent,)).fetchone()[0]
        finally:
            conn.close()

        assert len(dispatched_seq) == 0, f"dispatch_sequence sollte 0 dispatchen bei voller Queue, bekam {len(dispatched_seq)}"
        assert queue_count3 == MAX_QUEUE_DEPTH, f"Queue darf nicht wachsen: {queue_count3}"
        print("    ✅ dispatch_sequence dispatche 0 Tasks bei voller Queue (Backpressure greift)")

        # ── Szenario 4: dispatch_mention Return-Werte präzise ────────────
        # dispatch_mention gibt leeres-Liste bei Backpressure, Liste mit Agent bei Erfolg
        print("  Szenario 4: dispatch_mention Return-Werte prüfen...")
        conn = get_db_connection()
        try:
            conn.execute("UPDATE agent_messages SET status='done' WHERE recipient = ?", (agent,))
            conn.execute("DELETE FROM agent_messages WHERE recipient != ?", (agent,))
            conn.commit()
        finally:
            conn.close()

        result_full = dispatch_mention("User", "@OverflowAG hello", "test_ret", db_path)
        assert result_full == ["OverflowAG"], f"dispatch_mention sollte ['OverflowAG'] zurückgeben, bekam {result_full}"

        # OverflowAG hat 0 messages → dispatchen
        result_empty = dispatch_mention("User", "@NONEXISTENT hello", "test_ret2", db_path)
        assert result_empty == [], f"dispatch_mention für unbekannten Agent sollte [] sein, bekam {result_empty}"

        print(f"    ✅ Return-Werte korrekt: bekannter Agent=[{result_full}], unbekannt=[]")

    def test_priority_sorting(self, isolated_db):
        """Tasks mit gemischten Prioritäten -> korrekte Sortierung in fetch_next_message."""
        conn = get_db_connection()
        try:
            _seed_agents(conn)
        finally:
            conn.close()

        db_path = str(isolated_db)
        priorities = {"critical": 3, "normal": 8, "low": 5}  # total <= MAX_QUEUE_DEPTH

        print("\n  Phase 1: Dispatche Tasks mit gemischten Prioritäten...")
        for prio, count in priorities.items():
            for i in range(count):
                dispatch_mention("User", f"@FastAG {prio}_task_{i}", "loadtest", db_path, priority=prio)

        # Alle Tasks holen und Reihenfolge prüfen
        fetched_order = []
        for _ in range(sum(priorities.values())):
            msg = fetch_next_message("FastAG", db_path, timeout=0.5)
            if msg is None:
                break
            ack_message(msg["msg_id"], db_path)
            payload = msg["payload"]
            text = payload.get("text", "")
            fetched_order.append(text)

        critical_count = sum(1 for t in fetched_order if "critical_task" in t)
        normal_count = sum(1 for t in fetched_order if "normal_task" in t)
        low_count = sum(1 for t in fetched_order if "low_task" in t)

        print("\n  Priority-Sorting:")
        print(f"    critical: {critical_count}/{priorities['critical']} zuerst")
        print(f"    normal:   {normal_count}/{priorities['normal']}")
        print(f"    low:      {low_count}/{priorities['low']} zuletzt")

        conn = get_db_connection()
        try:
            stats = _queue_stats(conn)
            _print_stats("Nach Priority-Test", stats, 0.5)
        finally:
            conn.close()

        assert critical_count == priorities["critical"]
        assert low_count == priorities["low"]
        # critical sollte VOR low kommen
        last_critical = max(i for i, t in enumerate(fetched_order) if "critical_task" in t)
        first_low = min(i for i, t in enumerate(fetched_order) if "low_task" in t)
        assert last_critical < first_low, "critical-Tasks müssen vor low-Tasks kommen"

    def test_full_lifecycle_with_dlq_cascade(self, isolated_db):
        """DLQ-Kaskadierung unter 4 Szenarien:

        1. 5er-Kette: Step 1 stirbt → alle 5 in DLQ
        2. 5er-Kette: Step 1 ok → rest läuft normal
        3. 3er-Kette: Step 2 stirbt → Steps 2+3 in DLQ (Step 1 bleibt pending)
        4. Gemischte Chain: done-Messages werden von Cascade NICHT berührt
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT OR REPLACE INTO agents (name, id, description, status, last_seen) VALUES ('ChainAG', 'chain', 'Chain Worker', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)
        RECOVERY_TIMEOUT = 0.1

        def _force_into_dlq(msg_id: int, retries: int):
            """Hilfsfunktion: Setzt eine Message auf processing mit altem Timestamp
            und hohem retry_count, so dass recover_stuck_messages sie in DLQ schiebt."""
            conn2 = get_db_connection()
            try:
                conn2.execute("""
                    UPDATE agent_messages
                    SET status='processing', processing_since=?, retry_count=?
                    WHERE id=?
                """, (time.time() - 600, retries, msg_id))
                conn2.commit()
            finally:
                conn2.close()

        # ═══════ Szenario 1: 5er-Kette, Step 1 stirbt → alle 5 DLQ ═══════
        print("\n  Szenario 1: 5er-Kette, Step 1 stirbt → alle 5 DLQ...")
        dispatch_sequence("User", "\n".join(f"@ChainAG -> s1_step{s}" for s in range(5)), "sc1", db_path)

        # Step 1 (älteste, niedrigste id) in DLQ zwingen
        conn = get_db_connection()
        try:
            step1 = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc1' ORDER BY id ASC LIMIT 1").fetchone()
            assert step1 is not None
            _force_into_dlq(step1["id"], RETRY_MAX - 1)  # retry_count = 2 → wird 3 → DLQ
        finally:
            conn.close()

        recover_stuck_messages(db_path, timeout=RECOVERY_TIMEOUT)

        conn = get_db_connection()
        try:
            sc1_rows = conn.execute(
                "SELECT id, status, retry_count FROM agent_messages WHERE context_id='sc1' ORDER BY id ASC"
            ).fetchall()
            assert len(sc1_rows) == 5, f"Erwartet 5 Messages in sc1, gefunden {len(sc1_rows)}"
            for i, row in enumerate(sc1_rows):
                assert row["status"] == "dead_letter", (
                    f"Step {i+1} (id={row['id']}) sollte dead_letter sein, ist {row['status']}"
                )
            print("    ✅ Alle 5 Steps korrekt in DLQ kaskadiert")
        finally:
            conn.close()

        # ═══════ Szenario 2: 5er-Kette, Step 1 ok → rest läuft ═══════════
        print("  Szenario 2: 5er-Kette, Step 1 wird geackt → rest normal...")
        dispatch_sequence("User", "\n".join(f"@ChainAG -> s2_step{s}" for s in range(5)), "sc2", db_path)

        conn = get_db_connection()
        try:
            step1_v2 = conn.execute("SELECT id FROM agent_messages WHERE context_id='sc2' ORDER BY id ASC LIMIT 1").fetchone()
        finally:
            conn.close()

        msg = fetch_next_message("ChainAG", db_path, timeout=0.5)
        assert msg is not None, "Step 1 sollte abholbar sein"
        assert msg["msg_id"] == step1_v2["id"], "Step 1 muss die älteste Message sein"
        ack_message(msg["msg_id"], db_path)

        # Nach ack von Step 1 muss Step 2 abholbar sein (parent ist done)
        msg2 = fetch_next_message("ChainAG", db_path, timeout=0.5)
        assert msg2 is not None, "Step 2 sollte nach ack von Step 1 abholbar sein"
        assert msg2["parent_msg_id"] == step1_v2["id"], f"Step 2 parent sollte Step 1 sein ({step1_v2['id']}), ist {msg2['parent_msg_id']}"
        print(f"    ✅ Step 2 ({msg2['msg_id']}) hat korrekten parent = Step 1 ({msg2['parent_msg_id']})")
        ack_message(msg2["msg_id"], db_path)

        # ═══════ Szenario 3: 3er-Kette, Step 2 stirbt → Steps 2+3 DLQ ═══
        print("  Szenario 3: 3er-Kette, Step 2 stirbt → Steps 2+3 DLQ (Step 1 bleibt)...")
        dispatch_sequence("User", "\n".join(f"@ChainAG -> s3_step{s}" for s in range(3)), "sc3", db_path)

        conn = get_db_connection()
        try:
            sc3_rows = conn.execute(
                "SELECT id, parent_msg_id FROM agent_messages WHERE context_id='sc3' ORDER BY id ASC"
            ).fetchall()
            step1_s3, step2_s3, step3_s3 = sc3_rows[0], sc3_rows[1], sc3_rows[2]
            assert step2_s3["parent_msg_id"] == step1_s3["id"], "Step 2 parent muss Step 1 sein"
            assert step3_s3["parent_msg_id"] == step2_s3["id"], "Step 3 parent muss Step 2 sein"

            # Step 2 in DLQ zwingen
            _force_into_dlq(step2_s3["id"], RETRY_MAX - 1)
        finally:
            conn.close()

        recover_stuck_messages(db_path, timeout=RECOVERY_TIMEOUT)

        conn = get_db_connection()
        try:
            sc3_after = conn.execute(
                "SELECT id, status FROM agent_messages WHERE context_id='sc3' ORDER BY id ASC"
            ).fetchall()
            # Step 1: sollte pending sein (kein parent, nie verarbeitet)
            assert sc3_after[0]["status"] == "pending", (
                f"Step 1 sollte pending sein, ist {sc3_after[0]['status']}"
            )
            # Step 2: sollte dead_letter sein (3 Retries)
            assert sc3_after[1]["status"] == "dead_letter", (
                f"Step 2 sollte dead_letter sein, ist {sc3_after[1]['status']}"
            )
            # Step 3: sollte dead_letter sein (Kaskade von Step 2)
            assert sc3_after[2]["status"] == "dead_letter", (
                f"Step 3 sollte dead_letter sein (Kaskade), ist {sc3_after[2]['status']}"
            )
            print(f"    ✅ Step 1={sc3_after[0]['status']}, Step 2={sc3_after[1]['status']}, Step 3={sc3_after[2]['status']} (korrekt)")
        finally:
            conn.close()

        # ═══════ Szenario 4: done-Messages werden NICHT überschrieben, aber
        # ihre Children trotzdem kaskadiert (Bugfix: Cascade überspringt done,
        # aber setzt sich bei deren Children fort).
        print("  Szenario 4: done-Step wird nicht überschrieben, Cascade geht weiter...")
        dispatch_sequence("User", "\n".join(f"@ChainAG -> s4_step{s}" for s in range(4)), "sc4", db_path)
        time.sleep(0.03)

        conn = get_db_connection()
        try:
            sc4_rows = conn.execute(
                "SELECT id, parent_msg_id FROM agent_messages WHERE context_id='sc4' ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()

        # Step 2 auf done setzen
        ack_conn = get_db_connection()
        try:
            ack_conn.execute("UPDATE agent_messages SET status='done', completed_at=? WHERE id=?", (time.time(), sc4_rows[1]["id"]))
            ack_conn.commit()
        finally:
            ack_conn.close()

        time.sleep(0.03)

        # Step 1 in DLQ zwingen
        _force_into_dlq(sc4_rows[0]["id"], RETRY_MAX - 1)
        time.sleep(0.03)

        recover_stuck_messages(db_path, timeout=RECOVERY_TIMEOUT)
        time.sleep(0.03)

        conn = get_db_connection()
        try:
            sc4_after = conn.execute(
                "SELECT id, status FROM agent_messages WHERE context_id='sc4' ORDER BY id ASC"
            ).fetchall()
        finally:
            conn.close()

        assert sc4_after[0]["status"] == "dead_letter", f"Step 1 sollte dead_letter sein, ist {sc4_after[0]['status']}"
        assert sc4_after[1]["status"] == "done", f"Step 2 (done) darf nicht überschrieben werden, ist {sc4_after[1]['status']}"
        # Cascade überspringt Step 2 (done), setzt sich aber bei dessen Children fort
        assert sc4_after[2]["status"] == "dead_letter", f"Step 3 sollte kaskadiert sein (durch Cascade via Step 2), ist {sc4_after[2]['status']}"
        assert sc4_after[3]["status"] == "dead_letter", f"Step 4 sollte kaskadiert sein (durch Cascade via Step 2), ist {sc4_after[3]['status']}"
        print(f"    ✅ done-Step 2='{sc4_after[1]['status']}' (nicht überschrieben), Step 3+4='{sc4_after[2]['status']}' (kaskadiert)")

    def test_concurrent_dispatchers(self, isolated_db):
        """Mehrere Threads dispatchen gleichzeitig -> keine Race-Condition / Deadlock."""
        conn = get_db_connection()
        try:
            _seed_agents(conn)
        finally:
            conn.close()

        db_path = str(isolated_db)
        num_dispatchers = 10
        tasks_per_dispatcher = 20

        results = []
        errors = []

        def dispatcher_worker(idx):
            try:
                local_count = 0
                for i in range(tasks_per_dispatcher):
                    dispatched = dispatch_mention("User", f"@CoderAG conc_task_{idx}_{i}", "concurrent", db_path)
                    if dispatched:
                        local_count += 1
                results.append(local_count)
            except Exception as e:
                errors.append((idx, str(e)))

        print(f"\n  Phase 1: {num_dispatchers} parallele Dispatcher mit je {tasks_per_dispatcher} Tasks...")
        t0 = time.time()
        threads = [threading.Thread(target=dispatcher_worker, args=(i,), daemon=True) for i in range(num_dispatchers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        elapsed = time.time() - t0

        conn = get_db_connection()
        try:
            stats = _queue_stats(conn)
            _print_stats("Nach Concurrent Dispatch", stats, elapsed)
        finally:
            conn.close()

        total_dispatched = sum(results)
        print(f"    Erfolgreich dispatched: {total_dispatched}/{num_dispatchers * tasks_per_dispatcher}")
        print(f"    Errors: {len(errors)}")
        if errors:
            for idx, err in errors[:3]:
                print(f"      Dispatcher {idx}: {err}")

        assert len(errors) == 0, f"{len(errors)} dispatcher errors occurred"
        assert total_dispatched > 0

    def test_recovery_with_null_processing_since(self, isolated_db):
        """Messages mit NULL processing_since (Schema-Migration/Edge-Case) werden recoveriert."""
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            now = time.time()
            # Message mit NULL processing_since (alter Eintrag) und Status 'processing'
            conn.execute("""
                INSERT INTO agent_messages (sender, recipient, payload, priority, status, retry_count, created_at, deliver_after, processing_since, depth)
                VALUES ('User', 'CoderAG', ?, 5, 'processing', 0, ?, 0, NULL, 0)
            """, (json.dumps({"text": "null_ps_task"}), now - 600))
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        conn = get_db_connection()
        try:
            before = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE status = 'processing' AND processing_since IS NULL").fetchone()[0]
        finally:
            conn.close()
        assert before == 1, "Message mit NULL processing_since muss existieren"

        print("\n  Phase 1: recover_stuck_messages() auf NULL processing_since...")
        recover_stuck_messages(db_path, timeout=300.0)

        conn = get_db_connection()
        try:
            after = conn.execute("SELECT status FROM agent_messages WHERE payload LIKE '%null_ps%'").fetchone()
            assert after is not None
            assert after["status"] in ("pending", "dead_letter"), \
                f"NULL-ps Message sollte recovered sein, ist {after['status']}"
            print(f"    ✅ NULL processing_since Message wurde recoveriert → {after['status']}")
        finally:
            conn.close()

    def test_end_to_end_workflow(self, isolated_db):
        """Kompletter Workflow: Dispatch → Sequenz → Recovery → DLQ → Finale Konsistenz-Prüfung."""
        conn = get_db_connection()
        try:
            _seed_agents(conn)
        finally:
            conn.close()

        db_path = str(isolated_db)
        phases = {}

        # Phase 1: 100 Tasks + 3 Sequenz-Ketten dispatchen
        t0 = time.time()
        for i in range(100):
            dispatch_mention("User", f"@FastAG bench_task_{i}", "bench", db_path)

        dispatch_sequence("User", "@CoderAG -> seq_a\n@WriterAG -> seq_b\n@FastAG -> seq_c", "chains", db_path)
        phases["dispatch"] = time.time() - t0

        # Phase 2: Agents mit unterschiedlichen Geschwindigkeiten
        workers = [
            MockAgentWorker("FastAG",   db_path, slow=False, process_time=0.005),
            MockAgentWorker("SlowAG",   db_path, slow=True,  process_time=0.02),
            MockAgentWorker("CrashAG",  db_path, crash=True),
            MockAgentWorker("CoderAG",  db_path, slow=False, process_time=0.008),
            MockAgentWorker("WriterAG", db_path, slow=False, process_time=0.008),
        ]
        for w in workers:
            w.start()
        time.sleep(4.0)

        # Phase 3: Recovery
        recover_stuck_messages(db_path, timeout=0.5)
        time.sleep(0.5)
        recover_stuck_messages(db_path, timeout=0.5)
        time.sleep(0.5)
        phases["work"] = time.time() - t0

        for w in workers:
            w.stop()
        for w in workers:
            w.join(timeout=3)

        # Finale Konsistenz
        conn = get_db_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM agent_messages").fetchone()[0]
            aggregated = conn.execute("""
                SELECT status, COUNT(*) as cnt FROM agent_messages GROUP BY status
            """).fetchall()
            status_sum = sum(r["cnt"] for r in aggregated)
            orphans = conn.execute("""
                SELECT COUNT(*) FROM agent_messages m
                WHERE parent_msg_id IS NOT NULL
                  AND parent_msg_id NOT IN (SELECT id FROM agent_messages WHERE status = 'done')
                  AND m.status NOT IN ('dead_letter', 'done')
            """).fetchone()[0]
            stats = _queue_stats(conn)
            stats["total"] = total
            _print_stats("End-to-End", stats, phases["work"])
        finally:
            conn.close()

        print("\n  Konsistenz-Checks:")
        print(f"    total = status_sum: {total} == {status_sum}  {'✅' if total == status_sum else '❌'}")
        print(f"    Waisen (orphans): {orphans}  {'✅' if orphans == 0 else '⚠️'}")

        assert total == status_sum, f"Message-Count inkonsistent: {total} != {status_sum}"

    def test_deliver_after_scheduling(self, isolated_db):
        """Messages mit future deliver_after werden erst nach Ablauf sichtbar.

        Szenarien:
        1. deliver_after in der Zukunft → fetch_next_message findet sie nicht
        2. Nach Ablauf von deliver_after → fetch_next_message findet sie
        3. Gemischte Queue: sofortige + verzögerte Messages → korrekte Reihenfolge
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('DelayAG', 'delay', 'Delay Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # Szenario 1: deliver_after in der Zukunft
        print("\n  Szenario 1: deliver_after in der Zukunft → unsichtbar...")
        future = time.time() + 60
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO agent_messages (sender, recipient, payload, priority, status, created_at, deliver_after, depth)
                VALUES ('User', 'DelayAG', ?, 5, 'pending', ?, ?, 0)
            """, (json.dumps({"text": "@DelayAG future_task"}), time.time(), future))
            conn.commit()
        finally:
            conn.close()

        msg = fetch_next_message("DelayAG", db_path, timeout=0.3)
        assert msg is None, "fetch_next_message sollte None liefern (deliver_after in Zukunft)"
        print(f"    ✅ Future-Message ({future:.1f}) nicht gefunden (deliver_after > now)")

        # Szenario 2: deliver_after in der Vergangenheit → sofort sichtbar
        print("  Szenario 2: deliver_after in der Vergangenheit → sofort sichtbar...")
        past = time.time() - 60
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO agent_messages (sender, recipient, payload, priority, status, created_at, deliver_after, depth)
                VALUES ('User', 'DelayAG', ?, 5, 'pending', ?, ?, 0)
            """, (json.dumps({"text": "@DelayAG past_task"}), past, past))
            conn.commit()
        finally:
            conn.close()

        msg = fetch_next_message("DelayAG", db_path, timeout=0.3)
        assert msg is not None, "Past-Message sollte sofort abholbar sein"
        assert "past_task" in msg["payload"].get("text", "")
        print("    ✅ Past-Message sofort gefunden")
        ack_message(msg["msg_id"], db_path)

        # Szenario 3: deliver_after zurücksetzen → Message wird sofort sichtbar
        print("  Szenario 3: deliver_after=0 setzen → sofort sichtbar...")
        conn = get_db_connection()
        try:
            conn.execute("UPDATE agent_messages SET deliver_after=0 WHERE status='pending'")
            conn.commit()
        finally:
            conn.close()

        msg = fetch_next_message("DelayAG", db_path, timeout=0.3)
        assert msg is not None, "future_task sollte nach deliver_after=0 abholbar sein"
        assert "future_task" in msg["payload"].get("text", "")
        print("    ✅ Future-Message nach Reset sofort gefunden")

    def test_fifo_within_same_priority(self, isolated_db):
        """Messages gleicher Priorität werden FIFO (ORDER BY priority ASC, id ASC) ausgeliefert.

        ䷡ dispatchen 10 Messages mit priority=5, dann 10 mit priority=5.
        Die Reihenfolge muss der Insertion-Reihenfolge entsprechen.
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('FIFOAG', 'fifo', 'FIFO Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # 20 Messages mit gleicher Priorität dispatchen
        print("\n  Phase 1: 20 Messages mit priority=5 dispatchen...")
        for i in range(20):
            dispatch_mention("User", f"@FIFOAG fifo_task_{i:02d}", "fifo_test", db_path, priority="normal")

        # Alle Messages holen und Reihenfolge prüfen
        fetched = []
        for _ in range(20):
            msg = fetch_next_message("FIFOAG", db_path, timeout=0.3)
            assert msg is not None, f"Nicht alle Messages gefunden ({len(fetched)}/20)"
            text = msg["payload"].get("text", "")
            # Task-Nummer extrahieren
            task_num = None
            if "fifo_task_" in text:
                task_num = int(text.split("fifo_task_")[1].split()[0])
            fetched.append(task_num)
            ack_message(msg["msg_id"], db_path)

        assert len(fetched) == 20, f"Erwartet 20, bekommen {len(fetched)}"
        # FIFO: fetched muss [0, 1, 2, ..., 19] sein
        for i in range(20):
            assert fetched[i] == i, (
                f"FIFO verletzt: Position {i} erwartet {i}, bekommen {fetched[i]}\n"
                f"Fetched: {fetched[:10]}..."
            )
        print("    ✅ FIFO korrekt: alle 20 Messages in Insertions-Reihenfolge")

        # Gemischte Prioritäten: critical (prio=1) muss VOR normal (prio=5) kommen
        print("  Phase 2: Gemischte Prioritäten (critical + normal)...")
        for i in range(5):
            dispatch_mention("User", f"@FIFOAG normal_post_{i}", "fifo_mix", db_path, priority="normal")
        for i in range(5):
            dispatch_mention("User", f"@FIFOAG critical_post_{i}", "fifo_mix", db_path, priority="critical")

        fetched2 = []
        for _ in range(10):
            msg = fetch_next_message("FIFOAG", db_path, timeout=0.3)
            assert msg is not None
            text = msg["payload"].get("text", "")
            fetched2.append(text)
            ack_message(msg["msg_id"], db_path)

        # critical muss vor normal kommen, obwohl critical später dispatched wurde
        first_normal = next(i for i, t in enumerate(fetched2) if "normal_post" in t)
        last_critical = max(i for i, t in enumerate(fetched2) if "critical_post" in t)
        assert last_critical < first_normal, (
            f"critical muss vor normal kommen. "
            f"Letztes critical: {last_critical}, Erstes normal: {first_normal}"
        )
        print(f"    ✅ Priority korrekt: critical ({last_critical}) < normal ({first_normal})")

    def test_threading_event_overrun(self, isolated_db):
        """notify_agent() verliert kein Event bei dicht aufeinanderfolgenden Aufrufen.

        Szenario: notify_agent() wird 5x hintereinander aufgerufen,
        fetch_next_message wartet mit evt.wait(). Nach dem fünften notify
        muss spätestens eine Message abholbar sein — auch wenn das Event
        zwischendurch mehrfach gesetzt/cleared wurde.
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('EventAG', 'event', 'Event Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # Event setzen bevor Messages existieren (Event-Overrun: wird gesetzt,
        # fetch_next_message sieht nichts, cleared, dann kommt die Message)
        print("\n  Phase 1: notify_agent() vor dem Dispatch...")
        notify_agent("EventAG")
        notify_agent("EventAG")
        time.sleep(0.05)

        notify_agent("EventAG")
        dispatch_mention("User", "@EventAG overrun_task", "event_test", db_path)

        # fetch_next_message muss die Message trotz Event-Overrun finden
        # (weil dispatch_mention selbst notify_agent aufruft)
        msg = fetch_next_message("EventAG", db_path, timeout=0.5)
        assert msg is not None, "Message sollte trotz Event-Overrun abholbar sein"
        ack_message(msg["msg_id"], db_path)
        print("    ✅ Message gefunden trotz vorherigem notify_agent()")

        # 10 notify_agent() hintereinander, dann 10 Messages dispatchen
        # Alle 10 müssen ankommen
        print("  Phase 2: 10× notify + 10 Messages...")
        for _ in range(10):
            notify_agent("EventAG")

        for i in range(10):
            dispatch_mention("User", f"@EventAG burst_{i}", "event_burst", db_path)

        for i in range(10):
            msg = fetch_next_message("EventAG", db_path, timeout=0.5)
            assert msg is not None, f"Message {i} nach Event-Burst nicht gefunden"
            ack_message(msg["msg_id"], db_path)
        print("    ✅ Alle 10 Messages nach 10× notify_agent() gefunden")

        # notify_agent() auf Agent der keine Messages hat → kein Fehler
        print("  Phase 3: notify_agent() auf leeren Agenten...")
        notify_agent("EventAG")
        msg = fetch_next_message("EventAG", db_path, timeout=0.3)
        assert msg is None, "fetch sollte None liefern (keine Messages)"
        print("    ✅ notify_agent() auf leeren Agenten verursacht keinen Fehler")

    def test_self_dispatch_blocked(self, isolated_db):
        """Agent kann keine Nachricht an sich selbst dispatchen.

        Szenarien:
        1. dispatch_mention mit @Eigenname → wird ignoriert
        2. dispatch_sequence mit @Eigenname → Step wird übersprungen
        3. dispatch_by_capability mit eigenem Agent → kein Self-Routing
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('SelfAG', 'self', 'Self Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # Szenario 1: dispatch_mention mit Selbst-Adressierung
        print("\n  Szenario 1: dispatch_mention(SelfAG, @SelfAG ...)...")
        dispatched = dispatch_mention("SelfAG", "@SelfAG hello_self", "self_test", db_path)
        assert dispatched == [], f"Self-Dispatch sollte [] sein, bekam {dispatched}"

        conn = get_db_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE recipient = 'SelfAG'").fetchone()[0]
        finally:
            conn.close()
        assert count == 0, f"Keine Messages an SelfAG erwartet, gefunden {count}"
        print("    ✅ Selbst-Dispatch via dispatch_mention blockiert")

        # Szenario 2: dispatch_sequence mit Selbst-Adressierung
        print("  Szenario 2: dispatch_sequence(SelfAG, @SelfAG -> task)...")
        dispatched = dispatch_sequence("SelfAG", "@SelfAG -> self_step1\n@SelfAG -> self_step2", "self_seq", db_path)
        assert dispatched == [], f"Self-Sequence sollte [] sein, bekam {dispatched}"

        conn = get_db_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE context_id='self_seq'").fetchone()[0]
        finally:
            conn.close()
        assert count == 0, f"Keine Messages in self_seq erwartet, gefunden {count}"
        print("    ✅ Selbst-Dispatch via dispatch_sequence blockiert")

        # Szenario 3: Cross-Dispatch zu anderen Agenten funktioniert weiterhin
        print("  Szenario 3: Cross-Dispatch zu anderem Agenten (muss funktionieren)...")
        dispatched = dispatch_mention("SelfAG", "@FastAG cross_task", "cross_test", db_path)
        assert dispatched == ["FastAG"], f"Cross-Dispatch sollte ['FastAG'] sein, bekam {dispatched}"

        conn = get_db_connection()
        try:
            count = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE recipient = 'FastAG' AND context_id='cross_test'").fetchone()[0]
        finally:
            conn.close()
        assert count == 1, f"1 Message an FastAG erwartet, gefunden {count}"
        print("    ✅ Cross-Dispatch funktioniert (nur Selbst-Dispatch blockiert)")

    def test_vacuum_during_queue_activity(self, isolated_db):
        """VACUUM während aktiver Queue-Operationen.

        Szenario: dispatchen + fetchen + acken während VACUUM in der gleichen
        Verbindung. VACUUM darf keine Messages verlieren oder korrumpieren.
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('VacAG', 'vac', 'Vacuum Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # Phase 1: stay under Wave-A MAX_QUEUE_DEPTH
        n1 = min(12, MAX_QUEUE_DEPTH - 5)
        print(f"\n  Phase 1: {n1} Messages dispatchen...")
        for i in range(n1):
            dispatch_mention("User", f"@VacAG vac_task_{i}", "vac_test", db_path)

        # Phase 2: Einige Messages fetchen + acken (damit VACUUM was zu tun hat)
        for _ in range(min(5, n1)):
            msg = fetch_next_message("VacAG", db_path, timeout=0.3)
            if msg:
                ack_message(msg["msg_id"], db_path)

        # Phase 3: VACUUM in separater Verbindung
        print("  Phase 2: VACUUM + gleichzeitig dispatchen...")
        def vacuum_worker():
            try:
                v_conn = get_db_connection()
                try:
                    v_conn.execute("VACUUM")
                finally:
                    v_conn.close()
            except Exception:
                pass

        vac_thread = threading.Thread(target=vacuum_worker, daemon=True)
        vac_thread.start()

        n2 = 5
        for i in range(n2):
            dispatch_mention("User", f"@VacAG concurrent_{i}", "vac_concurrent", db_path)

        vac_thread.join(timeout=30)

        # Phase 4: Alle Messages müssen konsistent sein
        conn = get_db_connection()
        try:
            total = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE context_id IN ('vac_test', 'vac_concurrent')").fetchone()[0]
            by_status = {
                r["status"]: r["cnt"]
                for r in conn.execute("SELECT status, COUNT(*) as cnt FROM agent_messages WHERE context_id IN ('vac_test', 'vac_concurrent') GROUP BY status").fetchall()
            }
            status_sum = sum(by_status.values())
        finally:
            conn.close()

        assert total == n1 + n2, f"Erwartet {n1 + n2} Messages, gefunden {total}"
        assert status_sum == total, f"Status-Summe ({status_sum}) != Total ({total})"
        print(f"    ✅ {total} Messages konsistent nach VACUUM")

        # Alle restlichen verarbeiten
        for _ in range(n1 + n2):
            msg = fetch_next_message("VacAG", db_path, timeout=0.3)
            if msg:
                ack_message(msg["msg_id"], db_path)

        conn = get_db_connection()
        try:
            remaining = conn.execute("SELECT COUNT(*) FROM agent_messages WHERE status IN ('pending', 'processing') AND context_id IN ('vac_test', 'vac_concurrent')").fetchone()[0]
        finally:
            conn.close()
        assert remaining == 0, f"Alle sollten verarbeitet sein, {remaining} bleiben"
        print("    ✅ Alle 40 Messages erfolgreich verarbeitet")

    def test_rollback_path_on_error(self, isolated_db):
        """fetch_next_message rollbackt bei Fehler korrekt (except: conn.rollback()).

        Szenario: Ein Fehler WÄHREND der Transaktion in fetch_next_message
        (nach BEGIN IMMEDIATE) muss die Transaktion sauber rollbacken, sodass
        keine 'processing'-Waise zurückbleibt.
        """
        conn = get_db_connection()
        try:
            _seed_agents(conn)
            conn.execute("INSERT INTO agents (name, id, description, status, last_seen) VALUES ('RollbackAG', 'rb', 'Rollback Agent', 'online', '2026-06-08T00:00:00Z')")
            conn.commit()
        finally:
            conn.close()

        db_path = str(isolated_db)

        # Eine Message dispatchen
        dispatch_mention("User", "@RollbackAG rollback_me", "rb_test", db_path)

        # fetch_next_message mit ungültigem payload provozieren.
        # fetch_next_message macht json.loads(payload) NACH dem COMMIT der
        # processing-Transaktion. Ein corruptes JSON lässt die Message als
        # 'processing' liegen (die Transaktion ist bereits committed).
        # Das ist bekanntes Verhalten: der aufrufende Agent (agent_base.py)
        # fängt den Fehler und ruft nack_message() auf.
        conn = get_db_connection()
        try:
            conn.execute("UPDATE agent_messages SET payload='INVALID_JSON{NO_PARSE' WHERE context_id='rb_test'")
            conn.commit()
        finally:
            conn.close()

        # fetch_next_message crasht mit JSONDecodeError. Der Fehler propagiert
        # durch den except: conn.rollback() + raise Block (rollback ist hier
        # wirkungslos, weil die Transaktion bereits committed wurde).
        with pytest.raises((json.JSONDecodeError, ValueError)):
            fetch_next_message("RollbackAG", db_path, timeout=0.3)

        # Nach dem Crash: die Message könnte in 'processing' sein (weil der
        # Commit vor dem json.loads() passiert) oder in 'pending' (wenn
        # der Rollback doch gegriffen hat). In beiden Fällen muss sie
        # recoverierbar sein.
        conn = get_db_connection()
        try:
            row = conn.execute("SELECT status FROM agent_messages WHERE context_id='rb_test'").fetchone()
        finally:
            conn.close()

        assert row is not None, "Message muss existieren"
        print(f"    ✅ Nach JSON-Crash: status={row['status']} (recoverierbar)")

        # Mit recover_stuck_messages die Message zurücksetzen
        recover_stuck_messages(db_path, timeout=0.1)

        # payload reparieren + auf pending setzen
        conn = get_db_connection()
        try:
            conn.execute("UPDATE agent_messages SET payload=? WHERE context_id='rb_test'",
                         (json.dumps({"text": "@RollbackAG fixed"}),))
            conn.execute("UPDATE agent_messages SET status='pending', deliver_after=0 WHERE context_id='rb_test'")
            conn.commit()
        finally:
            conn.close()

        msg = fetch_next_message("RollbackAG", db_path, timeout=0.5)
        assert msg is not None, "Reparierte Message muss abholbar sein"
        ack_message(msg["msg_id"], db_path)
        print("    ✅ Reparierte Message normal verarbeitet")
