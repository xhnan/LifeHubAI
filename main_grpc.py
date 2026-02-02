from grpc_server.server import GRPCServer
if __name__ == "__main__":
    server = GRPCServer()
    server.start()