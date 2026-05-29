from agent.health.health_main import main


if __name__ == "__main__":
    result = main("我想要减肥，我要怎么调整我的饮食和锻炼计划？")

    print("=== Final Response ===")
    print(result["state"].get("final_response", ""))
    print()

    print("=== Review Status ===")
    print(result["state"].get("review_status", ""))
    print()

    print("=== Summary ===")
    print(result.get("summary", {}))
    # 同步流式输出
