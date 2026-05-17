#!/bin/bash
# ============================================================
# 中韩出海数智港 - 生产环境启动脚本
# China-Korea Digital Port - Production Startup Script
# ============================================================
set -euo pipefail

PROJECT_DIR="/var/www/china-korea-digital-port"
LOG_DIR="/var/log/ckdp"

echo "=========================================="
echo "  中韩出海数智港 - 启动脚本"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# Step 1: Create log directory
echo "[1/5] 确保日志目录存在..."
mkdir -p "$LOG_DIR"
echo "  ✓ $LOG_DIR"

# Step 2: Check Python venv
echo "[2/5] 检查 Python 虚拟环境..."
if [ -f "$PROJECT_DIR/venv/bin/python3" ]; then
    echo "  ✓ venv 存在"
else
    echo "  ! venv 不存在，创建中..."
    cd "$PROJECT_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
    echo "  ✓ venv 已创建"
fi

# Step 3: Check .env
echo "[3/5] 检查环境变量..."
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "  ✓ .env 文件存在"
else
    echo "  ✗ .env 文件缺失！请从 .env.example 复制"
    exit 1
fi

# Step 4: Restart backend via systemd
echo "[4/5] 重启后端服务..."
systemctl daemon-reload 2>/dev/null || true
systemctl enable auto-run.service 2>/dev/null || true
systemctl restart auto-run.service
sleep 2

# Step 5: Verify
echo "[5/5] 验证服务状态..."
if systemctl is-active --quiet auto-run.service; then
    echo "  ✓ auto-run.service 运行中"
else
    echo "  ✗ auto-run.service 启动失败"
    journalctl -u auto-run.service --no-pager -n 20
    exit 1
fi

# Health check
echo ""
echo "--- 健康检查 ---"
HEALTH=$(curl -s http://127.0.0.1:8000/health 2>/dev/null || echo "FAILED")
echo "  /health: $HEALTH"

echo ""
echo "=========================================="
echo "  启动完成 ✅"
echo "=========================================="
echo "  网址: https://www.go-aiport.com"
echo "  后端: http://127.0.0.1:8000"
echo "  日志: $LOG_DIR"
echo "=========================================="
