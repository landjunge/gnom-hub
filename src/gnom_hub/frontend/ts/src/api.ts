import type {
  ApiCallOptions,
  ApiClientOptions,
  ApiErrorShape,
  ChatMessage,
  HttpMethod,
  HubHealth,
  HubStats,
  AgentInfo,
} from "./types";

/** Same contract as core.js safeJsonParse — export for progressive use. */
export function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

const DEFAULT_DISCOVER_PORTS = [3003, 3002, 3001, 3000] as const;

export interface DiscoverApiBaseOptions {
  /** browser location.protocol; if not "file:", use origin + /api */
  protocol?: string;
  origin?: string;
  ports?: readonly number[];
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

/**
 * Resolve API base URL (…/api). Parity with core.js discoverPort.
 * Returns "" if nothing reachable (file:// probe failed).
 */
export async function discoverApiBase(
  opts: DiscoverApiBaseOptions = {},
): Promise<string> {
  const protocol = opts.protocol ?? (typeof location !== "undefined" ? location.protocol : "http:");
  const origin = opts.origin ?? (typeof location !== "undefined" ? location.origin : "");
  if (protocol !== "file:") {
    if (origin) return origin.replace(/\/$/, "") + "/api";
    return "/api";
  }
  const ports = opts.ports ?? DEFAULT_DISCOVER_PORTS;
  const fetchImpl = opts.fetchImpl ?? fetch;
  const timeoutMs = opts.timeoutMs ?? 2000;
  for (const p of ports) {
    try {
      const controller =
        typeof AbortController === "function" ? new AbortController() : null;
      let timeoutId: ReturnType<typeof setTimeout> | null = null;
      if (controller) {
        timeoutId = setTimeout(() => controller.abort(), timeoutMs);
      }
      const r = await fetchImpl(`http://127.0.0.1:${p}/api/stats`, {
        signal: controller?.signal,
      });
      if (timeoutId) clearTimeout(timeoutId);
      if (r.ok) return `http://127.0.0.1:${p}/api`;
    } catch {
      /* try next port */
    }
  }
  return "";
}

/**
 * Drop-in for core.js `api(method, path, body, opts)`.
 * Uses explicit baseUrl (window.API) so globals stay owned by core.js.
 */
export async function apiRequest(
  baseUrl: string,
  method: string,
  path: string,
  body?: unknown,
  opts?: ApiCallOptions,
): Promise<unknown> {
  const options = opts || {};
  const timeoutMs =
    typeof options.timeout === "number" ? options.timeout : 15000;
  const silent = !!options.silent;
  const base = (baseUrl || "").replace(/\/$/, "");
  const m = (method || "GET").toUpperCase() as HttpMethod;
  const client = createApiClient({
    baseUrl: base,
    timeoutMs,
    silent,
  });
  // Only send body when present (matches core.js: if (body) …)
  if (body !== undefined && body !== null && body !== false) {
    return client.request(m, path, body, { timeoutMs, silent });
  }
  return client.request(m, path, undefined, { timeoutMs, silent });
}

function makeError(
  path: string,
  baseUrl: string,
  message: string,
  status: number,
  body?: unknown,
  timeout?: boolean,
): Error & ApiErrorShape {
  const err = new Error(message) as Error & ApiErrorShape;
  err.status = status;
  err.url = baseUrl + path;
  err.body = body;
  if (timeout) err.timeout = true;
  return err;
}

/**
 * Typed thin client over the same contract as core.js `api()`.
 * Does not replace the global; optional progressive use via GnomTS.createApiClient.
 */
export function createApiClient(opts: ApiClientOptions) {
  const baseUrl = (opts.baseUrl || "").replace(/\/$/, "");
  const timeoutMs = typeof opts.timeoutMs === "number" ? opts.timeoutMs : 15000;
  const fetchImpl = opts.fetchImpl || fetch;
  const silent = !!opts.silent;

  async function request<T = unknown>(
    method: HttpMethod,
    path: string,
    body?: unknown,
    callOpts?: { timeoutMs?: number; silent?: boolean },
  ): Promise<T> {
    const tMs = callOpts?.timeoutMs ?? timeoutMs;
    const beSilent = callOpts?.silent ?? silent;
    const controller =
      typeof AbortController === "function" ? new AbortController() : null;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    if (controller) {
      timeoutId = setTimeout(() => controller.abort(), tMs);
    }
    try {
      const fetchOpts: RequestInit = {
        method,
        headers: { "Content-Type": "application/json" },
      };
      // Match core.js: only serialize when body is truthy / explicitly provided
      if (body !== undefined && body !== null) {
        fetchOpts.body = JSON.stringify(body);
      }
      if (controller) fetchOpts.signal = controller.signal;

      const r = await fetchImpl(baseUrl + path, fetchOpts);
      const text = await r.text();
      const data = text ? safeJsonParse(text) : null;

      if (!r.ok) {
        const detail =
          data && typeof data === "object" && data !== null && "detail" in data
            ? String((data as { detail: unknown }).detail)
            : text.slice(0, 200);
        const err = makeError(
          path,
          baseUrl,
          `API ${method} ${path} → ${r.status}: ${detail}`,
          r.status,
          data,
        );
        if (!beSilent) console.error("[GnomTS.api]", err.message);
        throw err;
      }
      return data as T;
    } catch (e) {
      const ex = e as { name?: string; status?: number; message?: string };
      if (ex && ex.name === "AbortError") {
        const err = makeError(
          path,
          baseUrl,
          `API ${method} ${path} timed out after ${tMs}ms`,
          0,
          undefined,
          true,
        );
        if (!beSilent) console.error("[GnomTS.api]", err.message);
        throw err;
      }
      if (ex && typeof ex.status === "number") throw e;
      const err = makeError(
        path,
        baseUrl,
        `API ${method} ${path} → network error: ${ex?.message || String(e)}`,
        0,
      );
      if (!beSilent) console.error("[GnomTS.api]", err.message);
      throw err;
    } finally {
      if (timeoutId) clearTimeout(timeoutId);
    }
  }

  return {
    request,
    getHealth: () => request<HubHealth>("GET", "/health"),
    getStats: () => request<HubStats>("GET", "/stats"),
    getAgents: () => request<AgentInfo[] | { agents: AgentInfo[] }>("GET", "/agents"),
    getChat: (limit = 50) =>
      request<ChatMessage[] | { messages: ChatMessage[] }>(
        "GET",
        `/chat?limit=${limit}`,
      ),
    postChat: (content: string, sender = "User") =>
      request("POST", "/chat", { content, sender }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
