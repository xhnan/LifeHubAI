"""
文件操作工具 - 为 Agent 提供文件读写能力
支持原子写入，防止文件损坏
"""
import os
import glob
from pathlib import Path
from typing import Dict, Any


class FileTool:
    """文件操作工具类"""

    def __init__(self, base_dir: str = None):
        """
        初始化文件工具

        Args:
            base_dir: 基础工作目录，默认为当前目录
        """
        self.base_dir = base_dir or os.getcwd()

    def write_file(
        self,
        file_path: str,
        content: str,
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """
        写入文件（原子操作，防止文件损坏）

        Args:
            file_path: 文件路径（绝对路径或相对路径）
            content: 文件内容
            overwrite: 是否覆盖已存在的文件

        Returns:
            {
                "success": True/False,
                "path": "文件完整路径",
                "size": "文件大小（字节）",
                "error": "错误信息（如果失败）"
            }
        """
        try:
            # 转换为绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.base_dir, file_path)

            file_path = os.path.abspath(file_path)

            # 检查文件是否已存在
            if os.path.exists(file_path) and not overwrite:
                return {
                    "success": False,
                    "error": f"文件已存在且 overwrite=False: {file_path}",
                    "path": file_path
                }

            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            # 原子写入：先写临时文件，再重命名
            temp_path = f"{file_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 原子替换（跨设备安全）
            os.replace(temp_path, file_path)

            return {
                "success": True,
                "path": file_path,
                "size": len(content),
                "message": f"文件写入成功: {file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path,
                "message": f"文件写入失败: {str(e)}"
            }

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """
        读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            {
                "success": True/False,
                "content": "文件内容",
                "size": "文件大小",
                "encoding": "utf-8",
                "error": "错误信息（如果失败）"
            }
        """
        try:
            # 转换为绝对路径
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.base_dir, file_path)

            file_path = os.path.abspath(file_path)

            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}",
                    "path": file_path
                }

            if not os.path.isfile(file_path):
                return {
                    "success": False,
                    "error": f"不是文件: {file_path}",
                    "path": file_path
                }

            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "success": True,
                "content": content,
                "path": file_path,
                "size": len(content),
                "encoding": "utf-8",
                "message": f"文件读取成功: {file_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": file_path,
                "message": f"文件读取失败: {str(e)}"
            }

    def create_directory(self, dir_path: str) -> Dict[str, Any]:
        """
        创建目录（包括所有父目录）

        Args:
            dir_path: 目录路径

        Returns:
            {
                "success": True/False,
                "path": "目录完整路径",
                "created": "是否是新创建的",
                "error": "错误信息（如果失败）"
            }
        """
        try:
            # 转换为绝对路径
            if not os.path.isabs(dir_path):
                dir_path = os.path.join(self.base_dir, dir_path)

            dir_path = os.path.abspath(dir_path)

            # 检查是否已存在
            exists = os.path.exists(dir_path)
            is_dir = os.path.isdir(dir_path) if exists else False

            if is_dir:
                return {
                    "success": True,
                    "path": dir_path,
                    "created": False,
                    "message": f"目录已存在: {dir_path}"
                }

            if exists and not is_dir:
                return {
                    "success": False,
                    "error": f"路径已存在但不是目录: {dir_path}",
                    "path": dir_path
                }

            # 创建目录
            os.makedirs(dir_path, exist_ok=True)

            return {
                "success": True,
                "path": dir_path,
                "created": True,
                "message": f"目录创建成功: {dir_path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": dir_path,
                "message": f"目录创建失败: {str(e)}"
            }

    def file_exists(self, path: str) -> Dict[str, Any]:
        """
        检查文件或目录是否存在

        Args:
            path: 文件或目录路径

        Returns:
            {
                "success": True,
                "exists": True/False,
                "is_file": True/False,
                "is_directory": True/False,
                "path": "完整路径"
            }
        """
        try:
            # 转换为绝对路径
            if not os.path.isabs(path):
                path = os.path.join(self.base_dir, path)

            path = os.path.abspath(path)

            exists = os.path.exists(path)

            if not exists:
                return {
                    "success": True,
                    "exists": False,
                    "is_file": False,
                    "is_directory": False,
                    "path": path,
                    "message": f"路径不存在: {path}"
                }

            is_file = os.path.isfile(path)
            is_dir = os.path.isdir(path)

            return {
                "success": True,
                "exists": True,
                "is_file": is_file,
                "is_directory": is_dir,
                "path": path,
                "message": f"文件存在: {path}" if is_file else f"目录存在: {path}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": path,
                "message": f"检查失败: {str(e)}"
            }

    def list_directory(self, dir_path: str = ".") -> Dict[str, Any]:
        """
        列出目录内容

        Args:
            dir_path: 目录路径

        Returns:
            {
                "success": True/False,
                "path": "目录路径",
                "items": ["文件/目录列表"],
                "count": "项目数量",
                "files": ["文件列表"],
                "directories": ["目录列表"]
            }
        """
        try:
            # 转换为绝对路径
            if not os.path.isabs(dir_path):
                dir_path = os.path.join(self.base_dir, dir_path)

            dir_path = os.path.abspath(dir_path)

            # 检查目录是否存在
            if not os.path.exists(dir_path):
                return {
                    "success": False,
                    "error": f"目录不存在: {dir_path}",
                    "path": dir_path
                }

            if not os.path.isdir(dir_path):
                return {
                    "success": False,
                    "error": f"不是目录: {dir_path}",
                    "path": dir_path
                }

            # 列出内容
            items = os.listdir(dir_path)

            # 分类
            files = []
            directories = []

            for item in items:
                item_path = os.path.join(dir_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
                elif os.path.isdir(item_path):
                    directories.append(item)

            return {
                "success": True,
                "path": dir_path,
                "items": items,
                "count": len(items),
                "files": sorted(files),
                "directories": sorted(directories),
                "message": f"找到 {len(files)} 个文件, {len(directories)} 个目录"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": dir_path,
                "message": f"列出目录失败: {str(e)}"
            }

    def find_files(self, pattern: str, root_path: str = None) -> Dict[str, Any]:
        """
        查找文件（支持 glob 模式）

        Args:
            pattern: glob 模式，如 "*.java", "**/*.py", "src/**/*.java"
            root_path: 搜索根路径，默认为基础目录

        Returns:
            {
                "success": True/False,
                "pattern": "搜索模式",
                "root_path": "搜索根目录",
                "files": ["匹配的文件列表"],
                "count": "文件数量"
            }
        """
        try:
            root_path = root_path or self.base_dir

            # 转换为绝对路径
            if not os.path.isabs(root_path):
                root_path = os.path.join(self.base_dir, root_path)

            root_path = os.path.abspath(root_path)

            # 使用 glob 查找文件
            search_pattern = os.path.join(root_path, pattern)
            matched_files = glob.glob(search_pattern, recursive=True)

            # 过滤掉目录，只返回文件
            files = [f for f in matched_files if os.path.isfile(f)]

            # 转换为相对路径（可选）
            relative_files = [os.path.relpath(f, root_path) for f in files]

            return {
                "success": True,
                "pattern": pattern,
                "root_path": root_path,
                "files": files,
                "relative_files": relative_files,
                "count": len(files),
                "message": f"找到 {len(files)} 个匹配的文件"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern,
                "message": f"查找文件失败: {str(e)}"
            }


# 便捷函数
def get_file_tool(base_dir: str = None) -> FileTool:
    """创建并返回文件工具实例"""
    return FileTool(base_dir)


# 测试代码
if __name__ == "__main__":
    import tempfile

    print("="*60)
    print("文件工具测试")
    print("="*60)

    # 创建临时目录测试
    with tempfile.TemporaryDirectory() as temp_dir:
        file_tool = FileTool(temp_dir)
        print(f"\n测试目录: {temp_dir}")

        # 测试 1: 创建目录
        print("\n【测试 1】创建目录")
        result = file_tool.create_directory("test/subdir")
        print(f"  {result['message']}")
        print(f"  创建新目录: {result['created']}")

        # 测试 2: 写入文件
        print("\n【测试 2】写入文件")
        result = file_tool.write_file(
            "test/hello.txt",
            "Hello, World!\n这是测试文件。"
        )
        print(f"  {result['message']}")
        print(f"  文件大小: {result['size']} 字节")

        # 测试 3: 读取文件
        print("\n【测试 3】读取文件")
        result = file_tool.read_file("test/hello.txt")
        print(f"  {result['message']}")
        print(f"  内容预览: {result['content'][:50]}...")

        # 测试 4: 检查文件存在
        print("\n【测试 4】检查文件存在")
        result = file_tool.file_exists("test/hello.txt")
        print(f"  {result['message']}")
        print(f"  是文件: {result['is_file']}")

        # 测试 5: 列出目录
        print("\n【测试 5】列出目录")
        result = file_tool.list_directory("test")
        print(f"  {result['message']}")
        print(f"  文件: {result['files']}")
        print(f"  目录: {result['directories']}")

        # 测试 6: 查找文件
        print("\n【测试 6】查找文件")
        result = file_tool.find_files("*.txt", temp_dir)
        print(f"  {result['message']}")
        for f in result['files']:
            print(f"    - {f}")

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
