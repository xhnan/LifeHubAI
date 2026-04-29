"""
健康 Agent 路由
提供健康咨询 REST API，支持 SSE 流式输出
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.health_agent import (
    HealthChatRequest,
    HealthChatResponse,
    HealthResetRequest,
    HealthStatusResponse,
    HealthErrorResponse
)
from services.health_agent_service import get_health_agent_service

router = APIRouter(prefix="/api/health", tags=["健康 Agent"])


@router.post(
    "/chat",
    summary="健康咨询（SSE 流式）",
    description="发送健康问题，以 SSE 流式方式返回 AI 回答"
)
async def chat_stream(request: HealthChatRequest):
    """SSE 流式健康咨询"""
    service = get_health_agent_service()

    def event_generator():
        try:
            for chunk in service.chat_stream(request.message, request.session_id):
                yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))
