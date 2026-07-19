/** Writes dist-test/run.mjs after esm bundle is built (npm pretest). */
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const out = join(__dirname, "..", "dist-test", "run.mjs");
mkdirSync(dirname(out), { recursive: true });

const src = `import test from 'node:test';
import assert from 'node:assert/strict';
import GnomTS from './gnom-ts.mjs';

const api = GnomTS.default || GnomTS;

test('version present', () => {
  assert.equal(typeof api.version, 'string');
});

test('known agent colors match core.js', () => {
  assert.equal(api.agentColor('CoderAG'), '#FF0000');
  assert.equal(api.agentColor('coderag'), '#FF0000');
  assert.equal(api.agentColor('SoulAG'), '#FF5E00');
  assert.equal(api.agentColor('GeneralAG'), '#00FFFF');
});

test('frozen / system / worker helpers', () => {
  assert.equal(api.isFrozenAgent('CoderAG'), true);
  assert.equal(api.isSystemAgent('SoulAG'), true);
  assert.equal(api.isWorkerAgent('WriterAG'), true);
  assert.equal(api.isSystemAgent('WriterAG'), false);
});

test('mention extraction skips @@system', () => {
  const m = api.extractMentions('@CoderAG please fix and @@status later @WriterAG');
  assert.deepEqual(m.map((x) => x.toLowerCase()), ['coderag', 'writerag']);
  assert.equal(api.isMultiMention('@CoderAG and @WriterAG'), true);
  assert.equal(api.isMultiMention('@CoderAG alone'), false);
});

test('only= helpers', () => {
  assert.equal(api.stripOnlyPrefix('only=CoderAG do the thing'), 'do the thing');
  assert.equal(api.withOnlyTarget('CoderAG', 'hello'), 'only=CoderAG hello');
});

test('createApiClient posts JSON', async () => {
  const calls = [];
  const client = api.createApiClient({
    baseUrl: 'http://127.0.0.1:3002/api',
    silent: true,
    fetchImpl: async (url, opts) => {
      calls.push({ url, opts });
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ ok: true }),
      };
    },
  });
  const r = await client.postChat('hi', 'User');
  assert.equal(r.ok, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'http://127.0.0.1:3002/api/chat');
  assert.equal(calls[0].opts.method, 'POST');
});

test('safeJsonParse and escapeHtml', () => {
  assert.deepEqual(api.safeJsonParse('{"a":1}'), { a: 1 });
  assert.equal(api.safeJsonParse('not-json'), 'not-json');
  assert.equal(api.escapeHtml('<b>&x'), '&lt;b&gt;&amp;x');
  assert.equal(api.escapeHtml('"q"'), '&quot;q&quot;');
});

test('discoverApiBase uses origin for http', async () => {
  const base = await api.discoverApiBase({
    protocol: 'http:',
    origin: 'http://127.0.0.1:3002',
  });
  assert.equal(base, 'http://127.0.0.1:3002/api');
});

test('discoverApiBase probes ports on file://', async () => {
  const tried = [];
  const base = await api.discoverApiBase({
    protocol: 'file:',
    ports: [3999, 3002],
    fetchImpl: async (url) => {
      tried.push(url);
      if (String(url).includes(':3002/')) {
        return { ok: true, status: 200, text: async () => '{}' };
      }
      throw new Error('down');
    },
  });
  assert.equal(base, 'http://127.0.0.1:3002/api');
  assert.ok(tried.some((u) => String(u).includes('3999')));
});

test('formatStatsPanel matches core UI strings', () => {
  const panel = api.formatStatsPanel(
    {
      agents: 8,
      sys_agents: 4,
      work_agents: 4,
      memory: 12,
      tokens_free: 1,
      tokens_pay: 2,
      queue: { pending: 3, processing: 1, dead_letter: 0 },
      leases: [{ id: 9, recipient: 'CoderAG' }],
      last_error: { status: 500, recipient: 'WriterAG' },
    },
    [],
  );
  assert.equal(panel.agents, '8 (Sys: 4 | Work: 4)');
  assert.equal(panel.tokens, 'Free: 1 | Pay: 2');
  assert.equal(panel.queue, '3/1/0');
  assert.equal(panel.leases, '1 CoderAG');
  assert.equal(panel.lastErr, '500 WriterAG');
});

test('apiRequest uses baseUrl + path', async () => {
  const calls = [];
  // inject via createApiClient path: apiRequest builds client without fetchImpl —
  // use global fetch override
  const prev = globalThis.fetch;
  globalThis.fetch = async (url, opts) => {
    calls.push({ url, opts });
    return { ok: true, status: 200, text: async () => JSON.stringify({ ok: 1 }) };
  };
  try {
    const r = await api.apiRequest('http://127.0.0.1:3002/api', 'GET', '/stats', null, { silent: true });
    assert.equal(r.ok, 1);
    assert.equal(calls[0].url, 'http://127.0.0.1:3002/api/stats');
  } finally {
    globalThis.fetch = prev;
  }
});

test('chat history push + navigate', () => {
  const store = new Map();
  const storage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => { store.set(k, v); },
  };
  api.pushChatHistory(storage, 'one');
  api.pushChatHistory(storage, 'two');
  api.pushChatHistory(storage, 'two'); // dedupe last
  const hist = api.loadChatHistory(storage);
  assert.deepEqual(hist, ['one', 'two']);
  let state = { idx: -1, draft: '' };
  let nav = api.navigateChatHistory('up', hist, state, 'drafting');
  assert.equal(nav.value, 'two');
  assert.equal(nav.state.draft, 'drafting');
  nav = api.navigateChatHistory('up', hist, nav.state, nav.value);
  assert.equal(nav.value, 'one');
  nav = api.navigateChatHistory('down', hist, nav.state, nav.value);
  assert.equal(nav.value, 'two');
  nav = api.navigateChatHistory('down', hist, nav.state, nav.value);
  assert.equal(nav.value, 'drafting');
  assert.equal(nav.state.idx, -1);
});

test('classifyLocalCommand', () => {
  assert.equal(api.classifyLocalCommand('@tts on').kind, 'tts_on');
  assert.equal(api.classifyLocalCommand('/coffee').kind, 'easter');
  assert.equal(api.classifyLocalCommand('@CoderAG fix it').kind, 'none');
  assert.equal(api.isLocalCommand('@@slides'), true);
  const sp = api.classifyLocalCommand('@showbox speed 2.5');
  assert.equal(sp.kind, 'showbox_speed');
  assert.equal(sp.valid, true);
  assert.equal(sp.seconds, 2.5);
});

test('formatChatResponseToast', () => {
  assert.equal(api.formatChatResponseToast(null).type, 'error');
  assert.match(api.formatChatResponseToast({ status: 'role_set', agent: 'A', role: 'r' }).message, /👑/);
  assert.match(api.formatChatResponseToast({ mode: 'brainstorm', asked: ['CoderAG'] }).message, /🧠/);
  // status:error uses message field (backend shape) — must be error, not fake success
  const err = api.formatChatResponseToast({ status: 'error', message: 'Empty content' });
  assert.equal(err.type, 'error');
  assert.match(err.message, /Empty content/);
  // saved + msg = soft info (DB busy path), not hard error
  const soft = api.formatChatResponseToast({
    status: 'saved',
    msg: 'Nachricht gespeichert, Dispatch wartet (DB busy)',
  });
  assert.equal(soft.type, 'info');
  // @@status legacy: agents array without status
  const st = api.formatChatResponseToast({
    agents: [{ name: 'CoderAG', role: 'coder', st: 'online' }],
  });
  assert.equal(st.type, 'info');
  assert.match(st.message, /CoderAG/);
  // merken success
  const mer = api.formatChatResponseToast({ status: 'saved', message: 'my fact' });
  assert.equal(mer.type, 'success');
  // blocked
  assert.equal(api.formatChatResponseToast({ status: 'blocked', msg: 'injection' }).type, 'error');
});

test('extractThoughtsAndClean + speech helpers', () => {
  const r = api.extractThoughtsAndClean('hi <think>secret</think> out');
  assert.deepEqual(r.thoughts, ['secret']);
  assert.ok(r.cleaned.includes('hi'));
  assert.ok(r.cleaned.includes('out'));
  assert.ok(!r.cleaned.includes('secret'));
  assert.ok(!r.cleaned.includes('<think>'));
  assert.equal(api.isSystemLogMessage('agent heartbeat ok'), true);
  assert.equal(api.isAgentToAgentMessage('@CoderAG do x'), true);
  assert.match(api.cleanActionTagsForSpeech('[WRITE: a.html]x[/WRITE]'), /schreibt Datei/);
});

test('prepareOutgoingChat multi-@', () => {
  const p = api.prepareOutgoingChat('@CoderAG and @WriterAG please', {
    isLocalCommand: api.isLocalCommand,
  });
  assert.equal(p.empty, false);
  assert.ok(p.multiMentionToast);
  assert.match(p.multiMentionToast, /Multi-@/);
  const local = api.prepareOutgoingChat('@tts on', { isLocalCommand: api.isLocalCommand });
  assert.equal(local.localCommand, true);
  assert.equal(local.multiMentionToast, null);
});
`;

writeFileSync(out, src);
console.log("wrote", out);
