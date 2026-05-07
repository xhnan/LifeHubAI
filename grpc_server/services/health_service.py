import grpc
import time
from generated import health_pb2
from generated.health_pb2_grpc import HealthServicer


class HealthService(HealthServicer):
    def Check(self, request, context):
        return health_pb2.HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=int(time.time())
        )

    def Ping(self, request, context):
        return health_pb2.PingResponse(message="pong")
