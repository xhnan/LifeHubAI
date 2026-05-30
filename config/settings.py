"""
配置管理模块
支持开发环境（本地 .env）和生产环境（Nacos 配置中心）
"""
import os
import logging
import threading
from typing import Any, Dict, Optional, Set
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Nacos 配置允许写入 os.environ 的白名单
_ALLOWED_NACOS_KEYS: Set[str] = {
    "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD",
    "DEEPSEEK_API_KEY", "DEEPSEEK_API_URL", "API_KEY", "AI_BASE_URL",
    "LLM_MODEL",
    "ZHIPU_API_KEY",
    "HEALTH_LLM_API_KEY", "HEALTH_LLM_BASE_URL", "HEALTH_LLM_MODEL",
    "FASTAPI_HOST", "FASTAPI_PORT",
    "CODE_OUTPUT_DIR", "CODE_PACKAGE_PREFIX",
    "NACOS_SERVICE_NAME", "NACOS_SERVICE_IP",
}


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
            self._load_env_by_environment()

        # 获取当前环境
        self.environment = os.getenv("ENVIRONMENT", "development").lower()
        self.nacos_enabled = os.getenv("NACOS_ENABLED", "false").lower() == "true"

        # Nacos 客户端实例
        self._nacos_client = None
        self._service_info = None
        self._heartbeat_running = False

        # 如果是生产环境且启用了 Nacos，则从 Nacos 加载配置（不注册服务）
        if self.environment == "production" and self.nacos_enabled:
            self._nacos_client = self._create_nacos_client()
            if self._nacos_client:
                self._load_from_nacos_with_client(self._nacos_client)

        logger.info(f"配置初始化完成, 环境: {self.environment}, Nacos: {'启用' if self.nacos_enabled else '未启用'}")

    def _load_env_by_environment(self):
        """根据环境变量加载对应的配置文件"""
        env = os.getenv("ENVIRONMENT", "development").lower()

        env_files = {
            "development": ".env.development",
            "production": ".env.production",
        }

        env_file = env_files.get(env, ".env")

        if os.path.exists(".env"):
            load_dotenv(".env")

        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
            logger.info(f"已加载环境配置: {env_file}")

    def _create_nacos_client(self):
        """创建 Nacos 客户端实例"""
        try:
            from nacos import NacosClient

            server_addresses = os.getenv("NACOS_SERVER_ADDRESSES")
            namespace = os.getenv("NACOS_NAMESPACE", "public")
            username = os.getenv("NACOS_USERNAME")
            password = os.getenv("NACOS_PASSWORD")

            if not server_addresses:
                logger.warning("NACOS_SERVER_ADDRESSES 未配置")
                return None

            client_kwargs = {
                "server_addresses": server_addresses,
                "namespace": namespace,
            }
            if username and password:
                client_kwargs["username"] = username
                client_kwargs["password"] = password

            client = NacosClient(**client_kwargs)
            logger.info(f"Nacos 客户端已创建: {server_addresses}")
            return client

        except ImportError:
            logger.warning("未安装 nacos-sdk-python，使用本地配置")
            return None
        except Exception as e:
            logger.error(f"创建 Nacos 客户端失败: {e}")
            return None

    def _load_from_nacos_with_client(self, client):
        """使用已有客户端从 Nacos 加载配置"""
        try:
            data_id = os.getenv("NACOS_CONFIG_DATA_ID")
            group = os.getenv("NACOS_CONFIG_GROUP", "DEFAULT_GROUP")

            if not data_id:
                logger.warning("NACOS_CONFIG_DATA_ID 未配置，跳过配置加载")
                return

            config_content = client.get_config(data_id, group)

            if config_content:
                self._parse_nacos_config(config_content)
                logger.info(f"已从 Nacos 加载配置: {data_id}/{group}")
            else:
                logger.warning("Nacos 配置为空，使用本地配置")

        except Exception as e:
            logger.error(f"从 Nacos 加载配置失败: {e}")

    def register_service(self):
        """向 Nacos 注册服务实例（由 lifespan 启动阶段调用）"""
        if not self._nacos_client:
            return
        try:
            import socket

            service_name = os.getenv("NACOS_SERVICE_NAME", "lifehubai")
            service_port = self.get_int("FASTAPI_PORT", 8000)
            group = os.getenv("NACOS_CONFIG_GROUP", "DEFAULT_GROUP")

            service_ip = os.getenv("NACOS_SERVICE_IP", "")
            if not service_ip:
                try:
                    service_ip = socket.gethostbyname(socket.gethostname())
                except Exception:
                    service_ip = "127.0.0.1"

            logger.info(f"注册服务: {service_name} ({service_ip}:{service_port})")

            self._service_info = {
                "service_name": service_name,
                "ip": service_ip,
                "port": service_port,
                "group": group,
            }

            self._nacos_client.add_naming_instance(
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
            logger.info(f"已注册到 Nacos: {service_name} ({service_ip}:{service_port})")

            self._heartbeat_running = True

            def heartbeat_loop():
                import time
                while self._heartbeat_running:
                    try:
                        self._nacos_client.send_heartbeat(
                            service_name,
                            service_ip,
                            service_port,
                            group_name=group,
                        )
                    except Exception as e:
                        logger.warning(f"Nacos 心跳发送失败: {e}")
                    time.sleep(5)

            heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True, name="nacos-heartbeat")
            heartbeat_thread.start()

        except Exception as e:
            logger.error(f"Nacos 服务注册失败: {e}")

    def deregister_service(self):
        """从 Nacos 注销服务实例"""
        self._heartbeat_running = False

        if not self._nacos_client:
            return
        try:
            if not self._service_info:
                return

            self._nacos_client.remove_naming_instance(
                self._service_info["service_name"],
                self._service_info["ip"],
                self._service_info["port"],
                group_name=self._service_info["group"],
            )
            logger.info(f"已从 Nacos 注销服务: {self._service_info['service_name']}")

        except Exception as e:
            logger.error(f"Nacos 服务注销失败: {e}")

    def _parse_nacos_config(self, config_content: str):
        """
        解析 Nacos 配置内容并更新环境变量（仅允许白名单内的 key）
        """
        import json

        def _apply(key: str, value: str):
            key = key.strip().upper()
            if key in _ALLOWED_NACOS_KEYS:
                os.environ[key] = value
            else:
                logger.debug(f"Nacos 配置忽略非白名单 key: {key}")

        if config_content.strip().startswith("{"):
            try:
                config_dict = json.loads(config_content)
                for key, value in config_dict.items():
                    if isinstance(value, (str, int, float, bool)):
                        _apply(key, str(value))
                return
            except json.JSONDecodeError:
                pass

        for line in config_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                value = value.strip()
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                _apply(key, value)

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
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

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

    def get_codegen_config(self) -> Dict[str, Any]:
        """获取代码生成配置"""
        return {
            "output_dir": self.get("CODE_OUTPUT_DIR", "./output"),
            "package_prefix": self.get("CODE_PACKAGE_PREFIX", "com.xhn"),
        }


# 全局配置实例 + 线程安全锁
_config: Optional[Config] = None
_config_lock = threading.Lock()


def get_config(env_file: Optional[str] = None) -> Config:
    """获取配置实例（线程安全单例）"""
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:
                _config = Config(env_file)
    return _config


def reload_config(env_file: Optional[str] = None):
    """重新加载配置"""
    global _config
    with _config_lock:
        _config = Config(env_file)


def get_setting(key: str, default: Any = None) -> Any:
    """快速获取配置值"""
    return get_config().get(key, default)
