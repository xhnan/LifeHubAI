from __future__ import annotations

from agent.health.health_agent_state import HealthAgentState


def build_health_summary(state: HealthAgentState) -> dict:
    return {
        "user_id": state.get("user_id", ""),
        "intent": state.get("user_intent", ""),
        "final_response": state.get("final_response", ""),
        "risk_level": state.get("health_risk_level", "unknown"),
        "risk_summary": state.get("health_risk_summary", ""),
        "review_status": state.get("review_status", "PENDING"),
        "diet_plan": state.get("diet_plan", ""),
        "workout_plan": state.get("workout_plan", ""),
        "psychology_plan": state.get("psychology_plan", ""),
        "chief_guidance": state.get("chief_expert_guidance", ""),
    }
