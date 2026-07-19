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
};

const GnomTS = {
  version: "0.2.0",
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
