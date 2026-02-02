import subprocess
import sys
from pathlib import Path

# grpc/scripts/generate_grpc.py -> project_root = grpc/
# But protos are at project root, so we need parent.parent
grpc_root = Path(__file__).parent.parent
project_root = grpc_root.parent
protos_dir = project_root / "protos"
generated_dir = project_root / "generated"

# Create generated directory
generated_dir.mkdir(exist_ok=True)

cmd = [
    sys.executable, "-m", "grpc_tools.protoc",
    f"-I{protos_dir}",
    f"--python_out={generated_dir}",
    f"--grpc_python_out={generated_dir}",
    str(protos_dir / "health.proto"),
]
subprocess.run(cmd, check=True)
print("gRPC代码生成完成")
