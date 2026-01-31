#!/usr/bin/env python3
"""
Generate Python code from Protocol Buffer definitions.

This script compiles .proto files into Python modules using grpc_tools.protoc.
Run this script after modifying .proto files or when setting up the project.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from grpc_tools import protoc


def generate_grpc_code():
    """Compile .proto files to Python code."""

    proto_dir = project_root / "protos"
    generated_dir = project_root / "generated"

    # Ensure generated directory exists
    generated_dir.mkdir(exist_ok=True)

    # Find all .proto files
    proto_files = list(proto_dir.glob("*.proto"))

    if not proto_files:
        print(f"No .proto files found in {proto_dir}")
        return False

    print(f"Found {len(proto_files)} .proto file(s):")
    for proto_file in proto_files:
        print(f"  - {proto_file.name}")

    # Build protoc command
    proto_include = protoc.__path__[0] + "/_proto"
    proto_import_paths = [
        str(proto_dir),
        proto_include,
    ]

    # Compile each .proto file
    success_count = 0
    for proto_file in proto_files:
        print(f"\nCompiling {proto_file.name}...")

        proto_path = str(proto_file)
        command = [
            "grpc_tools.protoc",
            f"--proto_path={','.join(proto_import_paths)}",
            f"--python_out={generated_dir}",
            f"--grpc_python_out={generated_dir}",
            proto_path,
        ]

        # Join arguments for protoc
        protoc_args = []
        for arg in command:
            if arg.startswith("--proto_path="):
                protoc_args.append(f"--proto_path={arg.split('=', 1)[1]}")
            elif arg.startswith("--python_out="):
                protoc_args.append(f"--python_out={arg.split('=', 1)[1]}")
            elif arg.startswith("--grpc_python_out="):
                protoc_args.append(f"--grpc_python_out={arg.split('=', 1)[1]}")
            else:
                protoc_args.append(arg)

        # Call protoc
        exit_code = protoc.main(protoc_args)

        if exit_code == 0:
            print(f"✓ Successfully compiled {proto_file.name}")
            success_count += 1
        else:
            print(f"✗ Failed to compile {proto_file.name}")
            return False

    # List generated files
    print(f"\nGenerated files in {generated_dir}:")
    generated_files = list(generated_dir.glob("*.py"))
    for py_file in generated_files:
        if py_file.name != "__init__.py":
            print(f"  - {py_file.name}")

    print(f"\n✓ Successfully compiled {success_count}/{len(proto_files)} file(s)")
    return True


if __name__ == "__main__":
    success = generate_grpc_code()
    sys.exit(0 if success else 1)
