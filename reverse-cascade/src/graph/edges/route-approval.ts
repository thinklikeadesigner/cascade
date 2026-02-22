import type { ReverseCascadeState } from "../state.js";

/**
 * Route based on the user's approval decision.
 */
export function routeApproval(
  state: ReverseCascadeState,
): "apply_changes" | "handle_rejection" | "analyze_impact" {
  const response = state.lastApprovalResponse;
  if (!response) {
    throw new Error("No approval response found");
  }

  switch (response.decision) {
    case "approve":
    case "stop":
      return "apply_changes";
    case "reject":
      return "handle_rejection";
    case "modify":
      // Re-analyze with feedback incorporated into the request
      return "analyze_impact";
    default:
      throw new Error(`Unknown decision: ${response.decision}`);
  }
}
