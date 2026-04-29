"""
健康 Agent 服务层
管理 Agent 实例和会话
"""
import uuid
from typing import Dict, Generator, Optional
from Agent.health_agent import HealthAgent


class HealthAgentService:
    """健康 Agent 服务"""

    def __init__(self):
        self._sessions: Dict[str, HealthAgent] = {}
        print("✓ 健康 Agent 服务初始化完成")

    def _get_or_create_agent(self, session_id: Optional[str] = None) -> tuple[str, HealthAgent]:
        """
        获取或创建 Agent 实例

        Returns:
            (session_id, agent) 元组
        """
        if session_id and session_id in self._sessions:
            return session_id, self._sessions[session_id]

        # 创建新会话
        new_session_id = session_id or str(uuid.uuid4())
        agent = HealthAgent()
        self._sessions[new_session_id] = agent
        return new_session_id, agent

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

    def chat_stream(self, message: str, session_id: Optional[str] = None) -> Generator[str, None, None]:
        """
        流式健康咨询

        Args:
            message: 用户消息
            session_id: 会话 ID

        Yields:
            文本片段
        """
        session_id, agent = self._get_or_create_agent(session_id)
        yield from agent.chat_stream(message)

    def reset(self, session_id: str) -> bool:
        """
        重置会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        if session_id in self._sessions:
            self._sessions[session_id].reset()
            return True
        return False

    def get_status(self) -> dict:
        """获取服务状态"""
        model = "unknown"
        if self._sessions:
            # 从任意活跃会话获取模型名
            first_agent = next(iter(self._sessions.values()))
            model = first_agent.model
        else:
            import os
            model = os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")

        return {
            "status": "healthy",
            "model": model,
            "session_count": len(self._sessions)
        }

    def get_session_ids(self) -> list[str]:
        """获取所有会话 ID"""
        return list(self._sessions.keys())


# 全局服务实例
_health_agent_service: Optional[HealthAgentService] = None


def get_health_agent_service() -> HealthAgentService:
    """获取健康 Agent 服务实例（单例）"""
    global _health_agent_service
    if _health_agent_service is None:
        _health_agent_service = HealthAgentService()
    return _health_agent_service
