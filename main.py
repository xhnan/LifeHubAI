"""
LifeHubAI FastAPI 主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import codegen_router, tts_router

# 创建 FastAPI 应用
app = FastAPI(
    title="LifeHubAI API",
    description="AI 驱动的代码生成和文本转语音服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(codegen_router)
app.include_router(tts_router)


@app.get("/", summary="根路径")
async def root():
    """API 根路径"""
    return {
        "name": "LifeHubAI API",
        "version": "1.0.0",
        "description": "AI 驱动的代码生成和文本转语音服务",
        "endpoints": {
            "docs": "/docs",
            "codegen": "/api/codegen",
            "tts": "/api/tts"
        }
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """整体健康检查"""
    return {
        "status": "healthy",
        "services": {
            "code_generation": "/api/codegen/health",
            "text_to_speech": "/api/tts/health"
        }
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": f"服务器错误: {str(exc)}",
            "detail": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn

    # 开发环境运行
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
