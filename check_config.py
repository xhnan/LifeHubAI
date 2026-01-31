"""
检查 .env 配置是否正确
"""
import os
from dotenv import load_dotenv

def check_config():
    """检查环境变量配置"""
    print("="*60)
    print("检查 .env 配置")
    print("="*60)

    # 加载环境变量
    load_dotenv(override=True)

    # 检查数据库配置
    print("\n【数据库配置】")
    db_configs = {
        "DB_HOST": os.getenv("DB_HOST"),
        "DB_PORT": os.getenv("DB_PORT"),
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD")
    }

    db_ok = True
    for key, value in db_configs.items():
        if value:
            # 隐藏密码
            display_value = "****" if "PASSWORD" in key else value
            print(f"  ✓ {key}: {display_value}")
        else:
            print(f"  ✗ {key}: 未设置")
            db_ok = False

    if not db_ok:
        print("\n⚠️  数据库配置不完整，请在 .env 文件中设置")

    # 检查 API 配置
    print("\n【API 配置】")

    # 优先使用 DEEPSEEK_API_KEY
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
    base_url = os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    if api_key:
        print(f"  ✓ API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"  ✓ Base URL: {base_url}")
        print(f"  ✓ Model: {model}")
        api_ok = True
    else:
        print(f"  ✗ API Key: 未设置")
        print(f"    提示: 请在 .env 中设置 DEEPSEEK_API_KEY=sk-xxxxx")
        api_ok = False

    # 总结
    print("\n" + "="*60)
    if db_ok and api_ok:
        print("✅ 配置检查通过！可以运行 Agent 了")
        print("\n运行命令:")
        print("  python test_agent.py")
    else:
        print("⚠️  配置不完整，请检查 .env 文件")
        if not db_ok:
            print("\n缺失数据库配置，请在 .env 中添加:")
            print("  DB_HOST=localhost")
            print("  DB_PORT=5432")
            print("  DB_NAME=your_database")
            print("  DB_USER=your_username")
            print("  DB_PASSWORD=your_password")
        if not api_ok:
            print("\n缺失 API 配置，请在 .env 中添加:")
            print("  DEEPSEEK_API_KEY=sk-your-api-key-here")
    print("="*60)

    return db_ok and api_ok


if __name__ == "__main__":
    check_config()
