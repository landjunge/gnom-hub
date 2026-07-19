/**
 * Classify local (client-only) chat commands before hub POST.
 * Side effects stay in chat.js; this only parses.
 */

export type LocalCommand =
  | { kind: "tts_on" }
  | { kind: "tts_off" }
  | { kind: "tts_toggle" }
  | { kind: "easter"; cmd: "ufo" | "ghost" | "coffee" }
  | { kind: "system_save" }
  | { kind: "system_unsave" }
  | { kind: "showbox_speed"; seconds: number; valid: boolean }
  | { kind: "showbox_load"; name: string; valid: boolean }
  | { kind: "help_slides" }
  | { kind: "art_show" }
  | { kind: "none" };

const SHOWBOX_NAME_RE = /^[a-zA-Z0-9_-]+$/;

export function classifyLocalCommand(msg: string): LocalCommand {
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
      valid: SHOWBOX_NAME_RE.test(name),
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

export function isLocalCommand(msg: string): boolean {
  return classifyLocalCommand(msg).kind !== "none";
}
