# Health Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a health consultation Agent with SSE streaming output and multi-model config, exposed via FastAPI REST API.

**Architecture:** Extend existing `SimpleAgent` base class to create `HealthAgent`. Expose through FastAPI router with SSE streaming via `StreamingResponse`. Follow existing project patterns (Router → Service → Agent).

**Tech Stack:** Python 3.10, FastAPI, OpenAI SDK (OpenAI-compatible API), SSE

---

## File Structure

| File | Responsibility |
|------|---------------|
| `Agent/prompts/health_system.txt` | Health advisor system prompt |
| `Agent/health_agent.py` | HealthAgent class (extends SimpleAgent), chat + streaming |
| `schemas/health_agent.py` | Pydantic request/response models |
| `services/health_agent_service.py` | Business logic, session management |
| `routers/health_agent.py` | REST API endpoints with SSE |
| `routers/__init__.py` | Register health_router (modify) |
| `main.py` | Register health_router in app (modify) |

---

### Task 1: Health System Prompt

**Files:**
- Create: `Agent/prompts/health_system.txt`

- [ ] **Step 1: Create the system prompt file**

```txt
你是一位专业的健康顾问 AI 助手。你的职责是为用户提供健康相关的咨询服务。

## 角色定位
- 你是一位经验丰富、知识渊博的健康顾问
- 你擅长用通俗易懂的语言解释健康知识
- 你始终保持专业、耐心、关怀的态度

## 能力范围
1. 健康知识科普：解释常见疾病的症状、成因、预防措施
2. 生活方式建议：饮食营养、运动锻炼、睡眠改善、压力管理
3. 症状初步分析：根据用户描述的症状提供初步的健康建议（非诊断）
4. 用药常识：常见药物的基本信息和注意事项（非处方建议）
5. 心理健康：情绪管理、焦虑缓解、心理健康建议

## 回答规范
- 使用清晰的结构化格式（标题、列表、分段）
- 重要信息用加粗或列表突出
- 回答简洁明了，避免过于专业的术语
- 必要时解释医学术语的含义
- 每次回答控制在合理长度，不要过于冗长

## 重要限制
1. 你不能提供医学诊断，只能提供健康建议和信息
2. 对于严重症状或紧急情况，必须建议用户立即就医
3. 你不能开具处方或推荐具体药物剂量
4. 你不能替代专业医生的意见
5. 涉及个人隐私的健康信息，提醒用户注意保护

## 免责声明
在涉及具体症状或疾病时，在回答末尾添加：
"以上建议仅供参考，不能替代专业医疗诊断。如有健康问题，请及时咨询专业医生。"

## 语言
使用中文回答，除非用户使用其他语言提问。
```

- [ ] **Step 2: Commit**

```bash
git add Agent/prompts/health_system.txt
git commit -m "feat: add health agent system prompt"
```

---

### Task 2: HealthAgent Core

**Files:**
- Create: `Agent/health_agent.py`

- [ ] **Step 1: Create HealthAgent class**

```python
"""
健康咨询 Agent
继承 SimpleAgent，提供健康问答能力，支持流式输出
"""
import os
from typing import Generator
from .code_agent import SimpleAgent


class HealthAgent(SimpleAgent):
    """健康咨询 Agent"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        # 优先使用 HEALTH_LLM_* 配置，回退到通用配置
        api_key = api_key or os.getenv("HEALTH_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("API_KEY")
        base_url = base_url or os.getenv("HEALTH_LLM_BASE_URL") or os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")

        super().__init__(api_key, base_url)

        # 模型配置
        self.model = model or os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")

        # 加载健康系统提示词
        self.system_prompt = self._load_system_prompt()

        # 初始化对话历史（带系统提示）
        self.messages = [{"role": "system", "content": self.system_prompt}]

        print(f"  ✓ 健康 Agent 模型: {self.model}")

    def _load_system_prompt(self) -> str:
        """加载健康顾问系统提示词"""
        prompt_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "prompts",
            "health_system.txt"
        )
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"⚠️ 系统提示文件不存在: {prompt_path}，使用默认提示")
            return "你是一位专业的健康顾问 AI 助手。请用中文回答用户的健康相关问题。"

    def chat(self, user_message: str) -> str:
        """
        同步对话

        Args:
            user_message: 用户消息

        Returns:
            完整的回答文本
        """
        self.messages.append({"role": "user", "content": user_message})

        response = self._call_llm(use_tools=False)
        assistant_message = response.choices[0].message

        self.messages.append({
            "role": "assistant",
            "content": assistant_message.content
        })

        return assistant_message.content

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """
        流式对话，逐 chunk 返回

        Args:
            user_message: 用户消息

        Yields:
            每次生成的文本片段
        """
        self.messages.append({"role": "user", "content": user_message})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True
        )

        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token

        # 将完整回复加入历史
        self.messages.append({
            "role": "assistant",
            "content": full_response
        })

    def reset(self):
        """重置对话历史（保留系统提示）"""
        self.messages = [{"role": "system", "content": self.system_prompt}]


# 便捷函数
def get_health_agent() -> HealthAgent:
    """创建并返回健康 Agent"""
    return HealthAgent()


# 测试代码
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("健康 Agent 测试")
    print("=" * 60)

    agent = get_health_agent()

    # 测试同步对话
    print("\n【测试 1】同步对话")
    response = agent.chat("我最近经常失眠，有什么建议吗？")
    print(f"回答: {response}")

    # 测试流式对话
    print("\n【测试 2】流式对话")
    agent.reset()
    for chunk in agent.chat_stream("如何保持健康的饮食习惯？"):
        print(chunk, end="", flush=True)
    print()

    print("\n" + "=" * 60)
    print("测试完成！")
```

- [ ] **Step 2: Test the HealthAgent manually**

```bash
python -m Agent.health_agent
```

Expected: Should print system prompt loaded, model info, and generate responses to test questions.

- [ ] **Step 3: Commit**

```bash
git add Agent/health_agent.py
git commit -m "feat: add HealthAgent with sync and streaming chat"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `schemas/health_agent.py`

- [ ] **Step 1: Create request/response models**

```python
"""
健康 Agent 相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class HealthChatRequest(BaseModel):
    """健康咨询请求"""
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话 ID，不传则自动创建")


class HealthChatResponse(BaseModel):
    """健康咨询响应（同步）"""
    response: str = Field(..., description="AI 回复内容")
    session_id: str = Field(..., description="会话 ID")


class HealthResetRequest(BaseModel):
    """重置会话请求"""
    session_id: str = Field(..., description="要重置的会话 ID")


class HealthStatusResponse(BaseModel):
    """健康 Agent 服务状态"""
    status: str = Field(..., description="服务状态")
    model: str = Field(..., description="当前使用的模型")
    session_count: int = Field(..., description="活跃会话数")


class HealthErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="错误详情")
```

- [ ] **Step 2: Commit**

```bash
git add schemas/health_agent.py
git commit -m "feat: add health agent Pydantic schemas"
```

---

### Task 4: Service Layer

**Files:**
- Create: `services/health_agent_service.py`

- [ ] **Step 1: Create service with session management**

```python
"""
健康 Agent 服务层
管理 Agent 实例和会话
"""
import uuid
from typing import Dict, Generator, Optional
from Agent.health_agent import HealthAgent


class HealthAgentService:
    """健康 Agent 服务"""

    def __init__(self):
        self._sessions: Dict[str, HealthAgent] = {}
        print("✓ 健康 Agent 服务初始化完成")

    def _get_or_create_agent(self, session_id: Optional[str] = None) -> tuple[str, HealthAgent]:
        """
        获取或创建 Agent 实例

        Returns:
            (session_id, agent) 元组
        """
        if session_id and session_id in self._sessions:
            return session_id, self._sessions[session_id]

        # 创建新会话
        new_session_id = session_id or str(uuid.uuid4())
        agent = HealthAgent()
        self._sessions[new_session_id] = agent
        return new_session_id, agent

    def chat(self, message: str, session_id: Optional[str] = None) -> dict:
        """
        同步健康咨询

        Args:
            message: 用户消息
            session_id: 会话 ID

        Returns:
            包含 response 和 session_id 的字典
        """
        session_id, agent = self._get_or_create_agent(session_id)
        response = agent.chat(message)
        return {
            "response": response,
            "session_id": session_id
        }

    def chat_stream(self, message: str, session_id: Optional[str] = None) -> Generator[str, None, None]:
        """
        流式健康咨询

        Args:
            message: 用户消息
            session_id: 会话 ID

        Yields:
            文本片段
        """
        session_id, agent = self._get_or_create_agent(session_id)
        yield from agent.chat_stream(message)

    def reset(self, session_id: str) -> bool:
        """
        重置会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        if session_id in self._sessions:
            self._sessions[session_id].reset()
            return True
        return False

    def get_status(self) -> dict:
        """获取服务状态"""
        model = "unknown"
        if self._sessions:
            # 从任意活跃会话获取模型名
            first_agent = next(iter(self._sessions.values()))
            model = first_agent.model
        else:
            import os
            model = os.getenv("HEALTH_LLM_MODEL") or os.getenv("LLM_MODEL", "deepseek-chat")

        return {
            "status": "healthy",
            "model": model,
            "session_count": len(self._sessions)
        }

    def get_session_ids(self) -> list[str]:
        """获取所有会话 ID"""
        return list(self._sessions.keys())


# 全局服务实例
_health_agent_service: Optional[HealthAgentService] = None


def get_health_agent_service() -> HealthAgentService:
    """获取健康 Agent 服务实例（单例）"""
    global _health_agent_service
    if _health_agent_service is None:
        _health_agent_service = HealthAgentService()
    return _health_agent_service
```

- [ ] **Step 2: Commit**

```bash
git add services/health_agent_service.py
git commit -m "feat: add health agent service with session management"
```

---

### Task 5: Router with SSE Streaming

**Files:**
- Create: `routers/health_agent.py`

- [ ] **Step 1: Create router with SSE and sync endpoints**

```python
"""
健康 Agent 路由
提供健康咨询 REST API，支持 SSE 流式输出
"""
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from schemas.health_agent import (
    HealthChatRequest,
    HealthChatResponse,
    HealthResetRequest,
    HealthStatusResponse,
    HealthErrorResponse
)
from services.health_agent_service import get_health_agent_service

router = APIRouter(prefix="/api/health", tags=["健康 Agent"])


@router.post(
    "/chat",
    summary="健康咨询（SSE 流式）",
    description="发送健康问题，以 SSE 流式方式返回 AI 回答"
)
async def chat_stream(request: HealthChatRequest):
    """SSE 流式健康咨询"""
    service = get_health_agent_service()

    def event_generator():
        try:
            for chunk in service.chat_stream(request.message, request.session_id):
                yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post(
    "/chat/sync",
    response_model=HealthChatResponse,
    summary="健康咨询（同步）",
    description="发送健康问题，同步返回完整 AI 回答"
)
async def chat_sync(request: HealthChatRequest):
    """同步健康咨询"""
    try:
        service = get_health_agent_service()
        result = service.chat(request.message, request.session_id)
        return HealthChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/reset",
    summary="重置会话",
    description="重置指定会话的对话历史"
)
async def reset_session(request: HealthResetRequest):
    """重置会话"""
    service = get_health_agent_service()
    success = service.reset(request.session_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"会话不存在: {request.session_id}")
    return {"success": True, "message": "会话已重置"}


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    summary="Agent 服务健康检查",
    description="检查健康 Agent 服务状态"
)
async def health_check():
    """Agent 服务健康检查"""
    try:
        service = get_health_agent_service()
        return HealthStatusResponse(**service.get_status())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Register router in `routers/__init__.py`**

修改 `routers/__init__.py`：

```python
"""路由模块初始化"""
from routers.codegen import codegen_router
from routers.tts import tts_router
from routers.health_agent import router as health_router

__all__ = ["codegen_router", "tts_router", "health_router"]
```

- [ ] **Step 3: Commit**

```bash
git add routers/health_agent.py routers/__init__.py
git commit -m "feat: add health agent router with SSE streaming"
```

---

### Task 6: Register in Main App

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Add health_router to main.py**

修改 `main.py` 的 import 和路由注册：

```python
from routers import codegen_router, tts_router, health_router
```

在路由注册部分添加：

```python
app.include_router(health_router)
```

更新根路径的 endpoints 信息：

```python
@app.get("/", summary="根路径")
async def root():
    """API 根路径"""
    return {
        "name": "LifeHubAI API",
        "version": "1.0.0",
        "description": "AI 驱动的代码生成和文本转语音服务",
        "endpoints": {
            "docs": "/docs",
            "codegen": "/api/codegen",
            "tts": "/api/tts",
            "health_agent": "/api/health"
        }
    }
```

更新全局健康检查：

```python
@app.get("/health", summary="健康检查")
async def health_check():
    """整体健康检查"""
    return {
        "status": "healthy",
        "servers": {
            "http": "running"
        },
        "services": {
            "code_generation": "/api/codegen/health",
            "text_to_speech": "/api/tts/health",
            "health_agent": "/api/health/health"
        }
    }
```

- [ ] **Step 2: Commit**

```bash
git add main.py
git commit -m "feat: register health agent router in main app"
```

---

### Task 7: Integration Test

**Files:**
- Create: `test_health_agent.py`

- [ ] **Step 1: Create integration test script**

```python
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
```

- [ ] **Step 2: Run the server and test**

Start server:
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

In another terminal, run tests:
```bash
python test_health_agent.py
```

Expected: All 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add test_health_agent.py
git commit -m "test: add health agent integration tests"
```

---

### Task 8: Update .env.example

**Files:**
- Modify: `.env.example` (if exists) or document env vars

- [ ] **Step 1: Add health agent config to .env.example**

Append to `.env.example`:

```env
# Health Agent Configuration (optional, falls back to general config)
HEALTH_LLM_MODEL=deepseek-chat
HEALTH_LLM_BASE_URL=https://api.deepseek.com/v1
HEALTH_LLM_API_KEY=
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add health agent env config examples"
```
