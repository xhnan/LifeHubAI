"""
数据库工具 - 为 Agent 提供数据库访问能力
支持 PostgreSQL 数据库，内置连接池和 SQL 注入防护
"""
import os
import re
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

# 标识符合法字符正则：只允许字母、数字、下划线，且以字母或下划线开头
_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')


def _validate_identifier(name: str, label: str = "identifier") -> None:
    """校验 SQL 标识符（表名、schema 名等），防止注入"""
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"非法 {label}: {name!r}（仅允许字母、数字、下划线）")


# 全局连接池（进程内单例）
_pool: Optional[ThreadedConnectionPool] = None


def _get_pool(db_config: Dict[str, Any]) -> ThreadedConnectionPool:
    """获取或创建全局连接池"""
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            **db_config
        )
        logger.info("数据库连接池已创建 (min=2, max=10)")
    return _pool


class DatabaseTool:
    """数据库操作工具类"""

    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        初始化数据库工具

        Args:
            db_config: 数据库配置字典，如果不提供则从环境变量读取
        """
        if db_config:
            self.db_config = db_config
        else:
            self.db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", 5432)),
                "database": os.getenv("DB_NAME"),
                "user": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD")
            }

    @contextmanager
    def _get_connection(self):
        """从连接池获取连接的上下文管理器"""
        pool = _get_pool(self.db_config)
        conn = pool.getconn()
        try:
            yield conn
        finally:
            pool.putconn(conn)

    def test_connection(self) -> Dict[str, Any]:
        """
        测试数据库连接

        Returns:
            {
                "success": True/False,
                "message": "连接成功/失败信息",
                "database": "数据库名",
                "version": "PostgreSQL版本",
                "error": "错误信息(如果失败)"
            }
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]

            return {
                "success": True,
                "message": "数据库连接成功",
                "database": self.db_config["database"],
                "host": self.db_config["host"],
                "port": self.db_config["port"],
                "version": version
            }

        except Exception as e:
            return {
                "success": False,
                "message": "数据库连接失败",
                "error": str(e),
            }

    def list_tables(
        self,
        schema: str = "public",
        prefix: str = ""
    ) -> Dict[str, Any]:
        """
        列出数据库中的所有表

        Args:
            schema: 数据库 schema，默认为 'public'
            prefix: 表名前缀过滤，如 'sys_' 只列出以 sys_ 开头的表

        Returns:
            {
                "success": True/False,
                "tables": ["table1", "table2", ...],
                "count": 表数量,
                "schema": "schema名称"
            }
        """
        _validate_identifier(schema, "schema")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema = %s
                        AND table_type = 'BASE TABLE'
                    """

                    if prefix:
                        query += " AND table_name LIKE %s"
                        cursor.execute(query, (schema, f"{prefix}%"))
                    else:
                        cursor.execute(query, (schema,))

                    rows = cursor.fetchall()
                    tables = [row[0] for row in rows]

            return {
                "success": True,
                "tables": sorted(tables),
                "count": len(tables),
                "schema": schema,
                "prefix": prefix
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"获取表列表失败: {str(e)}"
            }

    def get_table_schema(
        self,
        table_name: str,
        schema: str = "public"
    ) -> Dict[str, Any]:
        """
        获取表的完整结构信息

        Args:
            table_name: 表名
            schema: 数据库 schema，默认为 'public'

        Returns:
            {
                "success": True/False,
                "table_name": "表名",
                "schema": "schema名称",
                "columns": [...],
                "primary_keys": ["id"]
            }
        """
        _validate_identifier(table_name, "table_name")
        _validate_identifier(schema, "schema")
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 1. 获取字段信息
                    column_query = """
                        SELECT
                            column_name,
                            data_type,
                            character_maximum_length,
                            is_nullable,
                            column_default,
                            ordinal_position
                        FROM information_schema.columns
                        WHERE table_schema = %s
                        AND table_name = %s
                        ORDER BY ordinal_position
                    """
                    cursor.execute(column_query, (schema, table_name))
                    columns_info = cursor.fetchall()

                    if not columns_info:
                        return {
                            "success": False,
                            "error": f"表 {table_name} 不存在"
                        }

                    # 2. 获取主键信息
                    pk_query = """
                        SELECT a.column_name
                        FROM information_schema.table_constraints t
                        JOIN information_schema.key_column_usage a
                            ON t.constraint_name = a.constraint_name
                        WHERE t.table_schema = %s
                        AND t.table_name = %s
                        AND t.constraint_type = 'PRIMARY KEY'
                    """
                    cursor.execute(pk_query, (schema, table_name))
                    primary_keys = [row["column_name"] for row in cursor.fetchall()]

                    # 3. 获取字段注释
                    comment_query = """
                        SELECT
                            a.column_name,
                            pgd.description as comment
                        FROM information_schema.columns a
                        LEFT JOIN pg_catalog.pg_description pgd
                            ON pgd.objoid = (
                                SELECT oid FROM pg_class
                                WHERE relname = a.table_name
                            )
                            AND pgd.objsubid = a.ordinal_position
                        WHERE a.table_schema = %s
                        AND a.table_name = %s
                    """
                    cursor.execute(comment_query, (schema, table_name))
                    comments = {row["column_name"]: row["comment"]
                               for row in cursor.fetchall() if row["comment"]}

            # 4. 组装字段信息
            columns = []
            for col in columns_info:
                col_name = col["column_name"]
                columns.append({
                    "name": col_name,
                    "type": col["data_type"],
                    "max_length": col["character_maximum_length"],
                    "nullable": col["is_nullable"] == "YES",
                    "default": col["column_default"],
                    "is_primary_key": col_name in primary_keys,
                    "comment": comments.get(col_name, "")
                })

            return {
                "success": True,
                "table_name": table_name,
                "schema": schema,
                "columns": columns,
                "column_count": len(columns),
                "primary_keys": primary_keys
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"获取表结构失败: {str(e)}"
            }

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch: str = "all"
    ) -> Dict[str, Any]:
        """
        执行 SQL 查询（仅允许 SELECT）

        Args:
            query: SQL 查询语句（必须以 SELECT 开头）
            params: 查询参数（用于参数化查询）
            fetch: 返回模式，'all', 'one', 'none'

        Returns:
            {
                "success": True/False,
                "rows": [...],
                "row_count": 行数,
                "columns": ["列名", ...]
            }
        """
        # SQL 安全校验：仅允许 SELECT
        normalized = query.strip().upper()
        if not normalized.startswith("SELECT"):
            return {
                "success": False,
                "error": "安全限制：仅允许 SELECT 查询",
                "message": "execute_query 仅支持 SELECT 语句"
            }

        # 禁止多语句执行（去掉末尾分号后检查）
        stripped = query.rstrip(";").strip()
        if ";" in stripped:
            return {
                "success": False,
                "error": "安全限制：不允许多语句执行",
                "message": "单次查询只能包含一条 SQL 语句"
            }

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params or ())

                    if fetch == "all":
                        rows = cursor.fetchall()
                    elif fetch == "one":
                        rows = [cursor.fetchone()] if cursor.rowcount > 0 else []
                    else:
                        rows = []

                    if rows:
                        columns = list(rows[0].keys())
                        rows = [dict(row) for row in rows]
                    else:
                        columns = []
                        rows = []

            return {
                "success": True,
                "rows": rows,
                "row_count": len(rows),
                "columns": columns
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"查询执行失败: {str(e)}"
            }

    def get_table_info(
        self,
        table_name: str,
        schema: str = "public"
    ) -> Dict[str, Any]:
        """
        获取表的详细信息（包括记录数、大小等）

        Args:
            table_name: 表名
            schema: 数据库 schema

        Returns:
            {
                "success": True/False,
                "table_name": "表名",
                "row_count": 行数,
                "size": "表大小",
                "columns": [...],
                ...
            }
        """
        _validate_identifier(table_name, "table_name")
        _validate_identifier(schema, "schema")
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # 获取表行数（标识符已校验，使用 f-string 安全拼接）
                    count_query = f"SELECT COUNT(*) FROM {schema}.{table_name}"
                    cursor.execute(count_query)
                    row_count = cursor.fetchone()[0]

                    # 获取表大小
                    size_query = "SELECT pg_size_pretty(pg_total_relation_size(%s))"
                    cursor.execute(size_query, (f"{schema}.{table_name}",))
                    table_size = cursor.fetchone()[0]

            # 获取表结构
            schema_result = self.get_table_schema(table_name, schema)

            return {
                "success": True,
                "table_name": table_name,
                "schema": schema,
                "row_count": row_count,
                "size": table_size,
                "columns": schema_result.get("columns", []),
                "primary_keys": schema_result.get("primary_keys", [])
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"获取表信息失败: {str(e)}"
            }


# 便捷函数：创建默认实例
def get_db_tool() -> DatabaseTool:
    """创建并返回数据库工具实例（从环境变量读取配置）"""
    return DatabaseTool()


# 测试代码
if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    db = get_db_tool()

    # 测试连接
    print("=" * 50)
    print("1. 测试数据库连接")
    print("=" * 50)
    result = db.test_connection()
    print(f"连接状态: {'成功' if result['success'] else '失败'}")
    if result['success']:
        print(f"数据库: {result['database']}")
        print(f"版本: {result['version']}")

    # 列出表
    print("\n" + "=" * 50)
    print("2. 列出所有表")
    print("=" * 50)
    tables = db.list_tables(prefix="sys_")
    if tables['success']:
        print(f"找到 {tables['count']} 个表:")
        for table in tables['tables'][:5]:
            print(f"  - {table}")
        if tables['count'] > 5:
            print(f"  ... 还有 {tables['count'] - 5} 个表")

    # 获取表结构
    if tables['success'] and tables['tables']:
        first_table = tables['tables'][0]
        print(f"\n" + "=" * 50)
        print(f"3. 获取表结构: {first_table}")
        print("=" * 50)
        schema = db.get_table_schema(first_table)
        if schema['success']:
            print(f"表名: {schema['table_name']}")
            print(f"字段数: {schema['column_count']}")
            print(f"主键: {schema['primary_keys']}")
            print("\n字段列表:")
            for col in schema['columns']:
                pk_mark = " [PK]" if col['is_primary_key'] else ""
                nullable_mark = " NULL" if col['nullable'] else " NOT NULL"
                print(f"  - {col['name']}: {col['type']}{nullable_mark}{pk_mark}")
                if col['comment']:
                    print(f"    注释: {col['comment']}")
