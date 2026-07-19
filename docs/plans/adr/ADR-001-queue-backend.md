# ADR-001: Job Queue Backend

**Status:** Accepted  
**Date:** 2026-07-19  
**Deciders:** Gnom-Hub maintainers  

## Context

Today the multi-agent job queue lives in SQLite (`agent_messages`) with
`BEGIN IMMEDIATE` claims across **9 OS processes** (hub + 8 agents). Under
load this produces `database is locked`, chat timeouts, and failed dispatches
(see `docs/TECHNICAL_STATUS_REPORT_2026-07.md` P0.1).

We need a queue that supports:

- at-least-once delivery with lease / retry / DLQ  
- multi-consumer wake-up (no fake in-process `threading.Event`)  
- local-first operation (no cloud dependency)  
- clear migration path from SQLite  

## Decision

**Primary target: NATS JetStream (local binary / Docker).**  
**Fallback / alternative if NATS ops cost is too high: PostgreSQL with
`FOR UPDATE SKIP LOCKED`.**

| Option | Pros | Cons |
|--------|------|------|
| **NATS JetStream** | Purpose-built streams, consumer groups, ack/nak, durable, one binary | New dependency; ops learning |
| **Postgres SKIP LOCKED** | One OLTP store for chat+jobs; mature tooling | Heavier than embedded SQLite; still SQL-bound |
| Keep SQLite queue | Zero new deps | **Rejected** for multi-writer agent model |

### Rationale (2026)

1. **Separation of concerns:** Chat OLTP (low latency writes) must not share
   write locks with agent claim loops.  
2. **NATS** gives real cross-process notify (push/pull consumers) — replaces
   the ineffective `notify_agent()` Event.  
3. **Postgres** remains the preferred **OLTP** for chat/state if we leave
   embedded SQLite; using it *also* as queue is valid (Option B) but couples
   job latency to schema migrations.  
4. NATS + Postgres (or libSQL) is the clean Control/Data plane split from
   `docs/STRATEGY_PLAN_2026.md`.

## Consequences

### Positive

- Eliminates SQLite multi-writer storm on job claim  
- Enables horizontal agent workers later  
- First-class retry/backoff/DLQ semantics  

### Negative

- Extra process to run (`nats-server -js`)  
- Dual-write migration period complexity  

## Implementation plan

1. **Phase 1 (now):** Keep SQLite queue hardened (NACK, recovery, short busy).  
2. **Phase 2:** Dual-write `agent_messages` → NATS subject `gnom.jobs.<agent>`;  
   agents consume NATS; SQLite remains audit/mirror.  
3. **Phase 3:** Cut over reads; deprecate SQLite claim path.  

## Rollback

Feature flag `GNOM_QUEUE_BACKEND=sqlite|nats`. Default remains `sqlite`
until dual-write is green for 7 days.

## References

- Status report P0.1 / P1.1  
- Strategy plan Phase 2  
- NATS JetStream docs (consumer ack policy)  
