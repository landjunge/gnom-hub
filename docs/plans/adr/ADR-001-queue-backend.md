# ADR-001: Job Queue Backend

**Status:** Superseded / Rejected (2026-07-19)  
**Date:** 2026-07-19  

## Context

Earlier draft proposed NATS JetStream or Postgres as the job queue, including
local Docker for NATS.

## Decision (aktualisiert)

**Rejected for product direction.**

User constraint: **no Docker**, **no sandbox**, local-first only.

The job queue **stays SQLite** (`agent_messages`), hardened with:

- per-agent pending / concurrent limits  
- NACK on empty/router failure  
- stale pending auto-DLQ  
- `@@queue` / admin clear  
- optional later: **Hub HTTP claim** (claim only in hub process — still no
  extra daemon)

## Consequences

- No NATS, Redis, Postgres server, or Docker as roadmap items  
- Stability comes from code hygiene inside the existing process model  

## References

- `docs/STRATEGY_PLAN_2026.md` (Randbedingungen: kein Docker, keine Sandbox)
