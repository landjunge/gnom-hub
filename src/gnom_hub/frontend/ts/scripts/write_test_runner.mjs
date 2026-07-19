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
`;

writeFileSync(out, src);
console.log("wrote", out);
