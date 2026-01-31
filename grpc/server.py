"""gRPC server setup and configuration."""

import os
import sys
import signal
import logging
from concurrent import futures
from pathlib import Path
from typing import Optional

import grpc

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import generated protobuf classes
from generated import health_pb2_grpc
from grpc.services.health_service import HealthService

# Configure logging
logger = logging.getLogger(__name__)


class GRPCServer:
    """gRPC server for LifeHubAI."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize gRPC server.

        Args:
            host: Server host address (default from env or 0.0.0.0)
            port: Server port (default from env or 50051)
            max_workers: Maximum number of worker threads (default from env or 10)
        """
        self.host = host or os.getenv("GRPC_SERVER_HOST", "0.0.0.0")
        self.port = port or int(os.getenv("GRPC_SERVER_PORT", "50051"))
        self.max_workers = max_workers or int(os.getenv("GRPC_MAX_WORKERS", "10"))

        self.server: Optional[grpc.Server] = None

    def _create_server(self) -> grpc.Server:
        """
        Create and configure gRPC server.

        Returns:
            Configured grpc.Server instance
        """
        # Create thread pool executor
        thread_pool = futures.ThreadPoolExecutor(max_workers=self.max_workers)

        # Create gRPC server
        server = grpc.server(thread_pool)

        # Register health service
        health_service = HealthService()
        health_pb2_grpc.add_HealthServicer_to_server(health_service, server)

        # Configure server port
        server_address = f"{self.host}:{self.port}"
        server.add_insecure_port(server_address)

        logger.info(f"gRPC server configured on {server_address}")

        return server

    def start(self):
        """
        Start gRPC server (blocking).

        This method blocks until the server is stopped.
        Use start_non_blocking() for non-blocking operation.
        """
        logger.info("Starting gRPC server...")

        self.server = self._create_server()
        self.server.start()

        logger.info(f"gRPC server started on {self.host}:{self.port}")

        # Setup signal handlers for graceful shutdown
        def handle_shutdown(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        # Wait for termination
        try:
            self.server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.stop()

    def start_non_blocking(self):
        """
        Start gRPC server in a non-blocking manner.

        This method returns immediately after starting the server.
        The server runs in the background.
        """
        logger.info("Starting gRPC server (non-blocking)...")

        self.server = self._create_server()
        self.server.start()

        logger.info(f"gRPC server started on {self.host}:{self.port}")

    def stop(self, grace_period: int = 5):
        """
        Stop gRPC server gracefully.

        Args:
            grace_period: Grace period in seconds for existing RPCs to complete
        """
        if self.server is not None:
            logger.info(f"Stopping gRPC server (grace period: {grace_period}s)...")
            self.server.stop(grace_period)
            logger.info("gRPC server stopped")
        else:
            logger.warning("Attempted to stop gRPC server, but it was not running")


def is_grpc_enabled() -> bool:
    """
    Check if gRPC server is enabled via environment variable.

    Returns:
        True if gRPC should be started, False otherwise
    """
    enabled = os.getenv("GRPC_ENABLED", "true").lower()
    return enabled in ("true", "1", "yes", "on")


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Check if gRPC is enabled
    if not is_grpc_enabled():
        print("gRPC server is disabled via GRPC_ENABLED environment variable")
        sys.exit(0)

    # Create and start server
    server = GRPCServer()
    server.start()
