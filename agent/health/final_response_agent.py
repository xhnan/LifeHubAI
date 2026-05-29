from __future__ import annotations

from typing import Any

from agent.health.health_agent_state import HealthAgentState


def _collect_plan_sections(state: HealthAgentState) -> list[str]:
    sections: list[str] = []

    diet_plan = state.get("diet_plan", "").strip()
    workout_plan = state.get("workout_plan", "").strip()
    psychology_plan = state.get("psychology_plan", "").strip()

    if diet_plan:
        sections.append(f"饮食方案：\n{diet_plan}")
    if workout_plan:
        sections.append(f"运动方案：\n{workout_plan}")
    if psychology_plan:
        sections.append(f"心理与作息建议：\n{psychology_plan}")

    return sections


def _build_feasibility_text(state: HealthAgentState) -> str:
    risk_level = state.get("health_risk_level", "unknown")
    risk_summary = state.get("health_risk_summary", "").strip()
    review_status = state.get("review_status", "PENDING")
    conflict_report = state.get("conflict_report", "").strip()

    if review_status == "PASS":
        base = "从当前信息看，这套方案具备执行可行性。"
    else:
        base = "这套方案可以作为保守参考，但仍有部分限制条件需要注意。"

    if risk_level == "high":
        base += " 由于当前风险等级较高，建议优先采用低风险、可持续的执行方式。"
    elif risk_level == "medium":
        base += " 当前存在一定不确定性，建议先小步执行，再根据记录逐步调整。"

    if risk_summary:
        base += f" 当前主要限制是：{risk_summary}。"

    if conflict_report:
        base += f" 审查阶段提示：{conflict_report}。"

    return base


def _build_next_steps(state: HealthAgentState) -> str:
    missing_data: list[str] = []
    if not state.get("diet_records"):
        missing_data.append("饮食记录")
    if not state.get("exercise_records"):
        missing_data.append("运动记录")
    if not state.get("daily_consumption_records"):
        missing_data.append("活动消耗记录")
    if "psychology_agent" in state.get("selected_agents", []) and not state.get("psychology_records"):
        missing_data.append("心理状态记录")

    if not missing_data:
        return "下一步建议：按当前方案执行 7 天，并记录体重、饮食、运动和主观状态变化，再做一次复盘。"

    return (
        "下一步建议：先按当前保守方案执行，同时补充以下数据："
        f"{'、'.join(missing_data)}。连续记录 7 天后，再生成更精细的个性化调整方案。"
    )


def build_final_response(state: HealthAgentState) -> dict[str, Any]:
    intent = state.get("user_intent", "").strip() or "健康管理"
    chief_guidance = state.get("chief_expert_guidance", "").strip()
    plan_sections = _collect_plan_sections(state)
    feasibility_text = _build_feasibility_text(state)
    next_steps = _build_next_steps(state)

    parts = [
        f"针对你的目标“{intent}”，我给出的结论是：当前更适合采用稳妥、可持续的调整方案，而不是一次性做激进改变。",
    ]

    if plan_sections:
        parts.append("\n\n".join(plan_sections))

    parts.append(f"可行性判断：{feasibility_text}")

    if chief_guidance:
        parts.append(f"综合结论：{chief_guidance}")

    parts.append(next_steps)

    return {"final_response": "\n\n".join(parts)}
