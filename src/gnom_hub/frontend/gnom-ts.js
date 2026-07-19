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
    countAgentMentions: () => countAgentMentions,
    createApiClient: () => createApiClient,
    default: () => index_default,
    extractMentions: () => extractMentions,
    isFrozenAgent: () => isFrozenAgent,
    isMultiMention: () => isMultiMention,
    isSystemAgent: () => isSystemAgent,
    isWorkerAgent: () => isWorkerAgent,
    knownColor: () => knownColor,
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

  // src/index.ts
  var GnomTS = {
    version: "0.1.0",
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
    createApiClient
  };
  var index_default = GnomTS;
  if (typeof window !== "undefined") {
    window.GnomTS = GnomTS;
  }
  return __toCommonJS(index_exports);
})();
