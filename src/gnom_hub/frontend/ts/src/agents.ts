/** Frozen agent names + color helpers (parity with core.js KNOWN_COLORS). */

export const FROZEN_AGENTS = [
  "SoulAG",
  "GeneralAG",
  "SecurityAG",
  "WatchdogAG",
  "ResearcherAG",
  "WriterAG",
  "EditorAG",
  "CoderAG",
] as const;

export type FrozenAgent = (typeof FROZEN_AGENTS)[number];

export const SYSTEM_AGENTS = [
  "SoulAG",
  "GeneralAG",
  "SecurityAG",
  "WatchdogAG",
] as const;

export const WORKER_AGENTS = [
  "CoderAG",
  "WriterAG",
  "EditorAG",
  "ResearcherAG",
] as const;

/** Matches core.js KNOWN_COLORS keys (lowercase). */
export const KNOWN_COLORS: Readonly<Record<string, string>> = {
  soulag: "#FF5E00",
  generalag: "#00FFFF",
  securityag: "#FF69B4",
  watchdogag: "#FFA500",
  researcherag: "#FFFF00",
  writerag: "#00FF00",
  editorag: "#0088FF",
  coderag: "#FF0000",
};

/** Matches core.js P_COLORS palette for hash fallback. */
export const P_COLORS: readonly string[] = [
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
  "#00FFFF",
];

function djb2(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  }
  return h;
}

export function knownColor(name: string): string | null {
  if (!name) return null;
  return KNOWN_COLORS[name.toLowerCase()] ?? null;
}

/** Same algorithm as core.js agentColor. */
export function agentColor(name: string | null | undefined): string {
  if (!name) return "#00E5FF";
  const known = knownColor(name);
  if (known) return known;
  const h = djb2(name);
  return P_COLORS[Math.abs(h) % P_COLORS.length]!;
}

export function isSystemAgent(name: string): boolean {
  const n = name.toLowerCase();
  return (SYSTEM_AGENTS as readonly string[]).some((a) => a.toLowerCase() === n);
}

export function isWorkerAgent(name: string): boolean {
  const n = name.toLowerCase();
  return (WORKER_AGENTS as readonly string[]).some((a) => a.toLowerCase() === n);
}

export function isFrozenAgent(name: string): boolean {
  const n = name.toLowerCase();
  return (FROZEN_AGENTS as readonly string[]).some((a) => a.toLowerCase() === n);
}
