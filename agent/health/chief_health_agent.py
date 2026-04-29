from __future__ import annotations

from agent.health.health_agent_state import HealthAgentState


def generate_chief_guidance(state: HealthAgentState) -> dict:
    review_status = state.get("review_status", "PENDING")
    conflict_report = state.get("conflict_report", "").strip()
    risk_level = state.get("health_risk_level", "unknown")
    risk_summary = state.get("health_risk_summary", "").strip()
    selected_agents = state.get("selected_agents", [])

    covered_domains = ", ".join(selected_agents) if selected_agents else "no specialist agents"

    if review_status == "PASS":
        guidance = (
            f"Chief review passed. Covered agents: {covered_domains}. "
            f"Risk level: {risk_level}. "
            f"Key assessment: {risk_summary or 'no major risk flagged'}."
        )
    else:
        guidance = (
            f"Chief review requires revision. Covered agents: {covered_domains}. "
            f"Risk level: {risk_level}. "
            f"Conflicts: {conflict_report or 'unspecified issues'}. "
            f"Assessment: {risk_summary or 'no extra assessment notes'}."
        )

    return {"chief_expert_guidance": guidance}
