"""
LifeHubAI FastAPI 主应用
"""
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 统一加载环境变量（仅在入口加载一次）
load_dotenv()

from routers import codegen_router, tts_router, health_router, finance_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动和关闭时的回调"""
    # 启动时：向 Nacos 注册服务
    try:
        from config import get_config
        config = get_config()
        config.register_service()
    except Exception as e:
        logger.warning(f"Nacos 服务注册跳过: {e}")
    yield
    # 关闭时：从 Nacos 注销服务
    try:
        from config import get_config
        config = get_config()
        config.deregister_service()
    except Exception:
        pass


# 创建 FastAPI 应用
app = FastAPI(
    title="LifeHubAI API",
    description="AI 驱动的代码生成和文本转语音服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(health_router)
app.include_router(finance_router)


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
            "tts": "/api/tts",
            "health_agent": "/api/health",
            "finance_agent": "/api/finance"
        }
    }


@app.get("/health", summary="健康检查")
async def health_check():
    """整体健康检查"""
    return {
        "status": "healthy",
        "servers": {
            "http": "running"
        },
        "services": {
            "code_generation": "/api/codegen/health",
            "text_to_speech": "/api/tts/health",
            "health_agent": "/api/health/health",
            "finance_agent": "/api/finance/health"
        }
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器 — 详情仅写日志，不暴露给客户端"""
    logger.error(f"未处理异常 [{request.url}]: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误，请稍后重试"
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
