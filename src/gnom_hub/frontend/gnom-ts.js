"use strict";
var GnomTS = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // src/index.ts
  var index_exports = {};
  __export(index_exports, {
    FROZEN_AGENTS: () => FROZEN_AGENTS,
    KNOWN_COLORS: () => KNOWN_COLORS,
    P_COLORS: () => P_COLORS,
    SYSTEM_AGENTS: () => SYSTEM_AGENTS,
    WORKER_AGENTS: () => WORKER_AGENTS,
    agentColor: () => agentColor,
    apiRequest: () => apiRequest,
    countAgentGroups: () => countAgentGroups,
    countAgentMentions: () => countAgentMentions,
    createApiClient: () => createApiClient,
    default: () => index_default,
    discoverApiBase: () => discoverApiBase,
    escapeHtml: () => escapeHtml,
    extractMentions: () => extractMentions,
    formatAgentsLine: () => formatAgentsLine,
    formatLastError: () => formatLastError,
    formatLeases: () => formatLeases,
    formatQueueLine: () => formatQueueLine,
    formatStatsPanel: () => formatStatsPanel,
    formatTokensLine: () => formatTokensLine,
    isFrozenAgent: () => isFrozenAgent,
    isMultiMention: () => isMultiMention,
    isSystemAgent: () => isSystemAgent,
    isWorkerAgent: () => isWorkerAgent,
    knownColor: () => knownColor,
    safeJsonParse: () => safeJsonParse,
    stripOnlyPrefix: () => stripOnlyPrefix,
    withOnlyTarget: () => withOnlyTarget
  });

  // src/agents.ts
  var FROZEN_AGENTS = [
    "SoulAG",
    "GeneralAG",
    "SecurityAG",
    "WatchdogAG",
    "ResearcherAG",
    "WriterAG",
    "EditorAG",
    "CoderAG"
  ];
  var SYSTEM_AGENTS = [
    "SoulAG",
    "GeneralAG",
    "SecurityAG",
    "WatchdogAG"
  ];
  var WORKER_AGENTS = [
    "CoderAG",
    "WriterAG",
    "EditorAG",
    "ResearcherAG"
  ];
  var KNOWN_COLORS = {
    soulag: "#FF5E00",
    generalag: "#00FFFF",
    securityag: "#FF69B4",
    watchdogag: "#FFA500",
    researcherag: "#FFFF00",
    writerag: "#00FF00",
    editorag: "#0088FF",
    coderag: "#FF0000"
  };
  var P_COLORS = [
    "#00E5FF",
    "#B026FF",
    "#FF007F",
    "#39FF14",
    "#FF3366",
    "#8A2BE2",
    "#0066FF",
    "#00FF9D",
    "#FF9900",
    "#FFD700",
    "#FF1493",
    "#00FA9A",
    "#1E90FF",
    "#FF4500",
    "#00FFFF"
  ];
  function djb2(s) {
    let h = 5381;
    for (let i = 0; i < s.length; i++) {
      h = (h << 5) + h + s.charCodeAt(i) | 0;
    }
    return h;
  }
  function knownColor(name) {
    var _a;
    if (!name) return null;
    return (_a = KNOWN_COLORS[name.toLowerCase()]) != null ? _a : null;
  }
  function agentColor(name) {
    if (!name) return "#00E5FF";
    const known = knownColor(name);
    if (known) return known;
    const h = djb2(name);
    return P_COLORS[Math.abs(h) % P_COLORS.length];
  }
  function isSystemAgent(name) {
    const n = name.toLowerCase();
    return SYSTEM_AGENTS.some((a) => a.toLowerCase() === n);
  }
  function isWorkerAgent(name) {
    const n = name.toLowerCase();
    return WORKER_AGENTS.some((a) => a.toLowerCase() === n);
  }
  function isFrozenAgent(name) {
    const n = name.toLowerCase();
    return FROZEN_AGENTS.some((a) => a.toLowerCase() === n);
  }

  // src/chat_mentions.ts
  var MENTION_RE = /@([A-Za-z][A-Za-z0-9_]*)/g;
  function extractMentions(text) {
    if (!text) return [];
    const seen = /* @__PURE__ */ new Set();
    const out = [];
    MENTION_RE.lastIndex = 0;
    let m;
    while ((m = MENTION_RE.exec(text)) !== null) {
      const name = m[1];
      const key = name.toLowerCase();
      const at = m.index;
      if (at > 0 && text[at - 1] === "@") continue;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(name);
    }
    return out;
  }
  function countAgentMentions(text) {
    return extractMentions(text).length;
  }
  function isMultiMention(text) {
    return extractMentions(text).length > 1;
  }
  function stripOnlyPrefix(text) {
    if (!text) return "";
    return text.replace(/^\s*only=\S+\s*/i, "").trimStart();
  }
  function withOnlyTarget(agent, body) {
    const clean = (body || "").replace(/^\s*only=\S+\s*/i, "").trim();
    return `only=${agent} ${clean}`.trim();
  }

  // src/api.ts
  function safeJsonParse(text) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }
  var DEFAULT_DISCOVER_PORTS = [3003, 3002, 3001, 3e3];
  async function discoverApiBase(opts = {}) {
    var _a, _b, _c, _d, _e;
    const protocol = (_a = opts.protocol) != null ? _a : typeof location !== "undefined" ? location.protocol : "http:";
    const origin = (_b = opts.origin) != null ? _b : typeof location !== "undefined" ? location.origin : "";
    if (protocol !== "file:") {
      if (origin) return origin.replace(/\/$/, "") + "/api";
      return "/api";
    }
    const ports = (_c = opts.ports) != null ? _c : DEFAULT_DISCOVER_PORTS;
    const fetchImpl = (_d = opts.fetchImpl) != null ? _d : fetch;
    const timeoutMs = (_e = opts.timeoutMs) != null ? _e : 2e3;
    for (const p of ports) {
      try {
        const controller = typeof AbortController === "function" ? new AbortController() : null;
        let timeoutId = null;
        if (controller) {
          timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        }
        const r = await fetchImpl(`http://127.0.0.1:${p}/api/stats`, {
          signal: controller == null ? void 0 : controller.signal
        });
        if (timeoutId) clearTimeout(timeoutId);
        if (r.ok) return `http://127.0.0.1:${p}/api`;
      } catch {
      }
    }
    return "";
  }
  async function apiRequest(baseUrl, method, path, body, opts) {
    const options = opts || {};
    const timeoutMs = typeof options.timeout === "number" ? options.timeout : 15e3;
    const silent = !!options.silent;
    const base = (baseUrl || "").replace(/\/$/, "");
    const m = (method || "GET").toUpperCase();
    const client = createApiClient({
      baseUrl: base,
      timeoutMs,
      silent
    });
    if (body !== void 0 && body !== null && body !== false) {
      return client.request(m, path, body, { timeoutMs, silent });
    }
    return client.request(m, path, void 0, { timeoutMs, silent });
  }
  function makeError(path, baseUrl, message, status, body, timeout) {
    const err = new Error(message);
    err.status = status;
    err.url = baseUrl + path;
    err.body = body;
    if (timeout) err.timeout = true;
    return err;
  }
  function createApiClient(opts) {
    const baseUrl = (opts.baseUrl || "").replace(/\/$/, "");
    const timeoutMs = typeof opts.timeoutMs === "number" ? opts.timeoutMs : 15e3;
    const fetchImpl = opts.fetchImpl || fetch;
    const silent = !!opts.silent;
    async function request(method, path, body, callOpts) {
      var _a, _b;
      const tMs = (_a = callOpts == null ? void 0 : callOpts.timeoutMs) != null ? _a : timeoutMs;
      const beSilent = (_b = callOpts == null ? void 0 : callOpts.silent) != null ? _b : silent;
      const controller = typeof AbortController === "function" ? new AbortController() : null;
      let timeoutId = null;
      if (controller) {
        timeoutId = setTimeout(() => controller.abort(), tMs);
      }
      try {
        const fetchOpts = {
          method,
          headers: { "Content-Type": "application/json" }
        };
        if (body !== void 0 && body !== null) {
          fetchOpts.body = JSON.stringify(body);
        }
        if (controller) fetchOpts.signal = controller.signal;
        const r = await fetchImpl(baseUrl + path, fetchOpts);
        const text = await r.text();
        const data = text ? safeJsonParse(text) : null;
        if (!r.ok) {
          const detail = data && typeof data === "object" && data !== null && "detail" in data ? String(data.detail) : text.slice(0, 200);
          const err = makeError(
            path,
            baseUrl,
            `API ${method} ${path} \u2192 ${r.status}: ${detail}`,
            r.status,
            data
          );
          if (!beSilent) console.error("[GnomTS.api]", err.message);
          throw err;
        }
        return data;
      } catch (e) {
        const ex = e;
        if (ex && ex.name === "AbortError") {
          const err2 = makeError(
            path,
            baseUrl,
            `API ${method} ${path} timed out after ${tMs}ms`,
            0,
            void 0,
            true
          );
          if (!beSilent) console.error("[GnomTS.api]", err2.message);
          throw err2;
        }
        if (ex && typeof ex.status === "number") throw e;
        const err = makeError(
          path,
          baseUrl,
          `API ${method} ${path} \u2192 network error: ${(ex == null ? void 0 : ex.message) || String(e)}`,
          0
        );
        if (!beSilent) console.error("[GnomTS.api]", err.message);
        throw err;
      } finally {
        if (timeoutId) clearTimeout(timeoutId);
      }
    }
    return {
      request,
      getHealth: () => request("GET", "/health"),
      getStats: () => request("GET", "/stats"),
      getAgents: () => request("GET", "/agents"),
      getChat: (limit = 50) => request(
        "GET",
        `/chat?limit=${limit}`
      ),
      postChat: (content, sender = "User") => request("POST", "/chat", { content, sender })
    };
  }

  // src/stats.ts
  function countAgentGroups(agentList) {
    const total = agentList.length;
    let sys = 0;
    for (const a of agentList) {
      const n = (a.name || "").trim();
      if (n && isSystemAgent(n)) sys += 1;
    }
    return { total, sys, work: total - sys };
  }
  function formatAgentsLine(stats, agentList = []) {
    var _a, _b, _c;
    const groups = countAgentGroups(agentList);
    const totalA = (_a = stats.agents) != null ? _a : groups.total;
    const sysA = (_b = stats.sys_agents) != null ? _b : groups.sys;
    const workA = (_c = stats.work_agents) != null ? _c : totalA - sysA;
    return `${totalA} (Sys: ${sysA} | Work: ${workA})`;
  }
  function formatTokensLine(stats) {
    var _a, _b;
    const tFree = (_a = stats.tokens_free) != null ? _a : 0;
    const tPay = (_b = stats.tokens_pay) != null ? _b : 0;
    return `Free: ${tFree} | Pay: ${tPay}`;
  }
  function formatQueueLine(queue) {
    if (!queue || typeof queue !== "object") return null;
    return `${queue.pending || 0}/${queue.processing || 0}/${queue.dead_letter || 0}`;
  }
  function formatLeases(leases) {
    const list = Array.isArray(leases) ? leases : [];
    const n = list.length;
    const who = list.map((l) => l.recipient).filter(Boolean).slice(0, 3).join(",");
    const text = n ? `${n}${who ? " " + who : ""}` : "0";
    const title = list.map((l) => `#${l.id} ${l.recipient || ""}`.trim()).join("\n") || "no active leases";
    return { text, title };
  }
  function formatLastError(lastError) {
    var _a;
    if (!lastError) return { text: "\u2014", title: "" };
    const text = `${(_a = lastError.status) != null ? _a : ""} ${lastError.recipient || ""}`.trim();
    let title = "";
    try {
      title = JSON.stringify(lastError);
    } catch {
      title = String(lastError);
    }
    return { text: text || "\u2014", title };
  }
  function formatStatsPanel(stats, agentList = []) {
    var _a;
    const q = stats.queue;
    const leases = stats.leases;
    const lastErr = stats.last_error;
    const leaseFmt = formatLeases(leases);
    const errFmt = formatLastError(lastErr);
    return {
      agents: formatAgentsLine(stats, agentList),
      memory: (_a = stats.memory) != null ? _a : 0,
      tokens: formatTokensLine(stats),
      queue: formatQueueLine(q),
      leases: leaseFmt.text,
      leasesTitle: leaseFmt.title,
      lastErr: errFmt.text,
      lastErrTitle: errFmt.title
    };
  }

  // src/security.ts
  function escapeHtml(str) {
    if (str == null) return "";
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  }

  // src/index.ts
  var GnomTS = {
    version: "0.2.0",
    FROZEN_AGENTS,
    SYSTEM_AGENTS,
    WORKER_AGENTS,
    KNOWN_COLORS,
    P_COLORS,
    agentColor,
    knownColor,
    isSystemAgent,
    isWorkerAgent,
    isFrozenAgent,
    extractMentions,
    countAgentMentions,
    isMultiMention,
    stripOnlyPrefix,
    withOnlyTarget,
    createApiClient,
    safeJsonParse,
    discoverApiBase,
    apiRequest,
    countAgentGroups,
    formatAgentsLine,
    formatTokensLine,
    formatQueueLine,
    formatLeases,
    formatLastError,
    formatStatsPanel,
    escapeHtml
  };
  var index_default = GnomTS;
  if (typeof window !== "undefined") {
    window.GnomTS = GnomTS;
  }
  return __toCommonJS(index_exports);
})();
