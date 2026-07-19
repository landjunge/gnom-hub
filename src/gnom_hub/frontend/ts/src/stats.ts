/**
 * Pure stats-panel formatters (DOM stays in core.js updateStats).
 * Matches existing UI strings so core can delegate without visual change.
 */
import type { AgentInfo, HubStats } from "./types";
import { isSystemAgent } from "./agents";

export interface StatsPanelStrings {
  agents: string;
  memory: string | number;
  tokens: string;
  queue: string | null;
  leases: string;
  leasesTitle: string;
  lastErr: string;
  lastErrTitle: string;
  llm: string;
  llmTitle: string;
}

export interface QueueShape {
  pending?: number;
  processing?: number;
  dead_letter?: number;
}

export interface LeaseShape {
  id?: number | string;
  recipient?: string;
}

export interface LastErrorShape {
  status?: string | number;
  recipient?: string;
  [key: string]: unknown;
}

/** Count system vs worker agents from a live agent list. */
export function countAgentGroups(
  agentList: Array<Pick<AgentInfo, "name"> | { name?: string }>,
): { total: number; sys: number; work: number } {
  const total = agentList.length;
  let sys = 0;
  for (const a of agentList) {
    const n = (a.name || "").trim();
    if (n && isSystemAgent(n)) sys += 1;
  }
  return { total, sys, work: total - sys };
}

export function formatAgentsLine(
  stats: HubStats,
  agentList: Array<{ name?: string }> = [],
): string {
  const groups = countAgentGroups(agentList);
  const totalA = stats.agents ?? groups.total;
  const sysA = stats.sys_agents ?? groups.sys;
  const workA = stats.work_agents ?? totalA - sysA;
  return `${totalA} (Sys: ${sysA} | Work: ${workA})`;
}

export function formatTokensLine(stats: HubStats): string {
  const tFree = stats.tokens_free ?? 0;
  const tPay = stats.tokens_pay ?? 0;
  return `Free: ${tFree} | Pay: ${tPay}`;
}

export function formatQueueLine(queue: QueueShape | null | undefined): string | null {
  if (!queue || typeof queue !== "object") return null;
  return `${queue.pending || 0}/${queue.processing || 0}/${queue.dead_letter || 0}`;
}

export function formatLeases(
  leases: LeaseShape[] | null | undefined,
): { text: string; title: string } {
  const list = Array.isArray(leases) ? leases : [];
  const n = list.length;
  const who = list
    .map((l) => l.recipient)
    .filter(Boolean)
    .slice(0, 3)
    .join(",");
  const text = n ? `${n}${who ? " " + who : ""}` : "0";
  const title =
    list.map((l) => `#${l.id} ${l.recipient || ""}`.trim()).join("\n") ||
    "no active leases";
  return { text, title };
}

export function formatLastError(
  lastError: LastErrorShape | null | undefined,
): { text: string; title: string } {
  if (!lastError) return { text: "—", title: "" };
  const text = `${lastError.status ?? ""} ${lastError.recipient || ""}`.trim();
  let title = "";
  try {
    title = JSON.stringify(lastError);
  } catch {
    title = String(lastError);
  }
  return { text: text || "—", title };
}

/** Sidebar LLM line: active routing + probe tooltip. */
export function formatLlmLine(
  llm: HubStats["llm"] | null | undefined,
): { text: string; title: string } {
  if (!llm || typeof llm !== "object") {
    return { text: "—", title: "Kein LLM-Status (Probe noch nicht gelaufen?)" };
  }
  const text = (llm.summary || "—").trim() || "—";
  const lines: string[] = ["Aktive Agent-LLMs:"];
  const agents = llm.agents || {};
  const names = Object.keys(agents).sort();
  if (names.length) {
    for (const n of names) {
      const a = agents[n] || {};
      lines.push(`  ${n}: ${a.provider || "?"} / ${a.model || "?"}`);
    }
  } else {
    lines.push("  (keine llm_agents Map)");
  }
  const working = llm.working || [];
  if (working.length) {
    lines.push("", "Working free models:", "  " + working.slice(0, 8).join(", "));
  }
  const probe = llm.probe || {};
  if (probe.ts_iso || probe.ts) {
    lines.push("", `Letzter Probe: ${probe.ts_iso || probe.ts}`);
  }
  const failed = Array.isArray(probe.failed) ? probe.failed : [];
  if (failed.length) {
    lines.push(
      "Failed:",
      ...failed
        .slice(0, 8)
        .map((f) => `  ${f?.model || "?"} → ${f?.status ?? "?"}`),
    );
  }
  const repaired = Array.isArray(probe.repaired_agents)
    ? probe.repaired_agents
    : [];
  if (repaired.length) {
    lines.push("Auto-repair: " + repaired.join(", "));
  }
  return { text, title: lines.join("\n") };
}

/** Full panel payload for core.js updateStats. */
export function formatStatsPanel(
  stats: HubStats,
  agentList: Array<{ name?: string }> = [],
): StatsPanelStrings {
  const q = (stats as HubStats & { queue?: QueueShape }).queue;
  const leases = (stats as HubStats & { leases?: LeaseShape[] }).leases;
  const lastErr = (stats as HubStats & { last_error?: LastErrorShape }).last_error;
  const leaseFmt = formatLeases(leases);
  const errFmt = formatLastError(lastErr);
  const llmFmt = formatLlmLine(stats.llm);
  return {
    agents: formatAgentsLine(stats, agentList),
    memory: stats.memory ?? 0,
    tokens: formatTokensLine(stats),
    queue: formatQueueLine(q),
    leases: leaseFmt.text,
    leasesTitle: leaseFmt.title,
    lastErr: errFmt.text,
    lastErrTitle: errFmt.title,
    llm: llmFmt.text,
    llmTitle: llmFmt.title,
  };
}
