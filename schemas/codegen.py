"""
代码生成相关的数据模型
"""
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """代码生成服务健康检查响应"""
    status: str
    database_connected: bool


class AgentGenerateRequest(BaseModel):
    """基于自然语言的代码生成请求（供 LifeHubServer 调用）"""
    prompt: str = Field(..., description="自然语言描述，例如：为 sys_user 表生成完整的 CRUD 代码")


class AgentFileInfo(BaseModel):
    """生成的文件信息"""
    path: str = ""
    type: str = ""
    description: str = ""


class AgentGenerateResponse(BaseModel):
    """基于自然语言的代码生成响应（与原 gRPC GenerateResponse 字段对齐）"""
    success: bool = False
    message: str = ""
    description: str = ""
    files: list[AgentFileInfo] = []
    error: str = ""
    steps: list[str] = []


class DatabaseInfoResponse(BaseModel):
    """数据库信息响应"""
    host: str
    port: int
    database: str
    connected: bool
    version: str = ""


class TableListResponse(BaseModel):
    """表列表响应"""
    count: int
    tables: list[str]


class CodeGenResponse(BaseModel):
    """代码生成响应"""
    success: bool
    message: str
    total_tables: int
    generated_tables: list[str]
    failed_tables: list[str] = []
