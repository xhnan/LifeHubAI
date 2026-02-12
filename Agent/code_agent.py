"""
代码生成 Agent - 使用原生 OpenAI 接口集成数据库工具
不依赖 LangChain/LangGraph，轻量级实现
"""
import os
import re
import json
import traceback
from typing import List, Dict, Any, Callable
from dotenv import load_dotenv
from openai import OpenAI
from .tools.database_tool import get_db_tool
from .tools.file_tool import get_file_tool
from .prompt_loader import PromptLoader

# 加载环境变量
load_dotenv()


class SimpleAgent:
    """
    简单的 Agent 实现
    使用 OpenAI Function Calling 自动调用工具
    """

    def __init__(self, api_key: str = None, base_url: str = None):
        # 优先使用 DEEPSEEK_API_KEY，如果没有则使用 API_KEY
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
        base_url = base_url or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")

        if not api_key:
            raise ValueError(
                "未找到 API Key！请在 .env 文件中设置 DEEPSEEK_API_KEY 或 API_KEY\n"
                "示例: DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx"
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = os.getenv("LLM_MODEL", "deepseek-chat")
        self.tools: Dict[str, dict] = {}
        self.messages: List[Dict] = []

        print(f"✓ Agent 初始化完成")
        print(f"  ✓ API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"  ✓ Base URL: {base_url}")

    def register_tool(self, name: str, func: Callable, description: str, parameters: Dict):
        """注册一个工具"""
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
        """获取所有工具的 Schema"""
        return [tool["schema"] for tool in self.tools.values()]

    def _call_llm(self, use_tools: bool = True):
        """统一的 LLM 调用入口"""
        return self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.get_tools_schema() if use_tools and self.tools else None
        )

    def _execute_tool_call(self, tool_call, verbose: bool = True) -> Dict[str, Any]:
        """执行单个工具调用，返回记录"""
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)

        if verbose:
            print(f"     → 调用: {function_name}")
            print(f"     → 参数: {json.dumps(arguments, ensure_ascii=False)}")

        try:
            if function_name not in self.tools:
                result_str = f"错误: 未知工具 {function_name}"
                result = result_str
            else:
                result = self.tools[function_name]["function"](**arguments)
                result_str = json.dumps(result, ensure_ascii=False, indent=2) if isinstance(result, dict) else str(result)

            if verbose:
                print(f"     ← 返回: {result_str[:100]}...")

        except Exception as e:
            result_str = f"工具执行错误: {str(e)}"
            result = result_str
            if verbose:
                print(f"     ✗ 错误: {result_str}")

        # 将工具结果添加到消息历史
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": function_name,
            "content": result_str
        })

        return {"name": function_name, "args": arguments, "result": result}

    def run(self, user_message: str, max_iterations: int = 10, verbose: bool = True) -> Dict[str, Any]:
        """运行 Agent"""
        self.messages.append({"role": "user", "content": user_message})

        if verbose:
            print(f"\n{'='*60}")
            print(f"用户: {user_message}")
            print(f"{'='*60}")

        tool_calls_history = []

        for iteration in range(max_iterations):
            if verbose:
                print(f"\n[迭代 {iteration + 1}]")

            response = self._call_llm()
            message = response.choices[0].message

            self.messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls
            })

            if message.tool_calls:
                if verbose:
                    print(f"  💭 LLM 决定调用 {len(message.tool_calls)} 个工具")

                for tc in message.tool_calls:
                    record = self._execute_tool_call(tc, verbose)
                    tool_calls_history.append(record)
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

        return {
            "success": False,
            "error": "达到最大迭代次数",
            "final_response": "执行超时，请重试",
            "tool_calls": tool_calls_history
        }

    def reset(self):
        """清空对话历史"""
        self.messages = []


class CodeGenAgent(SimpleAgent):
    """
    代码生成 Agent
    集成数据库操作和文件写入工具
    """

    # 默认覆盖规则
    DEFAULT_OVERWRITE_RULES = {
        'base_entity': True,
        'entity': False,
        'mapper': False,
        'mapper_xml': False,
        'service': False,
        'service_impl': False,
        'controller': False,
    }

    # 默认组件列表
    DEFAULT_COMPONENTS = ['entity', 'mapper', 'service', 'service_impl', 'controller', 'mapper_xml']

    def __init__(self, output_dir: str = None, package_prefix: str = None):
        super().__init__()

        self.output_dir = output_dir or os.getenv("CODE_OUTPUT_DIR", "./output")
        self.package_prefix = package_prefix or os.getenv("CODE_PACKAGE_PREFIX", "com.xhn")

        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化工具
        self.db = get_db_tool()
        self.file = get_file_tool(base_dir=self.output_dir)
        self.prompt_loader = PromptLoader()

        # 注册数据库工具
        self._register_tools()

        print(f"✓ 代码生成 Agent 就绪")
        print(f"  ✓ 输出目录: {os.path.abspath(self.output_dir)}")
        print(f"  ✓ 包名前缀: {self.package_prefix}")

    # ==================== 工具注册 ====================

    def _register_tools(self):
        """注册所有工具"""
        tool_defs = [
            ("list_tables", self.db.list_tables,
             "列出数据库中的所有表。可以指定前缀来过滤表名。",
             {"type": "object", "properties": {
                 "prefix": {"type": "string", "description": "表名前缀，例如 'sys_' 只返回以 sys_ 开头的表。默认为空字符串返回所有表。"}
             }}),
            ("get_table_schema", lambda table_name: self.db.get_table_schema(table_name),
             "获取数据库表的完整结构信息，包括字段名、数据类型、主键、注释等。",
             {"type": "object", "properties": {
                 "table_name": {"type": "string", "description": "要查询的表名，例如 'sys_user'"}
             }, "required": ["table_name"]}),
            ("test_database_connection", lambda: self.db.test_connection(),
             "测试数据库连接是否正常，返回数据库版本信息。",
             {"type": "object", "properties": {}}),
            ("execute_query", lambda query: self.db.execute_query(query),
             "执行 SQL 查询语句。只允许 SELECT 查询，返回查询结果。",
             {"type": "object", "properties": {
                 "query": {"type": "string", "description": "SQL SELECT 查询语句"}
             }, "required": ["query"]}),
            ("get_table_info", lambda table_name: self.db.get_table_info(table_name),
             "获取表的详细信息，包括记录数、表大小、字段结构等。",
             {"type": "object", "properties": {
                 "table_name": {"type": "string", "description": "表名"}
             }, "required": ["table_name"]}),
            ("generate_code_for_table", self._generate_code_wrapper,
             "为指定的数据库表生成完整的 Java 代码（Entity、Mapper、Service、Controller等）。",
             {"type": "object", "properties": {
                 "table_name": {"type": "string", "description": "要生成代码的表名，例如 'sys_user'"}
             }, "required": ["table_name"]}),
            ("generate_code_for_tables", self._generate_batch_wrapper,
             "为多个数据库表批量生成 Java 代码。可以指定表名列表。",
             {"type": "object", "properties": {
                 "table_names": {"type": "array", "items": {"type": "string"},
                                 "description": "要生成代码的表名列表，例如 ['sys_user', 'sys_role', 'sys_menu']"}
             }, "required": ["table_names"]}),
        ]

        for name, func, desc, params in tool_defs:
            self.register_tool(name=name, func=func, description=desc, parameters=params)

    # ==================== 代码生成核心逻辑 ====================

    def _generate_code_wrapper(self, table_name: str) -> str:
        """代码生成工具的包装函数（供 Agent 调用）"""
        try:
            result = self.generate_code_for_table(table_name)
            lines = [
                f"{'✅' if result['success'] else '⚠️'} 表 {table_name} 代码生成{'成功' if result['success'] else '部分完成'}",
                f"生成文件: {len(result.get('generated_files', []))} 个",
                f"跳过文件: {len(result.get('skipped_files', []))} 个",
            ]
            if result.get('generated_files'):
                lines.append("\n生成的文件:")
                lines.extend(f"   - {f}" for f in result['generated_files'])
            if result.get('skipped_files'):
                lines.append("\n跳过的文件:")
                lines.extend(f"   - {f}" for f in result['skipped_files'])
            if result.get('errors'):
                lines.append("\n错误:")
                lines.extend(f"   - {e}" for e in result['errors'])
            if result['success']:
                lines.append(f"\n输出目录: {self.output_dir}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ 代码生成异常: {str(e)}\n异常类型: {type(e).__name__}"

    def _generate_batch_wrapper(self, table_names: list) -> str:
        """批量代码生成工具的包装函数"""
        try:
            results = []
            total_generated = 0
            total_skipped = 0

            for table_name in table_names:
                result = self.generate_code_for_table(table_name)
                gen_count = len(result.get('generated_files', []))
                skip_count = len(result.get('skipped_files', []))
                total_generated += gen_count
                total_skipped += skip_count
                status = "✅" if result['success'] else "❌"
                results.append(f"{status} {table_name}: {gen_count} 个文件")

            return (
                f"📦 批量生成完成！\n"
                f"共处理 {len(table_names)} 个表\n"
                f"生成文件: {total_generated} 个\n"
                f"跳过文件: {total_skipped} 个\n"
                f"输出目录: {self.output_dir}\n\n"
                f"详情:\n" + "\n".join(results)
            )
        except Exception as e:
            return f"❌ 批量代码生成异常: {str(e)}"

    def generate_code_for_table(
        self,
        table_name: str,
        components: list = None,
        overwrite_rules: dict = None
    ) -> Dict[str, Any]:
        """为指定表生成 Java 代码"""
        components = components or self.DEFAULT_COMPONENTS
        overwrite_rules = overwrite_rules or dict(self.DEFAULT_OVERWRITE_RULES)

        try:
            # 1. 获取表结构
            schema_result = self.db.get_table_schema(table_name)
            if not schema_result['success']:
                return {"success": False, "error": f"获取表结构失败: {schema_result.get('error')}"}

            # 2. 构建上下文
            context = self.prompt_loader.build_context_for_table(table_name, schema_result, self.package_prefix)

            generated_files = []
            skipped_files = []
            errors = []

            # 3. 逐组件生成
            for component in components:
                try:
                    if component == 'entity':
                        self._generate_entity(context, overwrite_rules, errors, generated_files, skipped_files)
                    else:
                        self._generate_component(component, context, overwrite_rules, errors, generated_files, skipped_files)
                except Exception as e:
                    errors.append(f"{component}: {type(e).__name__}: {str(e)}")
                    print(f"❌ 异常: {component} - {type(e).__name__}: {str(e)}")

            return {
                "success": len(errors) == 0,
                "table_name": table_name,
                "generated_files": generated_files,
                "skipped_files": skipped_files,
                "errors": errors,
                "message": f"成功生成 {len(generated_files)} 个文件，跳过 {len(skipped_files)} 个文件"
            }

        except Exception as e:
            return {"success": False, "error": str(e), "message": f"代码生成失败: {str(e)}"}

    def _generate_component(
        self, component: str, context: dict, overwrite_rules: dict,
        errors: list, generated_files: list, skipped_files: list
    ):
        """生成单个组件（非 Entity）"""
        file_path = self._get_file_path(context['table_name'], component, context)
        overwrite = overwrite_rules.get(component, False)

        # 检查是否需要跳过
        if self._should_skip(file_path, overwrite):
            skipped_files.append(file_path)
            print(f"⊘ 跳过已存在: {file_path}")
            return

        # 调用 LLM 生成
        prompt = self.prompt_loader.fill_template(component, context)
        response = self._call_llm_for_code(prompt)

        # 提取代码
        expected_lang = 'xml' if component == 'mapper_xml' else 'java'
        success, code = self._extract_single_code_block(response, expected_lang)

        if not success:
            errors.append(f"{component}: 无法从 LLM 输出中提取有效的代码块")
            print(f"⚠️ {component}: 代码提取失败")
            self._save_debug_info(component, response)
            return

        # 写入文件
        self._write_and_track(file_path, code, overwrite, component, errors, generated_files, skipped_files)

    def _generate_entity(
        self, context: dict, overwrite_rules: dict,
        errors: list, generated_files: list, skipped_files: list
    ):
        """生成 Entity 组件（BaseEntity + Entity 两个文件）"""
        table_name = context['table_name']
        base_file_path = self._get_file_path(table_name, 'base_entity', context)
        entity_file_path = self._get_file_path(table_name, 'entity', context)
        entity_overwrite = overwrite_rules.get('entity', False)

        entity_should_skip = self._should_skip(entity_file_path, entity_overwrite)

        # 调用 LLM 生成 Entity 代码（包含 BaseEntity 和 Entity 两个类）
        prompt = self.prompt_loader.fill_template('entity', context)
        response = self._call_llm_for_code(prompt)
        code_blocks = self._extract_multiple_code_blocks(response)

        if len(code_blocks) < 2:
            errors.append(f"entity: LLM 未返回 2 个代码块，只返回了 {len(code_blocks)} 个")
            self._save_debug_info('entity', response)
            return

        # 写入 BaseEntity（总是覆盖）
        self._write_and_track(base_file_path, code_blocks[0], True, 'base_entity', errors, generated_files, skipped_files)

        # 写入 Entity（根据规则决定是否跳过）
        if entity_should_skip:
            skipped_files.append(entity_file_path)
            print(f"⊘ 跳过已存在: {entity_file_path}")
        else:
            self._write_and_track(entity_file_path, code_blocks[1], entity_overwrite, 'entity', errors, generated_files, skipped_files)

    # ==================== 辅助方法 ====================

    def _call_llm_for_code(self, prompt: str) -> str:
        """调用 LLM 生成代码（不走 Agent 工具链，直接单次调用）"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    def _should_skip(self, file_path: str, overwrite: bool) -> bool:
        """检查文件是否应该跳过"""
        if overwrite:
            return False
        result = self.file.file_exists(file_path)
        return result.get('success', False) and result.get('exists', False)

    def _write_and_track(
        self, file_path: str, code: str, overwrite: bool,
        component: str, errors: list, generated_files: list, skipped_files: list
    ):
        """写入文件并更新跟踪列表"""
        result = self.file.write_file(file_path, code, overwrite=overwrite)
        if result['success']:
            generated_files.append(file_path)
            print(f"✅ 生成: {file_path} ({result.get('size', 0)} 字节)")
        else:
            errors.append(f"{component}: 写入失败 - {result.get('error', '未知')}")
            print(f"❌ {component}: 写入失败 - {result.get('error', '未知')}")

    def _save_debug_info(self, component: str, content: str):
        """保存 LLM 原始输出到调试文件"""
        import datetime
        logs_dir = os.path.join(self.output_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = os.path.join(logs_dir, f"debug_{component}_{timestamp}.txt")
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {component} LLM Output ===\n")
                f.write(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(content)
            print(f"💾 调试信息已保存: {debug_file}")
        except Exception as e:
            print(f"⚠️ 无法保存调试信息: {e}")

    # ==================== 代码提取 ====================

    def _extract_single_code_block(self, text: str, expected_lang: str = None) -> tuple:
        """从文本中提取单个代码块"""
        # 正则匹配
        patterns = [
            r'```(?:java|xml)?\s*\n(.*?)\n```',
            r'```(?:java|xml)?\s*\n(.*?)```',
            r'```(?:java|xml)? ([^`]+)```',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                code = match.group(1).strip()
                if len(code) > 50:
                    return True, code

        # 后备：字符串查找
        for marker in ['```java', '```xml', '```']:
            if marker in text:
                start = text.find(marker) + len(marker)
                end = text.find('```', start)
                code = (text[start:end] if end != -1 else text[start:]).strip()
                if len(code) > 50:
                    return True, code

        return False, ''

    def _extract_multiple_code_blocks(self, text: str) -> list:
        """从文本中提取所有 Java 代码块"""
        code_blocks = []
        lines = text.split('\n')
        current_block = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('```'):
                if not in_code_block:
                    if 'java' in stripped.lower():
                        in_code_block = True
                        current_block = []
                else:
                    if current_block:
                        code = '\n'.join(current_block).strip()
                        if len(code) > 50:
                            code_blocks.append(code)
                    in_code_block = False
                    current_block = []
                continue

            if in_code_block:
                current_block.append(line)

        # 处理未闭合的代码块
        if in_code_block and current_block:
            code = '\n'.join(current_block).strip()
            if len(code) > 50:
                code_blocks.append(code)

        return code_blocks

    # ==================== 文件路径 ====================

    def _get_file_path(self, table_name: str, component: str, context: dict) -> str:
        """获取生成文件的路径"""
        pkg_dir = context['package_path'].replace('.', '/')
        class_name = context['class_name']
        base = f"src/main/java/{pkg_dir}"

        path_map = {
            'base_entity': f"{base}/model/Base{class_name}.java",
            'entity':      f"{base}/model/{class_name}.java",
            'mapper':      f"{base}/mapper/{class_name}Mapper.java",
            'service':     f"{base}/service/{class_name}Service.java",
            'service_impl': f"{base}/service/impl/{class_name}ServiceImpl.java",
            'controller':  f"{base}/controller/{class_name}Controller.java",
            'mapper_xml':  f"src/main/resources/mapper/{context.get('module_name', '')}/{class_name}Mapper.xml",
        }

        if component not in path_map:
            raise ValueError(f"未知的组件类型: {component}")

        return path_map[component]


# ========== 便捷函数 ==========

def get_agent() -> CodeGenAgent:
    """创建并返回代码生成 Agent"""
    return CodeGenAgent()


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("\n" + "="*60)
    print("代码生成 Agent 测试")
    print("="*60)

    agent = get_agent()

    print("\n【测试 1】查询数据库表")
    result = agent.run("列出数据库中所有的表，告诉我有多少个表", verbose=True)

    print("\n\n【测试 2】获取表结构")
    agent.reset()
    result = agent.run("获取 sys_user 表的结构信息，告诉我有哪些字段", verbose=True)

    print("\n\n【测试 3】分析表信息")
    agent.reset()
    result = agent.run("分析 sys_user 表，包括字段数、主键、是否有注释等", verbose=True)
