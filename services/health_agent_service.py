"""
健康 Agent 服务层
管理 Agent 实例和会话
"""
import uuid
import time
import threading
import logging
from typing import Dict, Generator, Optional
from Agent.health_agent import HealthAgent

logger = logging.getLogger(__name__)

# 会话配置
MAX_SESSIONS = 100
SESSION_TTL_SECONDS = 3600  # 1 hour


class HealthAgentService:
    """健康 Agent 服务"""

    def __init__(self):
        self._sessions: Dict[str, dict] = {}  # {session_id: {"agent": HealthAgent, "last_access": timestamp}}
        self._lock = threading.Lock()
        logger.info("健康 Agent 服务初始化完成")

    def _get_or_create_agent(self, session_id: Optional[str] = None) -> tuple[str, HealthAgent]:
        """
        获取或创建 Agent 实例

        Returns:
            (session_id, agent) 元组
        """
        with self._lock:
            # 清理过期会话
            self._evict_expired_sessions()

            if session_id and session_id in self._sessions:
                self._sessions[session_id]["last_access"] = time.time()
                return session_id, self._sessions[session_id]["agent"]

            # 检查会话数限制
            if len(self._sessions) >= MAX_SESSIONS:
                self._evict_oldest_session()

            # 创建新会话
            new_session_id = session_id or str(uuid.uuid4())
            agent = HealthAgent()
            self._sessions[new_session_id] = {
                "agent": agent,
                "last_access": time.time()
            }
            logger.info(f"创建新会话: {new_session_id}")
            return new_session_id, agent

    def _evict_expired_sessions(self):
        """清理过期会话（需要在 _lock 内调用）"""
        now = time.time()
        expired = [
            sid for sid, data in self._sessions.items()
            if now - data["last_access"] > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]
            logger.info(f"清理过期会话: {sid}")

    def _evict_oldest_session(self):
        """清理最旧的会话（需要在 _lock 内调用）"""
        if not self._sessions:
            return
        oldest_sid = min(self._sessions, key=lambda sid: self._sessions[sid]["last_access"])
        del self._sessions[oldest_sid]
        logger.info(f"清理最旧会话（达到上限 {MAX_SESSIONS}）: {oldest_sid}")

    def chat(self, message: str, session_id: Optional[str] = None) -> dict:
        """
        同步健康咨询

        Args:
            message: 用户消息
            session_id: 会话 ID

        Returns:
            包含 response 和 session_id 的字典
        """
        session_id, agent = self._get_or_create_agent(session_id)
        response = agent.chat(message)
        return {
            "response": response,
            "session_id": session_id
        }

    def chat_stream(self, message: str, session_id: Optional[str] = None) -> Generator[dict, None, None]:
        """
        流式健康咨询

        Args:
            message: 用户消息
            session_id: 会话 ID

        Yields:
            包含 token 或 session_id 的字典
        """
        session_id, agent = self._get_or_create_agent(session_id)
        # 先发送 session_id
        yield {"type": "session", "session_id": session_id}
        # 再发送 token
        for token in agent.chat_stream(message):
            yield {"type": "token", "token": token}

    def reset(self, session_id: str) -> bool:
        """
        重置会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["agent"].reset()
                self._sessions[session_id]["last_access"] = time.time()
                return True
            return False

    def get_status(self) -> dict:
        """获取服务状态，实际验证关键配置"""
        import os

        with self._lock:
            session_count = len(self._sessions)

        # 验证 API Key
        api_key = os.getenv("HEALTH_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
        api_key_ok = bool(api_key)

        # 验证 Prompt 文件
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Agent", "prompts", "health_system.txt"
        )
        prompt_ok = os.path.isfile(prompt_path)

        # 验证模型配置
        model = os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")
        model_ok = bool(model)

        all_ok = api_key_ok and prompt_ok and model_ok

        return {
            "status": "healthy" if all_ok else "degraded",
            "model": model,
            "session_count": session_count,
            "checks": {
                "api_key": "ok" if api_key_ok else "missing",
                "prompt_file": "ok" if prompt_ok else f"not found: {prompt_path}",
                "model": "ok" if model_ok else "not configured"
            }
        }

    def get_session_ids(self) -> list[str]:
        """获取所有会话 ID"""
        with self._lock:
            return list(self._sessions.keys())


# 全局服务实例（线程安全的单例）
_health_agent_service: Optional[HealthAgentService] = None
_service_lock = threading.Lock()


def get_health_agent_service() -> HealthAgentService:
    """获取健康 Agent 服务实例（线程安全单例）"""
    global _health_agent_service
    if _health_agent_service is None:
        with _service_lock:
            if _health_agent_service is None:
                _health_agent_service = HealthAgentService()
    return _health_agent_service
