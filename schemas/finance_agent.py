"""
财务 Agent 相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict


class FinanceChatRequest(BaseModel):
    """财务咨询请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID，不传则自动创建")


class FinanceChatResponse(BaseModel):
    """财务咨询响应（同步）"""
    response: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")


class FinanceResetRequest(BaseModel):
    """重置会话请求"""
    session_id: str = Field(..., description="要重置的会话 ID")


class FinanceStatusResponse(BaseModel):
    """财务 Agent 服务状态"""
    status: str = Field(..., description="服务状态: healthy 或 degraded")
    model: str = Field(..., description="当前使用的模型")
    session_count: int = Field(..., description="活跃会话数")
    checks: Optional[Dict[str, str]] = Field(None, description="各项检查结果")
