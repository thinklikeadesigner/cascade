"""Build the reverse-cascade LangGraph state machine."""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from cascade_api.graph.edges.route_approval import route_approval
from cascade_api.graph.edges.should_propagate import advance_level, should_propagate
from cascade_api.graph.nodes.analyze_impact import analyze_impact
from cascade_api.graph.nodes.apply_changes import apply_changes
from cascade_api.graph.nodes.checkpoint_approval import checkpoint_approval
from cascade_api.graph.nodes.detect_change_level import detect_change_level
from cascade_api.graph.nodes.handle_rejection import handle_rejection
from cascade_api.graph.state import ReverseCascadeState


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Construct and compile the reverse-cascade graph.

    Topology (identical to the TypeScript version):
        start → detect_change_level → analyze_impact → checkpoint_approval
        checkpoint_approval →(route_approval)→ apply_changes | handle_rejection | analyze_impact
        handle_rejection → end
        apply_changes →(should_propagate)→ advance_level | end
        advance_level → analyze_impact
    """
    graph = StateGraph(ReverseCascadeState)

    # Nodes
    graph.add_node("detect_change_level", detect_change_level)
    graph.add_node("analyze_impact", analyze_impact)
    graph.add_node("checkpoint_approval", checkpoint_approval)
    graph.add_node("apply_changes", apply_changes)
    graph.add_node("handle_rejection", handle_rejection)
    graph.add_node("advance_level", advance_level)

    # Entry: start → detect level
    graph.add_edge(START, "detect_change_level")

    # detect → analyze at origin level
    graph.add_edge("detect_change_level", "analyze_impact")

    # analyze → checkpoint (present to user)
    graph.add_edge("analyze_impact", "checkpoint_approval")

    # checkpoint → route based on user decision
    graph.add_conditional_edges(
        "checkpoint_approval",
        route_approval,
        {
            "apply_changes": "apply_changes",
            "handle_rejection": "handle_rejection",
            "analyze_impact": "analyze_impact",  # "modify" loops back
        },
    )

    # rejection → end
    graph.add_edge("handle_rejection", END)

    # apply → check if we should propagate up
    graph.add_conditional_edges(
        "apply_changes",
        should_propagate,
        {
            "analyze_impact": "advance_level",
            "__end__": END,
        },
    )

    # advance level → analyze at next level up
    graph.add_edge("advance_level", "analyze_impact")

    return graph.compile(checkpointer=checkpointer or MemorySaver())
