import { interrupt } from "@langchain/langgraph";
import type { ReverseCascadeState } from "../state.js";
import type { ApprovalResponse } from "../state.js";
import { logger } from "../../logger.js";

/**
 * Pauses the graph and waits for user approval via WhatsApp.
 * The graph state is persisted to the checkpointer (Supabase/MemorySaver).
 * When the user responds, the graph resumes with Command({ resume: response }).
 */
export async function checkpointApproval(
  state: ReverseCascadeState,
): Promise<Partial<ReverseCascadeState>> {
  logger.info(
    { level: state.currentLevel },
    "Waiting for user approval (interrupt)",
  );

  // interrupt() pauses execution here. The value passed is metadata
  // that can help the API layer know what to send to the user.
  // When resumed, `response` contains the user's decision.
  const response = interrupt({
    level: state.currentLevel,
    message: state.checkpointMessage,
  }) as ApprovalResponse;

  logger.info(
    { level: state.currentLevel, decision: response.decision },
    "User responded to checkpoint",
  );

  return {
    lastApprovalResponse: response,
  };
}
