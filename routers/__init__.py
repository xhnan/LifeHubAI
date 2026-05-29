"""路由模块初始化"""
from routers.codegen import codegen_router
from routers.tts import tts_router
from routers.health_agent import router as health_router
from routers.finance_agent import router as finance_router

__all__ = ["codegen_router", "tts_router", "health_router", "finance_router"]
