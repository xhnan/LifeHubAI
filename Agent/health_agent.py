"""
健康咨询 Agent
继承 SimpleAgent，提供健康问答能力，支持流式输出
"""
import os
from typing import Generator
from .code_agent import SimpleAgent


class HealthAgent(SimpleAgent):
    """健康咨询 Agent"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        # 优先使用 HEALTH_LLM_* 配置，回退到通用配置
        api_key = api_key or os.getenv("HEALTH_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
        base_url = base_url or os.getenv("HEALTH_LLM_BASE_URL") or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")

        super().__init__(api_key, base_url)

        # 模型配置
        self.model = model or os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")

        # 加载健康系统提示词
        self.system_prompt = self._load_system_prompt()

        # 初始化对话历史（带系统提示）
        self.messages = [{"role": "system", "content": self.system_prompt}]

        print(f"  ✓ 健康 Agent 模型: {self.model}")

    def _load_system_prompt(self) -> str:
        """加载健康顾问系统提示词"""
        prompt_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "prompts",
            "health_system.txt"
        )
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ 系统提示文件不存在: {prompt_path}，使用默认提示")
            return "你是一位专业的健康顾问 AI 助手。请用中文回答用户的健康相关问题。"

    def chat(self, user_message: str) -> str:
        """
        同步对话

        Args:
            user_message: 用户消息

        Returns:
            完整的回答文本
        """
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
            # LLM 调用失败，移除已添加的用户消息，保持历史一致性
            self.messages.pop()
            raise

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        流式对话，逐 chunk 返回

        Args:
            user_message: 用户消息

        Yields:
            每次生成的文本片段
        """
        self.messages.append({"role": "user", "content": user_message})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True
        )

        full_response = ""
        try:
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield token
        finally:
            stream.close()
            # 将完整回复加入历史（即使出错也记录已生成的部分）
            if full_response:
                self.messages.append({
                    "role": "assistant",
                    "content": full_response
                })

    def reset(self):
        """重置对话历史（保留系统提示）"""
        self.messages = [{"role": "system", "content": self.system_prompt}]


# 便捷函数
def get_health_agent() -> HealthAgent:
    """创建并返回健康 Agent"""
    return HealthAgent()


# 测试代码
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("健康 Agent 测试")
    print("=" * 60)

    agent = get_health_agent()

    # 测试同步对话
    print("\n【测试 1】同步对话")
    response = agent.chat("我最近经常失眠，有什么建议吗？")
    print(f"回答: {response}")

    # 测试流式对话
    print("\n【测试 2】流式对话")
    agent.reset()
    for chunk in agent.chat_stream("如何保持健康的饮食习惯？"):
        print(chunk, end="", flush=True)
    print()

    print("\n" + "=" * 60)
    print("测试完成！")
