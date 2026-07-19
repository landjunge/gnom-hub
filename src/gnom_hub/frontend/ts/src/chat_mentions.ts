/**
 * Chat mention helpers.
 * Mirrors hub fan-out rules: multi-@ user messages should not storm workers;
 * backend uses only= for targeted delivery — UI can preview who is addressed.
 */

const MENTION_RE = /@([A-Za-z][A-Za-z0-9_]*)/g;

/** Extract unique @mentions (without the @), preserving first-seen order. */
export function extractMentions(text: string): string[] {
  if (!text) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  MENTION_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = MENTION_RE.exec(text)) !== null) {
    const name = m[1]!;
    const key = name.toLowerCase();
    // Skip double-@ system cmds handled as @@foo (regex still matches second part)
    const at = m.index;
    if (at > 0 && text[at - 1] === "@") continue;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(name);
  }
  return out;
}

/** Count user-facing agent mentions (not @@system). */
export function countAgentMentions(text: string): number {
  return extractMentions(text).length;
}

/**
 * Detect multi-@ fanout risk: more than one distinct agent mention.
 * UI can warn; backend already fans out with only= when targeted.
 */
export function isMultiMention(text: string): boolean {
  return extractMentions(text).length > 1;
}

/** Strip leading only=AgentName markers if present in drafts. */
export function stripOnlyPrefix(text: string): string {
  if (!text) return "";
  return text.replace(/^\s*only=\S+\s*/i, "").trimStart();
}

/** Build a targeted draft: only=<Agent> + message body. */
export function withOnlyTarget(agent: string, body: string): string {
  const clean = (body || "").replace(/^\s*only=\S+\s*/i, "").trim();
  return `only=${agent} ${clean}`.trim();
}
