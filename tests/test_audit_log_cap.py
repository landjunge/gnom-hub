"""Test: audit_log bleibt durch Cap selbsterhaltend klein."""
import sqlite3
from datetime import datetime, timezone


def _make_test_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            agent TEXT,
            event_type TEXT,
            details TEXT,
            trace_id TEXT
        )
    """)
    return conn


def test_cap_triggers_when_over_max():
    """Bei >MAX_ROWS werden die ältesten gelöscht, bis KEEP_ROWS erreicht ist."""
    from gnom_hub.db.system_repo import _enforce_audit_cap, AUDIT_LOG_MAX_ROWS, AUDIT_LOG_KEEP_ROWS

    conn = _make_test_db()
    now = datetime.now(timezone.utc).isoformat()
    # AUDIT_LOG_MAX_ROWS + 50 Zeilen
    for i in range(AUDIT_LOG_MAX_ROWS + 50):
        conn.execute(
            "INSERT INTO audit_log (timestamp, agent, event_type, details) VALUES (?, ?, ?, ?)",
            (now, f"agent_{i}", "test", "{}")
        )
    conn.commit()

    n_before = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    assert n_before == AUDIT_LOG_MAX_ROWS + 50

    _enforce_audit_cap(conn)
    conn.commit()

    n_after = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    assert n_after == AUDIT_LOG_KEEP_ROWS, f"erwartet {AUDIT_LOG_KEEP_ROWS}, bekam {n_after}"
    print(f"OK: {n_before} → {n_after} Zeilen (Cap greift)")


def test_cap_does_nothing_under_max():
    """Unter dem Limit passiert nichts."""
    from gnom_hub.db.system_repo import _enforce_audit_cap, AUDIT_LOG_MAX_ROWS

    conn = _make_test_db()
    now = datetime.now(timezone.utc).isoformat()
    for i in range(100):
        conn.execute(
            "INSERT INTO audit_log (timestamp, agent, event_type, details) VALUES (?, ?, ?, ?)",
            (now, f"agent_{i}", "test", "{}")
        )
    conn.commit()

    _enforce_audit_cap(conn)
    n = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    assert n == 100, f"unerwartete Änderung: {n}"
    print("OK: Unter Cap keine Änderung")


def test_cap_keeps_newest():
    """Die jüngsten Einträge müssen erhalten bleiben."""
    from gnom_hub.db.system_repo import _enforce_audit_cap, AUDIT_LOG_MAX_ROWS, AUDIT_LOG_KEEP_ROWS

    conn = _make_test_db()
    # Sequenziell wachsende timestamps
    for i in range(AUDIT_LOG_MAX_ROWS + 100):
        ts = f"2026-06-15T10:{i // 60:02d}:{i % 60:02d}Z"
        conn.execute(
            "INSERT INTO audit_log (timestamp, agent, event_type, details) VALUES (?, ?, ?, ?)",
            (ts, f"agent_{i:06d}", "test", "{}")
        )
    conn.commit()

    _enforce_audit_cap(conn)
    conn.commit()

    # Letzter Agent muss agent_... mit höchstem Index sein
    rows = conn.execute(
        "SELECT agent FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchall()
    newest_agent = rows[0][0]
    expected_index = AUDIT_LOG_MAX_ROWS + 100 - 1
    assert newest_agent == f"agent_{expected_index:06d}", \
        f"jüngster Eintrag fehlt: erwartet agent_{expected_index:06d}, bekam {newest_agent}"
    print(f"OK: Jüngster Eintrag erhalten ({newest_agent})")


if __name__ == "__main__":
    test_cap_triggers_when_over_max()
    test_cap_does_nothing_under_max()
    test_cap_keeps_newest()
    print("\nAlle audit_log-Cap-Tests bestanden.")
