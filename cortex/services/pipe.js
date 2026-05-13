// Cortex v2 — Message Pipe (Redis primary, in-memory fallback)
const store = require('../db/store');

async function send(sender, recipient, content) {
  const msg = { id: store.genId(), sender, recipient, content, timestamp: new Date().toISOString(), read: false };
  await store.pipeSend(recipient, msg);
  return msg;
}

async function read(recipient, unreadOnly = true) {
  return store.pipeRead(recipient, unreadOnly);
}

async function broadcast(sender, content, exclude = []) {
  let agents = store.isPostgres()
    ? await store.pg.queryAll('SELECT id FROM agents')
    : await store.queryAll('SELECT id FROM agents');
  const sent = [];
  for (const a of agents) {
    if (a.id !== sender && !exclude.includes(a.id)) sent.push(await send(sender, a.id, content));
  }
  return sent;
}

module.exports = { send, read, broadcast };
