"""
快速测试代码生成 Agent
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Agent.code_agent import get_agent

def main():
    print("\n" + "="*60)
    print("代码生成 Agent 快速测试")
    print("="*60)

    # 创建 Agent
    print("\n初始化 Agent...")
    agent = get_agent()

    # 测试查询
    print("\n" + "-"*60)
    print("测试: 查询数据库表")
    print("-"*60)

    result = agent.run(
        "帮我列出数据库中所有的表，并告诉我总共有多少个表",
        verbose=True
    )

    print("\n✓ 测试完成！")

if __name__ == "__main__":
    main()
