import threading
import uvicorn
from grpc_server.server import GRPCServer


def run_grpc():
    server = GRPCServer()
    server.start()


def run_fastapi():
    uvicorn.run("main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    grpc_thread = threading.Thread(target=run_grpc, daemon=True)
    grpc_thread.start()
    run_fastapi()