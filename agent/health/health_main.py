from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from agent.health.chief_health_agent import generate_chief_guidance
from agent.health.diet_agent import generate_diet_plan
from agent.health.final_response_agent import build_final_response
from agent.health.health_agent_state import HealthAgentState
from agent.health.health_assessment_agent import assess_health_status
from agent.health.intent_agent import intent_agent
from agent.health.long_term_memory_agent import retrieve_long_term_memory
from agent.health.psychology_agent import generate_psychology_plan
from agent.health.review_agent import review_plans
from agent.health.save_record_agent import build_record_payload
from agent.health.summary_agent import build_health_summary
from agent.health.tool_agent import get_health_data
from agent.health.workout_agent import generate_workout_plan


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    )


NODE_ORDER = [
    "intent_agent",
    "tool_agent",
    "long_term_memory_agent",
    "health_assessment_agent",
    "diet_agent",
    "workout_agent",
    "psychology_agent",
    "review_agent",
    "chief_health_agent",
    "final_response_agent",
    "summary_agent",
    "record_agent",
]

NODE_LABELS = {
    "intent_agent": "Analyzing intent",
    "tool_agent": "Loading health data",
    "long_term_memory_agent": "Loading long-term memory",
    "health_assessment_agent": "Assessing health risk",
    "diet_agent": "Generating diet plan",
    "workout_agent": "Generating workout plan",
    "psychology_agent": "Generating psychology plan",
    "review_agent": "Reviewing specialist plans",
    "chief_health_agent": "Generating chief guidance",
    "final_response_agent": "Building final response",
    "summary_agent": "Building summary",
    "record_agent": "Building record payload",
}


def create_initial_state(user_id: str, message: str) -> HealthAgentState:
    return {
        "user_id": user_id,
        "user_intent": message,
        "intent_type": "",
        "selected_agents": [],
        "required_plans": [],
        "revision_targets": [],
        "review_feedback": {},
        "final_response": "",
        "user_profile": {},
        "long_term_memory": {},
        "diet_records": [],
        "exercise_records": [],
        "daily_consumption_records": [],
        "psychology_records": [],
        "health_baseline": "",
        "diet_plan": "",
        "workout_plan": "",
        "psychology_plan": "",
        "review_status": "PENDING",
        "conflict_report": "",
        "chief_expert_guidance": "",
        "revision_count": 0,
        "max_revision_count": 2,
        "health_risk_level": "medium",
        "health_risk_summary": "",
        "summary": {},
    }


def _intent_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("intent_agent start")
    patch = intent_agent(state)
    logger.info(
        "intent_agent done intent_type=%s selected_agents=%s",
        patch.get("intent_type", ""),
        patch.get("selected_agents", []),
    )
    return patch


def _tool_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("tool_agent start")
    patch = get_health_data(state.get("user_intent", ""), state)
    logger.info(
        "tool_agent done profile=%s diet_records=%s exercise_records=%s psychology_records=%s",
        bool(patch.get("user_profile")),
        len(patch.get("diet_records", [])),
        len(patch.get("exercise_records", [])),
        len(patch.get("psychology_records", [])),
    )
    return patch


def _memory_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("long_term_memory_agent start")
    patch = retrieve_long_term_memory(state.get("user_intent", ""), state)
    logger.info("long_term_memory_agent done keys=%s", list(patch.get("long_term_memory", {}).keys()))
    return patch


def _assessment_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("health_assessment_agent start")
    patch = assess_health_status(state)
    logger.info(
        "health_assessment_agent done risk_level=%s risk_summary=%s",
        patch.get("health_risk_level", ""),
        patch.get("health_risk_summary", ""),
    )
    return patch


def _diet_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("diet_agent start revision_feedback=%s", state.get("review_feedback", {}).get("diet_agent", ""))
    patch = generate_diet_plan(state)
    logger.info("diet_agent done has_plan=%s", bool(patch.get("diet_plan", "").strip()))
    return patch


def _workout_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info(
        "workout_agent start revision_feedback=%s",
        state.get("review_feedback", {}).get("workout_agent", ""),
    )
    patch = generate_workout_plan(state)
    logger.info("workout_agent done has_plan=%s", bool(patch.get("workout_plan", "").strip()))
    return patch


def _psychology_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info(
        "psychology_agent start revision_feedback=%s",
        state.get("review_feedback", {}).get("psychology_agent", ""),
    )
    patch = generate_psychology_plan(state)
    logger.info("psychology_agent done has_plan=%s", bool(patch.get("psychology_plan", "").strip()))
    return patch


def _review_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("review_agent start")
    patch = review_plans(state)
    logger.info(
        "review_agent done status=%s revision_targets=%s conflict_report=%s",
        patch.get("review_status", ""),
        patch.get("revision_targets", []),
        patch.get("conflict_report", ""),
    )
    return patch


def _chief_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("chief_health_agent start")
    patch = generate_chief_guidance(state)
    logger.info("chief_health_agent done")
    return patch


def _final_response_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("final_response_agent start")
    patch = build_final_response(state)
    logger.info("final_response_agent done")
    return patch


def _summary_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("summary_agent start")
    patch = {"summary": build_health_summary(state)}
    logger.info("summary_agent done")
    return patch


def _record_node(state: HealthAgentState) -> dict[str, Any]:
    logger.info("record_agent start")
    patch = {"record_payload": build_record_payload(state)}
    logger.info("record_agent done")
    return patch


def _route_specialists(state: HealthAgentState) -> list[str]:
    selected = state.get("selected_agents", [])
    if selected:
        logger.info("route_specialists selected=%s", selected)
        return selected
    fallback = ["diet_agent", "workout_agent", "psychology_agent"]
    logger.info("route_specialists fallback=%s", fallback)
    return fallback


def _route_after_review(state: HealthAgentState) -> list[str]:
    if state.get("review_status") == "PASS":
        logger.info("route_after_review -> chief_health_agent (PASS)")
        return ["chief_health_agent"]

    if state.get("revision_count", 0) >= state.get("max_revision_count", 2):
        logger.info("route_after_review -> chief_health_agent (max revisions reached)")
        return ["chief_health_agent"]

    targets = state.get("revision_targets", [])
    logger.info("route_after_review -> revision targets=%s", targets)
    return targets or ["chief_health_agent"]


@lru_cache(maxsize=1)
def build_health_agent_graph():
    from langgraph.graph import END, START, StateGraph

    workflow = StateGraph(HealthAgentState)

    workflow.add_node("intent_agent", _intent_node)
    workflow.add_node("tool_agent", _tool_node)
    workflow.add_node("long_term_memory_agent", _memory_node)
    workflow.add_node("health_assessment_agent", _assessment_node)
    workflow.add_node("diet_agent", _diet_node)
    workflow.add_node("workout_agent", _workout_node)
    workflow.add_node("psychology_agent", _psychology_node)
    workflow.add_node("review_agent", _review_node)
    workflow.add_node("chief_health_agent", _chief_node)
    workflow.add_node("final_response_agent", _final_response_node)
    workflow.add_node("summary_agent", _summary_node)
    workflow.add_node("record_agent", _record_node)

    workflow.add_edge(START, "intent_agent")
    workflow.add_edge("intent_agent", "tool_agent")
    workflow.add_edge("intent_agent", "long_term_memory_agent")
    workflow.add_edge("tool_agent", "health_assessment_agent")
    workflow.add_edge("long_term_memory_agent", "health_assessment_agent")

    workflow.add_conditional_edges(
        "health_assessment_agent",
        _route_specialists,
        {
            "diet_agent": "diet_agent",
            "workout_agent": "workout_agent",
            "psychology_agent": "psychology_agent",
        },
    )

    workflow.add_edge("diet_agent", "review_agent")
    workflow.add_edge("workout_agent", "review_agent")
    workflow.add_edge("psychology_agent", "review_agent")

    workflow.add_conditional_edges(
        "review_agent",
        _route_after_review,
        {
            "diet_agent": "diet_agent",
            "workout_agent": "workout_agent",
            "psychology_agent": "psychology_agent",
            "chief_health_agent": "chief_health_agent",
        },
    )

    workflow.add_edge("chief_health_agent", "final_response_agent")
    workflow.add_edge("final_response_agent", "summary_agent")
    workflow.add_edge("summary_agent", "record_agent")
    workflow.add_edge("record_agent", END)

    return workflow.compile()


def run_health_agent(message: str, user_id: str = "local-user") -> dict[str, Any]:
    logger.info("run_health_agent start user_id=%s message=%s", user_id, message)
    graph = build_health_agent_graph()
    state = graph.invoke(create_initial_state(user_id=user_id, message=message))
    logger.info(
        "run_health_agent done status=%s revision_count=%s",
        state.get("review_status", ""),
        state.get("revision_count", 0),
    )
    return {
        "state": state,
        "summary": state.get("summary", build_health_summary(state)),
        "record_payload": state.get("record_payload", build_record_payload(state)),
    }


def stream_health_agent(message: str, user_id: str = "local-user"):
    logger.info("stream_health_agent start user_id=%s message=%s", user_id, message)
    graph = build_health_agent_graph()
    initial_state = create_initial_state(user_id=user_id, message=message)
    yield {
        "event": "start",
        "data": {
            "user_id": user_id,
            "message": message,
            "steps": NODE_ORDER,
            "step_labels": NODE_LABELS,
        },
    }

    final_state: HealthAgentState = initial_state
    completed_nodes = 0
    for chunk in graph.stream(initial_state, stream_mode="updates"):
        for node_name, patch in chunk.items():
            final_state.update(patch)
            completed_nodes += 1
            progress = min(int(completed_nodes * 100 / len(NODE_ORDER)), 99)
            logger.info("stream_health_agent node=%s keys=%s", node_name, list(patch.keys()))
            yield {
                "event": "node",
                "data": {
                    "node": node_name,
                    "label": NODE_LABELS.get(node_name, node_name),
                    "progress": progress,
                    "patch": patch,
                },
            }

    result = {
        "state": final_state,
        "summary": final_state.get("summary", build_health_summary(final_state)),
        "record_payload": final_state.get("record_payload", build_record_payload(final_state)),
    }
    logger.info(
        "stream_health_agent done status=%s revision_count=%s",
        final_state.get("review_status", ""),
        final_state.get("revision_count", 0),
    )
    yield {"event": "final", "data": {"progress": 100, **result}}
    yield {"event": "done", "data": {"status": "completed"}}


def main(message: str, user_id: str = "local-user") -> dict[str, Any]:
    return run_health_agent(message=message, user_id=user_id)
