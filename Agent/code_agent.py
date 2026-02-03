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
from .tools.file_tool import get_file_tool
from .prompt_loader import PromptLoader
from .code_validator import CodeValidator

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

    def __init__(
        self,
        output_dir: str = None,
        package_prefix: str = None,
        enable_validation: bool = None,
        enable_llm_validation: bool = True,
        enable_compile_check: bool = True,
        enable_prompt_check: bool = True
    ):
        """
        初始化 Agent

        Args:
            output_dir: 代码生成输出目录（默认从环境变量 CODE_OUTPUT_DIR 读取）
            package_prefix: 包名前缀（默认从环境变量 CODE_PACKAGE_PREFIX 读取）
            enable_validation: 是否启用验证（默认从环境变量读取）
            enable_llm_validation: 是否启用 LLM 验证
            enable_compile_check: 是否启用编译检查
            enable_prompt_check: 是否启用 Prompt 符合度检查
        """
        # 初始化基类
        super().__init__()

        # 从环境变量读取配置
        self.output_dir = output_dir or os.getenv("CODE_OUTPUT_DIR", "./output")
        self.package_prefix = package_prefix or os.getenv("CODE_PACKAGE_PREFIX", "com.xhn")

        # 验证开关配置（从环境变量或参数读取）
        self.enable_validation = enable_validation if enable_validation is not None else \
                                 os.getenv("CODE_ENABLE_VALIDATION", "true").lower() == "true"
        self.enable_llm_validation = enable_llm_validation and \
                                    os.getenv("CODE_ENABLE_LLM_VALIDATION", "true").lower() == "true"
        self.enable_compile_check = enable_compile_check and \
                                    os.getenv("CODE_ENABLE_COMPILE_CHECK", "true").lower() == "true"
        self.enable_prompt_check = enable_prompt_check and \
                                   os.getenv("CODE_ENABLE_PROMPT_CHECK", "true").lower() == "true"

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 初始化工具
        self.db = get_db_tool()
        self.file = get_file_tool(base_dir=self.output_dir)
        self.prompt_loader = PromptLoader()

        # 初始化验证器
        if self.enable_validation:
            self.validator = CodeValidator()
            print(f"✓ 代码验证器已启用")
        else:
            self.validator = None
            print(f"⊘ 代码验证器已禁用")

        # 注册数据库工具
        self._register_database_tools()

        print(f"✓ 代码生成 Agent 就绪")
        print(f"  ✓ 输出目录: {os.path.abspath(self.output_dir)}")
        print(f"  ✓ 包名前缀: {self.package_prefix}")

        # 显示验证配置
        if self.enable_validation:
            print(f"  ✓ 验证配置:")
            print(f"     - LLM 验证: {'✓' if self.enable_llm_validation else '⊘'}")
            print(f"     - 编译检查: {'✓' if self.enable_compile_check else '⊘'}")
            print(f"     - Prompt 检查: {'✓' if self.enable_prompt_check else '⊘'}")

    def _generate_code_wrapper(self, table_name: str) -> str:
        """
        代码生成工具的包装函数
        供 Agent 调用，返回格式化的结果信息

        Args:
            table_name: 表名

        Returns:
            格式化的结果字符串
        """
        try:
            result = self.generate_code_for_table(
                table_name=table_name,
                components=['entity', 'mapper', 'service', 'service_impl', 'controller', 'mapper_xml'],
                overwrite_rules=None  # 使用默认规则
            )

            # 构建详细的结果报告
            report_lines = [
                f"表: {table_name}",
                f"生成文件: {len(result.get('generated_files', []))} 个",
                f"跳过文件: {len(result.get('skipped_files', []))} 个",
            ]

            # 显示生成的文件
            if result.get('generated_files'):
                report_lines.append("\n✅ 生成的文件:")
                for f in result['generated_files']:
                    report_lines.append(f"   - {f}")

            # 显示跳过的文件
            if result.get('skipped_files'):
                report_lines.append("\n⊘ 跳过的文件:")
                for f in result['skipped_files']:
                    report_lines.append(f"   - {f}")

            # 显示错误
            if result.get('errors'):
                report_lines.append("\n❌ 错误详情:")
                for err in result['errors']:
                    report_lines.append(f"   - {err}")

            # 判断总体成功或失败
            if result['success']:
                report_lines.insert(0, f"✅ 成功为表 {table_name} 生成代码！")
                report_lines.append(f"\n输出目录: {self.output_dir}")
            else:
                report_lines.insert(0, f"⚠️ 表 {table_name} 代码生成部分完成")

            return "\n".join(report_lines)

        except Exception as e:
            return f"❌ 代码生成异常: {str(e)}\n异常类型: {type(e).__name__}"

    def _generate_batch_wrapper(self, table_names: list) -> str:
        """
        批量代码生成工具的包装函数

        Args:
            table_names: 表名列表

        Returns:
            格式化的结果字符串
        """
        try:
            results = []
            total_generated = 0
            total_skipped = 0

            for table_name in table_names:
                result = self.generate_code_for_table(
                    table_name=table_name,
                    components=['entity', 'mapper', 'service', 'service_impl', 'controller', 'mapper_xml'],
                    overwrite_rules=None
                )

                if result['success']:
                    total_generated += len(result['generated_files'])
                    total_skipped += len(result['skipped_files'])
                    results.append(f"✅ {table_name}: {len(result['generated_files'])} 个文件")
                else:
                    results.append(f"❌ {table_name}: {result.get('message', '失败')}")

            summary = "\n".join(results)
            return (
                f"📦 批量生成完成！\n"
                f"共处理 {len(table_names)} 个表\n"
                f"生成文件: {total_generated} 个\n"
                f"跳过文件: {total_skipped} 个\n"
                f"输出目录: {self.output_dir}\n\n"
                f"详情:\n{summary}"
            )

        except Exception as e:
            return f"❌ 批量代码生成异常: {str(e)}"

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

        # 工具 6: 为单个表生成代码
        self.register_tool(
            name="generate_code_for_table",
            func=self._generate_code_wrapper,
            description="为指定的数据库表生成完整的 Java 代码（Entity、Mapper、Service、Controller等）。",
            parameters={
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "要生成代码的表名，例如 'sys_user'"
                    }
                },
                "required": ["table_name"]
            }
        )

        # 工具 7: 批量生成多个表的代码
        self.register_tool(
            name="generate_code_for_tables",
            func=self._generate_batch_wrapper,
            description="为多个数据库表批量生成 Java 代码。可以指定表名列表。",
            parameters={
                "type": "object",
                "properties": {
                    "table_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要生成代码的表名列表，例如 ['sys_user', 'sys_role', 'sys_menu']"
                    }
                },
                "required": ["table_names"]
            }
        )

    def _save_debug_info(self, component: str, content: str, output_dir: str = None) -> None:
        """
        保存 LLM 原始输出到调试文件

        Args:
            component: 组件名称
            content: 原始内容
            output_dir: 输出目录（默认使用 self.output_dir）
        """
        if output_dir is None:
            output_dir = self.output_dir

        # 创建 logs 目录
        logs_dir = os.path.join(output_dir, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        # 使用时间戳创建唯一的调试文件名
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = os.path.join(logs_dir, f"debug_{component}_{timestamp}.txt")

        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {component} LLM Output ===\n")
                f.write(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(content)
            print(f"💾 调试信息已保存: {debug_file}")
        except Exception as debug_err:
            print(f"⚠️ 无法保存调试信息: {debug_err}")

    def _write_component_file(
        self,
        file_path: str,
        code: str,
        overwrite: bool,
        component_name: str,
        errors_list: list = None
    ) -> dict:
        """
        统一的组件文件写入逻辑

        Args:
            file_path: 文件路径
            code: 代码内容
            overwrite: 是否覆盖
            component_name: 组件名称（用于错误消息）
            errors_list: 错误列表（可选）

        Returns:
            {
                'success': True/False,
                'action': 'generated'/'skipped'/'failed',
                'message': '描述信息'
            }
        """
        result = {
            'success': False,
            'action': 'failed',
            'message': ''
        }

        try:
            # 检查文件是否已存在
            exists_result = self.file.file_exists(file_path)
            should_skip = (
                exists_result.get('success', False) and
                exists_result.get('exists', False) and
                not overwrite
            )

            if should_skip:
                result['action'] = 'skipped'
                result['message'] = f"⊘ 跳过已存在: {file_path}"
                result['success'] = True
                print(result['message'])
            else:
                write_result = self.file.write_file(file_path, code, overwrite=overwrite)
                if write_result['success']:
                    result['action'] = 'generated'
                    result['message'] = f"✅ 生成: {file_path} ({write_result.get('size', 0)} 字节)"
                    result['success'] = True
                    print(result['message'])
                else:
                    error_msg = f"{component_name}: 写入失败 | 错误: {write_result.get('error', '未知')} | 路径: {file_path}"
                    result['message'] = f"❌ {error_msg}"
                    if errors_list:
                        errors_list.append(error_msg)
                    print(result['message'])

        except Exception as e:
            error_msg = f"{component_name}: 写入异常 | {type(e).__name__}: {str(e)} | 路径: {file_path}"
            result['message'] = f"❌ {error_msg}"
            if errors_list:
                errors_list.append(error_msg)
            print(result['message'])

        return result

    def _generate_entity_component(
        self,
        context: dict,
        overwrite_rules: dict,
        errors_list: list,
        generated_files: list,
        skipped_files: list
    ) -> bool:
        """
        生成 Entity 组件（包括 BaseEntity 和 Entity 两个类）

        BaseEntity: 每次强制生成，不验证
        Entity: 存在则跳过，不存在才生成并验证

        Args:
            context: 上下文信息
            overwrite_rules: 覆盖规则
            errors_list: 错误列表
            generated_files: 已生成文件列表
            skipped_files: 已跳过文件列表

        Returns:
            是否成功（部分成功也返回 True）
        """
        try:
            table_name = context.get('table_name', '')
            base_file_path = self._get_file_path(table_name, 'base_entity', context)
            entity_file_path = self._get_file_path(table_name, 'entity', context)
            base_overwrite = overwrite_rules.get('base_entity', True)
            entity_overwrite = overwrite_rules.get('entity', False)

            # 0. 检查 Entity 文件是否需要生成（BaseEntity 总是生成）
            entity_exists = self.file.file_exists(entity_file_path)
            entity_should_skip = (
                entity_exists.get('success', False) and
                entity_exists.get('exists', False) and
                not entity_overwrite
            )

            if entity_should_skip:
                # Entity 文件存在且不覆盖，只生成 BaseEntity
                print(f"⊘ 跳过已存在: {entity_file_path}")
                skipped_files.append(entity_file_path)

                # 单独生成 BaseEntity
                prompt = self.prompt_loader.fill_template('entity', context)
                response = self.client.chat.completions.create(
                    model=os.getenv("LLM_MODEL", "deepseek-chat"),
                    messages=[{"role": "user", "content": prompt}]
                )
                generated_code = response.choices[0].message.content
                code_blocks = self._extract_multiple_code_blocks(generated_code)

                if len(code_blocks) < 2:
                    errors_list.append(f"entity: LLM 未返回 2 个代码块")
                    self._save_debug_info('entity', generated_code)
                    return False

                # 写入 BaseEntity（不验证）
                base_result = self._write_component_file(
                    base_file_path,
                    code_blocks[0],
                    True,  # BaseEntity 总是覆盖
                    'base_entity',
                    errors_list
                )
                if base_result['success'] and base_result['action'] == 'generated':
                    generated_files.append(base_file_path)
                return True

            # 需要生成两个文件，调用 LLM
            # 1. 加载并填充 Prompt
            prompt = self.prompt_loader.fill_template('entity', context)

            # 2. 调用 LLM 生成代码
            response = self.client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}]
            )

            generated_code = response.choices[0].message.content

            # 3. 分离两个类的代码（Base 类和继承类）
            code_blocks = self._extract_multiple_code_blocks(generated_code)

            # 4. 验证代码块数量
            if len(code_blocks) < 2:
                error_detail = (
                    f"entity: LLM 未返回 2 个代码块，只返回了 {len(code_blocks)} 个。"
                    f"原始输出长度: {len(generated_code)}"
                )
                errors_list.append(error_detail)
                print(f"⚠️ {error_detail}")
                self._save_debug_info('entity', generated_code)
                return False

            # 5. 写入 BaseEntity 文件（不验证）
            base_result = self._write_component_file(
                base_file_path,
                code_blocks[0],
                True,  # BaseEntity 总是覆盖
                'base_entity',
                errors_list
            )

            if base_result['success']:
                if base_result['action'] == 'generated':
                    generated_files.append(base_file_path)
                elif base_result['action'] == 'skipped':
                    skipped_files.append(base_file_path)

            # 6. 写入 Entity 文件（新文件才验证）
            is_new_entity = not (entity_exists.get('success', False) and entity_exists.get('exists', False))

            # 如果是新文件且启用了验证，先验证再写入
            if is_new_entity and self.validator and self.enable_validation:
                validation_result = self.validator.validate_all(
                    code=code_blocks[1],
                    component='entity',
                    context=context,
                    enable_llm=self.enable_llm_validation,
                    enable_compile=self.enable_compile_check,
                    enable_prompt=self.enable_prompt_check
                )

                if not validation_result['success']:
                    validation_issues = []
                    if validation_result.get('llm_check') and not validation_result['llm_check']['passed']:
                        issues = validation_result['llm_check'].get('issues', [])
                        validation_issues.extend([f"[LLM] {i}" for i in issues])
                    if validation_result.get('compile_check') and not validation_result['compile_check']['passed']:
                        errs = validation_result['compile_check'].get('errors', [])[:3]
                        validation_issues.extend([f"[编译] {e}" for e in errs])
                    if validation_result.get('prompt_check') and not validation_result['prompt_check']['passed']:
                        missing = validation_result['prompt_check'].get('missing_items', [])
                        validation_issues.extend([f"[符合度] {m}" for m in missing])

                    if validation_issues:
                        error_detail = f"entity: 验证未通过 - " + "; ".join(validation_issues[:3])
                        errors_list.append(error_detail)
                        print(f"⚠️ {error_detail}")
                        self._save_debug_info(f"entity_validation_failed", code_blocks[1])

            entity_result = self._write_component_file(
                entity_file_path,
                code_blocks[1],
                entity_overwrite,
                'entity',
                errors_list
            )

            if entity_result['success']:
                if entity_result['action'] == 'generated':
                    generated_files.append(entity_file_path)
                elif entity_result['action'] == 'skipped':
                    skipped_files.append(entity_file_path)

            return True

        except Exception as e:
            import traceback
            error_detail = f"entity: {type(e).__name__}: {str(e)}\n堆栈: {traceback.format_exc()[-500:]}"
            errors_list.append(error_detail)
            print(f"❌ 异常: entity - {type(e).__name__}: {str(e)}")
            return False

    def generate_code_for_table(
        self,
        table_name: str,
        components: list = None,
        overwrite_rules: dict = None
    ) -> Dict[str, Any]:
        """
        为指定表生成 Java 代码

        Args:
            table_name: 数据库表名
            components: 要生成的组件列表，默认为 ['entity', 'mapper', 'service', 'service_impl', 'controller']
                        可选值: 'entity', 'mapper', 'service', 'service_impl', 'controller', 'mapper_xml'
            overwrite_rules: 覆盖规则，例如 {'entity': False, 'service_impl': True}
                            True=强制覆盖, False=跳过已存在文件

        Returns:
            {
                "success": True/False,
                "table_name": "表名",
                "generated_files": ["生成的文件路径列表"],
                "skipped_files": ["跳过的文件路径列表"],
                "errors": ["错误列表"]
            }
        """
        if components is None:
            components = ['entity', 'mapper', 'service', 'service_impl', 'controller']

        if overwrite_rules is None:
            # 默认规则：base_entity 强制覆盖，其他类如果存在则不覆盖
            overwrite_rules = {
                'base_entity': True,      # 基类强制覆盖
                'entity': False,          # 继承类不覆盖
                'mapper': False,          # Mapper 不覆盖
                'mapper_xml': False,      # XML 不覆盖
                'service': False,         # Service 不覆盖
                'service_impl': False,    # ServiceImpl 不覆盖
                'controller': False       # Controller 不覆盖
            }

        try:
            # 1. 获取表结构
            schema_result = self.db.get_table_schema(table_name)
            if not schema_result['success']:
                return {
                    "success": False,
                    "error": f"获取表结构失败: {schema_result.get('error')}"
                }

            # 2. 构建上下文
            context = self.prompt_loader.build_context_for_table(
                table_name,
                schema_result,
                self.package_prefix
            )

            generated_files = []
            skipped_files = []
            errors = []

            # 3. 为每个组件生成代码
            for component in components:
                try:
                    # Entity 组件特殊处理：生成两个文件（Base{class_name} 和 {class_name}）
                    if component == 'entity':
                        self._generate_entity_component(
                            context=context,
                            overwrite_rules=overwrite_rules,
                            errors_list=errors,
                            generated_files=generated_files,
                            skipped_files=skipped_files
                        )
                        continue

                    # 0. 先检查文件是否存在，决定是否需要生成（优化：跳过不需要生成的组件）
                    file_path = self._get_file_path(table_name, component, context)
                    overwrite = overwrite_rules.get(component, False)

                    # 检查文件是否已存在
                    exists_result = self.file.file_exists(file_path)
                    if exists_result.get('success', False) and exists_result.get('exists', False) and not overwrite:
                        # 文件已存在且不覆盖，直接跳过（不调用 LLM，不验证）
                        skipped_files.append(file_path)
                        print(f"⊘ 跳过已存在: {file_path}")
                        continue

                    # 文件不存在或需要覆盖，开始生成流程
                    # 1. 加载并填充 Prompt
                    prompt = self.prompt_loader.fill_template(component, context)

                    # 2. 调用 LLM 生成代码
                    response = self.client.chat.completions.create(
                        model=os.getenv("LLM_MODEL", "deepseek-chat"),
                        messages=[{"role": "user", "content": prompt}]
                    )

                    generated_code = response.choices[0].message.content

                    # 3. 提取代码（使用健壮的提取方法）
                    original_code = generated_code  # 保存原始输出用于调试

                    # 根据组件类型确定期望的语言
                    expected_lang = 'xml' if component == 'mapper_xml' else 'java'

                    # 使用健壮的提取方法
                    success, generated_code = self._extract_single_code_block(
                        generated_code,
                        expected_lang=expected_lang
                    )

                    if not success:
                        # 提取失败，记录错误并跳过此组件
                        error_detail = f"{component}: 无法从 LLM 输出中提取有效的代码块"
                        errors.append(error_detail)
                        print(f"⚠️ {error_detail}")
                        self._save_debug_info(component, original_code)
                        continue

                    # 4. 代码验证（仅对新文件启用，BaseEntity 不验证）
                    # BaseEntity 在 entity 组件中单独处理，这里不验证
                    # 只有新生成的非 BaseEntity 文件才验证
                    is_new_file = not (exists_result.get('success', False) and exists_result.get('exists', False))

                    if self.validator and self.enable_validation and is_new_file:
                        validation_result = self.validator.validate_all(
                            code=generated_code,
                            component=component,
                            context=context,
                            enable_llm=self.enable_llm_validation,
                            enable_compile=self.enable_compile_check,
                            enable_prompt=self.enable_prompt_check
                        )

                        # 如果验证失败，记录问题但继续写入（可选择跳过）
                        if not validation_result['success']:
                            validation_issues = []

                            if validation_result.get('llm_check') and not validation_result['llm_check']['passed']:
                                issues = validation_result['llm_check'].get('issues', [])
                                validation_issues.extend([f"[LLM] {i}" for i in issues])

                            if validation_result.get('compile_check') and not validation_result['compile_check']['passed']:
                                errs = validation_result['compile_check'].get('errors', [])[:3]
                                validation_issues.extend([f"[编译] {e}" for e in errs])

                            if validation_result.get('prompt_check') and not validation_result['prompt_check']['passed']:
                                missing = validation_result['prompt_check'].get('missing_items', [])
                                validation_issues.extend([f"[符合度] {m}" for m in missing])

                            # 记录验证问题
                            if validation_issues:
                                error_detail = f"{component}: 验证未通过 - " + "; ".join(validation_issues[:3])
                                errors.append(error_detail)
                                print(f"⚠️ {error_detail}")

                                # 保存验证失败的代码供调试
                                self._save_debug_info(f"{component}_validation_failed", generated_code)

                                # 可选：跳过写入验证失败的代码
                                # continue

                    # 5. 写入文件
                    # 使用统一的文件写入方法
                    write_result = self._write_component_file(
                        file_path=file_path,
                        code=generated_code,
                        overwrite=overwrite,
                        component_name=component,
                        errors_list=errors
                    )

                    # 根据结果更新文件列表
                    if write_result['success']:
                        if write_result['action'] == 'generated':
                            generated_files.append(file_path)
                        elif write_result['action'] == 'skipped':
                            skipped_files.append(file_path)

                except Exception as e:
                    import traceback
                    error_detail = f"{component}: {type(e).__name__}: {str(e)}\n堆栈: {traceback.format_exc()[-500:]}"
                    errors.append(error_detail)
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
            return {
                "success": False,
                "error": str(e),
                "message": f"代码生成失败: {str(e)}"
            }

    def _extract_single_code_block(self, text: str, expected_lang: str = None) -> tuple:
        """
        从文本中提取单个代码块（健壮版本）

        Args:
            text: 包含代码块标记的文本
            expected_lang: 期望的语言类型（java/xml），None 表示自动检测

        Returns:
            (success: bool, code: str) - 成功标志和提取的代码
        """
        import re

        # 使用正则表达式匹配代码块，处理各种格式变体
        # 支持的格式：
        # ```java ... ```
        # ```java\n ... \n```
        # ``` ... ```
        # ```xml ... ```
        patterns = [
            r'```(?:java|xml)?\s*\n(.*?)\n```',  # 标准格式，可能有换行
            r'```(?:java|xml)?\s*\n(.*?)```',    # 结束标记无换行
            r'```(?:java|xml)? ([^`]+)```',      # 单行格式
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                code = match.group(1).strip()
                # 过滤掉明显无效的内容（如太短）
                if len(code) > 50:
                    return True, code

        # 如果正则表达式失败，尝试简单的字符串查找（作为后备方案）
        for marker in ['```java', '```xml', '```']:
            if marker in text:
                start = text.find(marker) + len(marker)
                # 查找结束标记
                end = text.find('```', start)
                if end != -1:
                    code = text[start:end].strip()
                    if len(code) > 50:
                        return True, code
                else:
                    # 没有结束标记，取到末尾
                    code = text[start:].strip()
                    if len(code) > 50:
                        return True, code

        return False, ''

    def _extract_multiple_code_blocks(self, text: str) -> list:
        """
        从包含多个代码块的文本中提取所有 Java 代码块
        健壮版本：处理各种格式的代码块标记

        Args:
            text: 包含多个 ```java 代码块的文本

        Returns:
            代码块列表，每个元素是纯 Java 代码（不含 ```java 标记）
        """
        code_blocks = []
        lines = text.split('\n')
        current_block = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            # 检查是否是代码块标记（开始或结束）
            if stripped.startswith('```'):
                if not in_code_block:
                    # 开始新的代码块
                    if 'java' in stripped.lower():
                        in_code_block = True
                        current_block = []
                        continue
                else:
                    # 结束当前代码块（接受任何 ``` 变体）
                    # 只有在有内容时才保存
                    if current_block:
                        code_content = '\n'.join(current_block).strip()
                        # 跳过空代码块或过短的无效代码块
                        if len(code_content) > 50:  # 至少要有一定长度
                            code_blocks.append(code_content)
                    in_code_block = False
                    current_block = []
                    continue

            # 收集代码块内容
            if in_code_block:
                current_block.append(line)

        # 处理最后一个代码块（如果没有结束标记）
        if in_code_block and current_block:
            code_content = '\n'.join(current_block).strip()
            if len(code_content) > 50:
                code_blocks.append(code_content)

        return code_blocks

    def _get_file_path(self, table_name: str, component: str, context: dict) -> str:
        """
        获取生成文件的完整路径

        Args:
            table_name: 表名
            component: 组件类型
            context: 上下文信息

        Returns:
            文件路径（相对于 output_dir）
        """
        package_path = context['package_path']
        class_name = context['class_name']

        if component == 'base_entity':
            filename = f"Base{class_name}.java"
            subdir = f"src/main/java/{package_path.replace('.', '/')}/model"

        elif component == 'entity':
            filename = f"{class_name}.java"
            subdir = f"src/main/java/{package_path.replace('.', '/')}/model"

        elif component == 'mapper':
            filename = f"{class_name}Mapper.java"
            subdir = f"src/main/java/{package_path.replace('.', '/')}/mapper"

        elif component == 'service':
            filename = f"{class_name}Service.java"
            subdir = f"src/main/java/{package_path.replace('.', '/')}/service"

        elif component == 'service_impl':
            filename = f"{class_name}ServiceImpl.java"
            subdir = f"src/main/java/{package_path.replace('.', '/')}/service/impl"

        elif component == 'controller':
            filename = f"{class_name}Controller.java"
            subdir = f"src/main/java/{package_path.replace('.', '/')}/controller"

        elif component == 'mapper_xml':
            filename = f"{class_name}Mapper.xml"
            # Mapper XML 放在 resources 目录，与 Java 文件保持一致的项目结构
            module = context.get('module_name', '')
            subdir = f"src/main/resources/mapper/{module}"

        else:
            raise ValueError(f"未知的组件类型: {component}")

        return f"{subdir}/{filename}"


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
