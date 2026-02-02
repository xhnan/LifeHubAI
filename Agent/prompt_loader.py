"""
Prompt 模板加载器
负责加载和填充代码生成的 Prompt 模板
"""
import os
from typing import Dict, Any
from datetime import datetime


class PromptLoader:
    """Prompt 模板加载器"""

    def __init__(self, prompt_dir: str = None):
        """
        初始化 Prompt 加载器

        Args:
            prompt_dir: Prompt 模板目录，默认为项目根目录下的 prompts/
        """
        if prompt_dir is None:
            # 获取项目根目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            prompt_dir = os.path.join(project_root, "prompts")

        self.prompt_dir = prompt_dir
        self.base_prompt = self._load_base_prompt()

    def _load_base_prompt(self) -> str:
        """加载基础 Prompt（包含通用指令）"""
        base_path = os.path.join(self.prompt_dir, "base.txt")
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def load_template(self, template_name: str) -> str:
        """
        加载指定的 Prompt 模板

        Args:
            template_name: 模板名称（如 'entity', 'mapper', 'service'）
                         会自动添加 .txt 后缀，并从 java/ 子目录查找

        Returns:
            模板内容字符串
        """
        template_path = os.path.join(self.prompt_dir, "java", f"{template_name}.txt")

        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Prompt 模板不存在: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def fill_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        填充 Prompt 模板

        Args:
            template_name: 模板名称
            context: 上下文数据，包含：
                - table_name: 表名
                - class_name: Java 类名
                - package_path: 完整包路径
                - module_name: 模块名
                - table_comment: 表注释
                - columns_info: 字段信息（格式化后的字符串）
                - primary_keys: 主键信息
                - date: 当前日期

        Returns:
            填充后的完整 Prompt（包含基础 Prompt + 模板内容）
        """
        # 加载模板
        template = self.load_template(template_name)

        # 添加默认上下文
        default_context = {
            "date": datetime.now().strftime("%Y-%m-%d"),
        }
        context = {**default_context, **context}

        # 填充模板变量
        filled_template = template.format(**context)

        # 组合基础 Prompt 和具体模板
        return f"{self.base_prompt}\n\n{'='*60}\n\n{filled_template}"

    def format_columns_info(self, columns: list) -> str:
        """
        格式化字段信息为可读的字符串

        Args:
            columns: 字段列表，每个字段是字典格式

        Returns:
            格式化后的字符串
        """
        if not columns:
            return "（无字段信息）"

        lines = []
        for col in columns:
            nullable = "NULL" if col.get("nullable") else "NOT NULL"
            pk_mark = " [主键]" if col.get("is_primary_key") else ""

            line = (
                f"- {col['name']}: {col['type']} {nullable}{pk_mark}"
            )

            if col.get("comment"):
                line += f" -- {col['comment']}"

            lines.append(line)

        return "\n".join(lines)

    def format_primary_keys(self, primary_keys: list) -> str:
        """
        格式化主键信息

        Args:
            primary_keys: 主键字段名列表

        Returns:
            格式化后的字符串
        """
        if not primary_keys:
            return "（无主键）"

        return ", ".join(primary_keys)

    def build_context_for_table(
        self,
        table_name: str,
        table_schema: dict,
        package_prefix: str = "com.xhn"
    ) -> Dict[str, Any]:
        """
        为表构建完整的上下文数据

        Args:
            table_name: 表名
            table_schema: 表结构信息（来自数据库工具的 get_table_schema）
            package_prefix: 包名前缀

        Returns:
            上下文字典
        """
        # 提取模块名
        parts = table_name.split("_")
        module_name = parts[0] if len(parts) > 1 else ""

        # 生成类名
        class_name = "".join(word.capitalize() for word in table_name.split("_"))

        # 生成包路径
        suffix = table_name.replace(f"{module_name}_", "") if module_name else table_name
        package_path = f"{package_prefix}.{module_name}.{suffix}"

        # 生成表路径（用于 URL 路径，去掉所有下划线）
        # 例如: sys_user → user, sys_user_role → userrole, sys_user_app → userapp
        table_path = suffix.replace("_", "")

        # 生成类名的小驼峰形式（用于变量名）
        # 例如: SysUser → sysUser, SysUserRole → sysUserRole
        class_name_lower = class_name[0].lower() + class_name[1:] if class_name else ""

        return {
            "table_name": table_name,
            "class_name": class_name,
            "class_name_lower": class_name_lower,  # 小驼峰形式，用于变量名
            "package_path": package_path,
            "module_name": module_name,
            "table_path": table_path,  # 用于 URL 路径
            "table_comment": table_schema.get("comment", ""),
            "columns_info": self.format_columns_info(table_schema.get("columns", [])),
            "primary_keys": self.format_primary_keys(table_schema.get("primary_keys", [])),
            "columns": table_schema.get("columns", []),  # 原始字段数据
            "id": "id",  # 用于路径占位符，如 @GetMapping("/{id}")
        }


# 便捷函数
def get_prompt_loader() -> PromptLoader:
    """创建并返回 Prompt 加载器实例"""
    return PromptLoader()


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("Prompt 加载器测试")
    print("=" * 60)

    # 创建加载器
    loader = get_prompt_loader()

    # 测试 1: 加载基础 Prompt
    print("\n【测试 1】加载基础 Prompt")
    print(f"基础 Prompt 长度: {len(loader.base_prompt)} 字符")
    print(f"前 100 字符: {loader.base_prompt[:100]}...")

    # 测试 2: 加载 Entity 模板
    print("\n【测试 2】加载 Entity 模板")
    template = loader.load_template("entity")
    print(f"模板长度: {len(template)} 字符")

    # 测试 3: 填充模板
    print("\n【测试 3】填充模板")
    mock_schema = {
        "comment": "用户表",
        "columns": [
            {"name": "id", "type": "bigint", "nullable": False, "is_primary_key": True, "comment": "主键ID"},
            {"name": "user_name", "type": "varchar", "nullable": False, "comment": "用户名"},
            {"name": "email", "type": "varchar", "nullable": True, "comment": "邮箱"},
        ],
        "primary_keys": ["id"]
    }

    context = loader.build_context_for_table("sys_user", mock_schema, "com.xhn")
    filled_prompt = loader.fill_template("entity", context)

    print(f"完整 Prompt 长度: {len(filled_prompt)} 字符")
    print(f"前 200 字符: {filled_prompt[:200]}...")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
