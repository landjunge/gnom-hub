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
    CHAT_HISTORY_KEY: () => CHAT_HISTORY_KEY,
    CHAT_HISTORY_MAX: () => CHAT_HISTORY_MAX,
    FROZEN_AGENTS: () => FROZEN_AGENTS,
    KNOWN_COLORS: () => KNOWN_COLORS,
    P_COLORS: () => P_COLORS,
    SYSTEM_AGENTS: () => SYSTEM_AGENTS,
    WORKER_AGENTS: () => WORKER_AGENTS,
    agentColor: () => agentColor,
    apiRequest: () => apiRequest,
    classifyLocalCommand: () => classifyLocalCommand,
    cleanActionTagsForSpeech: () => cleanActionTagsForSpeech,
    countAgentGroups: () => countAgentGroups,
    countAgentMentions: () => countAgentMentions,
    createApiClient: () => createApiClient,
    default: () => index_default,
    discoverApiBase: () => discoverApiBase,
    escapeHtml: () => escapeHtml,
    extractMentions: () => extractMentions,
    extractThoughtsAndClean: () => extractThoughtsAndClean,
    formatAgentsLine: () => formatAgentsLine,
    formatChatResponseToast: () => formatChatResponseToast,
    formatLastError: () => formatLastError,
    formatLeases: () => formatLeases,
    formatQueueLine: () => formatQueueLine,
    formatStatsPanel: () => formatStatsPanel,
    formatTokensLine: () => formatTokensLine,
    isAgentToAgentMessage: () => isAgentToAgentMessage,
    isFrozenAgent: () => isFrozenAgent,
    isLocalCommand: () => isLocalCommand,
    isMultiMention: () => isMultiMention,
    isSystemAgent: () => isSystemAgent,
    isSystemLogMessage: () => isSystemLogMessage,
    isWorkerAgent: () => isWorkerAgent,
    knownColor: () => knownColor,
    loadChatHistory: () => loadChatHistory,
    navigateChatHistory: () => navigateChatHistory,
    prepareOutgoingChat: () => prepareOutgoingChat,
    pushChatHistory: () => pushChatHistory,
    safeJsonParse: () => safeJsonParse,
    stripInvisibleTrailing: () => stripInvisibleTrailing,
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

  // src/chat_history.ts
  var CHAT_HISTORY_KEY = "chatHistory";
  var CHAT_HISTORY_MAX = 50;
  function loadChatHistory(storage, key = CHAT_HISTORY_KEY) {
    try {
      const raw = storage.getItem(key);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.map(String) : [];
    } catch {
      return [];
    }
  }
  function pushChatHistory(storage, msg, max = CHAT_HISTORY_MAX, key = CHAT_HISTORY_KEY) {
    if (!msg) return loadChatHistory(storage, key);
    let history = loadChatHistory(storage, key);
    if (history.length === 0 || history[history.length - 1] !== msg) {
      history = history.concat([msg]);
      if (history.length > max) {
        history = history.slice(history.length - max);
      }
      try {
        storage.setItem(key, JSON.stringify(history));
      } catch {
      }
    }
    return history;
  }
  function navigateChatHistory(direction, history, state, currentValue) {
    if (!history.length) {
      return { state, value: currentValue, changed: false };
    }
    let idx = state.idx;
    let draft = state.draft;
    let value = currentValue;
    let changed = false;
    if (direction === "up") {
      if (idx === -1) {
        draft = currentValue;
        idx = history.length - 1;
        value = history[idx];
        changed = true;
      } else if (idx > 0) {
        idx -= 1;
        value = history[idx];
        changed = true;
      }
    } else {
      if (idx === -1) {
        return { state, value: currentValue, changed: false };
      }
      if (idx < history.length - 1) {
        idx += 1;
        value = history[idx];
        changed = true;
      } else {
        idx = -1;
        value = draft;
        changed = true;
      }
    }
    return { state: { idx, draft }, value, changed };
  }

  // src/chat_commands.ts
  var SHOWBOX_NAME_RE = /^[a-zA-Z0-9_-]+$/;
  function classifyLocalCommand(msg) {
    const m = (msg || "").toLowerCase().trim();
    if (!m) return { kind: "none" };
    if (m === "@tts on") return { kind: "tts_on" };
    if (m === "@tts off") return { kind: "tts_off" };
    if (m === "@tts") return { kind: "tts_toggle" };
    if (m === "/ufo") return { kind: "easter", cmd: "ufo" };
    if (m === "/ghost") return { kind: "easter", cmd: "ghost" };
    if (m === "/coffee") return { kind: "easter", cmd: "coffee" };
    if (m === "@system save") return { kind: "system_save" };
    if (m === "@system unsave") return { kind: "system_unsave" };
    if (m.startsWith("@showbox speed ")) {
      const speedVal = parseFloat(m.substring("@showbox speed ".length).trim());
      const valid = !Number.isNaN(speedVal) && speedVal > 0;
      return { kind: "showbox_speed", seconds: speedVal, valid };
    }
    if (m.startsWith("@showbox ")) {
      const name = msg.trim().substring("@showbox ".length).trim();
      return {
        kind: "showbox_load",
        name,
        valid: SHOWBOX_NAME_RE.test(name)
      };
    }
    if (m === "@@slides" || m === "@@hilfe-slides" || m === "@@hilfeslides") {
      return { kind: "help_slides" };
    }
    if (m === "@@artshow" || m === "@@art" || m === "@@art-show") {
      return { kind: "art_show" };
    }
    return { kind: "none" };
  }
  function isLocalCommand(msg) {
    return classifyLocalCommand(msg).kind !== "none";
  }

  // src/chat_response.ts
  function detailOf(res) {
    var _a, _b;
    const d = (_b = (_a = res.msg) != null ? _a : res.message) != null ? _b : res.error;
    return d != null ? String(d).trim() : "";
  }
  function askedList(res) {
    const a = res.asked;
    if (Array.isArray(a)) return a.map(String).filter(Boolean);
    if (typeof a === "string" && a.trim()) return [a.trim()];
    return [];
  }
  function formatChatResponseToast(res) {
    if (!res) {
      return { message: "Hub unreachable", type: "error" };
    }
    const status = String(res.status || "").toLowerCase();
    const detail = detailOf(res);
    if (status === "blocked") {
      return {
        message: `\u{1F6A8} ${detail || "Prompt blockiert"}`,
        type: "error"
      };
    }
    if (status === "error" || res.error && !status) {
      return {
        message: `\u26A0\uFE0F ${detail || String(res.error || "Fehler")}`,
        type: "error"
      };
    }
    if (status === "role_set") {
      return {
        message: `\u{1F451} ${res.agent || "?"} \u2192 ${res.role || "?"}`,
        type: "success"
      };
    }
    if (status === "idea_saved") {
      return { message: "\u{1F4A1} Idea saved", type: "success" };
    }
    if (status === "job_created") {
      const task = (res.task || "").toString().substring(0, 60);
      const who = res.general || "?";
      return {
        message: task ? `\u{1F4CB} Job \u2192 ${who}: ${task}` : `\u{1F4CB} Job erstellt \u2192 ${who}`,
        type: "success"
      };
    }
    if (status === "cleared" || status === "agents_cleared" || status === "project_cleared") {
      return { message: "\u{1F5D1} Chat cleared", type: "success" };
    }
    if (status === "saved") {
      if (detail) {
        const soft = /busy|wartet|gespeichert/i.test(detail);
        return {
          message: soft ? `\u{1F4BE} ${detail}` : `\u{1F4BE} ${detail}`,
          type: soft ? "info" : "success"
        };
      }
      return { message: "\u{1F4BE} Gespeichert", type: "success" };
    }
    if (status === "workflow_started") {
      const steps = res.steps != null ? String(res.steps) : "?";
      const id = typeof res.workflow_id === "string" ? res.workflow_id.slice(0, 8) : "";
      return {
        message: id ? `\u{1F504} Workflow gestartet (${steps} Steps, ${id}\u2026)` : `\u{1F504} Workflow gestartet (${steps} Steps)`,
        type: "success"
      };
    }
    if (status === "ok") {
      return {
        message: detail ? `\u2705 ${detail}` : "\u2705 OK",
        type: "success"
      };
    }
    if (status === "agents" || Array.isArray(res.agents) && !status && !res.mode) {
      const list = (res.agents || []).map((a) => {
        const st = a.st ? `/${a.st}` : "";
        return `${a.name || "?"}(${a.role || "?"}${st})`;
      }).join(", ");
      return { message: `\u{1F4CA} ${list || "(keine Agenten)"}`, type: "info" };
    }
    const asked = askedList(res);
    if (status === "dispatched" || status === "chat" || asked.length > 0 || res.target || res.mode) {
      const target = res.target ? `\u2192 ${res.target}` : `\u2192 ${asked.join(", ") || "nobody"}`;
      const icon = res.mode === "brainstorm" ? "\u{1F9E0}" : res.mode === "research" ? "\u{1F50D}" : res.mode === "worker" ? "\u{1F477}" : "\u{1F4AC}";
      if (status === "dispatched" || asked.length || res.target || res.mode) {
        return { message: `${icon} ${target}`, type: "success" };
      }
    }
    if (detail) {
      return { message: `\u2139\uFE0F ${detail}`, type: "info" };
    }
    return { message: "\u{1F4AC} OK", type: "success" };
  }

  // src/chat_content.ts
  var INVISIBLE_TRAIL_RE = /[\u200B-\u200D\uFEFF\u2060\u2061\u2062\u2063\u2064\u00AD\u034F\u115F\u1160\u17B4\u17B5\u180E\u2028\u2029\u202A-\u202E\u2066-\u2069\u2800\u3164\uFFA0]+$/g;
  var THINK_STRIP_RE = /<think>[\s\S]*?<\/think>/gi;
  function stripInvisibleTrailing(text) {
    if (!text) return "";
    return text.replace(INVISIBLE_TRAIL_RE, "");
  }
  function extractThoughtsAndClean(content) {
    const thoughts = [];
    const cleaned = content || "";
    let match;
    const re = /<think>([\s\S]*?)<\/think>/gi;
    while ((match = re.exec(cleaned)) !== null) {
      const t = (match[1] || "").trim();
      if (t) thoughts.push(t);
    }
    const finalCleaned = cleaned.replace(THINK_STRIP_RE, "").trim();
    return { thoughts, cleaned: finalCleaned };
  }
  function isSystemLogMessage(text) {
    const cleaned = text || "";
    const lower = cleaned.toLowerCase().trim();
    return cleaned.includes("[AUTO-APPROVED]") || cleaned.includes("heartbeat") || cleaned.includes("status=") || lower.includes("status online") || lower.includes("status busy");
  }
  var AGENT_AT_PREFIXES = [
    "@coderag",
    "@researcherag",
    "@writerag",
    "@editorag",
    "@generalag",
    "@watchdogag",
    "@securityag",
    "@soulag"
  ];
  function isAgentToAgentMessage(text) {
    const lower = (text || "").toLowerCase().trim();
    return AGENT_AT_PREFIXES.some((p) => lower.startsWith(p));
  }
  function cleanActionTagsForSpeech(text) {
    let speechText = text || "";
    speechText = speechText.replace(
      /\[WRITE:\s*([^\]\n]+)\]([\s\S]*?)\[\/WRITE\]/gi,
      "schreibt Datei $1"
    ).replace(/\[SHELL:\s*([^\]\n]+)\]/gi, "f\xFChrt Befehl $1 aus").replace(/\[READ:\s*([^\]\n]+)\]/gi, "liest Datei $1").replace(/\[BROWSER:\s*([^\]\n]+)\]/gi, "f\xFChrt Browser-Aktion $1 aus").replace(/\[IMAGE:\s*([^\]\n]+)\]/gi, "generiert Bild $1").replace(/<SHOWBOX[\s\S]*?<\/SHOWBOX>/gi, "").trim();
    speechText = speechText.replace(/^@user\s*/gi, "").replace(/^@\w+\s*/g, "").trim();
    return speechText;
  }
  function prepareOutgoingChat(raw, opts) {
    const trimmed = (raw || "").trim();
    if (!trimmed) {
      return {
        trimmed: "",
        empty: true,
        multiMentionToast: null,
        localCommand: false
      };
    }
    const localFn = opts == null ? void 0 : opts.isLocalCommand;
    const localCommand = localFn ? localFn(trimmed) : false;
    let multiMentionToast = null;
    if (!localCommand && isMultiMention(trimmed)) {
      const names = extractMentions(trimmed).join(", ");
      multiMentionToast = `\u{1F3AF} Multi-@ \u2192 ${names} (targeted only=)`;
    }
    return {
      trimmed,
      empty: false,
      multiMentionToast,
      localCommand
    };
  }

  // src/index.ts
  var GnomTS = {
    version: "0.3.1",
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
    escapeHtml,
    CHAT_HISTORY_KEY,
    CHAT_HISTORY_MAX,
    loadChatHistory,
    pushChatHistory,
    navigateChatHistory,
    classifyLocalCommand,
    isLocalCommand,
    formatChatResponseToast,
    stripInvisibleTrailing,
    extractThoughtsAndClean,
    isSystemLogMessage,
    isAgentToAgentMessage,
    cleanActionTagsForSpeech,
    prepareOutgoingChat
  };
  var index_default = GnomTS;
  if (typeof window !== "undefined") {
    window.GnomTS = GnomTS;
  }
  return __toCommonJS(index_exports);
})();
