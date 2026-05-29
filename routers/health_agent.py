"""
健康 Agent 路由
提供健康咨询 REST API，支持 SSE 流式输出

提供两套 SSE 协议：
- 公开协议（/chat） — type: session/token （供 uni-app 等直连使用）
- Java 兼容协议（/agent/stream） — event: start/node/final/error （供 LifeHubServer 调用）
"""
import json
import logging
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from schemas.health_agent import (
    HealthChatRequest,
    HealthChatResponse,
    HealthResetRequest,
    HealthStatusResponse,
)
from services.health_agent_service import get_health_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/health", tags=["健康 Agent"])


# ============== 业务侧 SSE（保持原有协议） ==============

@router.post(
    "/chat",
    summary="健康咨询（SSE 流式 - 业务协议）",
    description="发送健康问题，以 SSE 流式方式返回 AI 回答（type: session / token）"
)
def chat_stream(request: HealthChatRequest):
    """SSE 流式健康咨询（业务侧协议）"""
    service = get_health_agent_service()

    def event_generator():
        try:
            for event in service.chat_stream(request.message, request.session_id):
                if event["type"] == "session":
                    yield f"data: {json.dumps({'session_id': event['session_id']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "token":
                    yield f"data: {json.dumps({'token': event['token']}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"流式对话错误: {e}")
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============== Java 兼容侧 SSE（新增） ==============

class JavaAgentRequest(BaseModel):
    """LifeHubServer 调用的 Agent 请求"""
    message: str = Field(..., description="用户消息")
    user_id: Optional[str] = Field(None, description="用户 ID（可选，由 Java 端 JWT 派生）")
    session_id: Optional[str] = Field(None, description="会话 ID（可选）")


def _format_sse_event(event_name: str, data: dict) -> str:
    """格式化为带 event 字段的 SSE 块"""
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/agent/stream",
    summary="健康 Agent 流式调用（Java 兼容协议）",
    description="供 LifeHubServer 后端调用，发出 start/final/error 命名事件"
)
def java_agent_stream(request: JavaAgentRequest):
    """
    Java 兼容协议 SSE 流。
    协议格式：
        event: start
        data: {"user_id": "...", "message": "..."}

        event: final
        data: {"state": {"final_response": "..."}, "summary": {...}, "record_payload": {...}}

        event: error
        data: {"message": "...", "detail": "..."}
    """
    service = get_health_agent_service()

    def event_generator():
        try:
            # 发送 start 事件
            yield _format_sse_event("start", {
                "user_id": request.user_id or "anonymous",
                "message": request.message,
            })

            # 收集完整响应
            full_response = ""
            session_id = None
            for event in service.chat_stream(request.message, request.session_id):
                if event["type"] == "session":
                    session_id = event["session_id"]
                elif event["type"] == "token":
                    full_response += event["token"]
                    # 同时透传 token 作为 node 事件，让 Java 端可选展示进度
                    # (Java 端的 node handler 会跳过非已知节点)

            # 发送 final 事件（Java 端从 state.final_response 提取文本）
            yield _format_sse_event("final", {
                "state": {
                    "final_response": full_response,
                    "session_id": session_id,
                },
                "summary": {
                    "agent_type": "health",
                    "session_id": session_id,
                },
                "record_payload": {},
            })
        except Exception as e:
            logger.error(f"Java 兼容 Agent 流错误: {e}", exc_info=True)
            yield _format_sse_event("error", {
                "message": str(e),
                "detail": type(e).__name__,
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============== 同步与管理端点（保持不变） ==============

@router.post(
    "/chat/sync",
    response_model=HealthChatResponse,
    summary="健康咨询（同步）",
    description="发送健康问题，同步返回完整 AI 回答"
)
async def chat_sync(request: HealthChatRequest):
    """同步健康咨询"""
    try:
        service = get_health_agent_service()
        result = service.chat(request.message, request.session_id)
        return HealthChatResponse(**result)
    except Exception as e:
        logger.error(f"同步对话错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reset",
    summary="重置会话",
    description="重置指定会话的对话历史"
)
async def reset_session(request: HealthResetRequest):
    """重置会话"""
    service = get_health_agent_service()
    success = service.reset(request.session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"会话不存在: {request.session_id}")
    return {"success": True, "message": "会话已重置"}


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    summary="Agent 服务健康检查",
    description="检查健康 Agent 服务状态"
)
async def health_check():
    """Agent 服务健康检查"""
    try:
        service = get_health_agent_service()
        return HealthStatusResponse(**service.get_status())
    except Exception as e:
        logger.error(f"健康检查错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
