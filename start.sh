#!/bin/bash

# LifeHubAI API 启动脚本

echo "Starting LifeHubAI API Server..."

# 激活 conda 环境
eval "$(conda shell.bash hook)"
conda activate lifehubai310

# 启动 FastAPI 服务
uvicorn main:app --reload --host 0.0.0.0 --port 8000
