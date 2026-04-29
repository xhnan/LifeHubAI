from typing import Any, Dict, List, Literal, TypedDict


class HealthAgentState(TypedDict, total=False):
    user_id: str
    user_intent: str
    intent_type: str
    selected_agents: List[str]
    required_plans: List[str]
    revision_targets: List[str]
    review_feedback: Dict[str, str]
    final_response: str
    summary: Dict[str, Any]
    user_profile: Dict[str, Any]
    long_term_memory: Dict[str, Any]
    diet_records: List[Dict[str, Any]]
    exercise_records: List[Dict[str, Any]]
    daily_consumption_records: List[Dict[str, Any]]
    psychology_records: List[Dict[str, Any]]
    health_baseline: str
    diet_plan: str
    workout_plan: str
    psychology_plan: str
    review_status: Literal["PASS", "REJECT", "PENDING"]
    conflict_report: str
    chief_expert_guidance: str
    revision_count: int
    max_revision_count: int
    health_risk_level: Literal["low", "medium", "high"]
    health_risk_summary: str
