"""
LifeHubAI API 测试脚本
"""
import requests
import time
from typing import Optional


class LifeHubAPIClient:
    """LifeHubAI API 客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def test_root(self):
        """测试根路径"""
        print("\n=== 测试根路径 ===")
        response = requests.get(f"{self.base_url}/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

    def test_health(self):
        """测试健康检查"""
        print("\n=== 测试健康检查 ===")
        response = requests.get(f"{self.base_url}/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

    def test_codegen_health(self):
        """测试代码生成服务健康检查"""
        print("\n=== 测试代码生成服务健康检查 ===")
        response = requests.get(f"{self.base_url}/api/codegen/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

    def test_codegen_database(self):
        """测试获取数据库信息"""
        print("\n=== 测试获取数据库信息 ===")
        response = requests.get(f"{self.base_url}/api/codegen/database")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

    def test_list_tables(self, prefix: str = ""):
        """测试列出表"""
        print(f"\n=== 测试列出表 (prefix: {prefix or '无'}) ===")
        response = requests.get(f"{self.base_url}/api/codegen/tables", params={"prefix": prefix})
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"表数量: {result.get('count')}")
        print(f"表列表: {result.get('tables')}")

    def test_generate_code(self, tables: Optional[list] = None):
        """测试代码生成"""
        print(f"\n=== 测试代码生成 ===")
        start_time = time.time()

        if tables:
            # 生成指定表
            response = requests.post(
                f"{self.base_url}/api/codegen/generate",
                json={"tables": tables}
            )
        else:
            # 生成所有表
            response = requests.get(f"{self.base_url}/api/codegen/generate")

        elapsed = time.time() - start_time
        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"成功: {result.get('success')}")
        print(f"消息: {result.get('message')}")
        print(f"生成表数: {result.get('total_tables')}")
        print(f"生成的表: {result.get('generated_tables')}")
        print(f"执行时间: {elapsed:.2f}秒")

    def test_tts_health(self):
        """测试 TTS 服务健康检查"""
        print("\n=== 测试 TTS 服务健康检查 ===")
        response = requests.get(f"{self.base_url}/api/tts/health")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")

    def test_tts_generate(self, text: str = "你好，这是测试语音"):
        """测试 TTS 生成"""
        print(f"\n=== 测试 TTS 生成 ===")
        print(f"文本: {text}")

        response = requests.post(
            f"{self.base_url}/api/tts/speak",
            json={
                "text": text,
                "voice": "female",
                "speed": 1.0,
                "volume": 1.0
            }
        )

        print(f"状态码: {response.status_code}")
        result = response.json()
        print(f"响应: {result}")

    def test_tts_download(self, text: str = "你好，这是一段测试音频", save_path: str = "test_audio.pcm"):
        """测试 TTS 下载"""
        print(f"\n=== 测试 TTS 下载 ===")
        print(f"文本: {text}")

        response = requests.post(
            f"{self.base_url}/api/tts/generate",
            json={
                "text": text,
                "voice": "female",
                "speed": 1.0,
                "volume": 1.0
            }
        )

        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(response.content)
            print(f"音频已保存到: {save_path}")
            print(f"文件大小: {len(response.content)} 字节")
        else:
            print(f"错误: {response.text}")

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("LifeHubAI API 测试套件")
        print("=" * 60)

        try:
            # 基础测试
            self.test_root()
            self.test_health()

            # 代码生成测试
            self.test_codegen_health()
            self.test_codegen_database()
            self.test_list_tables(prefix="sys")
            # 注意：代码生成可能需要很长时间，请根据需要取消注释
            # self.test_generate_code()

            # TTS 测试
            self.test_tts_health()
            self.test_tts_generate()
            self.test_tts_download()

            print("\n" + "=" * 60)
            print("测试完成！")
            print("=" * 60)

        except requests.exceptions.ConnectionError:
            print("\n❌ 错误: 无法连接到 API 服务器")
            print("请确认服务器正在运行: uvicorn main:app")
        except Exception as e:
            print(f"\n❌ 测试失败: {str(e)}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="LifeHubAI API 测试工具")
    parser.add_argument("--url", default="http://localhost:8000", help="API 基础 URL")
    parser.add_argument("--test", choices=["all", "codegen", "tts", "health"], default="all",
                       help="运行特定测试")

    args = parser.parse_args()

    client = LifeHubAPIClient(base_url=args.url)

    if args.test == "all":
        client.run_all_tests()
    elif args.test == "codegen":
        client.test_codegen_health()
        client.test_codegen_database()
        client.test_list_tables()
    elif args.test == "tts":
        client.test_tts_health()
        client.test_tts_generate()
        client.test_tts_download()
    elif args.test == "health":
        client.test_health()
        client.test_codegen_health()
        client.test_tts_health()


if __name__ == "__main__":
    main()
