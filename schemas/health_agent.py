"""
健康 Agent 相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class HealthChatRequest(BaseModel):
    """健康咨询请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID，不传则自动创建")


class HealthChatResponse(BaseModel):
    """健康咨询响应（同步）"""
    response: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")


class HealthResetRequest(BaseModel):
    """重置会话请求"""
    session_id: str = Field(..., description="要重置的会话 ID")


class HealthStatusResponse(BaseModel):
    """健康 Agent 服务状态"""
    status: str = Field(..., description="服务状态")
    model: str = Field(..., description="当前使用的模型")
    session_count: int = Field(..., description="活跃会话数")


class HealthErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="错误详情")
