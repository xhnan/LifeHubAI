"""
代码验证模块 - 验证生成的 Java 代码质量
"""
import os
import re
import logging
import subprocess
from typing import Dict, List, Any
from openai import OpenAI

logger = logging.getLogger(__name__)


class CodeValidator:
    """代码验证器 - 检查生成的代码质量"""

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        初始化验证器

        Args:
            api_key: OpenAI API Key
            base_url: API Base URL
        """
        # 优先使用 DEEPSEEK_API_KEY，如果没有则使用 API_KEY
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
        base_url = base_url or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")

        if api_key:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = None
            logger.warning("未配置 API Key，LLM 验证功能将不可用")

    def validate_all(
        self,
        code: str,
        component: str,
        context: dict,
        enable_llm: bool = True,
        enable_compile: bool = True,
        enable_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        执行所有验证

        Args:
            code: 生成的代码
            component: 组件类型
            context: 上下文信息
            enable_llm: 启用 LLM 验证
            enable_compile: 启用编译检查
            enable_prompt: 启用 Prompt 符合度检查

        Returns:
            {
                'success': True/False,
                'llm_check': {'passed': bool, 'issues': []},
                'compile_check': {'passed': bool, 'errors': []},
                'prompt_check': {'passed': bool, 'missing_items': []}
            }
        """
        results = {
            'success': True,
            'llm_check': None,
            'compile_check': None,
            'prompt_check': None
        }

        # 1. LLM 自我验证
        if enable_llm and self.client:
            logger.debug("执行 LLM 验证...")
            results['llm_check'] = self._llm_validate(code, component, context)

        # 2. 语法编译检查
        if enable_compile and component in ['entity', 'base_entity', 'mapper', 'service', 'service_impl', 'controller']:
            logger.debug("执行语法检查...")
            results['compile_check'] = self._compile_check(code, component)

        # 3. Prompt 符合度检查
        if enable_prompt:
            logger.debug("执行 Prompt 符合度检查...")
            results['prompt_check'] = self._prompt_compliance_check(code, component, context)

        # 判断总体是否通过
        for check_name in ['llm_check', 'compile_check', 'prompt_check']:
            check = results[check_name]
            if check and not check.get('passed', True):
                results['success'] = False

        return results

    def _llm_validate(self, code: str, component: str, context: dict) -> Dict[str, Any]:
        """
        LLM 自我验证 - 让 LLM 检查代码质量

        Args:
            code: 生成的代码
            component: 组件类型
            context: 上下文信息

        Returns:
            {'passed': bool, 'issues': [], 'suggestions': []}
        """
        try:
            table_name = context.get('table_name', '')
            class_name = context.get('class_name', '')
            fields = context.get('fields', [])

            prompt = f"""请检查以下生成的 {component} 代码是否正确、完整和符合最佳实践：

表名: {table_name}
类名: {class_name}
字段列表: {', '.join([f['name'] for f in fields])}

生成的代码：
```java
{code}
```

请检查以下方面：
1. 语法正确性
2. 代码完整性（是否包含所有必需的字段、方法）
3. 最佳实践（命名、注释、代码结构）
4. 框架规范（Spring Boot、MyBatis Plus 等注解是否正确）

请以 JSON 格式返回检查结果：
{{
    "passed": true/false,
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}

只返回 JSON，不要有其他内容。"""

            response = self.client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "deepseek-chat"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # 降低温度以获得更一致的结果
            )

            result_text = response.choices[0].message.content.strip()

            # 提取 JSON
            import json
            # 尝试直接解析
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # 如果失败，尝试提取 JSON 代码块
                if '```json' in result_text:
                    start = result_text.find('```json') + 7
                    end = result_text.find('```', start)
                    result = json.loads(result_text[start:end].strip())
                elif '```' in result_text:
                    start = result_text.find('```') + 3
                    end = result_text.find('```', start)
                    result = json.loads(result_text[start:end].strip())
                else:
                    raise

            passed = result.get('passed', True)
            issues = result.get('issues', [])
            suggestions = result.get('suggestions', [])

            if passed:
                logger.debug("LLM 验证通过")
            else:
                logger.warning("LLM 验证发现问题:")
                for issue in issues:
                    logger.warning(f"  - {issue}")

            if suggestions:
                logger.info("LLM 建议:")
                for suggestion in suggestions:
                    logger.info(f"  - {suggestion}")

            return {
                'passed': passed,
                'issues': issues,
                'suggestions': suggestions
            }

        except Exception as e:
            logger.warning(f"LLM 验证失败: {str(e)}")
            return {'passed': False, 'issues': [f"验证异常: {str(e)}"], 'suggestions': []}

    def _compile_check(self, code: str, component: str) -> Dict[str, Any]:
        """
        语法编译检查 - 尝试编译 Java 代码

        Args:
            code: 生成的代码
            component: 组件类型

        Returns:
            {'passed': bool, 'errors': []}
        """
        # 检查 Java 是否可用
        try:
            result = subprocess.run(
                ['javac', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            java_available = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            java_available = False

        if not java_available:
            logger.warning("未检测到 Java 环境，跳过编译检查")
            return {'passed': True, 'errors': [], 'skipped': True}

        # 创建临时文件进行编译
        import tempfile
        temp_dir = tempfile.mkdtemp()

        try:
            # 根据组件确定文件名
            class_name_match = re.search(r'public\s+(class|interface|enum)\s+(\w+)', code)
            if not class_name_match:
                return {'passed': False, 'errors': ['无法找到类/接口定义']}

            class_name = class_name_match.group(2)
            java_file = os.path.join(temp_dir, f"{class_name}.java")

            # 写入代码
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # 尝试编译
            result = subprocess.run(
                ['javac', '-encoding', 'UTF-8', java_file],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=temp_dir
            )

            if result.returncode == 0:
                logger.debug("编译检查通过")
                return {'passed': True, 'errors': []}
            else:
                errors = result.stderr.strip().split('\n')
                logger.warning("编译检查失败:")
                for error in errors[:5]:
                    logger.warning(f"  - {error}")
                return {'passed': False, 'errors': errors}

        except subprocess.TimeoutExpired:
            return {'passed': False, 'errors': ['编译超时']}
        except Exception as e:
            return {'passed': False, 'errors': [f'编译检查异常: {str(e)}']}
        finally:
            # 清理临时文件
            import shutil
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    def _prompt_compliance_check(self, code: str, component: str, context: dict) -> Dict[str, Any]:
        """
        Prompt 符合度检查 - 验证代码是否包含必需元素

        Args:
            code: 生成的代码
            component: 组件类型
            context: 上下文信息

        Returns:
            {'passed': bool, 'missing_items': []}
        """
        missing_items = []
        fields = context.get('fields', [])
        table_name = context.get('table_name', '')
        class_name = context.get('class_name', '')

        # 基础检查：代码不能为空
        if not code or len(code.strip()) < 50:
            missing_items.append('代码内容过短或为空')
            return {'passed': False, 'missing_items': missing_items}

        # 根据组件类型进行特定检查
        if component in ['entity', 'base_entity']:
            # Entity 类检查

            # 1. 检查类定义
            if f'class {class_name}' not in code and f'interface {class_name}' not in code:
                missing_items.append(f'缺少类定义: {class_name}')

            # 2. 检查字段是否包含
            for field in fields:
                field_name = field['name']
                # 转换为驼峰命名
                camel_name = self._to_camel_case(field_name)
                if camel_name not in code:
                    missing_items.append(f'缺少字段: {camel_name}')

            # 3. 检查必需注解
            if component == 'entity':
                if '@Data' not in code and '@Getter' not in code and '@Setter' not in code:
                    missing_items.append('缺少 Lombok 注解 (@Data/@Getter/@Setter)')
                if '@TableName' not in code and 'TableName' not in code:
                    missing_items.append('缺少 @TableName 注解')

            # 4. 检查主键字段
            pk_field = context.get('pk_field')
            if pk_field:
                pk_camel = self._to_camel_case(pk_field)
                if '@TableId' not in code and 'TableId' not in code:
                    missing_items.append(f'缺少主键注解 @TableId (字段: {pk_camel})')

        elif component == 'mapper':
            # Mapper 检查
            if f'interface {class_name}Mapper' not in code:
                missing_items.append(f'缺少 Mapper 接口定义')
            if 'extends BaseMapper' not in code:
                missing_items.append('缺少继承 BaseMapper<T>')
            if '@Mapper' not in code and 'Mapper' not in code:
                missing_items.append('缺少 @Mapper 注解')

        elif component == 'service':
            # Service 接口检查
            if f'interface {class_name}Service' not in code:
                missing_items.append(f'缺少 Service 接口定义')

        elif component == 'service_impl':
            # ServiceImpl 检查
            if f'class {class_name}ServiceImpl' not in code:
                missing_items.append(f'缺少 ServiceImpl 类定义')
            if f'implements {class_name}Service' not in code:
                missing_items.append(f'缺少实现 {class_name}Service')
            if '@Service' not in code:
                missing_items.append('缺少 @Service 注解')
            if 'extends ServiceImpl' not in code:
                missing_items.append('缺少继承 ServiceImpl<T>')

        elif component == 'controller':
            # Controller 检查
            if f'class {class_name}Controller' not in code:
                missing_items.append(f'缺少 Controller 类定义')
            if '@RestController' not in code and '@Controller' not in code:
                missing_items.append('缺少 @RestController 或 @Controller 注解')
            if '@RequestMapping' not in code and '@RestController' not in code:
                missing_items.append('缺少 @RequestMapping 注解')
            # 检查基本 CRUD 方法
            if 'public' not in code:
                missing_items.append('缺少 public 方法')

        elif component == 'mapper_xml':
            # Mapper XML 检查
            if '<?xml version="1.0"' not in code and '<?xml' not in code:
                missing_items.append('缺少 XML 声明')
            if '<mapper' not in code:
                missing_items.append('缺少 <mapper> 根元素')
            if 'namespace' not in code:
                missing_items.append('缺少 namespace 属性')

        # 判断是否通过
        passed = len(missing_items) == 0

        if passed:
            logger.debug("Prompt 符合度检查通过")
        else:
            logger.warning("Prompt 符合度检查发现问题:")
            for item in missing_items:
                logger.warning(f"  - {item}")

        return {
            'passed': passed,
            'missing_items': missing_items
        }

    def _to_camel_case(self, snake_str: str) -> str:
        """将下划线命名转换为驼峰命名"""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])


# 便捷函数
def get_validator() -> CodeValidator:
    """获取代码验证器实例"""
    return CodeValidator()
