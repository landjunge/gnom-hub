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
import { createApiClient } from "./api";

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
};

const GnomTS = {
  version: "0.1.0",
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
