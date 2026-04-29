from __future__ import annotations

import asyncio
import json
import logging

from agent.health.health_agent_state import HealthAgentState
from agent.llm_model import zhipu_llm


logger = logging.getLogger(__name__)


def _extract_ai_content(result: dict) -> str:
    try:
        from langchain.messages import AIMessage
    except Exception as exc:
        raise ValueError("langchain is not installed") from exc

    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage) and isinstance(message.content, str):
            return message.content
    raise ValueError("agent 未返回可解析的 AI 文本内容")


def _parse_json_content(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    return json.loads(cleaned)


def _ensure_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _build_health_state(message: str, state: HealthAgentState, data: dict | None = None) -> dict:
    data = data or {}
    profile = data.get("profile") or data.get("user_profile") or state.get("user_profile") or {}
    required_data = data.get("required_data") or {}
    health_data = data.get("health_data") or {}

    plans = health_data.get("plans") or []
    exercise_records = health_data.get("exercise_records") or []
    weight_records = health_data.get("weight_records") or []
    activity_records = health_data.get("activity_records") or []
    diet_records = health_data.get("diet_records") or []
    psychology_records = health_data.get("psychology_records") or []

    baseline_payload = {
        "required_data": required_data,
        "plans": plans,
        "weight_records": weight_records,
        "activity_records": activity_records,
        "psychology_records": psychology_records,
    }

    return {
        "user_profile": profile,
        "diet_records": _ensure_list(diet_records),
        "exercise_records": _ensure_list(exercise_records),
        "daily_consumption_records": _ensure_list(activity_records),
        "psychology_records": _ensure_list(psychology_records),
        "health_baseline": json.dumps(baseline_payload, ensure_ascii=False),
    }


def _fallback_health_data(message: str, state: HealthAgentState) -> dict:
    return _build_health_state(
        message,
        state,
        {
            "profile": state.get("user_profile", {}),
            "required_data": {"types": ["diet", "exercise", "activity"], "range": "recent 7 days"},
            "health_data": {
                "diet_records": state.get("diet_records", []),
                "exercise_records": state.get("exercise_records", []),
                "activity_records": state.get("daily_consumption_records", []),
                "psychology_records": state.get("psychology_records", []),
            },
        },
    )


async def _load_mcp_tools(client):
    return await client.get_tools()


async def _invoke_health_data_agent(agent, sys_message, human_message):
    return await agent.ainvoke({"messages": [sys_message, human_message]})


def _run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def get_health_data(message: str, state: HealthAgentState) -> dict:
    try:
        logger.info("get_health_data start user_id=%s", state.get("user_id", ""))
        from langchain.agents import create_agent
        from langchain.messages import HumanMessage, SystemMessage
        from langchain_mcp_adapters.client import MultiServerMCPClient

        model = zhipu_llm()
        sys_message = SystemMessage(
            content=(
                "你是健康数据编排助手。请结合可用工具识别用户画像、需要查询的数据类型和时间范围，"
                "并以 JSON 返回 profile、required_data、health_data 三个字段。不要输出 Markdown。"
            )
        )
        human_message = HumanMessage(content=f"用户请求：{message}。userId={state['user_id']}")
        mcp_client = MultiServerMCPClient(
            {
                "health-manager": {
                    "transport": "sse",
                    "url": "http://localhost:9000/health/mcp/health-manager/sse",
                },
                "diet": {
                    "transport": "sse",
                    "url": "http://localhost:9000/health/mcp/diet/sse",
                },
                "weight-trend": {
                    "transport": "sse",
                    "url": "http://localhost:9000/health/mcp/weight-trend/sse",
                },
                "activity": {
                    "transport": "sse",
                    "url": "http://localhost:9000/health/mcp/activity/sse",
                },
                "mental-support": {
                    "transport": "sse",
                    "url": "http://localhost:9000/health/mcp/mental-support/sse",
                },
                "risk-guard": {
                    "transport": "sse",
                    "url": "http://localhost:9000/health/mcp/risk-guard/sse",
                },
            }
        )
        tools = _run_async(_load_mcp_tools(mcp_client))
        logger.info("get_health_data loaded_mcp_tools count=%s", len(tools))
        agent = create_agent(model, tools)
        result = _run_async(_invoke_health_data_agent(agent, sys_message, human_message))
        content = _extract_ai_content(result)
        data = _parse_json_content(content)
        patch = _build_health_state(message, state, data)
        logger.info(
            "get_health_data success diet_records=%s exercise_records=%s psychology_records=%s",
            len(patch.get("diet_records", [])),
            len(patch.get("exercise_records", [])),
            len(patch.get("psychology_records", [])),
        )
        return patch
    except Exception as exc:
        logger.exception("get_health_data fallback due to error: %s", exc)
        return _fallback_health_data(message, state)
