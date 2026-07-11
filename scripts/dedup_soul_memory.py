#!/usr/bin/env python3
"""Dedup Soul Memory — Run save_soul_fact_smart over the full backup-DB.

This script proves that the new smart-dedup engine reduces the existing 1666
soul facts to a clean curated list (target 100–200 facts, 30–60 KB).

SAFETY
------
* Source DB is opened READ-ONLY (URI mode=ro) — never modified.
* Snapshot copy is written to dev/backups_datenbanken/... (gitignored, never
  committed) so the original archive is still bit-identical.
* The dedup pass runs in a fresh test DB inside a tempdir.
* Test DB and the embedder / passive-archive side-effects are all redirected
  to the tempdir. No real hub state is touched.
* After the run, the tempdir is removed.

USAGE
-----
    PYTHONPATH=src python3.10 scripts/dedup_soul_memory.py
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# ── Paths ──────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DB = Path(
    "/Users/landjunge/Desktop/gnom_dev/backups_datenbanken/"
    "2026-06-23_18-23-53_pre-push/data/gnomhub.db"
)
BACKUP_DIR = REPO_ROOT / "dev" / "backups_datenbanken" / "2026-06-23_soul-dedup-pre"

PRIO_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1, "": 0, None: 0}


# ── Helpers ────────────────────────────────────────────────────────────────
def _normalize_key(key: str) -> str:
    """Same normalization as save_soul_fact_smart — for inserted-vs-merged detection."""
    if not key:
        return ""
    k = str(key).lower().strip()
    k = re.sub(r"[^a-z0-9]+", "_", k)
    k = re.sub(r"_+", "_", k)
    return k.strip("_")


def _read_source_facts() -> list[sqlite3.Row]:
    """Open source DB read-only, return rows sorted by priority DESC, timestamp DESC."""
    uri = f"file:{SRC_DB}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT key, value, timestamp, priority, agent FROM soul_memory"
        ).fetchall()
    finally:
        conn.close()

    def _sort_key(r):
        return (
            -PRIO_RANK.get((r["priority"] or "").lower(), 0),
            r["timestamp"] or "",
        )

    return sorted(rows, key=_sort_key)


def _db_stats(db_path: Path) -> tuple[int, int, list[sqlite3.Row]]:
    """Return (count, total_chars, all_rows) for a DB file."""
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT key, value, timestamp, priority, agent FROM soul_memory "
            "ORDER BY priority DESC, timestamp DESC"
        ).fetchall()
    finally:
        conn.close()
    total_chars = sum(len(r["value"]) for r in rows)
    return len(rows), total_chars, rows


# ── Side-effect patches ────────────────────────────────────────────────────
class _NoopEmbedder:
    """Drop-in replacement for SoulEmbedder that does nothing."""

    def add_fact(self, *args, **kwargs):
        return None

    def search_sync(self, *args, **kwargs):
        return []

    def get_helper(self, *args, **kwargs):
        return None


def _noop_embedder_factory():
    return _NoopEmbedder()


# ── Main ───────────────────────────────────────────────────────────────────
def main() -> int:
    if not SRC_DB.exists():
        print(f"[error] Source DB not found: {SRC_DB}", file=sys.stderr)
        return 1

    # 1) Snapshot the source DB to a gitignored dir (paranoia — never modify
    #    the archive). We only do this if no copy exists yet so repeated runs
    #    stay idempotent.
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / "gnomhub.db"
    if not backup_path.exists():
        shutil.copy2(SRC_DB, backup_path)
        print(f"[snapshot] Copied source DB → {backup_path}")
    else:
        print(f"[snapshot] Reusing existing snapshot at {backup_path}")

    # 2) Read facts from source (read-only)
    print(f"[read] Source DB: {SRC_DB}")
    rows = _read_source_facts()
    before_count = len(rows)
    before_chars = sum(len(r["value"]) for r in rows)
    print(
        f"[read] {before_count} facts, {before_chars:,} chars "
        f"({before_chars / 1024:.1f} KB) total"
    )

    # 3) Set up test DB in tempdir
    tmpdir = Path(tempfile.mkdtemp(prefix="gnom_soul_dedup_"))
    test_db = tmpdir / "test_gnomhub.db"
    passive_db = tmpdir / "passive_archive.db"
    print(f"[setup] Test DB at {test_db}")

    # Make repo src/ importable
    sys.path.insert(0, str(REPO_ROOT / "src"))

    # Lazy imports so the path is in place
    from gnom_hub.core import config as config_mod
    from gnom_hub.db import passive_db as passive_mod
    from gnom_hub.db.schema import init_database
    from gnom_hub.db.soul_repo import save_soul_fact_smart

    # 4) Initialize test DB schema (uses Config.DB_PATH → we patch it)
    with patch.object(config_mod.Config, "DB_PATH", test_db), \
         patch.object(passive_mod, "PASSIVE_DB_PATH", passive_db):
        init_database()
    print("[setup] Schema initialized in test DB")

    # 5) Run each fact through the smart-dedup writer
    inserted = merged = rejected = 0
    rejected_examples: list[tuple[str, int, str]] = []

    patch_ctx = patch.multiple(
        config_mod.Config,
        DB_PATH=test_db,
    )
    passive_patch = patch.object(passive_mod, "PASSIVE_DB_PATH", passive_db)
    embedder_patch = patch(
        "gnom_hub.memory.embeddings.get_embedder", _noop_embedder_factory
    )

    with patch_ctx, passive_patch, embedder_patch:
        for i, r in enumerate(rows, 1):
            result = save_soul_fact_smart(
                r["key"],
                r["value"],
                agent=(r["agent"] or "System"),
                priority=(r["priority"] or "medium"),
            )
            if result is None:
                rejected += 1
                if len(rejected_examples) < 5:
                    rejected_examples.append(
                        (r["key"], len(r["value"]), (r["value"] or "")[:60])
                    )
            elif result == _normalize_key(r["key"]):
                inserted += 1
            else:
                # Returned a different canonical key → merged into another slot
                merged += 1

            if i % 200 == 0:
                print(f"  ... processed {i}/{before_count}")

    # 5b) Snapshot AFTER smart-dedup (before forced cleanup), then force a full
    #     cleanup pass to demonstrate the integrated engine's post-cleanup state.
    #     The cleanup hook in save_soul_fact_smart is throttled by
    #     CLEANUP_INTERVAL=1800s, so it only fires once during a bulk insert.
    #     Here we bypass that throttle (reset _last_cleanup_time=0) and run
    #     cleanup until the count stops shrinking.
    from gnom_hub.soul import soul as soul_mod

    dedup_count, dedup_chars, _ = _db_stats(test_db)
    cleanup_iters = 0
    with patch.object(config_mod.Config, "DB_PATH", test_db), \
         patch.object(passive_mod, "PASSIVE_DB_PATH", passive_db):
        prev_count = dedup_count
        while True:
            cleanup_iters += 1
            soul_mod._last_cleanup_time = 0  # bypass throttle
            soul_mod._periodic_cleanup()
            cur_count, _, _ = _db_stats(test_db)
            if cur_count >= prev_count:
                break
            prev_count = cur_count
            if cleanup_iters > 20:
                break

    # 6) Read final state of test DB
    after_count, after_chars, final_rows = _db_stats(test_db)
    print()
    print("=" * 72)
    print("RESULT")
    print("=" * 72)
    print(
        f"Before:                    {before_count:>5} facts, "
        f"{before_chars:>7,} chars ({before_chars / 1024:.1f} KB)"
    )
    print(
        f"After smart-dedup:         {dedup_count:>5} facts, "
        f"{dedup_chars:>7,} chars "
        f"({dedup_chars / 1024:.1f} KB)  "
        f"[inserted={inserted} merged={merged} rejected={rejected}]"
    )
    print(
        f"After smart-dedup+cleanup: {after_count:>5} facts, "
        f"{after_chars:>7,} chars "
        f"({after_chars / 1024:.1f} KB)  "
        f"[forced {cleanup_iters - 1} extra cleanup pass(es)]"
    )
    delta_count = before_count - after_count
    delta_chars = before_chars - after_chars
    print()
    print(
        f"Δ end-to-end: {delta_count} facts gone "
        f"({100 * delta_count / max(before_count, 1):.1f}%), "
        f"{delta_chars:,} chars saved "
        f"({100 * delta_chars / max(before_chars, 1):.1f}%)"
    )
    print()
    if rejected_examples:
        print("Rejected examples (first 5):")
        for key, ln, snippet in rejected_examples:
            print(f"  • {key!r} (len={ln}) → {snippet!r}")

    # 7) Top-30 preview of surviving facts
    print()
    print("=" * 72)
    print("Top 30 surviving facts (priority DESC, timestamp DESC)")
    print("=" * 72)
    for i, r in enumerate(final_rows[:30], 1):
        pri = (r["priority"] or "?").ljust(8)
        ts = (r["timestamp"] or "")[:19]
        preview = (r["value"] or "")[:80].replace("\n", " ").replace("\r", " ")
        print(f"  {i:>2}. [{pri}] {ts}  {r['key']}")
        print(f"      └─ {preview}{'…' if len(r['value'] or '') > 80 else ''}")

    # 8) Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)
    print()
    print(f"[cleanup] Removed test DB at {tmpdir}")
    print(f"[snapshot] Source backup at {backup_path} (gitignored, untouched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
