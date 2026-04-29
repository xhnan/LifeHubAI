from __future__ import annotations

from agent.health.health_agent_state import HealthAgentState


def retrieve_long_term_memory(message: str, state: HealthAgentState) -> dict:
    profile = state.get("user_profile", {})
    return {
        "long_term_memory": {
            "recent_goal": message,
            "diet_preference": profile.get("diet_preference", "unknown"),
            "exercise_preference": profile.get("exercise_preference", "unknown"),
        }
    }
