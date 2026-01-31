"""
代码生成 Agent - 使用原生 OpenAI 接口集成数据库工具
不依赖 LangChain/LangGraph，轻量级实现
"""
import os
import json
from typing import List, Dict, Any, Callable
from dotenv import load_dotenv
from openai import OpenAI
from .tools.database_tool import get_db_tool

# 加载环境变量
load_dotenv()


class SimpleAgent:
    """
    简单的 Agent 实现
    使用 OpenAI Function Calling 自动调用工具
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化 Agent

        Args:
            api_key: OpenAI API Key (默认从环境变量读取)
            base_url: API Base URL (默认从环境变量读取)
        """
        # 优先使用 DEEPSEEK_API_KEY，如果没有则使用 API_KEY
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
        base_url = base_url or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")

        if not api_key:
            raise ValueError(
                "未找到 API Key！请在 .env 文件中设置 DEEPSEEK_API_KEY 或 API_KEY\n"
                "示例: DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx"
            )

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

        print(f"  ✓ API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"  ✓ Base URL: {base_url}")

        # 工具注册表
        self.tools: Dict[str, Callable] = {}

        # 对话历史
        self.messages: List[Dict] = []

        print(f"✓ Agent 初始化完成")

    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        parameters: Dict
    ):
        """
        注册一个工具

        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述（给 LLM 看的）
            parameters: JSON Schema 格式的参数定义
        """
        self.tools[name] = {
            "function": func,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
        }
        print(f"  ✓ 注册工具: {name}")

    def get_tools_schema(self) -> List[Dict]:
        """获取所有工具的 Schema（用于发送给 LLM）"""
        return [tool["schema"] for tool in self.tools.values()]

    def run(
        self,
        user_message: str,
        max_iterations: int = 10,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        运行 Agent

        Args:
            user_message: 用户消息
            max_iterations: 最大迭代次数（防止无限循环）
            verbose: 是否打印详细过程

        Returns:
            {
                "success": True/False,
                "final_response": "最终回复",
                "tool_calls": ["工具调用记录"],
                "iterations": "迭代次数"
            }
        """
        # 添加用户消息
        self.messages.append({
            "role": "user",
            "content": user_message
        })

        if verbose:
            print(f"\n{'='*60}")
            print(f"用户: {user_message}")
            print(f"{'='*60}")

        tool_calls_history = []

        # 循环处理（LLM 可能需要多次调用工具）
        for iteration in range(max_iterations):
            if verbose:
                print(f"\n[迭代 {iteration + 1}]")

            # 调用 LLM
            response = self.client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "deepseek-chat"),
                messages=self.messages,
                tools=self.get_tools_schema() if self.tools else None
            )

            message = response.choices[0].message

            # 保存助手回复到历史
            self.messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls
            })

            # 情况 1: LLM 想调用工具
            if message.tool_calls:
                if verbose:
                    print(f"  💭 LLM 决定调用 {len(message.tool_calls)} 个工具")

                # 执行每个工具调用
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    if verbose:
                        print(f"     → 调用: {function_name}")
                        print(f"     → 参数: {json.dumps(arguments, ensure_ascii=False)}")

                    # 执行工具
                    try:
                        if function_name not in self.tools:
                            result = f"错误: 未知工具 {function_name}"
                        else:
                            result = self.tools[function_name]["function"](**arguments)

                        # 转换结果为字符串
                        if isinstance(result, dict):
                            result_str = json.dumps(result, ensure_ascii=False, indent=2)
                        else:
                            result_str = str(result)

                        if verbose:
                            print(f"     ← 返回: {result_str[:100]}...")

                        # 记录工具调用
                        tool_calls_history.append({
                            "name": function_name,
                            "args": arguments,
                            "result": result
                        })

                    except Exception as e:
                        result = f"工具执行错误: {str(e)}"
                        if verbose:
                            print(f"     ✗ 错误: {result}")

                    # 将工具结果添加到消息历史
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": result_str
                    })

            # 情况 2: LLM 完成任务，返回最终回复
            else:
                if verbose:
                    print(f"\n✅ 完成！")
                    print(f"{'='*60}")
                    print(f"最终回复:\n{message.content}")
                    print(f"{'='*60}")

                return {
                    "success": True,
                    "final_response": message.content,
                    "tool_calls": tool_calls_history,
                    "iterations": iteration + 1
                }

        # 达到最大迭代次数
        return {
            "success": False,
            "error": "达到最大迭代次数",
            "final_response": "执行超时，请重试",
            "tool_calls": tool_calls_history
        }

    def reset(self):
        """清空对话历史"""
        self.messages = []
        print("✓ 对话历史已清空")


class CodeGenAgent(SimpleAgent):
    """
    代码生成 Agent
    集成数据库操作工具
    """

    def __init__(self):
        # 初始化基类
        super().__init__()

        # 初始化数据库工具
        self.db = get_db_tool()

        # 注册数据库工具
        self._register_database_tools()

        print(f"✓ 代码生成 Agent 就绪")

    def _register_database_tools(self):
        """注册数据库相关工具"""

        # 工具 1: 列出表
        self.register_tool(
            name="list_tables",
            func=self.db.list_tables,
            description="列出数据库中的所有表。可以指定前缀来过滤表名。",
            parameters={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": "表名前缀，例如 'sys_' 只返回以 sys_ 开头的表。默认为空字符串返回所有表。"
                    }
                }
            }
        )

        # 工具 2: 获取表结构
        self.register_tool(
            name="get_table_schema",
            func=lambda table_name: self.db.get_table_schema(table_name),
            description="获取数据库表的完整结构信息，包括字段名、数据类型、主键、注释等。",
            parameters={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "要查询的表名，例如 'sys_user'"
                    }
                },
                "required": ["table_name"]
            }
        )

        # 工具 3: 测试数据库连接
        self.register_tool(
            name="test_database_connection",
            func=lambda: self.db.test_connection(),
            description="测试数据库连接是否正常，返回数据库版本信息。",
            parameters={
                "type": "object",
                "properties": {}
            }
        )

        # 工具 4: 执行 SQL 查询
        self.register_tool(
            name="execute_query",
            func=lambda query: self.db.execute_query(query),
            description="执行 SQL 查询语句。只允许 SELECT 查询，返回查询结果。",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL SELECT 查询语句"
                    }
                },
                "required": ["query"]
            }
        )

        # 工具 5: 获取表详细信息
        self.register_tool(
            name="get_table_info",
            func=lambda table_name: self.db.get_table_info(table_name),
            description="获取表的详细信息，包括记录数、表大小、字段结构等。",
            parameters={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "表名"
                    }
                },
                "required": ["table_name"]
            }
        )


# ========== 便捷函数 ==========

def get_agent() -> CodeGenAgent:
    """创建并返回代码生成 Agent"""
    return CodeGenAgent()


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("\n" + "="*60)
    print("代码生成 Agent 测试")
    print("="*60)

    # 创建 Agent
    agent = get_agent()

    # 测试 1: 查询表列表
    print("\n【测试 1】查询数据库表")
    result = agent.run(
        "列出数据库中所有的表，告诉我有多少个表",
        verbose=True
    )

    # 测试 2: 获取表结构
    print("\n\n【测试 2】获取表结构")
    agent.reset()  # 清空历史
    result = agent.run(
        "获取 sys_user 表的结构信息，告诉我有哪些字段",
        verbose=True
    )

    # 测试 3: 分析表
    print("\n\n【测试 3】分析表信息")
    agent.reset()
    result = agent.run(
        "分析 sys_user 表，包括字段数、主键、是否有注释等",
        verbose=True
    )
