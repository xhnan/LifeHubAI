from __future__ import annotations

from typing import Any

from agent.health.health_agent_state import HealthAgentState
from agent.llm_model import zhipu_llm


def _fallback_workout_plan(state: HealthAgentState) -> str:
    goal = state.get("user_intent", "build a sustainable workout routine")
    risk = state.get("health_risk_summary", "no major risk summary")
    return (
        f"Workout goal: {goal}\n"
        f"Risk notes: {risk}\n"
        "1. Do 3 moderate sessions per week, 30 to 45 minutes each.\n"
        "2. Include 2 strength sessions focused on major movement patterns.\n"
        "3. Add daily walking and mobility work on non-training days.\n"
        "4. If fatigue or pain increases, reduce intensity and review the baseline again."
    )


def generate_workout_plan(state: HealthAgentState) -> dict[str, Any]:
    try:
        from langchain.messages import HumanMessage, SystemMessage

        model = zhipu_llm(temperature=0.5)
        system_prompt = (
            "You are a workout specialist. Produce a practical and safe training plan based on the user's "
            "goal, records, and health risk summary. Avoid unsafe intensity if risk is elevated."
        )
        human_prompt = (
            f"Goal: {state.get('user_intent', '')}\n"
            f"Profile: {state.get('user_profile', {})}\n"
            f"Baseline: {state.get('health_baseline', '')}\n"
            f"Exercise records: {state.get('exercise_records', [])}\n"
            f"Activity records: {state.get('daily_consumption_records', [])}\n"
            f"Diet records: {state.get('diet_records', [])}\n"
            f"Risk notes: {state.get('health_risk_summary', '')}\n"
            f"Review feedback: {state.get('review_feedback', {}).get('workout_agent', '')}"
        )
        result = model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
        content = getattr(result, "content", "").strip()
        if content:
            return {"workout_plan": content}
    except Exception:
        pass

    return {"workout_plan": _fallback_workout_plan(state)}
