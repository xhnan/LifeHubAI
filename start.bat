@echo off
REM LifeHubAI API 启动脚本 (Windows)

echo Starting LifeHubAI API Server...

REM 激活 conda 环境
call conda activate lifehubai310

REM 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
