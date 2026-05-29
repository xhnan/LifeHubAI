"""
代码生成路由
"""
from functools import lru_cache
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from schemas.codegen import (
    CodeGenResponse,
    TableListResponse,
    DatabaseInfoResponse,
    HealthResponse
)
from services.codegen_service import CodegenService

router = APIRouter(prefix="/api/codegen", tags=["代码生成"])


@lru_cache()
def get_codegen_service() -> CodegenService:
    return CodegenService()


@router.get("/health", response_model=HealthResponse, summary="代码生成服务健康检查")
async def health_check(service: CodegenService = Depends(get_codegen_service)):
    """检查代码生成服务健康状态"""
    try:
        db_connected = service.check_database_connection()
        return HealthResponse(
            status="healthy" if db_connected else "unhealthy",
            database_connected=db_connected
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database", response_model=DatabaseInfoResponse, summary="获取数据库信息")
async def get_database_info(service: CodegenService = Depends(get_codegen_service)):
    """获取数据库连接信息"""
    try:
        info = service.get_database_info()
        return DatabaseInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables", response_model=TableListResponse, summary="列出数据库表")
async def list_tables(prefix: Optional[str] = "", service: CodegenService = Depends(get_codegen_service)):
    """
    列出数据库表

    - prefix: 表名前缀过滤，例如 "sys" 只显示以 "sys" 开头的表
    """
    try:
        tables = service.list_tables(prefix=prefix)
        return TableListResponse(
            count=len(tables),
            tables=tables
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate", response_model=CodeGenResponse, summary="生成所有表的代码")
async def generate_all_code(service: CodegenService = Depends(get_codegen_service)):
    """
    为配置中的所有表生成 Java 代码
    """
    try:
        result = service.generate_all()
        return CodeGenResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=CodeGenResponse, summary="生成指定表的代码")
async def generate_code(tables: list[str], service: CodegenService = Depends(get_codegen_service)):
    """
    为指定的表生成 Java 代码

    - tables: 要生成的表名列表
    """
    try:
        if not tables:
            raise HTTPException(status_code=400, detail="表名列表不能为空")

        result = service.generate_tables(tables)
        return CodeGenResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


codegen_router = router
