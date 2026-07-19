# Gnom-Hub frontend TypeScript (S5 gradual)

Local-first TypeScript layer beside the existing `*.js` UI.

- **Source:** `src/`
- **Browser bundle:** `../gnom-ts.js` (IIFE → `window.GnomTS`)
- **No rewrite:** core.js / chat.js stay; they can call `GnomTS.*` when present

## Commands

```bash
cd src/gnom_hub/frontend/ts
npm install
npm run check    # typecheck + build + node tests
# or
../../../../scripts/build_frontend_ts.sh
```

## Public API (`window.GnomTS`)

| Export | Purpose |
|--------|---------|
| `agentColor(name)` | Same palette as `core.js` |
| `FROZEN_AGENTS` / `isSystemAgent` / `isWorkerAgent` | Agent set helpers |
| `extractMentions` / `isMultiMention` | Multi-@ preview |
| `withOnlyTarget` / `stripOnlyPrefix` | `only=` draft helpers |
| `createApiClient({ baseUrl })` | Typed thin fetch client |
| `apiRequest(base, method, path, body, opts)` | Drop-in for `core.js` `api()` |
| `discoverApiBase(opts)` | Port / origin discovery |
| `safeJsonParse` / `escapeHtml` | Shared pure helpers |
| `formatStatsPanel(stats, agents)` | Stats panel string model |
| `pushChatHistory` / `navigateChatHistory` | localStorage history |
| `classifyLocalCommand` / `isLocalCommand` | client-only cmds |
| `formatChatResponseToast` | POST `/chat` toast text |
| `prepareOutgoingChat` | trim + multi-@ toast |
| `extractThoughtsAndClean` / speech filters | render/TTS pure helpers |

Runtime does **not** require `npm` — commit the built `gnom-ts.js`.
