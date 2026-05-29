from __future__ import annotations

from typing import Any

from agent.health.health_agent_state import HealthAgentState


KEYWORDS = {
    "diet": ["diet", "food", "meal", "nutrition", "eat", "饮食", "吃", "营养", "减脂餐", "控糖"],
    "workout": ["workout", "exercise", "fitness", "run", "training", "运动", "锻炼", "健身", "跑步", "训练"],
    "psychology": ["stress", "anxiety", "sleep", "emotion", "mental", "心理", "情绪", "焦虑", "压力", "睡眠"],
}

PLAN_TO_AGENT = {
    "diet": "diet_agent",
    "workout": "workout_agent",
    "psychology": "psychology_agent",
}


def _contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _resolve_requested_domains(message: str) -> list[str]:
    matched = [name for name, keywords in KEYWORDS.items() if _contains_any(message, keywords)]
    return matched or ["diet", "workout", "psychology"]


def analyze_intent(message: str) -> dict[str, Any]:
    requested_domains = _resolve_requested_domains(message)
    selected_agents = [PLAN_TO_AGENT[domain] for domain in requested_domains]
    intent_type = "comprehensive" if len(requested_domains) > 1 else requested_domains[0]

    return {
        "intent_type": intent_type,
        "required_plans": requested_domains,
        "selected_agents": selected_agents,
    }


def intent_agent(state: HealthAgentState) -> dict[str, Any]:
    message = state.get("user_intent", "")
    return analyze_intent(message)
