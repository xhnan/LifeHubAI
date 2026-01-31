@echo off
REM gRPC Installation Script for Windows
REM This script attempts to install gRPC with pre-built wheels first,
REM then falls back to source compilation if needed.

echo ========================================
echo LifeHubAI gRPC Dependencies Installation
echo ========================================
echo.

echo Checking Python version...
python --version
echo.

echo Attempting to install grpcio with pre-built wheels...
pip install grpcio --only-binary grpcio

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Pre-built wheel installation failed.
    echo Attempting source compilation...
    echo.
    echo NOTE: Source compilation requires Visual Studio Build Tools.
    echo Download from: https://visualstudio.microsoft.com/downloads/
    echo.

    pip install grpcio grpcio-tools protobuf
) else (
    echo.
    echo Successfully installed grpcio from pre-built wheel.
    echo Installing remaining dependencies...
    pip install grpcio-tools protobuf
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Installation successful!
    echo ========================================
    echo.
    echo Next step: Generate gRPC code from proto files:
    echo   python scripts\generate_grpc.py
    echo.
) else (
    echo.
    echo ========================================
    echo Installation failed!
    echo ========================================
    echo.
    echo Please install Visual Studio Build Tools and try again.
    echo Or use conda: conda install -c conda-forge grpcio grpcio-tools protobuf
    echo.
)

pause
