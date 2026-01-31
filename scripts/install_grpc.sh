#!/bin/bash
# gRPC Installation Script for Linux/macOS

echo "========================================"
echo "LifeHubAI gRPC Dependencies Installation"
echo "========================================"
echo

echo "Checking Python version..."
python3 --version
echo

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    OS="unknown"
fi

echo "Detected OS: $OS"
echo

# Install system dependencies if needed
if [[ "$OS" == "linux" ]]; then
    echo "Checking for system dependencies..."
    if ! command -v dpkg &> /dev/null; then
        echo "Warning: Cannot check system packages. Please ensure python3-dev and build-essential are installed."
    else
        if ! dpkg -l | grep -q python3-dev; then
            echo "Installing python3-dev..."
            sudo apt-get update
            sudo apt-get install -y python3-dev
        fi

        if ! dpkg -l | grep -q build-essential; then
            echo "Installing build-essential..."
            sudo apt-get install -y build-essential
        fi

        if ! dpkg -l | grep -q libgrpc-dev; then
            echo "Installing libgrpc-dev..."
            sudo apt-get install -y libgrpc-dev
        fi
    fi
elif [[ "$OS" == "macos" ]]; then
    echo "Checking for Xcode command line tools..."
    if ! command -v clang &> /dev/null; then
        echo "Installing Xcode command line tools..."
        xcode-select --install
        echo "Please complete the Xcode installation and run this script again."
        exit 1
    fi
fi

echo
echo "Installing Python packages..."
pip install grpcio grpcio-tools protobuf

if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "Installation successful!"
    echo "========================================"
    echo
    echo "Next step: Generate gRPC code from proto files:"
    echo "  python scripts/generate_grpc.py"
    echo
else
    echo
    echo "========================================"
    echo "Installation failed!"
    echo "========================================"
    echo
    echo "Please ensure you have the required build tools installed."
    exit 1
fi
