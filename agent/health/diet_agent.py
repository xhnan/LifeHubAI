from __future__ import annotations

from typing import Any

from agent.health.health_agent_state import HealthAgentState
from agent.llm_model import zhipu_llm


def _fallback_diet_plan(state: HealthAgentState) -> str:
    goal = state.get("user_intent", "improve diet quality")
    risk = state.get("health_risk_summary", "no major risk summary")
    return (
        f"Diet goal: {goal}\n"
        f"Risk notes: {risk}\n"
        "1. Keep meal timing regular and prioritize minimally processed foods.\n"
        "2. Make half of each plate vegetables, a quarter lean protein, and a quarter complex carbs.\n"
        "3. Reduce sugary drinks and late-night snacks for the next 7 days.\n"
        "4. Track hunger, fullness, and energy after meals to refine the next plan."
    )


def generate_diet_plan(state: HealthAgentState) -> dict[str, Any]:
    try:
        from langchain.messages import HumanMessage, SystemMessage

        model = zhipu_llm(temperature=0.6)
        system_prompt = (
            "You are a diet specialist. Produce a concise, practical diet plan based on the user's goal, "
            "baseline, recent records, and risk notes. Avoid markdown tables."
        )
        human_prompt = (
            f"Goal: {state.get('user_intent', '')}\n"
            f"Profile: {state.get('user_profile', {})}\n"
            f"Baseline: {state.get('health_baseline', '')}\n"
            f"Diet records: {state.get('diet_records', [])}\n"
            f"Exercise records: {state.get('exercise_records', [])}\n"
            f"Activity records: {state.get('daily_consumption_records', [])}\n"
            f"Memory: {state.get('long_term_memory', {})}\n"
            f"Risk notes: {state.get('health_risk_summary', '')}\n"
            f"Review feedback: {state.get('review_feedback', {}).get('diet_agent', '')}"
        )
        result = model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
        content = getattr(result, "content", "").strip()
        if content:
            return {"diet_plan": content}
    except Exception:
        pass

    return {"diet_plan": _fallback_diet_plan(state)}
