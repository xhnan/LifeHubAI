"""路由模块初始化"""
from routers.codegen import codegen_router
from routers.tts import tts_router

__all__ = ["codegen_router", "tts_router"]
