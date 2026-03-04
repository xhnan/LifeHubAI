# 环境配置管理说明

## 概述

本项目支持多环境配置管理，可以实现：
- **开发环境**：使用本地 `.env.development` 文件，不接入 Nacos
- **生产环境**：接入 Nacos 配置中心，从 Nacos 动态获取配置

## 快速开始

### 1. 安装依赖

```bash
# 开发环境（不需要 Nacos）
pip install -r requirements.txt

# 生产环境（需要 Nacos）
pip install -r requirements.txt
pip install nacos-sdk-python
```

### 2. 配置文件说明

```
.env                 # 基础配置（默认）
.env.development     # 开发环境配置（会覆盖基础配置）
.env.production      # 生产环境配置（会覆盖基础配置）
```

### 3. 启动方式

#### 方式一：使用环境启动脚本（推荐）

```bash
# 开发环境
python start_with_env.py --env development

# 生产环境
python start_with_env.py --env production
```

#### 方式二：通过环境变量

```bash
# Linux/Mac
export ENVIRONMENT=production
python main.py

# Windows
set ENVIRONMENT=production
python main.py
```

#### 方式三：指定配置文件

```python
from config import get_config

# 加载特定环境配置
config = get_config(env_file=".env.production")
```

## 配置使用示例

### 基本使用

```python
from config import get_config, get_setting

# 获取配置实例
config = get_config()

# 检查环境
if config.is_production():
    # 生产环境逻辑
    pass

# 获取配置值
api_key = config.get("DEEPSEEK_API_KEY")
port = config.get_int("DB_PORT", 5432)
enabled = config.get_bool("GRPC_ENABLED", False)

# 快捷函数
model = get_setting("LLM_MODEL")
```

### 获取结构化配置

```python
from config import get_config

config = get_config()

# 数据库配置
db_config = config.get_database_config()
# {
#     "host": "localhost",
#     "port": 5432,
#     "database": "LifeHub",
#     "user": "postgres",
#     "password": "password"
# }

# AI 配置
ai_config = config.get_ai_config()

# gRPC 配置
grpc_config = config.get_grpc_config()

# 代码生成配置
codegen_config = config.get_codegen_config()
```

## Nacos 配置

### 生产环境配置步骤

1. **在 .env.production 中配置 Nacos 连接信息**

```env
ENVIRONMENT=production
NACOS_ENABLED=true
NACOS_SERVER_ADDRESSES=127.0.0.1:8848
NACOS_NAMESPACE=public
NACOS_CONFIG_DATA_ID=lifehubai
NACOS_CONFIG_GROUP=DEFAULT_GROUP
```

2. **在 Nacos 控制台创建配置**

访问 Nacos 控制台：`http://your-nacos-server:8848/nacos`

创建配置：
- Data ID: `lifehubai`
- Group: `DEFAULT_GROUP`
- 配置格式：TEXT 或 JSON

**TEXT 格式示例：**
```properties
DB_HOST=production-db.example.com
DB_PORT=5432
DB_NAME=LifeHub
DB_USER=prod_user
DB_PASSWORD=prod_password
DEEPSEEK_API_KEY=your-production-key
DEEPSEEK_API_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

**JSON 格式示例：**
```json
{
  "DB_HOST": "production-db.example.com",
  "DB_PORT": 5432,
  "DB_NAME": "LifeHub",
  "DB_USER": "prod_user",
  "DB_PASSWORD": "prod_password",
  "DEEPSEEK_API_KEY": "your-production-key",
  "DEEPSEEK_API_URL": "https://api.deepseek.com/v1",
  "LLM_MODEL": "deepseek-chat"
}
```

3. **启动应用**

```bash
python start_with_env.py --env production
```

应用会自动从 Nacos 加载配置。

### Nacos 配置优先级

```
Nacos 配置 > .env.production > .env
```

## 环境变量说明

| 变量名 | 说明 | 开发环境 | 生产环境 |
|--------|------|----------|----------|
| `ENVIRONMENT` | 运行环境 | `development` | `production` |
| `NACOS_ENABLED` | 是否启用 Nacos | `false` | `true` |
| `NACOS_SERVER_ADDRESSES` | Nacos 服务器地址 | - | `127.0.0.1:8848` |
| `NACOS_NAMESPACE` | Nacos 命名空间 | - | `public` |
| `NACOS_CONFIG_DATA_ID` | 配置 Data ID | - | `lifehubai` |
| `NACOS_CONFIG_GROUP` | 配置分组 | - | `DEFAULT_GROUP` |

## 测试配置

运行配置示例：

```bash
python config/example_usage.py
```

## 迁移现有代码

### 旧代码（使用 dotenv）

```python
from dotenv import load_dotenv
import os

load_dotenv()
db_host = os.getenv("DB_HOST")
```

### 新代码（使用配置管理）

```python
from config import get_config

config = get_config()
db_host = config.get("DB_HOST")

# 或者使用快捷函数
db_config = config.get_database_config()
db_host = db_config["host"]
```

## 常见问题

### Q: 开发环境需要 Nacos 吗？
A: 不需要。开发环境设置 `NACOS_ENABLED=false`，只使用本地配置文件。

### Q: 如何在本地测试生产环境配置？
A:
```bash
# 设置环境变量
export ENVIRONMENT=production
export NACOS_ENABLED=true

# 启动应用
python start_with_env.py --env production
```

### Q: Nacos 连接失败会怎样？
A: 如果无法连接 Nacos，会自动回退到本地 `.env.production` 配置，不会影响应用启动。

### Q: 如何动态更新配置？
A: Nacos 支持配置动态刷新。需要在 Nacos 控制台修改配置后，应用重启即可生效。
