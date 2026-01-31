"""Health check gRPC service implementation."""

import time
from typing import Optional

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

# Import generated protobuf classes
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from generated import health_pb2
from generated.health_pb2_grpc import HealthServicer

# Import existing services
from services.codegen_service import CodegenService
from services.tts_service import TtsService


class HealthService(HealthServicer):
    """Health check service implementation."""

    def __init__(self):
        """Initialize health service with existing service instances."""
        self.codegen_service = CodegenService()
        self.tts_service = TtsService()

    def Check(self, request, context) -> health_pb2.HealthResponse:
        """
        Check overall system health.

        Args:
            request: Empty request
            context: gRPC context

        Returns:
            HealthResponse with status, version, and timestamp
        """
        try:
            # Get current timestamp
            timestamp = int(time.time())

            # Build response
            response = health_pb2.HealthResponse(
                status="healthy",
                version="1.0.0",
                timestamp=timestamp,
            )

            return response

        except Exception as e:
            # Return unhealthy status on error
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Health check failed: {str(e)}")
            return health_pb2.HealthResponse(
                status="unhealthy",
                version="1.0.0",
                timestamp=int(time.time()),
            )

    def CheckService(self, request, context) -> health_pb2.ServiceHealthResponse:
        """
        Check health of a specific service.

        Args:
            request: ServiceRequest with service_name
            context: gRPC context

        Returns:
            ServiceHealthResponse with service-specific health information
        """
        service_name = request.service_name.lower()

        try:
            if service_name in ["code_generation", "codegen", "code_generation_service"]:
                return self._check_codegen_service()
            elif service_name in ["text_to_speech", "tts", "tts_service"]:
                return self._check_tts_service()
            elif service_name in ["database", "db"]:
                return self._check_database_service()
            else:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Unknown service: {service_name}")
                return health_pb2.ServiceHealthResponse(
                    status="unknown",
                    database_connected=False,
                    message=f"Service '{service_name}' not found",
                )

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Service health check failed: {str(e)}")
            return health_pb2.ServiceHealthResponse(
                status="unhealthy",
                database_connected=False,
                message=f"Error: {str(e)}",
            )

    def _check_codegen_service(self) -> health_pb2.ServiceHealthResponse:
        """Check code generation service health."""
        try:
            # Use existing service health check
            health_info = self.codegen_service.get_health_info()

            return health_pb2.ServiceHealthResponse(
                status="healthy" if health_info["database_connected"] else "unhealthy",
                database_connected=health_info["database_connected"],
                message="Code generation service is operational",
            )
        except Exception as e:
            return health_pb2.ServiceHealthResponse(
                status="unhealthy",
                database_connected=False,
                message=f"Code generation service error: {str(e)}",
            )

    def _check_tts_service(self) -> health_pb2.ServiceHealthResponse:
        """Check TTS service health."""
        try:
            # Use existing service health check
            health_info = self.tts_service.get_health_info()

            return health_pb2.ServiceHealthResponse(
                status="healthy",
                database_connected=False,  # TTS doesn't use database
                message="Text-to-speech service is operational",
            )
        except Exception as e:
            return health_pb2.ServiceHealthResponse(
                status="unhealthy",
                database_connected=False,
                message=f"TTS service error: {str(e)}",
            )

    def _check_database_service(self) -> health_pb2.ServiceHealthResponse:
        """Check database service health."""
        try:
            # Use codegen service to check database
            health_info = self.codegen_service.get_health_info()

            return health_pb2.ServiceHealthResponse(
                status="healthy" if health_info["database_connected"] else "unhealthy",
                database_connected=health_info["database_connected"],
                message="Database connection is operational" if health_info["database_connected"] else "Database connection failed",
            )
        except Exception as e:
            return health_pb2.ServiceHealthResponse(
                status="unhealthy",
                database_connected=False,
                message=f"Database service error: {str(e)}",
            )
