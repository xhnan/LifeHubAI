# ============================================
# LifeHubAI Dockerfile
# Python 3.10 + FastAPI + gRPC
# ============================================

# ---------- 构建阶段 ----------
FROM python:3.10-slim AS builder

WORKDIR /app

# 安装系统依赖（psycopg2-binary 需要 libpq）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- 运行阶段 ----------
FROM python:3.10-slim

LABEL maintainer="LifeHubAI"
LABEL description="AI-powered code generation and TTS service"

WORKDIR /app

# 只安装运行时需要的系统库
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝已安装的 Python 依赖
COPY --from=builder /install /usr/local

# 拷贝项目源码
COPY . .

# 环境变量默认值
ENV ENVIRONMENT=production \
    NACOS_ENABLED=true \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 暴露端口：FastAPI HTTP + gRPC
EXPOSE 8000 50051

# 健康检查（FastAPI /health 端点）
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令：使用 start_with_env.py 以生产模式运行
CMD ["python", "start_with_env.py", "--env", "production"]
