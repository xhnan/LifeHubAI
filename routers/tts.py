"""
文本转语音路由
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from schemas.tts import TTSRequest, TTSResponse, HealthResponse
from services.tts_service import TTSService

router = APIRouter(prefix="/api/tts", tags=["文本转语音"])

tts_service = TTSService()


@router.get("/health", response_model=HealthResponse, summary="TTS服务健康检查")
async def health_check():
    """检查 TTS 服务健康状态"""
    try:
        api_configured = tts_service.check_api_key()
        return HealthResponse(
            status="healthy" if api_configured else "unhealthy",
            api_configured=api_configured
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/speak", response_model=TTSResponse, summary="生成语音（JSON返回）")
async def generate_speech(request: TTSRequest):
    """
    生成语音并返回 JSON 格式的响应

    - text: 要转换的文本
    - voice: 发音人（female/male）
    - speed: 语速（0.5-2.0）
    - volume: 音量（0.1-1.0）
    """
    try:
        result = tts_service.generate_speech(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            volume=request.volume
        )
        return TTSResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", summary="生成语音（文件下载）")
async def generate_speech_file(request: TTSRequest):
    """
    生成语音并直接返回音频文件

    - text: 要转换的文本
    - voice: 发音人（female/male）
    - speed: 语速（0.5-2.0）
    - volume: 音量（0.1-1.0）
    """
    try:
        audio_data = tts_service.generate_speech_bytes(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
            volume=request.volume
        )

        return Response(
            content=audio_data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=audio.pcm",
                "Content-Length": str(len(audio_data))
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 导出路由
tts_router = router
