"""
Agent 公共配置
统一管理环境变量读取和 fallback 逻辑

支持 health / finance 两类 Agent 各自独立的 LLM 配置，
未配置时 fallback 到 DEEPSEEK_API_KEY 等通用变量。
"""
import os


# ============== Health Agent ==============

def get_health_api_key() -> str:
    """获取健康 Agent API Key，按优先级 fallback"""
    return os.getenv("HEALTH_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY") or ""


def get_health_base_url() -> str:
    """获取健康 Agent API Base URL"""
    return os.getenv("HEALTH_LLM_BASE_URL") or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")


def get_health_model() -> str:
    """获取健康 Agent 模型名"""
    return os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")


# ============== Finance Agent ==============

def get_finance_api_key() -> str:
    """获取财务 Agent API Key，未配置时复用 health 的"""
    return os.getenv("FINANCE_LLM_API_KEY") or get_health_api_key()


def get_finance_base_url() -> str:
    """获取财务 Agent API Base URL"""
    return os.getenv("FINANCE_LLM_BASE_URL") or get_health_base_url()


def get_finance_model() -> str:
    """获取财务 Agent 模型名"""
    return os.getenv("FINANCE_LLM_MODEL") or get_health_model()
