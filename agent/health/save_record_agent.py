from __future__ import annotations

from datetime import datetime, timezone

from agent.health.health_agent_state import HealthAgentState


def build_record_payload(state: HealthAgentState) -> dict:
    return {
        "user_id": state.get("user_id", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "intent": state.get("user_intent", ""),
        "final_response": state.get("final_response", ""),
        "review_status": state.get("review_status", "PENDING"),
        "risk_level": state.get("health_risk_level", "unknown"),
        "plans": {
            "diet": state.get("diet_plan", ""),
            "workout": state.get("workout_plan", ""),
            "psychology": state.get("psychology_plan", ""),
        },
        "guidance": state.get("chief_expert_guidance", ""),
    }
