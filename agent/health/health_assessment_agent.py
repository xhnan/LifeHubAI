from __future__ import annotations

import json
from typing import Any

from agent.health.health_agent_state import HealthAgentState


def _safe_load_baseline(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def assess_health_status(state: HealthAgentState) -> dict:
    baseline = _safe_load_baseline(state.get("health_baseline", ""))
    diet_count = len(state.get("diet_records", []))
    exercise_count = len(state.get("exercise_records", []))
    activity_count = len(state.get("daily_consumption_records", []))
    psychology_count = len(state.get("psychology_records", []))

    risks: list[str] = []
    if not baseline:
        risks.append("health baseline is incomplete")
    if diet_count == 0:
        risks.append("missing recent diet records")
    if exercise_count == 0:
        risks.append("missing recent exercise records")
    if activity_count == 0:
        risks.append("missing recent activity records")
    if "psychology" in state.get("required_plans", []) and psychology_count == 0:
        risks.append("missing recent psychology records")

    risk_level = "low"
    if len(risks) >= 3:
        risk_level = "high"
    elif risks:
        risk_level = "medium"

    return {
        "health_risk_level": risk_level,
        "health_risk_summary": "; ".join(risks) if risks else "baseline data is sufficient for planning",
    }
