from __future__ import annotations

from typing import Any

from agent.health.health_agent_state import HealthAgentState
from agent.llm_model import zhipu_llm


def _fallback_psychology_plan(state: HealthAgentState) -> str:
    goal = state.get("user_intent", "improve mental resilience")
    risk = state.get("health_risk_summary", "no major risk summary")
    return (
        f"Psychology goal: {goal}\n"
        f"Risk notes: {risk}\n"
        "1. Use one 10-minute check-in each day to track mood, stress, and energy.\n"
        "2. Keep a fixed wind-down routine before sleep and reduce screen stimulation at night.\n"
        "3. When stress spikes, use breathing or grounding for 3 to 5 minutes before reacting.\n"
        "4. Escalate to professional support if low mood, panic, or insomnia persists."
    )


def generate_psychology_plan(state: HealthAgentState) -> dict[str, Any]:
    try:
        from langchain.messages import HumanMessage, SystemMessage

        model = zhipu_llm(temperature=0.6)
        system_prompt = (
            "You are a psychology specialist. Produce a practical mental health support plan based on the "
            "user goal, records, memory, and risk notes. Keep it supportive and non-diagnostic."
        )
        human_prompt = (
            f"Goal: {state.get('user_intent', '')}\n"
            f"Profile: {state.get('user_profile', {})}\n"
            f"Baseline: {state.get('health_baseline', '')}\n"
            f"Psychology records: {state.get('psychology_records', [])}\n"
            f"Activity records: {state.get('daily_consumption_records', [])}\n"
            f"Memory: {state.get('long_term_memory', {})}\n"
            f"Risk notes: {state.get('health_risk_summary', '')}\n"
            f"Review feedback: {state.get('review_feedback', {}).get('psychology_agent', '')}"
        )
        result = model.invoke([SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)])
        content = getattr(result, "content", "").strip()
        if content:
            return {"psychology_plan": content}
    except Exception:
        pass

    return {"psychology_plan": _fallback_psychology_plan(state)}
