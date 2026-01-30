"""
文本转语音相关的数据模型
"""
from pydantic import BaseModel, Field


class TTSRequest(BaseModel):
    """TTS 请求模型"""
    text: str = Field(..., min_length=1, max_length=1000, description="要转换的文本")
    voice: str = Field(default="female", pattern="^(female|male)$", description="发音人")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速")
    volume: float = Field(default=1.0, ge=0.1, le=1.0, description="音量")


class TTSResponse(BaseModel):
    """TTS 响应模型"""
    success: bool
    message: str
    audio_size: int = 0
    format: str = "pcm"


class HealthResponse(BaseModel):
    """TTS 服务健康检查响应"""
    status: str
    api_configured: bool
