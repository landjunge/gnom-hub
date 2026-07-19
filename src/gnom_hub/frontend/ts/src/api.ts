import type {
  ApiClientOptions,
  ApiErrorShape,
  ChatMessage,
  HttpMethod,
  HubHealth,
  HubStats,
  AgentInfo,
} from "./types";

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
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
