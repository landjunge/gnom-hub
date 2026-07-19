/** Shared API / UI types for the gradual TS frontend (S5). */

export type AgentStatus = "online" | "offline" | "busy" | "error" | string;

export interface AgentInfo {
  name: string;
  status?: AgentStatus;
  role?: string;
  group?: string;
  capabilities?: string[];
  color?: string;
}

export interface HubHealth {
  status?: string;
  healthy?: number;
  agents?: number;
  [key: string]: unknown;
}

export interface HubStats {
  agents?: number;
  sys_agents?: number;
  work_agents?: number;
  memory?: number;
  tokens_free?: number;
  tokens_pay?: number;
  queue_pending?: number;
  queue?: {
    pending?: number;
    processing?: number;
    dead_letter?: number;
  };
  leases?: Array<{ id?: number | string; recipient?: string }>;
  last_error?: {
    status?: string | number;
    recipient?: string;
    [key: string]: unknown;
  };
  llm?: {
    summary?: string;
    agents?: Record<string, { provider?: string; model?: string }>;
    working?: string[];
    probe?: {
      ts?: number;
      ts_iso?: string;
      failed?: Array<{ model?: string; status?: number }>;
      repaired_agents?: string[];
      [key: string]: unknown;
    };
  };
  [key: string]: unknown;
}

export interface ApiCallOptions {
  timeout?: number;
  silent?: boolean;
}

export interface ChatMessage {
  id?: number | string;
  msg_id?: number | string;
  sender?: string;
  content?: string;
  text?: string;
  timestamp?: string;
  context_id?: string;
}

export interface ApiErrorShape {
  status: number;
  url: string;
  message: string;
  body?: unknown;
  timeout?: boolean;
}

export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface ApiClientOptions {
  /** Base URL ending with /api (or empty to use relative /api). */
  baseUrl: string;
  timeoutMs?: number;
  silent?: boolean;
  fetchImpl?: typeof fetch;
}
