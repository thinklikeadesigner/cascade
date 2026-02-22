import { StateGraph, MemorySaver } from "@langchain/langgraph";
import { ReverseCascadeAnnotation } from "./state.js";
import { detectChangeLevel } from "./nodes/detect-change-level.js";
import { analyzeImpact } from "./nodes/analyze-impact.js";
import { checkpointApproval } from "./nodes/checkpoint-approval.js";
import { applyChanges } from "./nodes/apply-changes.js";
import { handleRejection } from "./nodes/handle-rejection.js";
import { routeApproval } from "./edges/route-approval.js";
import { shouldPropagate, advanceLevel } from "./edges/should-propagate.js";

export function buildGraph(checkpointer?: InstanceType<typeof MemorySaver>) {
  const graph = new StateGraph(ReverseCascadeAnnotation)
    // Nodes
    .addNode("detect_change_level", detectChangeLevel)
    .addNode("analyze_impact", analyzeImpact)
    .addNode("checkpoint_approval", checkpointApproval)
    .addNode("apply_changes", applyChanges)
    .addNode("handle_rejection", handleRejection)
    .addNode("advance_level", advanceLevel)

    // Entry: start → detect level
    .addEdge("__start__", "detect_change_level")

    // detect → analyze at origin level
    .addEdge("detect_change_level", "analyze_impact")

    // analyze → checkpoint (present to user)
    .addEdge("analyze_impact", "checkpoint_approval")

    // checkpoint → route based on user decision
    .addConditionalEdges("checkpoint_approval", routeApproval, {
      apply_changes: "apply_changes",
      handle_rejection: "handle_rejection",
      analyze_impact: "analyze_impact", // "modify" loops back
    })

    // rejection → end
    .addEdge("handle_rejection", "__end__")

    // apply → check if we should propagate up
    .addConditionalEdges("apply_changes", shouldPropagate, {
      analyze_impact: "advance_level",
      __end__: "__end__",
    })

    // advance level → analyze at next level up
    .addEdge("advance_level", "analyze_impact");

  return graph.compile({
    checkpointer: checkpointer ?? new MemorySaver(),
  });
}

export type ReverseCascadeGraph = ReturnType<typeof buildGraph>;
