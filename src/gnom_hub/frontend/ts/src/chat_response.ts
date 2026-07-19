/** Format toast text from POST /chat response (parity with chat.js sendChat). */

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
  agents?: Array<{ name?: string; role?: string }>;
  target?: string;
  asked?: string[];
  mode?: string;
  [key: string]: unknown;
}

export function formatChatResponseToast(
  res: ChatPostResponse | null | undefined,
): ChatToast {
  if (!res) {
    return { message: "Hub unreachable", type: "error" };
  }
  if (res.status === "role_set") {
    return {
      message: `👑 ${res.agent || "?"} → ${res.role || "?"}`,
      type: "success",
    };
  }
  if (res.status === "idea_saved") {
    return { message: "💡 Idea saved", type: "success" };
  }
  if (res.status === "job_created") {
    const task = (res.task || "").substring(0, 60);
    return {
      message: `📋 Job → ${res.general || "?"}: ${task}`,
      type: "success",
    };
  }
  if (res.msg) {
    return { message: `⚠️ ${res.msg}`, type: "error" };
  }
  if (res.status === "cleared") {
    return { message: "🗑 Chat cleared", type: "success" };
  }
  if (res.status === "agents" && Array.isArray(res.agents)) {
    const list = res.agents
      .map((a) => `${a.name || "?"}(${a.role || "?"})`)
      .join(", ");
    return { message: `📊 ${list}`, type: "info" };
  }
  const target = res.target
    ? `→ ${res.target}`
    : `→ ${(res.asked || []).join(", ") || "nobody"}`;
  const icon =
    res.mode === "brainstorm" ? "🧠" : res.mode === "research" ? "🔍" : "💬";
  return { message: `${icon} ${target}`, type: "success" };
}
