// ============================================================================
//  Cortex v2 — Task Service
//  Redis primary for active tasks, persistent backup in memories table
// ============================================================================

const store = require('../db/store');

async function createTask({ title, description = '', assignee = '', priority = 5, tags = [], source = 'user' }) {
  const id = store.genId();
  const task = {
    id, title, description, assignee, priority, status: 'open',
    tags, source, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
  };

  await store.setTask(id, task);

  // Also persist as a memory
  if (store.isPostgres()) {
    await store.pg.insertMemory({
      id, content: `[TASK] ${title}: ${description}`, type: 'task',
      importance: priority, source, tags, context: {},
    });
  } else {
    await store.execute(
      `INSERT INTO memories (id, content, memory_type, importance, source, tags, created_at, updated_at)
       VALUES (?, ?, 'task', ?, ?, ?, datetime('now'), datetime('now'))`,
      id, `[TASK] ${title}: ${description}`, priority, source, JSON.stringify(tags)
    );
  }

  return task;
}

async function updateTask(id, updates) {
  const task = await store.getTask(id);
  if (!task) return null;
  const updated = { ...task, ...updates, updatedAt: new Date().toISOString() };
  await store.setTask(id, updated);
  return updated;
}

async function completeTask(id) {
  return updateTask(id, { status: 'done' });
}

async function getTask(id) {
  return store.getTask(id);
}

async function getActiveTasks() {
  return store.getActiveTasks();
}

async function getOverdueTasks(maxAgeHours = 24) {
  const cutoff = Date.now() - maxAgeHours * 60 * 60 * 1000;
  const tasks = await store.getActiveTasks();
  return tasks.filter(t => new Date(t.createdAt).getTime() < cutoff);
}

module.exports = { createTask, updateTask, completeTask, getTask, getActiveTasks, getOverdueTasks };
