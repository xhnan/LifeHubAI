"""
健康 Agent API 集成测试
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_health_check():
    """测试 Agent 服务健康检查"""
    print("\n【测试 1】Agent 服务健康检查")
    resp = requests.get(f"{BASE_URL}/api/health/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), ensure_ascii=False, indent=2)}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    print("✅ 通过")


def test_sync_chat():
    """测试同步健康咨询"""
    print("\n【测试 2】同步健康咨询")
    resp = requests.post(
        f"{BASE_URL}/api/health/chat/sync",
        json={"message": "如何保持健康的饮食习惯？"}
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Session ID: {data['session_id']}")
    print(f"Response: {data['response'][:200]}...")
    assert resp.status_code == 200
    assert "response" in data
    assert "session_id" in data
    print("✅ 通过")
    return data["session_id"]


def test_stream_chat():
    """测试 SSE 流式健康咨询"""
    print("\n【测试 3】SSE 流式健康咨询")
    resp = requests.post(
        f"{BASE_URL}/api/health/chat",
        json={"message": "失眠怎么办？"},
        stream=True
    )
    print(f"Status: {resp.status_code}")
    print("Stream output:")
    tokens = []
    for line in resp.iter_lines():
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                data = json.loads(data_str)
                if "token" in data:
                    tokens.append(data["token"])
                    print(data["token"], end="", flush=True)
    print()
    assert len(tokens) > 0
    print(f"\n✅ 通过 (共 {len(tokens)} 个 token)")


def test_reset_session(session_id: str):
    """测试重置会话"""
    print("\n【测试 4】重置会话")
    resp = requests.post(
        f"{BASE_URL}/api/health/reset",
        json={"session_id": session_id}
    )
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")
    assert resp.status_code == 200
    print("✅ 通过")


def test_reset_nonexistent_session():
    """测试重置不存在的会话"""
    print("\n【测试 5】重置不存在的会话")
    resp = requests.post(
        f"{BASE_URL}/api/health/reset",
        json={"session_id": "nonexistent-id"}
    )
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 404
    print("✅ 通过 (正确返回 404)")


if __name__ == "__main__":
    print("=" * 60)
    print("健康 Agent API 集成测试")
    print("=" * 60)

    test_health_check()
    session_id = test_sync_chat()
    test_stream_chat()
    test_reset_session(session_id)
    test_reset_nonexistent_session()

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
