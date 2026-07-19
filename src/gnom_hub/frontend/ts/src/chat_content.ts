/**
 * Message content pure transforms: thoughts, speech filters, showbox strip.
 */
import { extractMentions, isMultiMention } from "./chat_mentions";

const INVISIBLE_TRAIL_RE =
  /[\u200B-\u200D\uFEFF\u2060\u2061\u2062\u2063\u2064\u00AD\u034F\u115F\u1160\u17B4\u17B5\u180E\u2028\u2029\u202A-\u202E\u2066-\u2069\u2800\u3164\uFFA0]+$/g;

const THINK_STRIP_RE = /<think>[\s\S]*?<\/think>/gi;

export function stripInvisibleTrailing(text: string): string {
  if (!text) return "";
  return text.replace(INVISIBLE_TRAIL_RE, "");
}

export function extractThoughtsAndClean(content: string | null | undefined): {
  thoughts: string[];
  cleaned: string;
} {
  const thoughts: string[] = [];
  const cleaned = content || "";
  let match: RegExpExecArray | null;
  const re = /<think>([\s\S]*?)<\/think>/gi;
  while ((match = re.exec(cleaned)) !== null) {
    const t = (match[1] || "").trim();
    if (t) thoughts.push(t);
  }
  const finalCleaned = cleaned.replace(THINK_STRIP_RE, "").trim();
  return { thoughts, cleaned: finalCleaned };
}

export function isSystemLogMessage(text: string): boolean {
  const cleaned = text || "";
  const lower = cleaned.toLowerCase().trim();
  return (
    cleaned.includes("[AUTO-APPROVED]") ||
    cleaned.includes("heartbeat") ||
    cleaned.includes("status=") ||
    lower.includes("status online") ||
    lower.includes("status busy")
  );
}

const AGENT_AT_PREFIXES = [
  "@coderag",
  "@researcherag",
  "@writerag",
  "@editorag",
  "@generalag",
  "@watchdogag",
  "@securityag",
  "@soulag",
];

export function isAgentToAgentMessage(text: string): boolean {
  const lower = (text || "").toLowerCase().trim();
  return AGENT_AT_PREFIXES.some((p) => lower.startsWith(p));
}

/** Replace action tags with short German speech phrases (chat.js TTS path). */
export function cleanActionTagsForSpeech(text: string): string {
  let speechText = text || "";
  speechText = speechText
    .replace(
      /\[WRITE:\s*([^\]\n]+)\]([\s\S]*?)\[\/WRITE\]/gi,
      "schreibt Datei $1",
    )
    .replace(/\[SHELL:\s*([^\]\n]+)\]/gi, "führt Befehl $1 aus")
    .replace(/\[READ:\s*([^\]\n]+)\]/gi, "liest Datei $1")
    .replace(/\[BROWSER:\s*([^\]\n]+)\]/gi, "führt Browser-Aktion $1 aus")
    .replace(/\[IMAGE:\s*([^\]\n]+)\]/gi, "generiert Bild $1")
    .replace(/<SHOWBOX[\s\S]*?<\/SHOWBOX>/gi, "")
    .trim();
  speechText = speechText
    .replace(/^@user\s*/gi, "")
    .replace(/^@\w+\s*/g, "")
    .trim();
  return speechText;
}

export interface OutgoingChatPrep {
  trimmed: string;
  empty: boolean;
  multiMentionToast: string | null;
  localCommand: boolean;
}

/**
 * Pure pre-send pipeline for the chat input value.
 */
export function prepareOutgoingChat(
  raw: string,
  opts?: { isLocalCommand?: (msg: string) => boolean },
): OutgoingChatPrep {
  const trimmed = (raw || "").trim();
  if (!trimmed) {
    return {
      trimmed: "",
      empty: true,
      multiMentionToast: null,
      localCommand: false,
    };
  }
  const localFn = opts?.isLocalCommand;
  const localCommand = localFn ? localFn(trimmed) : false;
  let multiMentionToast: string | null = null;
  if (!localCommand && isMultiMention(trimmed)) {
    const names = extractMentions(trimmed).join(", ");
    multiMentionToast = `🎯 Multi-@ → ${names} (targeted only=)`;
  }
  return {
    trimmed,
    empty: false,
    multiMentionToast,
    localCommand,
  };
}
