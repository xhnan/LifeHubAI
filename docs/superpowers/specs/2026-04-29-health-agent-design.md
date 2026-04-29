# 健康 Agent 设计文档

## 概述

为 LifeHubAI 添加健康领域 Agent，提供健康咨询问答能力，支持 SSE 流式输出和多模型配置。

## 目标

- **Phase 1 (MVP)**: 健康咨询问答 + 流式输出 + 多模型配置
- **Phase 2**: 健康数据分析（接入 Java 后端持久化数据）
- **Phase 3**: 工具调用型 Agent（数据库查询、外部 API 等）

## 架构

```
客户端 (浏览器/App)
    │
    │  POST /api/health/chat (SSE)
    ▼
FastAPI Router (routers/health_agent.py)
    │
    ▼
HealthAgentService (services/health_agent_service.py)
    │
    ▼
HealthAgent (Agent/health_agent.py)
    │  继承 SimpleAgent
    │  加载 health_system.txt 作为系统提示词
    │  使用 OpenAI-compatible API
    ▼
LLM API (DeepSeek / Zhipu / 其他)
```

## 新增文件

### Agent 层

**Agent/health_agent.py** - 健康 Agent 核心

```python
class HealthAgent(SimpleAgent):
    """健康咨询 Agent"""
    
    def __init__(self, api_key=None, base_url=None, model=None):
        super().__init__(api_key, base_url)
        # 加载健康系统提示词
        # 设置模型 (支持 HEALTH_LLM_MODEL 环境变量)
    
    def chat_stream(self, user_message: str) -> Generator[str]:
        """流式对话，逐 token 返回"""
    
    def chat(self, user_message: str) -> str:
        """同步对话，返回完整回答"""
    
    def reset(self):
        """重置对话上下文"""
```

关键设计:
- 继承 `SimpleAgent`，复用 OpenAI 客户端和工具注册机制
- `chat_stream()` 使用 `stream=True` 参数调用 LLM，逐 chunk yield
- 系统提示词从 `Agent/prompts/health_system.txt` 加载
- 支持独立的模型配置 (环境变量 `HEALTH_LLM_*`)

**Agent/prompts/health_system.txt** - 系统提示词

定义健康顾问的角色、知识范围、回答规范:
- 角色: 专业健康顾问
- 能力: 健康知识问答、症状初步分析、生活方式建议
- 限制: 不提供诊断、建议就医场景
- 输出规范: 结构化、易读、附带免责声明

### 服务层

**services/health_agent_service.py** - 业务逻辑

```python
class HealthAgentService:
    def __init__(self):
        self.agent = HealthAgent()
    
    def chat_stream(self, message: str, session_id: str = None) -> Generator[str]:
        """流式健康咨询"""
    
    def chat(self, message: str, session_id: str = None) -> dict:
        """同步健康咨询"""
    
    def reset(self, session_id: str = None):
        """重置会话"""
    
    def check_health(self) -> dict:
        """服务健康检查"""
```

会话管理:
- 使用 `session_id` 区分不同会话
- 每个会话维护独立的对话历史
- 内存存储 (Phase 1)，后续可接入 Redis 或 Java 后端

### 路由层

**routers/health_agent.py** - REST API

端点:
- `POST /api/health/chat` - SSE 流式健康咨询
  - 请求体: `{"message": "...", "session_id": "..."}`
  - 响应: `text/event-stream`，每个 event 是一个 token
- `POST /api/health/chat/sync` - 同步健康咨询
  - 请求体: 同上
  - 响应: `{"response": "...", "session_id": "..."}`
- `GET /api/health/health` - Agent 服务健康检查
- `POST /api/health/reset` - 重置会话

### Schema 层

**schemas/health_agent.py** - 数据模型

```python
class HealthChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class HealthChatResponse(BaseModel):
    response: str
    session_id: str

class HealthStatusResponse(BaseModel):
    status: str
    model: str
    session_count: int
```

## 流式输出实现

使用 FastAPI `StreamingResponse` + SSE:

```python
@router.post("/chat")
async def chat_stream(request: HealthChatRequest):
    async def event_generator():
        for chunk in service.chat_stream(request.message, request.session_id):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

客户端使用 `EventSource` 或 `fetch` + `ReadableStream` 接收。

## 多模型配置

环境变量 (`.env`):
```
# 健康 Agent 专用配置 (可选，不设置则使用通用配置)
HEALTH_LLM_MODEL=deepseek-chat
HEALTH_LLM_BASE_URL=https://api.deepseek.com/v1
HEALTH_LLM_API_KEY=sk-xxx

# 通用配置 (回退)
LLM_MODEL=deepseek-chat
API_KEY=sk-xxx
DEEPSEEK_API_URL=https://api.deepseek.com/v1
```

优先级: `HEALTH_LLM_*` > 通用配置

## 与现有系统的关系

- **不修改** 现有 gRPC 服务
- **不修改** 现有 codegen 路由
- **复用** `SimpleAgent` 基类
- **复用** `config/settings.py` 配置管理
- **遵循** 现有 FastAPI 路由/服务/Schema 分层模式

## Phase 2+ 扩展点

- 添加健康工具 (数据库查询、外部 API)
- 接入 Java 后端进行数据持久化
- 多轮对话记忆管理
- 用户健康档案管理

## 测试策略

- 单元测试: HealthAgent 的 chat/chat_stream 方法
- 集成测试: API 端点的请求/响应
- 手动测试: 流式输出在浏览器中的表现
