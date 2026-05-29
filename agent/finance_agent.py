"""
财务咨询 Agent
继承 SimpleAgent，提供个人理财问答能力，支持流式输出
"""
import os
import logging
import threading
from typing import Generator
from .code_agent import SimpleAgent
from .config import (
    get_finance_api_key,
    get_finance_base_url,
    get_finance_model,
)

logger = logging.getLogger(__name__)


class FinanceAgent(SimpleAgent):
    """财务咨询 Agent"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        api_key = api_key or get_finance_api_key()
        base_url = base_url or get_finance_base_url()

        super().__init__(api_key, base_url)

        self.model = model or get_finance_model()

        # 加载财务系统提示词
        self.system_prompt = self._load_system_prompt()

        # 初始化对话历史（带系统提示）
        self.messages = [{"role": "system", "content": self.system_prompt}]

        # 会话级锁，防止并发请求污染消息历史
        self._chat_lock = threading.Lock()
        # 流式输出标志，防止并发 chat_stream 交错写入历史
        self._streaming = False

        logger.info(f"财务 Agent 模型: {self.model}")

    def _load_system_prompt(self) -> str:
        """加载财务顾问系统提示词"""
        prompt_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "prompts",
            "finance_system.txt"
        )
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning(f"系统提示文件不存在: {prompt_path}，使用默认提示")
            return "你是一位专业的财务顾问 AI 助手。请用中文回答用户的理财相关问题。"

    def chat(self, user_message: str) -> str:
        """
        同步对话

        Args:
            user_message: 用户消息

        Returns:
            完整的回答文本

        Raises:
            RuntimeError: 当同一会话有正在进行的流式请求时
        """
        with self._chat_lock:
            if self._streaming:
                raise RuntimeError("该会话有正在进行的流式请求，请等待完成")
            self.messages.append({"role": "user", "content": user_message})

            try:
                response = self._call_llm(use_tools=False)
                assistant_message = response.choices[0].message

                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message.content
                })

                return assistant_message.content
            except Exception:
                self.messages.pop()
                raise

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        流式对话，逐 chunk 返回

        Args:
            user_message: 用户消息

        Yields:
            每次生成的文本片段

        Raises:
            RuntimeError: 当同一会话已有正在进行的流式请求时
        """
        with self._chat_lock:
            if self._streaming:
                raise RuntimeError("该会话已有正在进行的流式请求")
            self._streaming = True
            self.messages.append({"role": "user", "content": user_message})

        stream = None
        full_response = ""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield token
        except Exception:
            with self._chat_lock:
                if self.messages and self.messages[-1]["role"] == "user":
                    self.messages.pop()
            raise
        finally:
            if stream is not None:
                stream.close()
            with self._chat_lock:
                if full_response:
                    self.messages.append({
                        "role": "assistant",
                        "content": full_response
                    })
                self._streaming = False

    def reset(self):
        """重置对话历史（保留系统提示）"""
        self.messages = [{"role": "system", "content": self.system_prompt}]


def get_finance_agent() -> FinanceAgent:
    """创建并返回财务 Agent"""
    return FinanceAgent()
