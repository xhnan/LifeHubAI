"""
环境配置启动脚本
支持通过命令行参数指定环境
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_config


def start_development():
    """启动开发环境"""
    print("="*60)
    print("🚀 启动开发环境")
    print("="*60)

    # 设置开发环境
    os.environ["ENVIRONMENT"] = "development"
    os.environ["NACOS_ENABLED"] = "false"

    # 重新加载配置
    from config import reload_config
    reload_config()

    config = get_config()
    print(f"✓ 环境: {config.environment}")
    print(f"✓ Nacos: {'启用' if config.nacos_enabled else '未启用'}")
    print(f"✓ 数据库: {config.get('DB_HOST')}:{config.get('DB_PORT')}")

    # 启动 FastAPI
    import uvicorn
    from main import app

    print("\n启动 FastAPI 服务器...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


def start_production():
    """启动生产环境"""
    print("="*60)
    print("🚀 启动生产环境")
    print("="*60)

    # 设置生产环境
    os.environ["ENVIRONMENT"] = "production"
    os.environ["NACOS_ENABLED"] = "true"

    # 重新加载配置
    from config import reload_config
    reload_config()

    config = get_config()
    print(f"✓ 环境: {config.environment}")
    print(f"✓ Nacos: {'启用' if config.nacos_enabled else '未启用'}")

    if config.nacos_enabled:
        print(f"✓ Nacos 服务器: {config.get('NACOS_SERVER_ADDRESSES')}")
        print(f"✓ Nacos 命名空间: {config.get('NACOS_NAMESPACE')}")
        print(f"✓ Nacos Data ID: {config.get('NACOS_CONFIG_DATA_ID')}")

    # 启动 FastAPI
    import uvicorn
    from main import app

    print("\n启动 FastAPI 服务器...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # 生产环境不使用热重载
        log_level="info"
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="LifeHubAI 环境配置启动")
    parser.add_argument(
        "--env",
        choices=["development", "production", "dev", "prod"],
        default="development",
        help="运行环境"
    )

    args = parser.parse_args()

    # 标准化环境名称
    env = args.env
    if env in ["dev"]:
        env = "development"
    elif env in ["prod"]:
        env = "production"

    # 启动对应环境
    if env == "production":
        start_production()
    else:
        start_development()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 服务已停止")
        sys.exit(0)
