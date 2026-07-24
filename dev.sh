#!/bin/bash
# ReviewAnalyzer 开发环境一键启动
# 用法: bash dev.sh

set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "=== ReviewAnalyzer 开发环境 ==="

# 清理旧进程
pkill -f "uvicorn app.main" 2>/dev/null || true
pkill -f "celery.*worker" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
sleep 1

# 1. 后端 (FastAPI)
cd "$ROOT/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
echo "✓ 后端: http://localhost:8000 (Swagger: /docs)"

# 2. Celery Worker
cd "$ROOT/backend"
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2 &
echo "✓ Celery Worker: redis://localhost:6379"

# 3. 前端 (Next.js)
cd "$ROOT/frontend"
pnpm dev &
echo "✓ 前端: http://localhost:3000"

echo ""
echo "=== 全部启动完成 ==="
echo "  前端:    http://localhost:3000"
echo "  后端:    http://localhost:8000"
echo "  Swagger: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待任意子进程退出
wait
