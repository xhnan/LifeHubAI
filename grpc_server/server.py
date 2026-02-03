import os
import grpc
from concurrent import futures
from generated import health_pb2_grpc, codegen_pb2_grpc
from grpc_server.services.health_service import HealthService
from grpc_server.services.codegen_service import CodeGenerationService


class GRPCServer:
    def __init__(self, host="0.0.0.0", port=50051):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

        # 注册 Health 服务
        health_pb2_grpc.add_HealthServicer_to_server(HealthService(), self.server)
        print("✓ Health 服务已注册")

        # 注册 CodeGeneration 服务
        codegen_pb2_grpc.add_CodeGenerationServicer_to_server(CodeGenerationService(), self.server)
        print("✓ CodeGeneration 服务已注册")

        self.server.add_insecure_port(f"{host}:{port}")
        self.host = host
        self.port = port

    def start(self):
        print(f"\ngRPC 服务器启动在 {self.host}:{self.port}")
        print("=" * 50)
        print("已注册的服务:")
        print("  - lifehub.Health (健康检查)")
        print("  - lifehub.CodeGeneration (代码生成)")
        print("=" * 50)
        self.server.start()
        self.server.wait_for_termination()


if __name__ == "__main__":
    server = GRPCServer()
    server.start()
