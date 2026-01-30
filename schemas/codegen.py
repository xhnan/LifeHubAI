"""
代码生成相关的数据模型
"""
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """代码生成服务健康检查响应"""
    status: str
    database_connected: bool


class DatabaseInfoResponse(BaseModel):
    """数据库信息响应"""
    host: str
    port: int
    database: str
    user: str
    connected: bool


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
