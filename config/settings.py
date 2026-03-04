"""
配置管理模块
支持开发环境（本地 .env）和生产环境（Nacos 配置中心）
"""
import os
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """配置管理类"""

    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置

        Args:
            env_file: 指定 .env 文件路径，不指定则自动加载
        """
        # 加载环境变量
        if env_file:
            load_dotenv(env_file)
        else:
            # 自动检测环境并加载对应的配置文件
            self._load_env_by_environment()

        # 获取当前环境
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.nacos_enabled = os.getenv("NACOS_ENABLED", "false").lower() == "true"

        # Nacos 客户端实例（用于服务注册/注销）
        self._nacos_client = None

        # 如果是生产环境且启用了 Nacos，则从 Nacos 加载配置
        if self.environment == "production" and self.nacos_enabled:
            self._nacos_client = self._create_nacos_client()
            if self._nacos_client:
                self._load_from_nacos_with_client(self._nacos_client)
                self._register_service(self._nacos_client)

        logger.info(f"✓ 配置初始化完成")
        logger.info(f"  环境: {self.environment}")
        logger.info(f"  Nacos: {'启用' if self.nacos_enabled else '未启用'}")

    def _load_env_by_environment(self):
        """根据环境变量加载对应的配置文件"""
        env = os.getenv("ENVIRONMENT", "development").lower()

        # 优先加载指定的环境配置文件
        env_files = {
            "development": ".env.development",
            "production": ".env.production",
        }

        env_file = env_files.get(env, ".env")

        # 首先加载基础 .env
        if os.path.exists(".env"):
            load_dotenv(".env")

        # 然后加载环境特定配置（会覆盖基础配置）
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            logger.info(f"✓ 已加载环境配置: {env_file}")

    def _create_nacos_client(self):
        """创建 Nacos 客户端实例"""
        try:
            from nacos import NacosClient

            server_addresses = os.getenv("NACOS_SERVER_ADDRESSES")
            namespace = os.getenv("NACOS_NAMESPACE", "public")
            username = os.getenv("NACOS_USERNAME")
            password = os.getenv("NACOS_PASSWORD")

            if not server_addresses:
                print("⚠️ NACOS_SERVER_ADDRESSES 未配置")
                return None

            client_kwargs = {
                "server_addresses": server_addresses,
                "namespace": namespace,
            }
            if username and password:
                client_kwargs["username"] = username
                client_kwargs["password"] = password

            client = NacosClient(**client_kwargs)
            print(f"✓ Nacos 客户端已创建: {server_addresses}")
            return client

        except ImportError:
            print("⚠️ 未安装 nacos-sdk-python，使用本地配置")
            print("   安装命令: pip install nacos-sdk-python")
            return None
        except Exception as e:
            print(f"❌ 创建 Nacos 客户端失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _load_from_nacos_with_client(self, client):
        """使用已有客户端从 Nacos 加载配置"""
        try:
            data_id = os.getenv("NACOS_CONFIG_DATA_ID")
            group = os.getenv("NACOS_CONFIG_GROUP", "DEFAULT_GROUP")

            if not data_id:
                print("⚠️ NACOS_CONFIG_DATA_ID 未配置，跳过配置加载")
                return

            config_content = client.get_config(data_id, group)

            if config_content:
                self._parse_nacos_config(config_content)
                print(f"✓ 已从 Nacos 加载配置: {data_id}/{group}")
            else:
                print("⚠️ Nacos 配置为空，使用本地配置")

        except Exception as e:
            print(f"❌ 从 Nacos 加载配置失败: {str(e)}")
            import traceback
            traceback.print_exc()
            print("   使用本地配置")

    def _register_service(self, client):
        """向 Nacos 注册服务实例"""
        try:
            import socket
            import threading

            service_name = os.getenv("NACOS_SERVICE_NAME", "lifehubai")
            service_port = self.get_int("FASTAPI_PORT", 8000)
            group = os.getenv("NACOS_CONFIG_GROUP", "DEFAULT_GROUP")

            # 获取容器 IP（Docker 内部 IP）
            service_ip = os.getenv("NACOS_SERVICE_IP", "")
            if not service_ip:
                try:
                    service_ip = socket.gethostbyname(socket.gethostname())
                except Exception:
                    service_ip = "127.0.0.1"

            print(f"  注册服务中: {service_name} ({service_ip}:{service_port}) -> {group}")

            # 保存注册信息，供心跳和注销使用
            self._service_info = {
                "service_name": service_name,
                "ip": service_ip,
                "port": service_port,
                "group": group,
            }

            # 注册服务（临时实例，需要心跳保活）
            client.add_naming_instance(
                service_name,
                service_ip,
                service_port,
                group_name=group,
                ephemeral=True,
                weight=1.0,
                metadata={
                    "version": "1.0.0",
                    "framework": "FastAPI",
                    "language": "Python",
                },
            )
            print(f"✓ 已注册到 Nacos 服务列表: {service_name} ({service_ip}:{service_port})")

            # 启动心跳线程，每 5 秒发送一次心跳
            self._heartbeat_running = True

            def heartbeat_loop():
                import time
                while self._heartbeat_running:
                    try:
                        client.send_heartbeat(
                            service_name,
                            service_ip,
                            service_port,
                            group_name=group,
                        )
                    except Exception as e:
                        print(f"⚠️ Nacos 心跳发送失败: {str(e)}")
                    time.sleep(5)

            heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True, name="nacos-heartbeat")
            heartbeat_thread.start()
            print(f"✓ Nacos 心跳线程已启动 (间隔 5s)")


        except Exception as e:
            print(f"❌ Nacos 服务注册失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def deregister_service(self):
        """从 Nacos 注销服务实例"""
        # 停止心跳线程
        self._heartbeat_running = False

        if not self._nacos_client:
            return
        try:
            info = getattr(self, "_service_info", None)
            if not info:
                return

            self._nacos_client.remove_naming_instance(
                info["service_name"],
                info["ip"],
                info["port"],
                group_name=info["group"],
            )
            print(f"✓ 已从 Nacos 注销服务: {info['service_name']}")

        except Exception as e:
            print(f"❌ Nacos 服务注销失败: {str(e)}")

    def _parse_nacos_config(self, config_content: str):
        """
        解析 Nacos 配置内容并更新环境变量

        支持的格式：
        1. KEY=VALUE 格式（类似 .env）
        2. JSON 格式（会转换为环境变量）
        """
        import json

        # 尝试解析为 JSON
        if config_content.strip().startswith("{"):
            try:
                config_dict = json.loads(config_content)
                for key, value in config_dict.items():
                    if isinstance(value, (str, int, float, bool)):
                        os.environ[key.upper()] = str(value)
                return
            except json.JSONDecodeError:
                pass

        # 按行解析 KEY=VALUE 格式
        for line in config_content.split("\n"):
            line = line.strip()
            # 跳过注释和空行
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().upper()
                value = value.strip()
                # 移除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                os.environ[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return os.getenv(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        try:
            return int(os.getenv(key, default))
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        try:
            return float(os.getenv(key, default))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔配置"""
        value = os.getenv(key, "").lower()
        return value in ("true", "1", "yes", "on")

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"

    def get_database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        return {
            "host": self.get("DB_HOST", "localhost"),
            "port": self.get_int("DB_PORT", 5432),
            "database": self.get("DB_NAME", "LifeHub"),
            "user": self.get("DB_USER", "postgres"),
            "password": self.get("DB_PASSWORD", ""),
        }

    def get_ai_config(self) -> Dict[str, Any]:
        """获取 AI 配置"""
        return {
            "api_key": self.get("DEEPSEEK_API_KEY", ""),
            "base_url": self.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1"),
            "model": self.get("LLM_MODEL", "deepseek-chat"),
        }

    def get_grpc_config(self) -> Dict[str, Any]:
        """获取 gRPC 配置"""
        return {
            "enabled": self.get_bool("GRPC_ENABLED", False),
            "host": self.get("GRPC_HOST", "0.0.0.0"),
            "port": self.get_int("GRPC_PORT", 50051),
        }

    def get_codegen_config(self) -> Dict[str, Any]:
        """获取代码生成配置"""
        return {
            "output_dir": self.get("CODE_OUTPUT_DIR", "./output"),
            "package_prefix": self.get("CODE_PACKAGE_PREFIX", "com.xhn"),
        }


# 全局配置实例
_config = None


def get_config(env_file: Optional[str] = None) -> Config:
    """获取配置实例（单例模式）"""
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None):
    """重新加载配置"""
    global _config
    _config = Config(env_file)


# 便捷函数
def get_setting(key: str, default: Any = None) -> Any:
    """快速获取配置值"""
    return get_config().get(key, default)
