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
`;

writeFileSync(out, src);
console.log("wrote", out);
