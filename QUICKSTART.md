# Quick Start: gRPC Server Integration

Get the gRPC server up and running in 5 minutes.

## Prerequisites

- Python 3.7+ (3.8+ recommended)
- pip package manager

## Installation (Choose One)

### Option 1: Automated (Recommended)

**Windows:**
```cmd
scripts\install_grpc.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/install_grpc.sh
bash scripts/install_grpc.sh
```

### Option 2: Manual

**For Python 3.8+:**
```bash
pip install grpcio grpcio-tools protobuf
```

**For Python 3.7 or Windows (use pre-built wheels):**
```bash
pip install grpcio --only-binary grpcio
pip install grpcio-tools protobuf
```

## Setup

### 1. Generate gRPC Code
```bash
python scripts/generate_grpc.py
```

Expected output:
```
Found 1 .proto file(s):
  - health.proto
✓ Successfully compiled health.proto
```

### 2. Configure Environment

Copy example environment file:
```bash
cp .env.example .env
```

Edit `.env` if needed (defaults are fine for local development):
```env
GRPC_SERVER_PORT=50051
FASTAPI_PORT=8000
```

## Run

### Development Mode (FastAPI only)
```bash
uvicorn main:app --reload
```

### Production Mode (Both FastAPI + gRPC)
```bash
python main_dual.py
```

You should see:
```
============================================================
LifeHubAI Dual Server Mode
============================================================
✓ gRPC server thread started successfully
✓ gRPC server started on 0.0.0.0:50051
INFO: Uvicorn running on http://0.0.0.0:8000
```

## Test

### Test HTTP Endpoint
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "servers": {
    "http": "running",
    "grpc": "running"
  }
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
✓ PASS: Overall Health Check
✓ PASS: Code Generation Service
✓ PASS: TTS Service
✓ PASS: Database Service
✓ PASS: Error Handling

All tests passed!
```

## Verify

Check that both ports are listening:

**Linux/Mac:**
```bash
lsof -i :8000  # FastAPI
lsof -i :50051  # gRPC
```

**Windows:**
```cmd
netstat -ano | findstr :8000
netstat -ano | findstr :50051
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'grpc'"
**Solution:** Install dependencies again
```bash
pip install grpcio grpcio-tools protobuf
```

### "Compilation failed" error
**Solution:** Use pre-built wheels (Windows)
```cmd
pip install grpcio --only-binary grpcio
```

### Port already in use
**Solution:** Change port in `.env`
```env
GRPC_SERVER_PORT=50052
```

### Generated files missing
**Solution:** Regenerate gRPC code
```bash
python scripts/generate_grpc.py
```

## Next Steps

- Read [GRPC_README.md](GRPC_README.md) for detailed documentation
- Read [CLAUDE.md](CLAUDE.md) for architecture details
- Explore `grpc/services/` to add new services
- Run `python test_grpc.py` to see example usage

## What's Running?

After starting `main_dual.py`:

- **FastAPI (HTTP)**: http://localhost:8000
  - REST API for web clients
  - Interactive docs: http://localhost:8000/docs

- **gRPC Server**: localhost:50051
  - High-performance RPC for service-to-service communication
  - Test with: `python test_grpc.py`

## Support

For detailed troubleshooting, see [GRPC_README.md](GRPC_README.md).

For implementation details, see [GRPC_IMPLEMENTATION_SUMMARY.md](GRPC_IMPLEMENTATION_SUMMARY.md).
