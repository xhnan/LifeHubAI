"""
财务 Agent 路由
提供财务咨询 REST API，支持 SSE 流式输出

提供两套 SSE 协议：
- 公开协议（/chat） — type: session/token （供 uni-app 等直连使用）
- Java 兼容协议（/agent/stream） — event: start/final/error （供 LifeHubServer 调用）
"""
import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from schemas.finance_agent import (
    FinanceChatRequest,
    FinanceChatResponse,
    FinanceResetRequest,
    FinanceStatusResponse,
)
from services.finance_agent_service import get_finance_agent_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/finance", tags=["财务 Agent"])


# ============== 业务侧 SSE ==============

@router.post(
    "/chat",
    summary="财务咨询（SSE 流式 - 业务协议）",
    description="发送理财问题，以 SSE 流式方式返回 AI 回答（type: session / token）"
)
def chat_stream(request: FinanceChatRequest):
    """SSE 流式财务咨询（业务侧协议）"""
    service = get_finance_agent_service()

    def event_generator():
        try:
            for event in service.chat_stream(request.message, request.session_id):
                if event["type"] == "session":
                    yield f"data: {json.dumps({'session_id': event['session_id']}, ensure_ascii=False)}\n\n"
                elif event["type"] == "token":
                    yield f"data: {json.dumps({'token': event['token']}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"财务流式对话错误: {e}")
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


# ============== Java 兼容协议 ==============

class JavaFinanceAgentRequest(BaseModel):
    """LifeHubServer 调用的财务 Agent 请求"""
    message: str = Field(..., description="用户消息")
    user_id: Optional[str] = Field(None, description="用户 ID（可选，由 Java 端 JWT 派生）")
    session_id: Optional[str] = Field(None, description="会话 ID（可选）")


def _format_sse_event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post(
    "/agent/stream",
    summary="财务 Agent 流式调用（Java 兼容协议）",
    description="供 LifeHubServer 后端调用，发出 start/final/error 命名事件"
)
def java_agent_stream(request: JavaFinanceAgentRequest):
    """
    Java 兼容协议 SSE 流。
    与 health agent 的 /api/health/agent/stream 协议完全相同，
    但路由到 finance agent 实例。
    """
    service = get_finance_agent_service()

    def event_generator():
        try:
            yield _format_sse_event("start", {
                "user_id": request.user_id or "anonymous",
                "message": request.message,
            })

            full_response = ""
            session_id = None
            for event in service.chat_stream(request.message, request.session_id):
                if event["type"] == "session":
                    session_id = event["session_id"]
                elif event["type"] == "token":
                    full_response += event["token"]

            yield _format_sse_event("final", {
                "state": {
                    "final_response": full_response,
                    "session_id": session_id,
                },
                "summary": {
                    "agent_type": "finance",
                    "session_id": session_id,
                },
                "record_payload": {},
            })
        except Exception as e:
            logger.error(f"Java 兼容财务 Agent 流错误: {e}", exc_info=True)
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


# ============== 同步与管理端点 ==============

@router.post(
    "/chat/sync",
    response_model=FinanceChatResponse,
    summary="财务咨询（同步）",
    description="发送理财问题，同步返回完整 AI 回答"
)
async def chat_sync(request: FinanceChatRequest):
    """同步财务咨询"""
    try:
        service = get_finance_agent_service()
        result = service.chat(request.message, request.session_id)
        return FinanceChatResponse(**result)
    except Exception as e:
        logger.error(f"同步对话错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reset",
    summary="重置会话",
    description="重置指定会话的对话历史"
)
async def reset_session(request: FinanceResetRequest):
    """重置会话"""
    service = get_finance_agent_service()
    success = service.reset(request.session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"会话不存在: {request.session_id}")
    return {"success": True, "message": "会话已重置"}


@router.get(
    "/health",
    response_model=FinanceStatusResponse,
    summary="财务 Agent 服务健康检查",
)
async def health_check():
    """财务 Agent 服务健康检查"""
    try:
        service = get_finance_agent_service()
        return FinanceStatusResponse(**service.get_status())
    except Exception as e:
        logger.error(f"健康检查错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))
