import subprocess
import sys
import re
from pathlib import Path

# grpc/scripts/generate_grpc.py -> project_root = grpc/
# But protos are at project root, so we need parent.parent
grpc_root = Path(__file__).parent.parent
project_root = grpc_root.parent
protos_dir = project_root / "protos"
generated_dir = project_root / "generated"

# Create generated directory
generated_dir.mkdir(exist_ok=True)

# 获取所有 proto 文件
proto_files = list(protos_dir.glob("*.proto"))

if not proto_files:
    print("没有找到 .proto 文件")
    sys.exit(1)

print(f"找到 {len(proto_files)} 个 proto 文件")

# 为每个 proto 文件生成代码
for proto_file in proto_files:
    cmd = [
        sys.executable, "-m", "grpc_tools.protoc",
        f"-I{protos_dir}",
        f"--python_out={generated_dir}",
        f"--grpc_python_out={generated_dir}",
        str(proto_file),
    ]
    print(f"正在生成: {proto_file.name}")
    subprocess.run(cmd, check=True)

print("\ngRPC代码生成完成，正在修复 import 路径...")

# 修复生成文件中的 import 路径
fix_pattern = re.compile(r'^import (\w+_pb2)')
grpc_fix_pattern = re.compile(r'^import (\w+_pb2_grpc)')

for py_file in generated_dir.glob("*.py"):
    if py_file.name == "__init__.py":
        continue

    print(f"  修复: {py_file.name}")
    with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复普通 import
    content = fix_pattern.sub(r'import generated.\1', content)

    # 修复 grpc import
    content = grpc_fix_pattern.sub(r'from generated import \1', content)

    # 写回文件
    with open(py_file, 'w', encoding='utf-8') as f:
        f.write(content)

print("✓ Import 路径修复完成")
