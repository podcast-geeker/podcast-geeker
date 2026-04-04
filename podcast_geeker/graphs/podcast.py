from langgraph.graph import END, START, StateGraph
from podcast_creator.nodes import (
    combine_audio_node,
    generate_all_audio_node,
    generate_outline_node,
)

from podcast_geeker.podcasts.nodes import (
    advance_segment_node,
    after_review,
    expert_turn_node,
    host_turn_node,
    prepare_graph_state_node,
    prepare_segment_node,
    quality_review_node,
    route_after_advance,
    route_prepared_segment,
    should_continue,
)
from podcast_geeker.podcasts.state import PodcastAgentState

workflow = StateGraph(PodcastAgentState)

workflow.add_node("prepare_graph_state", prepare_graph_state_node)
workflow.add_node("generate_outline", generate_outline_node)
workflow.add_node("prepare_segment", prepare_segment_node)
workflow.add_node("host_turn", host_turn_node)
workflow.add_node("expert_turn", expert_turn_node)
workflow.add_node("quality_review", quality_review_node)
workflow.add_node("advance_segment", advance_segment_node)
workflow.add_node("generate_audio", generate_all_audio_node)
workflow.add_node("combine_audio", combine_audio_node)

workflow.add_edge(START, "prepare_graph_state")
workflow.add_edge("prepare_graph_state", "generate_outline")
workflow.add_edge("generate_outline", "prepare_segment")
workflow.add_conditional_edges(
    "prepare_segment",
    route_prepared_segment,
    {
        "host_turn": "host_turn",
        "generate_audio": "generate_audio",
    },
)
workflow.add_edge("host_turn", "expert_turn")
workflow.add_conditional_edges(
    "expert_turn",
    should_continue,
    {
        "continue": "host_turn",
        "review": "quality_review",
        "finalize": "advance_segment",
    },
)
workflow.add_conditional_edges(
    "quality_review",
    after_review,
    {
        "pass": "advance_segment",
        "retry": "host_turn",
    },
)
workflow.add_conditional_edges(
    "advance_segment",
    route_after_advance,
    {
        "next_segment": "prepare_segment",
        "generate_audio": "generate_audio",
    },
)
workflow.add_edge("generate_audio", "combine_audio")
workflow.add_edge("combine_audio", END)

graph = workflow.compile()
