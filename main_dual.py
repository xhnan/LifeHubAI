"""Dual server launcher for FastAPI and gRPC."""

import os
import sys
import threading
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from grpc.server import GRPCServer, is_grpc_enabled

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_grpc_server():
    """Run gRPC server in a background thread."""
    try:
        logger.info("Starting gRPC server thread...")

        grpc_server = GRPCServer()
        grpc_server.start()  # This blocks

    except Exception as e:
        logger.error(f"gRPC server error: {e}", exc_info=True)


def run_fastapi_server():
    """Run FastAPI server."""
    try:
        host = os.getenv("FASTAPI_HOST", "0.0.0.0")
        port = int(os.getenv("FASTAPI_PORT", "8000"))

        logger.info(f"Starting FastAPI server on {host}:{port}...")

        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=False,  # No reload in production dual-server mode
            log_level="info",
        )

    except Exception as e:
        logger.error(f"FastAPI server error: {e}", exc_info=True)


def run_dual_servers():
    """Run both FastAPI and gRPC servers concurrently."""
    logger.info("=" * 60)
    logger.info("LifeHubAI Dual Server Mode")
    logger.info("=" * 60)

    # Start gRPC server in background thread
    grpc_thread = None
    if is_grpc_enabled():
        logger.info("gRPC server is enabled, starting in background thread...")
        grpc_thread = threading.Thread(
            target=run_grpc_server,
            name="GRPCServer",
            daemon=True,  # Daemon thread will exit when main thread exits
        )
        grpc_thread.start()

        # Wait a moment for gRPC to start
        time.sleep(1)

        if grpc_thread.is_alive():
            logger.info("✓ gRPC server thread started successfully")
        else:
            logger.warning("gRPC server thread failed to start")
    else:
        logger.info("gRPC server is disabled via GRPC_ENABLED environment variable")

    # Start FastAPI server in main thread (blocking)
    logger.info("Starting FastAPI server in main thread...")
    logger.info("=" * 60)

    try:
        run_fastapi_server()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        logger.info("Servers stopped")


if __name__ == "__main__":
    run_dual_servers()
