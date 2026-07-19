/** Format toast text from POST /chat response (parity + gap-fixes for backend shapes). */

export type ToastType = "success" | "error" | "info";

export interface ChatToast {
  message: string;
  type: ToastType;
}

export interface ChatPostResponse {
  status?: string;
  agent?: string;
  role?: string;
  general?: string;
  task?: string;
  msg?: string;
  message?: string;
  error?: string;
  agents?: Array<{ name?: string; role?: string; st?: string }>;
  target?: string;
  asked?: string[] | string | null;
  mode?: string;
  steps?: number;
  workflow_id?: string;
  [key: string]: unknown;
}

function detailOf(res: ChatPostResponse): string {
  const d = res.msg ?? res.message ?? res.error;
  return d != null ? String(d).trim() : "";
}

function askedList(res: ChatPostResponse): string[] {
  const a = res.asked;
  if (Array.isArray(a)) return a.map(String).filter(Boolean);
  if (typeof a === "string" && a.trim()) return [a.trim()];
  return [];
}

/**
 * Map every common backend chat response into a toast.
 * Critical: `status: "error"` often uses `message` (not `msg`);
 * `status: "saved"` with `msg` is soft-info (DB busy), not a hard error.
 */
export function formatChatResponseToast(
  res: ChatPostResponse | null | undefined,
): ChatToast {
  if (!res) {
    return { message: "Hub unreachable", type: "error" };
  }

  const status = String(res.status || "").toLowerCase();
  const detail = detailOf(res);

  // Hard failures first
  if (status === "blocked") {
    return {
      message: `🚨 ${detail || "Prompt blockiert"}`,
      type: "error",
    };
  }
  if (status === "error" || (res.error && !status)) {
    return {
      message: `⚠️ ${detail || String(res.error || "Fehler")}`,
      type: "error",
    };
  }

  if (status === "role_set") {
    return {
      message: `👑 ${res.agent || "?"} → ${res.role || "?"}`,
      type: "success",
    };
  }
  if (status === "idea_saved") {
    return { message: "💡 Idea saved", type: "success" };
  }
  if (status === "job_created") {
    const task = (res.task || "").toString().substring(0, 60);
    const who = res.general || "?";
    return {
      message: task
        ? `📋 Job → ${who}: ${task}`
        : `📋 Job erstellt → ${who}`,
      type: "success",
    };
  }
  if (
    status === "cleared" ||
    status === "agents_cleared" ||
    status === "project_cleared"
  ) {
    return { message: "🗑 Chat cleared", type: "success" };
  }

  // @merken / agent self-save / soft DB-busy after user message stored
  if (status === "saved") {
    if (detail) {
      // e.g. "Nachricht gespeichert, Dispatch wartet (DB busy)…"
      const soft = /busy|wartet|gespeichert/i.test(detail);
      return {
        message: soft ? `💾 ${detail}` : `💾 ${detail}`,
        type: soft ? "info" : "success",
      };
    }
    return { message: "💾 Gespeichert", type: "success" };
  }

  if (status === "workflow_started") {
    const steps = res.steps != null ? String(res.steps) : "?";
    const id =
      typeof res.workflow_id === "string"
        ? res.workflow_id.slice(0, 8)
        : "";
    return {
      message: id
        ? `🔄 Workflow gestartet (${steps} Steps, ${id}…)`
        : `🔄 Workflow gestartet (${steps} Steps)`,
      type: "success",
    };
  }

  if (status === "ok") {
    return {
      message: detail ? `✅ ${detail}` : "✅ OK",
      type: "success",
    };
  }

  // @@status → { agents: [...] } without status field (legacy)
  if (
    status === "agents" ||
    (Array.isArray(res.agents) && !status && !res.mode)
  ) {
    const list = (res.agents || [])
      .map((a) => {
        const st = a.st ? `/${a.st}` : "";
        return `${a.name || "?"}(${a.role || "?"}${st})`;
      })
      .join(", ");
    return { message: `📊 ${list || "(keine Agenten)"}`, type: "info" };
  }

  // Dispatch paths
  const asked = askedList(res);
  if (
    status === "dispatched" ||
    status === "chat" ||
    asked.length > 0 ||
    res.target ||
    res.mode
  ) {
    const target = res.target
      ? `→ ${res.target}`
      : `→ ${asked.join(", ") || "nobody"}`;
    const icon =
      res.mode === "brainstorm"
        ? "🧠"
        : res.mode === "research"
          ? "🔍"
          : res.mode === "worker"
            ? "👷"
            : "💬";
    // Empty asked on "dispatched" is unusual; still show target
    if (status === "dispatched" || asked.length || res.target || res.mode) {
      return { message: `${icon} ${target}`, type: "success" };
    }
  }

  // leftover detail without classified status
  if (detail) {
    return { message: `ℹ️ ${detail}`, type: "info" };
  }

  return { message: "💬 OK", type: "success" };
}
