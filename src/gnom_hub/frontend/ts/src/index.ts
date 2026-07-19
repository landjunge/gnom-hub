/**
 * Gnom-Hub frontend TypeScript entry (S5 gradual migration).
 * Bundled as IIFE → window.GnomTS (see package.json build script).
 */
import {
  FROZEN_AGENTS,
  SYSTEM_AGENTS,
  WORKER_AGENTS,
  KNOWN_COLORS,
  P_COLORS,
  agentColor,
  knownColor,
  isSystemAgent,
  isWorkerAgent,
  isFrozenAgent,
} from "./agents";
import {
  extractMentions,
  countAgentMentions,
  isMultiMention,
  stripOnlyPrefix,
  withOnlyTarget,
} from "./chat_mentions";
import {
  createApiClient,
  safeJsonParse,
  discoverApiBase,
  apiRequest,
} from "./api";
import {
  countAgentGroups,
  formatAgentsLine,
  formatTokensLine,
  formatQueueLine,
  formatLeases,
  formatLastError,
  formatStatsPanel,
} from "./stats";
import { escapeHtml } from "./security";
import {
  CHAT_HISTORY_KEY,
  CHAT_HISTORY_MAX,
  loadChatHistory,
  pushChatHistory,
  navigateChatHistory,
} from "./chat_history";
import { classifyLocalCommand, isLocalCommand } from "./chat_commands";
import { formatChatResponseToast } from "./chat_response";
import {
  stripInvisibleTrailing,
  extractThoughtsAndClean,
  isSystemLogMessage,
  isAgentToAgentMessage,
  cleanActionTagsForSpeech,
  prepareOutgoingChat,
} from "./chat_content";

export type * from "./types";
export {
  FROZEN_AGENTS,
  SYSTEM_AGENTS,
  WORKER_AGENTS,
  KNOWN_COLORS,
  P_COLORS,
  agentColor,
  knownColor,
  isSystemAgent,
  isWorkerAgent,
  isFrozenAgent,
  extractMentions,
  countAgentMentions,
  isMultiMention,
  stripOnlyPrefix,
  withOnlyTarget,
  createApiClient,
  safeJsonParse,
  discoverApiBase,
  apiRequest,
  countAgentGroups,
  formatAgentsLine,
  formatTokensLine,
  formatQueueLine,
  formatLeases,
  formatLastError,
  formatStatsPanel,
  escapeHtml,
  CHAT_HISTORY_KEY,
  CHAT_HISTORY_MAX,
  loadChatHistory,
  pushChatHistory,
  navigateChatHistory,
  classifyLocalCommand,
  isLocalCommand,
  formatChatResponseToast,
  stripInvisibleTrailing,
  extractThoughtsAndClean,
  isSystemLogMessage,
  isAgentToAgentMessage,
  cleanActionTagsForSpeech,
  prepareOutgoingChat,
};

const GnomTS = {
  version: "0.3.1",
  FROZEN_AGENTS,
  SYSTEM_AGENTS,
  WORKER_AGENTS,
  KNOWN_COLORS,
  P_COLORS,
  agentColor,
  knownColor,
  isSystemAgent,
  isWorkerAgent,
  isFrozenAgent,
  extractMentions,
  countAgentMentions,
  isMultiMention,
  stripOnlyPrefix,
  withOnlyTarget,
  createApiClient,
  safeJsonParse,
  discoverApiBase,
  apiRequest,
  countAgentGroups,
  formatAgentsLine,
  formatTokensLine,
  formatQueueLine,
  formatLeases,
  formatLastError,
  formatStatsPanel,
  escapeHtml,
  CHAT_HISTORY_KEY,
  CHAT_HISTORY_MAX,
  loadChatHistory,
  pushChatHistory,
  navigateChatHistory,
  classifyLocalCommand,
  isLocalCommand,
  formatChatResponseToast,
  stripInvisibleTrailing,
  extractThoughtsAndClean,
  isSystemLogMessage,
  isAgentToAgentMessage,
  cleanActionTagsForSpeech,
  prepareOutgoingChat,
};

export default GnomTS;

// Browser: also attach when loaded as classic script after IIFE assigns global
declare global {
  interface Window {
    GnomTS?: typeof GnomTS;
  }
}

if (typeof window !== "undefined") {
  window.GnomTS = GnomTS;
}
