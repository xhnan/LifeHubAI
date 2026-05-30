"""
配置测试脚本
验证配置是否正确加载
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import get_config


def test_config():
    """测试配置加载"""
    print("="*60)
    print("🧪 配置测试")
    print("="*60)

    config = get_config()

    # 测试基本信息
    print(f"\n✓ 环境: {config.environment}")
    print(f"✓ Nacos 启用: {config.nacos_enabled}")

    # 测试配置获取
    tests = [
        ("数据库主机", config.get("DB_HOST")),
        ("数据库端口", config.get_int("DB_PORT")),
        ("LLM 模型", config.get("LLM_MODEL")),
    ]

    print(f"\n配置测试:")
    all_passed = True
    for name, value in tests:
        status = "✓" if value is not None else "✗"
        print(f"  {status} {name}: {value}")
        if value is None:
            all_passed = False

    # 测试结构化配置
    print(f"\n结构化配置:")

    db_config = config.get_database_config()
    print(f"  ✓ 数据库: {db_config['host']}:{db_config['port']}/{db_config['database']}")

    ai_config = config.get_ai_config()
    api_key = ai_config['api_key']
    if api_key:
        masked_key = f"{api_key[:10]}...{api_key[-4:]}"
        print(f"  ✓ AI: {ai_config['model']} (key: {masked_key})")
    else:
        print(f"  ✗ AI: 未配置 API Key")
        all_passed = False

    # 测试结果
    print("\n" + "="*60)
    if all_passed:
        print("✅ 所有配置测试通过")
        return 0
    else:
        print("⚠️ 部分配置缺失，请检查配置文件")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试 LifeHubAI 配置")
    parser.add_argument("--env", choices=["development", "production"],
                       help="指定测试环境（默认使用当前环境）")

    args = parser.parse_args()

    if args.env:
        import os
        os.environ["ENVIRONMENT"] = args.env
        from config import reload_config
        reload_config()

    sys.exit(test_config())
