"""
代码生成 gRPC 服务
"""
import grpc
from typing import List
from generated import codegen_pb2
from generated.codegen_pb2_grpc import CodeGenerationServicer
from Agent.code_agent import CodeGenAgent


class CodeGenerationService(CodeGenerationServicer):
    """代码生成服务"""

    def __init__(self):
        """初始化服务，创建 Agent 实例"""
        self.agent = None
        self._init_agent()

    def _init_agent(self):
        """初始化 Agent（延迟加载）"""
        try:
            self.agent = CodeGenAgent()
            print("✓ CodeGenAgent 初始化成功")
        except Exception as e:
            print(f"✗ CodeGenAgent 初始化失败: {e}")
            self.agent = None

    def GenerateCode(self, request, context):
        """
        通过自然语言描述生成代码

        Args:
            request: GenerateRequest { prompt: "用户描述" }
            context: gRPC 上下文

        Returns:
            GenerateResponse
        """
        print("收到代码生成请求：", request.prompt)
        try:
            prompt = request.prompt

            if not prompt:
                print("请求参数 prompt 为空")
                return codegen_pb2.GenerateResponse(
                    success=False,
                    message="请求参数不能为空",
                    error="prompt 参数为空"
                )

            # 检查 Agent 是否可用
            if self.agent is None:
                self._init_agent()
                if self.agent is None:
                    print("Agent 初始化失败，无法处理请求")
                    return codegen_pb2.GenerateResponse(
                        success=False,
                        message="Agent 初始化失败",
                        error="CodeGenAgent 不可用"
                    )

            # 调用 Agent 处理请求
            result = self.agent.run(
                user_message=prompt,
                max_iterations=20,
                verbose=True  # gRPC 环境不打印详细日志
            )

            # 解析结果
            if result.get('success'):
                # 成功：提取工具调用信息，构建文件列表
                files = self._extract_files_from_result(result)

                return codegen_pb2.GenerateResponse(
                    success=True,
                    message="代码生成成功",
                    description=result.get('final_response', ''),
                    files=files,
                    steps=[str(tc) for tc in result.get('tool_calls', [])]
                )
            else:
                # 失败
                return codegen_pb2.GenerateResponse(
                    success=False,
                    message="代码生成失败",
                    error=result.get('error', '未知错误'),
                    steps=[str(tc) for tc in result.get('tool_calls', [])]
                )

        except Exception as e:
            return codegen_pb2.GenerateResponse(
                success=False,
                message="服务异常",
                error=str(e)
            )

    def _extract_files_from_result(self, result: dict) -> List[codegen_pb2.FileInfo]:
        """
        从 Agent 结果中提取文件信息

        Args:
            result: Agent.run() 返回的结果

        Returns:
            FileInfo 列表
        """
        files = []

        # 遍历工具调用历史，查找文件写入操作
        for tool_call in result.get('tool_calls', []):
            tool_name = tool_call.get('name', '')
            tool_result = tool_call.get('result', '')

            # 如果是文件写入工具
            if 'write_file' in tool_name or tool_name == 'write_file':
                # 尝试从结果中解析文件路径
                if isinstance(tool_result, dict):
                    path = tool_result.get('path', '')
                    file_type = self._infer_file_type(path)
                    description = f"生成的 {file_type} 文件"

                    files.append(codegen_pb2.FileInfo(
                        path=path,
                        type=file_type,
                        description=description
                    ))

        # 如果工具调用中没有文件信息，尝试从 final_response 中解析
        if not files:
            final_response = result.get('final_response', '')
            # 简单的路径匹配（假设路径包含 .java 或 .xml）
            import re
            pattern = r'([\w/]+\.(?:java|xml))'
            matches = re.findall(pattern, final_response)
            for match in matches:
                file_type = self._infer_file_type(match)
                files.append(codegen_pb2.FileInfo(
                    path=match,
                    type=file_type,
                    description=f"生成的 {file_type} 文件"
                ))

        return files

    def _infer_file_type(self, file_path: str) -> str:
        """
        从文件路径推断文件类型

        Args:
            file_path: 文件路径

        Returns:
            文件类型字符串
        """
        path_lower = file_path.lower()

        if 'base' in path_lower and 'entity' in path_lower:
            return 'base_entity'
        elif 'entity' in path_lower or 'model' in path_lower:
            return 'entity'
        elif 'mapper' in path_lower:
            return 'mapper' if file_path.endswith('.java') else 'mapper_xml'
        elif 'service' in path_lower:
            return 'service_impl' if 'impl' in path_lower else 'service'
        elif 'controller' in path_lower:
            return 'controller'
        else:
            return 'unknown'
