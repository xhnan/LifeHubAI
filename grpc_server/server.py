import os
import grpc
from concurrent import futures
from generated import health_pb2_grpc
from grpc_server.services.health_service import HealthService


class GRPCServer:
    def __init__(self, host="0.0.0.0", port=50051):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        health_pb2_grpc.add_HealthServicer_to_server(HealthService(), self.server)
        self.server.add_insecure_port(f"{host}:{port}")

    def start(self):
        self.server.start()
        print(f"gRPC服务器启动在端口 50051")
        self.server.wait_for_termination()