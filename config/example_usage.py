"""
配置管理使用示例
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import get_config, get_setting


def example_basic_usage():
    """基本使用示例"""
    print("="*60)
    print("配置管理基本使用")
    print("="*60)

    config = get_config()

    # 获取单个配置值
    print(f"\n当前环境: {config.environment}")
    print(f"是否生产环境: {config.is_production()}")
    print(f"Nacos 启用: {config.nacos_enabled}")

    # 获取不同类型的配置值
    print(f"\n数据库端口: {config.get_int('DB_PORT', 5432)}")
    print(f"gRPC 启用: {config.get_bool('GRPC_ENABLED', False)}")

    # 使用快捷函数
    print(f"\nLLM 模型: {get_setting('LLM_MODEL', 'unknown')}")


def example_database_config():
    """数据库配置示例"""
    print("\n" + "="*60)
    print("数据库配置")
    print("="*60)

    config = get_config()
    db_config = config.get_database_config()

    print(f"主机: {db_config['host']}")
    print(f"端口: {db_config['port']}")
    print(f"数据库: {db_config['database']}")
    print(f"用户: {db_config['user']}")
    print(f"密码: {'*' * len(db_config['password'])}")


def example_ai_config():
    """AI 配置示例"""
    print("\n" + "="*60)
    print("AI 配置")
    print("="*60)

    config = get_config()
    ai_config = config.get_ai_config()

    print(f"API Key: {ai_config['api_key'][:10]}...{ai_config['api_key'][-4:]}")
    print(f"Base URL: {ai_config['base_url']}")
    print(f"模型: {ai_config['model']}")


def example_code_generation():
    """代码生成配置示例"""
    print("\n" + "="*60)
    print("代码生成配置")
    print("="*60)

    config = get_config()
    codegen_config = config.get_codegen_config()

    print(f"输出目录: {codegen_config['output_dir']}")
    print(f"包名前缀: {codegen_config['package_prefix']}")


def example_environment_switching():
    """环境切换示例"""
    print("\n" + "="*60)
    print("环境切换示例")
    print("="*60)

    from config import reload_config

    # 加载开发环境配置
    print("\n加载开发环境配置:")
    reload_config(".env.development")
    config = get_config()
    print(f"环境: {config.environment}")
    print(f"数据库: {config.get('DB_HOST')}")

    # 加载生产环境配置
    print("\n加载生产环境配置:")
    reload_config(".env.production")
    config = get_config()
    print(f"环境: {config.environment}")
    print(f"Nacos 启用: {config.nacos_enabled}")
    print(f"数据库: {config.get('DB_HOST')}")

    # 重新加载默认配置
    print("\n恢复默认配置:")
    reload_config()
    config = get_config()
    print(f"环境: {config.environment}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("LifeHubAI 配置管理示例")
    print("="*60)

    example_basic_usage()
    example_database_config()
    example_ai_config()
    example_code_generation()
    # example_environment_switching()  # 取消注释以测试环境切换

    print("\n" + "="*60)
    print("示例运行完成")
    print("="*60)
