"""
财务 Agent 服务层
管理 Agent 实例和会话
"""
import uuid
import time
import threading
import logging
from typing import Dict, Generator, Optional
from agent.finance_agent import FinanceAgent

logger = logging.getLogger(__name__)

# 会话配置
MAX_SESSIONS = 100
SESSION_TTL_SECONDS = 3600  # 1 hour
_CLEANUP_INTERVAL_SECONDS = 300  # 5 分钟


class FinanceAgentService:
    """财务 Agent 服务"""

    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._start_cleanup_thread()
        logger.info("财务 Agent 服务初始化完成")

    def _start_cleanup_thread(self):
        def _cleanup_loop():
            while True:
                time.sleep(_CLEANUP_INTERVAL_SECONDS)
                try:
                    with self._lock:
                        self._evict_expired_sessions()
                except Exception as e:
                    logger.error(f"会话清理异常: {e}")

        t = threading.Thread(target=_cleanup_loop, daemon=True, name="finance-session-cleanup")
        t.start()

    def _get_or_create_agent(self, session_id: Optional[str] = None) -> tuple[str, FinanceAgent]:
        with self._lock:
            self._evict_expired_sessions()

            if session_id and session_id in self._sessions:
                self._sessions[session_id]["last_access"] = time.time()
                return session_id, self._sessions[session_id]["agent"]

            if len(self._sessions) >= MAX_SESSIONS:
                self._evict_oldest_session()

            new_session_id = session_id or str(uuid.uuid4())
            agent = FinanceAgent()
            self._sessions[new_session_id] = {
                "agent": agent,
                "last_access": time.time()
            }
            logger.info(f"创建新财务会话: {new_session_id}")
            return new_session_id, agent

    def _evict_expired_sessions(self):
        now = time.time()
        expired = [
            sid for sid, data in self._sessions.items()
            if now - data["last_access"] > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]
            logger.info(f"清理过期财务会话: {sid}")

    def _evict_oldest_session(self):
        if not self._sessions:
            return
        oldest_sid = min(self._sessions, key=lambda sid: self._sessions[sid]["last_access"])
        del self._sessions[oldest_sid]
        logger.info(f"清理最旧财务会话（达到上限 {MAX_SESSIONS}）: {oldest_sid}")

    def chat(self, message: str, session_id: Optional[str] = None) -> dict:
        session_id, agent = self._get_or_create_agent(session_id)
        response = agent.chat(message)
        return {
            "response": response,
            "session_id": session_id
        }

    def chat_stream(self, message: str, session_id: Optional[str] = None) -> Generator[dict, None, None]:
        session_id, agent = self._get_or_create_agent(session_id)
        yield {"type": "session", "session_id": session_id}
        for token in agent.chat_stream(message):
            yield {"type": "token", "token": token}

    def reset(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["agent"].reset()
                self._sessions[session_id]["last_access"] = time.time()
                return True
            return False

    def get_status(self) -> dict:
        import os
        from agent.config import get_finance_api_key, get_finance_model

        with self._lock:
            session_count = len(self._sessions)

        api_key_ok = bool(get_finance_api_key())

        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "agent", "prompts", "finance_system.txt"
        )
        prompt_ok = os.path.isfile(prompt_path)

        model = get_finance_model()
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


# 全局服务实例（线程安全的单例）
_finance_agent_service: Optional[FinanceAgentService] = None
_service_lock = threading.Lock()


def get_finance_agent_service() -> FinanceAgentService:
    """获取财务 Agent 服务实例（线程安全单例）"""
    global _finance_agent_service
    with _service_lock:
        if _finance_agent_service is None:
            _finance_agent_service = FinanceAgentService()
    return _finance_agent_service
