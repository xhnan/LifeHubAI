"""
代码生成服务
"""
import os
import psycopg2
from dotenv import load_dotenv
import yaml

# 加载环境变量
load_dotenv()


class CodegenService:
    """代码生成服务"""

    def __init__(self):
        self.db_config = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD")
        }

        # 加载配置文件
        config_path = os.path.join(os.path.dirname(__file__), "../Generate/config.yaml")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = {
                "module_name": "sys",
                "table_name": ["sys"],
                "allowed_tables": False
            }

    def check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.close()
            return True
        except Exception:
            return False

    def get_database_info(self) -> dict:
        """获取数据库信息"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            return {
                "host": self.db_config["host"],
                "port": int(self.db_config["port"]),
                "database": self.db_config["database"],
                "user": self.db_config["user"],
                "connected": True,
                "version": version
            }
        except Exception as e:
            return {
                "host": self.db_config.get("host", ""),
                "port": int(self.db_config.get("port", 0)),
                "database": self.db_config.get("database", ""),
                "user": self.db_config.get("user", ""),
                "connected": False,
                "error": str(e)
            }

    def list_tables(self, prefix: str = "") -> list[str]:
        """列出数据库表"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
            """

            if prefix:
                query += f" AND table_name LIKE %s"
                cursor.execute(query, (f"{prefix}%",))
            else:
                cursor.execute(query)

            tables = [row[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return sorted(tables)
        except Exception as e:
            raise Exception(f"获取表列表失败: {str(e)}")

    def generate_all(self) -> dict:
        """生成所有配置的表的代码"""
        try:
            # 获取表名前缀
            table_filters = self.config.get("table_name", ["sys"])

            # 收集所有匹配的表
            all_tables = []
            for prefix in table_filters:
                tables = self.list_tables(prefix=prefix)
                all_tables.extend(tables)

            if not all_tables:
                return {
                    "success": True,
                    "message": "没有找到匹配的表",
                    "total_tables": 0,
                    "generated_tables": [],
                    "failed_tables": []
                }

            return self.generate_tables(all_tables)

        except Exception as e:
            return {
                "success": False,
                "message": f"生成失败: {str(e)}",
                "total_tables": 0,
                "generated_tables": [],
                "failed_tables": []
            }

    def generate_tables(self, tables: list[str]) -> dict:
        """生成指定表的代码"""
        # TODO: 实现实际的代码生成逻辑
        # 这里需要调用 Generate/JavaCodeGenerate.py 中的逻辑

        generated = []
        failed = []

        for table in tables:
            try:
                # 占位符：实际应该调用代码生成逻辑
                # 例如：from Generate.JavaCodeGenerate import generate_single_table
                # generate_single_table(table)
                generated.append(table)
            except Exception as e:
                failed.append(f"{table}: {str(e)}")

        return {
            "success": len(failed) == 0,
            "message": f"生成完成: {len(generated)} 成功, {len(failed)} 失败",
            "total_tables": len(tables),
            "generated_tables": generated,
            "failed_tables": failed
        }
