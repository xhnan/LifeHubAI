from __future__ import annotations

import json
from typing import Any

from agent.health.health_agent_state import HealthAgentState


PLAN_TO_AGENT = {
    "diet": "diet_agent",
    "workout": "workout_agent",
    "psychology": "psychology_agent",
}

AGENT_TO_PLAN = {value: key for key, value in PLAN_TO_AGENT.items()}


def _safe_load_baseline(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def _resolve_expected_plans(state: HealthAgentState) -> set[str]:
    required_plans = state.get("required_plans", [])
    if isinstance(required_plans, list):
        plans = {str(item).strip().lower() for item in required_plans if str(item).strip()}
        plans = {plan for plan in plans if plan in PLAN_TO_AGENT}
        if plans:
            return plans

    selected_agents = state.get("selected_agents", [])
    if isinstance(selected_agents, list):
        plans = {
            AGENT_TO_PLAN.get(str(item).strip().lower(), str(item).strip().lower())
            for item in selected_agents
            if str(item).strip()
        }
        plans = {plan for plan in plans if plan in PLAN_TO_AGENT}
        if plans:
            return plans

    produced_plans: set[str] = set()
    if state.get("diet_plan", "").strip():
        produced_plans.add("diet")
    if state.get("workout_plan", "").strip():
        produced_plans.add("workout")
    if state.get("psychology_plan", "").strip():
        produced_plans.add("psychology")
    return produced_plans


def _add_issue(bucket: dict[str, list[str]], plan: str, message: str) -> None:
    bucket.setdefault(plan, [])
    if message not in bucket[plan]:
        bucket[plan].append(message)


def _is_conservative_workout(workout_plan: str) -> bool:
    high_intensity_tokens = ("hiit", "sprint", "burpee", "all-out", "max", "failure")
    return not any(token in workout_plan for token in high_intensity_tokens)


def _build_review_result(state: HealthAgentState, expected_plans: set[str]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    baseline = _safe_load_baseline(state.get("health_baseline", ""))
    blocking: dict[str, list[str]] = {}
    advisory: dict[str, list[str]] = {}

    for plan in expected_plans:
        plan_field = f"{plan}_plan"
        if not state.get(plan_field, "").strip():
            _add_issue(blocking, plan, f"{plan} plan is missing")

    risk_level = _normalize_text(state.get("health_risk_level", "medium"))
    risk_summary = state.get("health_risk_summary", "").strip()
    intent_text = _normalize_text(state.get("user_intent", ""))
    diet_plan = _normalize_text(state.get("diet_plan", ""))
    workout_plan = _normalize_text(state.get("workout_plan", ""))
    psychology_plan = _normalize_text(state.get("psychology_plan", ""))

    if risk_summary:
        for plan in expected_plans:
            _add_issue(advisory, plan, f"risk summary noted: {risk_summary}")

    if risk_level == "high":
        for plan in expected_plans:
            _add_issue(advisory, plan, "health risk is high, prefer conservative recommendations")

    if "diet" in expected_plans and "lose weight" in intent_text:
        if any(token in diet_plan for token in ("bulk", "surplus", "high calorie", "mass gain")):
            _add_issue(blocking, "diet", "diet plan conflicts with weight-loss intent")

    if "psychology" in expected_plans and any(token in psychology_plan for token in ("stay up late", "skip sleep")):
        _add_issue(blocking, "psychology", "psychology plan contains recovery-harming advice")

    if "workout" in expected_plans:
        injuries = _normalize_text(baseline.get("injuries") or baseline.get("injury_history") or [])
        conditions = _normalize_text(baseline.get("chronic_diseases") or baseline.get("conditions") or [])

        if injuries and any(token in workout_plan for token in ("hiit", "sprint", "jump", "burpee")):
            _add_issue(blocking, "workout", "workout intensity may exceed injury constraints")
        if conditions and any(token in workout_plan for token in ("max", "failure", "all-out", "high intensity")):
            _add_issue(blocking, "workout", "workout plan may conflict with chronic condition constraints")
        if risk_level == "high" and workout_plan and not _is_conservative_workout(workout_plan):
            _add_issue(blocking, "workout", "workout plan is not conservative enough for current risk level")

    if "workout" in expected_plans and "psychology" in expected_plans:
        if "rest" in psychology_plan and any(
            token in workout_plan for token in ("daily hiit", "two-a-day", "high intensity every day")
        ):
            _add_issue(blocking, "workout", "workout intensity conflicts with recovery advice")
            _add_issue(blocking, "psychology", "recovery advice conflicts with workout load")

    return blocking, advisory


def review_plans(state: HealthAgentState) -> dict:
    expected_plans = _resolve_expected_plans(state)
    blocking_issues, advisory_issues = _build_review_result(state, expected_plans)

    revision_targets = [PLAN_TO_AGENT[plan] for plan in blocking_issues if plan in PLAN_TO_AGENT]
    review_feedback = {
        PLAN_TO_AGENT[plan]: "; ".join(messages)
        for plan, messages in blocking_issues.items()
        if plan in PLAN_TO_AGENT
    }

    status = "PASS" if not revision_targets else "REJECT"
    reports: list[str] = []
    if blocking_issues:
        reports.extend(f"{plan}: {', '.join(messages)}" for plan, messages in blocking_issues.items())
    if advisory_issues:
        reports.extend(f"{plan} advisory: {', '.join(messages)}" for plan, messages in advisory_issues.items())

    patch: dict[str, Any] = {
        "review_status": status,
        "conflict_report": "; ".join(reports),
        "revision_targets": revision_targets,
        "review_feedback": review_feedback,
    }
    if status == "REJECT":
        patch["revision_count"] = state.get("revision_count", 0) + 1
    return patch
