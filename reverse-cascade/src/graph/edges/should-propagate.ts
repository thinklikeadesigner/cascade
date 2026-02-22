import type { ReverseCascadeState } from "../state.js";
import { getNextLevelUp } from "../../cascade/level-utils.js";

/**
 * After applying changes, decide whether to propagate upward or stop.
 */
export function shouldPropagate(
  state: ReverseCascadeState,
): "analyze_impact" | "__end__" {
  // User chose "stop" — accept changes but don't propagate
  if (
    state.lastApprovalResponse?.decision === "stop" ||
    state.propagationStopped
  ) {
    return "__end__";
  }

  // Check if analysis says propagation is needed
  if (!state.currentAnalysis?.requiresPropagation) {
    return "__end__";
  }

  // Check if there's a level above to propagate to
  const nextLevel = getNextLevelUp(state.currentLevel);
  if (!nextLevel) {
    return "__end__"; // Already at year level
  }

  // Check if we have a file for the next level
  if (!state.cascadeFiles[nextLevel]) {
    return "__end__"; // No file at next level
  }

  return "analyze_impact";
}

/**
 * Transition state to the next level up before re-entering analyze_impact.
 */
export async function advanceLevel(
  state: ReverseCascadeState,
): Promise<Partial<ReverseCascadeState>> {
  const nextLevel = getNextLevelUp(state.currentLevel);
  if (!nextLevel) {
    return { propagationStopped: true };
  }

  return {
    currentLevel: nextLevel,
    currentAnalysis: null,
    lastApprovalResponse: null,
  };
}
