# gRPC Server Integration - Setup Guide

This guide covers the gRPC server integration for LifeHubAI.

## Prerequisites

### Platform-Specific Requirements

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y python3-dev build-essential libgrpc-dev
```

**macOS:**
```bash
xcode-select --install
```

**Windows:**
- Requires Visual Studio 2015 or later with C++ build tools
- Download from: https://visualstudio.microsoft.com/downloads/
- Select "Desktop development with C++" workload

OR install pre-built wheels (recommended):
```bash
pip install grpcio==1.48.2 --only-binary grpcio
```

## Installation

### Step 1: Install Dependencies

**For Python 3.8+ (Recommended):**
```bash
pip install grpcio>=1.60.0 grpcio-tools>=1.60.0 protobuf>=4.25.0
```

**For Python 3.7 or Windows 32-bit:**
```bash
# Use older version with pre-built wheels
pip install grpcio==1.48.2 grpcio-tools==1.48.2 protobuf
```

### Step 2: Generate gRPC Code

```bash
python scripts/generate_grpc.py
```

This compiles `.proto` files in `protos/` to Python modules in `generated/`.

Expected output:
```
Found 1 .proto file(s):
  - health.proto

Compiling health.proto...
✓ Successfully compiled health.proto

Generated files in generated/:
  - health_pb2.py
  - health_pb2_grpc.py

✓ Successfully compiled 1/1 file(s)
```

## Configuration

Add to your `.env` file:

```env
# gRPC Server Configuration
GRPC_SERVER_HOST=0.0.0.0
GRPC_SERVER_PORT=50051
GRPC_MAX_WORKERS=10
GRPC_ENABLED=true

# FastAPI Server Configuration
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
```

## Running the Servers

### Development Mode (FastAPI only with auto-reload)
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode (Both FastAPI and gRPC)
```bash
python main_dual.py
```

Expected output:
```
============================================================
LifeHubAI Dual Server Mode
============================================================
gRPC server is enabled, starting in background thread...
Starting gRPC server (non-blocking)...
gRPC server configured on 0.0.0.0:50051
gRPC server started on 0.0.0.0:50051
✓ gRPC server thread started successfully
Starting FastAPI server in main thread...
============================================================
Starting FastAPI server on 0.0.0.0:8000...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Standalone gRPC Server
```bash
python -m grpc.server
```

## Testing

### Test HTTP Endpoint
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "servers": {
    "http": "running",
    "grpc": "running"
  },
  "services": {
    "code_generation": "/api/codegen/health",
    "text_to_speech": "/api/tts/health"
  },
  "grpc_endpoint": "localhost:50051"
}
```

### Test gRPC Endpoint
```bash
python test_grpc.py
```

Expected output:
```
============================================================
LifeHubAI gRPC Health Service Test Suite
============================================================

============================================================
Testing Overall Health Check
============================================================
Calling Health.Check() on localhost:50051...
✓ Status: healthy
✓ Version: 1.0.0
✓ Timestamp: 1706745600 (Mon Jan 31 2025)

============================================================
Testing CODE_GENERATION Service Health Check
============================================================
Calling Health.CheckService(service_name='code_generation')...
✓ Status: healthy
✓ Database Connected: True
✓ Message: Code generation service is operational

... (additional tests)

============================================================
Test Summary
============================================================
✓ PASS: Overall Health Check
✓ PASS: Code Generation Service
✓ PASS: TTS Service
✓ PASS: Database Service
✓ PASS: Error Handling

All tests passed!
```

## Troubleshooting

### Issue: grpcio installation fails with compilation errors

**Solution 1:** Use pre-built wheels
```bash
pip install grpcio --only-binary grpcio
```

**Solution 2:** Install platform-specific build tools
- Linux: `python3-dev build-essential libgrpc-dev`
- macOS: `xcode-select --install`
- Windows: Visual Studio Build Tools

**Solution 3:** Use conda (recommended for Windows)
```bash
conda install -c conda-forge grpcio grpcio-tools protobuf
```

### Issue: "ModuleNotFoundError: No module named 'grpc'"

**Solution:** Ensure you're using the correct Python environment
```bash
# Check which Python you're using
python --version
which python

# Install in the correct environment
pip install grpcio grpcio-tools protobuf
```

### Issue: gRPC server fails to start

**Solution:** Check if port is already in use
```bash
# Linux/Mac
lsof -i :50051

# Windows
netstat -ano | findstr :50051
```

Change port in `.env`:
```env
GRPC_SERVER_PORT=50052
```

### Issue: Generated protobuf files are missing

**Solution:** Regenerate gRPC code
```bash
python scripts/generate_grpc.py
```

Verify files exist:
```bash
ls -la generated/
# Should see: health_pb2.py, health_pb2_grpc.py
```

## Architecture

### Directory Structure
```
LifeHubAI/
├── protos/                    # Protocol Buffer definitions
│   └── health.proto          # Health check service
├── grpc/                      # gRPC server implementation
│   ├── server.py             # Server setup
│   └── services/
│       └── health_service.py # Service implementation
├── generated/                 # Generated Python from protos
│   ├── health_pb2.py         # Message classes
│   └── health_pb2_grpc.py    # Service stub/servicer
├── scripts/
│   └── generate_grpc.py      # Proto compilation script
├── main.py                    # FastAPI app (dev mode)
├── main_dual.py              # Dual server launcher (prod)
└── test_grpc.py              # gRPC test client
```

### Service Communication Flow

```
┌─────────────────┐
│   FastAPI       │  HTTP (Port 8000)
│   (main.py)     │  ←→ Web Clients
└────────┬────────┘
         │
         │ Shared Services
         ▼
    ┌─────────────────┐
    │  CodegenService │
    │  TtsService     │
    └────────┬────────┘
             │
    ┌────────▼────────┐
    │  gRPC Server    │  gRPC (Port 50051)
    │  (grpc/server)  │  ←→ Java/Spring Boot clients
    └─────────────────┘
```

## Future Enhancements

After basic setup is verified:
1. Add code generation service to gRPC
2. Add TTS service to gRPC
3. Implement authentication/authorization interceptors
4. Add TLS support for secure connections
5. Add service reflection for debugging
6. Add streaming endpoints for TTS

## Additional Resources

- [gRPC Python Quick Start](https://grpc.io/docs/languages/python/quickstart/)
- [Protocol Buffers Basics](https://protobuf.dev/programming-guides/proto3/)
- [gRPC Python Documentation](https://grpc.github.io/grpc/python/)
