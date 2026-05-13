// Cortex v2 — Cron Service (croner + hybrid store)
const { Cron } = require('croner');
const store = require('../db/store');
const activeJobs = new Map();

async function init() {
  let jobs = [];
  if (store.isPostgres()) {
    jobs = await store.pg.getCronJobs(true);
  } else {
    jobs = await store.queryAll('SELECT * FROM cron_jobs WHERE enabled = 1');
  }
  for (const job of jobs) scheduleJob(job);
  console.log(`[Cortex/Cron] Loaded ${jobs.length} cron jobs`);
}

async function createJob({ name, schedule, action, enabled = true }) {
  const id = store.genId();
  if (store.isPostgres()) {
    await store.pg.insertCronJob({ id, name, schedule, action, enabled });
  } else {
    await store.execute(
      `INSERT INTO cron_jobs (id, name, schedule, action, enabled, created_at) VALUES (?, ?, ?, ?, ?, datetime('now'))`,
      id, name, schedule, JSON.stringify(action), enabled ? 1 : 0
    );
  }
  if (enabled) scheduleJob({ id, name, schedule, action: typeof action === 'string' ? action : JSON.stringify(action) });
  return { id, name, schedule };
}

function scheduleJob(jobRow) {
  try {
    const action = typeof jobRow.action === 'string' ? JSON.parse(jobRow.action) : jobRow.action;
    const cron = new Cron(jobRow.schedule, () => executeJob(jobRow.id, action));
    activeJobs.set(jobRow.id, cron);
  } catch (err) {
    console.error(`[Cortex/Cron] Failed to schedule ${jobRow.name}:`, err.message);
  }
}

async function executeJob(jobId, action) {
  if (store.isPostgres()) {
    await store.pg.execute('UPDATE cron_jobs SET last_run = NOW(), run_count = run_count + 1 WHERE id = $1', [jobId]);
  } else {
    await store.execute('UPDATE cron_jobs SET last_run = datetime(\'now\'), run_count = run_count + 1 WHERE id = ?', jobId);
  }
  if (cronHandler) cronHandler(jobId, action);
}

let cronHandler = null;
function onCronExec(handler) { cronHandler = handler; }

async function listJobs() {
  let rows;
  if (store.isPostgres()) {
    rows = await store.pg.getCronJobs();
  } else {
    rows = await store.queryAll('SELECT * FROM cron_jobs ORDER BY created_at DESC');
  }
  return rows.map(r => ({
    id: r.id, name: r.name, schedule: r.schedule,
    action: typeof r.action === 'string' ? safeParse(r.action, {}) : r.action,
    enabled: typeof r.enabled === 'boolean' ? r.enabled : !!r.enabled,
    lastRun: r.last_run, runCount: r.run_count,
  }));
}

async function toggleJob(id, enabled) {
  if (store.isPostgres()) {
    await store.pg.execute('UPDATE cron_jobs SET enabled = $1 WHERE id = $2', [enabled, id]);
  } else {
    await store.execute('UPDATE cron_jobs SET enabled = ? WHERE id = ?', enabled ? 1 : 0, id);
  }
  if (!enabled) { const c = activeJobs.get(id); if (c) { c.stop(); activeJobs.delete(id); } }
}

async function deleteJob(id) {
  const c = activeJobs.get(id); if (c) { c.stop(); activeJobs.delete(id); }
  if (store.isPostgres()) { await store.pg.execute('DELETE FROM cron_jobs WHERE id = $1', [id]); }
  else { await store.execute('DELETE FROM cron_jobs WHERE id = ?', id); }
}

function safeParse(s, f) { try { return JSON.parse(s); } catch { return f; } }

module.exports = { init, createJob, listJobs, toggleJob, deleteJob, onCronExec };
