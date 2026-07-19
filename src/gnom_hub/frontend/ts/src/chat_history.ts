/** Pure chat localStorage history + arrow-key navigation. */

export const CHAT_HISTORY_KEY = "chatHistory";
export const CHAT_HISTORY_MAX = 50;

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export interface HistoryNavState {
  /** -1 = not browsing history (live draft) */
  idx: number;
  draft: string;
}

export function loadChatHistory(
  storage: StorageLike,
  key: string = CHAT_HISTORY_KEY,
): string[] {
  try {
    const raw = storage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

/**
 * Append msg if non-empty and not equal to last entry. Cap at max.
 * Returns the new history array.
 */
export function pushChatHistory(
  storage: StorageLike,
  msg: string,
  max: number = CHAT_HISTORY_MAX,
  key: string = CHAT_HISTORY_KEY,
): string[] {
  if (!msg) return loadChatHistory(storage, key);
  let history = loadChatHistory(storage, key);
  if (history.length === 0 || history[history.length - 1] !== msg) {
    history = history.concat([msg]);
    if (history.length > max) {
      history = history.slice(history.length - max);
    }
    try {
      storage.setItem(key, JSON.stringify(history));
    } catch {
      /* quota / private mode */
    }
  }
  return history;
}

/**
 * Arrow-up / arrow-down through history. Pure — no DOM.
 * Returns new state + value for the textarea.
 */
export function navigateChatHistory(
  direction: "up" | "down",
  history: string[],
  state: HistoryNavState,
  currentValue: string,
): { state: HistoryNavState; value: string; changed: boolean } {
  if (!history.length) {
    return { state, value: currentValue, changed: false };
  }

  let idx = state.idx;
  let draft = state.draft;
  let value = currentValue;
  let changed = false;

  if (direction === "up") {
    if (idx === -1) {
      draft = currentValue;
      idx = history.length - 1;
      value = history[idx]!;
      changed = true;
    } else if (idx > 0) {
      idx -= 1;
      value = history[idx]!;
      changed = true;
    }
  } else {
    // down
    if (idx === -1) {
      return { state, value: currentValue, changed: false };
    }
    if (idx < history.length - 1) {
      idx += 1;
      value = history[idx]!;
      changed = true;
    } else {
      idx = -1;
      value = draft;
      changed = true;
    }
  }

  return { state: { idx, draft }, value, changed };
}
