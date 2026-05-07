"""
健康 Agent 公共配置
统一管理环境变量读取和 fallback 逻辑
"""
import os


def get_health_api_key() -> str:
    """获取健康 Agent API Key，按优先级 fallback"""
    return os.getenv("HEALTH_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY") or ""


def get_health_base_url() -> str:
    """获取健康 Agent API Base URL"""
    return os.getenv("HEALTH_LLM_BASE_URL") or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")


def get_health_model() -> str:
    """获取健康 Agent 模型名"""
    return os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")
