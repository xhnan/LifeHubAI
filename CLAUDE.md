# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LifeHubAI is an AI-powered backend code generation tool that automatically creates complete Java Spring Boot applications from PostgreSQL database schemas. The project uses DeepSeek LLM to generate production-ready code following MyBatis Plus and Spring Boot conventions.

## Environment Setup

This project uses a Conda environment for dependency management.

```bash
# Activate the development environment
conda activate lifehubai310
```

The `lifehubai310` environment includes Python 3.10 and all required dependencies.

## Development Commands

### Run the FastAPI Server
```bash
# Development with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the start script
./start.sh          # Linux/Mac
start.bat           # Windows
```

### Generate Java Code from Database
```bash
python Generate/JavaCodeGenerate.py
```
Requires `.env` file with database connection details.

### Test Text-to-Speech
```bash
# Static WAV file generation
python audio/demo.py

# Real-time streaming with pygame playback
python audio/glmtts.py
```

### Run API Tests
```bash
python test_api.py
```

### gRPC Server Setup

**Note**: gRPC dependencies require compilation from source. For best results, use Python 3.8+ with proper build tools.

```bash
# Install gRPC dependencies
pip install grpcio>=1.60.0 grpcio-tools>=1.60.0 protobuf>=4.25.0

# Generate Python code from .proto files
python scripts/generate_grpc.py
```

**Platform-specific notes:**
- **Windows**: Requires Visual Studio C++ build tools for grpcio compilation
- **Linux**: Requires `python3-dev`, `build-essential`, and `libgrpc-dev`
- **macOS**: Requires Xcode command line tools

If compilation fails, pre-compiled wheels are available from PyPI for most platforms.

### Run gRPC Server

```bash
# Run both FastAPI and gRPC servers (production mode)
python main_dual.py

# Or run gRPC server standalone
python -m grpc.server
```

### Test gRPC Services
```bash
python test_grpc.py
```

### Docker Deployment
```bash
# Build image
docker build -t lifehubai .

# Run container
docker run -p 8000:8000 --env-file .env lifehubai
```

## Architecture

### Database-First Code Generation

The code generation flow:
1. **Connect** to PostgreSQL using credentials from `.env`
2. **Analyze Schema** - list tables matching prefix pattern (configured in `Generate/config.yaml`)
3. **Generate Code** - use DeepSeek LLM API to create complete Java CRUD layers
4. **Write Files** - atomic file operations to prevent corruption

### Code Generation Layers

For each database table, generates:
- **Entity**: `Base{Table}.java` (base) + `{Table}.java` (Lombok implementation)
- **Mapper**: `{Table}Mapper.java` (MyBatis Plus interface)
- **Service**: `{Table}Service.java` + `{Table}ServiceImpl.java`
- **Controller**: `{Table}Controller.java` (REST endpoints)
- **MyBatis XML**: Mapper configuration

Package structure: `com.xhn.{module_name}.{table_suffix}.{layer}`
- `module_name`: from `config.yaml` (e.g., "sys")
- `table_suffix`: table name with prefix removed (e.g., "menu" from "sys_menu")

### FastAPI Application Structure

```
LifeHubAI/
├── main.py              # FastAPI application entry point
├── main_dual.py         # Dual server launcher (FastAPI + gRPC)
├── routers/             # API route handlers
│   ├── codegen.py       # Code generation endpoints
│   └── tts.py           # Text-to-speech endpoints
├── services/            # Business logic layer
│   ├── codegen_service.py
│   └── tts_service.py
├── schemas/             # Pydantic data models
│   ├── codegen.py
│   └── tts.py
├── Generate/            # Java code generation module
├── audio/               # TTS module (Zhipu AI GLM-TTS)
├── protos/              # Protocol Buffer definitions
│   └── health.proto     # Health check service definition
├── grpc/                # gRPC server and services
│   ├── server.py        # gRPC server setup
│   └── services/
│       └── health_service.py  # Health check implementation
├── generated/           # Generated Python code from protos
├── scripts/
│   └── generate_grpc.py # Proto compilation script
├── test_api.py          # HTTP API test client
└── test_grpc.py         # gRPC test client
```

### Layer Separation

- **Routers**: HTTP request/response handling, validation via Pydantic schemas
- **Services**: Business logic, calls into Generate/ and audio/ modules
- **Schemas**: Request/response data models with validation

## Configuration

### Environment Variables (`.env`)
```
# Database Configuration
DB_HOST=<host>          # PostgreSQL host
DB_PORT=<port>          # PostgreSQL port
DB_NAME=<database>      # Database name
DB_USER=<username>      # Database user
DB_PASSWORD=<password>  # Database password

# AI Configuration
AI_BASE_URL=<url>       # DeepSeek API endpoint
API_KEY=<key>           # DeepSeek API key

# Zhipu AI TTS Configuration
ZHIPU_API_KEY=<key>     # Zhipu AI API key (for TTS)

# gRPC Server Configuration
GRPC_SERVER_HOST=0.0.0.0
GRPC_SERVER_PORT=50051
GRPC_MAX_WORKERS=10
GRPC_ENABLED=true

# FastAPI Server Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
```

### Code Generation Config (`Generate/config.yaml`)
```yaml
module_name: sys              # Module name for package structure
project_root: <path>          # Where generated Java code is written
ai_prompts:
  content: "<prompt>"         # Custom prompt for code generation
allowed_tables: False         # If False, uses all tables matching prefix
table_name:
  - sys_menu                  # Used as prefix filter when allowed_tables: False
```

When `allowed_tables: False`, entries in `table_name` act as **prefix filters**. For example, `sys_menu` matches all tables starting with `sys_menu`.

## Key Implementation Details

### Atomic File Operations (`Generate/file_utils.py`)

The code generation uses atomic writes to prevent corruption:
- `write_overwrite_atomic()` - safely update existing files
- `write_if_not_exists()` - create new files without overwriting
- `extract_java_code()` - extract Java from LLM markdown responses

Atomic operations use temporary files in the same directory to ensure cross-device atomic replacement.

### TTS Configuration (Zhipu AI GLM-TTS)
- `model`: 'glm-tts'
- `voice`: 'female' or 'male'
- `speed`: 0.5-2.0 (default 1.0)
- `volume`: 0.1-1.0 (default 1.0)
- Audio format: PCM, 24000Hz, mono, 16-bit

### API Endpoints

**Code Generation:**
- `GET /` - API info
- `GET /health` - Overall health check
- `GET /api/codegen/health` - Codegen service health
- `GET /api/codegen/database` - Database information
- `GET /api/codegen/tables?prefix=xxx` - List tables
- `GET /api/codegen/generate` - Generate code for all tables
- `POST /api/codegen/generate` - Generate code for specific tables

**Text-to-Speech:**
- `GET /api/tts/health` - TTS service health
- `POST /api/tts/speak` - Generate TTS audio (JSON response)
- `POST /api/tts/generate` - Generate TTS audio (file download)

**gRPC Services (Port 50051):**

`lifehub.Health` service:
- `Check()` - Overall system health
- `CheckService(service_name)` - Service-specific health checks

Service names for `CheckService()`:
- `code_generation` - Code generation service health
- `text_to_speech` / `tts` - TTS service health
- `database` / `db` - Database connection health

Example gRPC usage (Python):
```python
import grpc
from generated import health_pb2, health_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = health_pb2_grpc.HealthStub(channel)

# Overall health check
response = stub.Check(health_pb2.Empty())
print(f"Status: {response.status}")

# Service-specific check
request = health_pb2.ServiceRequest(service_name="code_generation")
response = stub.CheckService(request)
print(f"Service status: {response.status}")
```

## gRPC Architecture

LifeHubAI uses an **in-process multi-server architecture**:

- **FastAPI (HTTP)** on port 8000 - REST API for web clients
- **gRPC server** on port 50051 - High-performance RPC for service-to-service communication
- **Shared service layer** - Business logic reused between HTTP and gRPC

Both servers run concurrently in a single process when using `main_dual.py`.

### gRPC Design Decisions

**Why In-Process Architecture?**
- Simpler deployment (single process)
- Shared service layer between HTTP and gRPC
- Lower resource footprint
- Easier debugging and monitoring

**Why Health Service First?**
- Simple, non-controversial starting point
- Demonstrates gRPC setup without business logic complexity
- Provides foundation for future services
- Reuses existing service health check patterns

## Important Notes

- **Database**: Uses `psycopg2-binary` for PostgreSQL connectivity
- **Primary Keys**: Automatically detected from schema and used in generated entities
- **CORS**: Currently allows all origins - restrict in production
- **Project Root**: Generated Java code writes to a separate project directory (configured in `config.yaml`), not in LifeHubAI itself
- **Table Naming**: Tables expected to have prefix pattern (e.g., `sys_*`) which is stripped for package naming
- **gRPC Dependencies**: grpcio requires C++ build tools for compilation. Pre-built wheels recommended for Windows

