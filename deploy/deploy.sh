#!/usr/bin/env bash
# ============================================================
# 中韩出海数智港 — 一键部署脚本
# 目标服务器: 47.100.160.250 (阿里云ECS, Ubuntu)
# 使用方式:
#   chmod +x deploy/deploy.sh
#   sudo ./deploy/deploy.sh
# ============================================================
set -euo pipefail

# ── 配置 ──
APP_DIR="/var/www/china-korea-digital-port"
SERVICE_NAME="ckdp-backend"
NGINX_SITE="go-aiport.com"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NGINX_SRC="$SCRIPT_DIR/nginx.conf"
SERVICE_SRC="$SCRIPT_DIR/ckdp-backend.service"

echo ""
echo "=========================================="
echo "  中韩出海数智港 — 一键部署"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# ── Step 0: 确保目标目录存在 ──
echo "[0/7] 确保目标目录存在..."
if [ ! -d "$APP_DIR" ]; then
    echo "  ! 目标目录 $APP_DIR 不存在，请先手动创建或从 Git 克隆"
    echo "  执行: sudo mkdir -p $APP_DIR && sudo chown \$USER:\$USER $APP_DIR && git clone <repo-url> $APP_DIR"
    exit 1
fi

# ── Step 1: 拉取最新代码 ──
echo "[1/8] 拉取最新代码..."
cd "$APP_DIR"
if [ -d ".git" ]; then
    git pull origin main
else
    echo "  ! 不是 Git 仓库，跳过 git pull"
fi

# ── Step 2: 创建/更新 Python 虚拟环境 ──
echo "[2/8] 设置 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ 虚拟环境已创建"
fi
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet uvicorn[standard]

# ── Step 3: 配置环境变量 ──
echo "[3/8] 配置环境变量..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "  ✓ 已从 .env.example 创建 .env"
        echo "  ! 请编辑 .env 填入 SECRET_KEY 等敏感配置"
    else
        echo "  ! .env.example 不存在，跳过创建 .env"
    fi
else
    echo "  ✓ .env 已存在"
fi

# ── Step 4: 部署 Nginx 配置 ──
echo "[4/8] 部署 Nginx 配置..."
sudo cp "$NGINX_SRC" "/etc/nginx/sites-available/$NGINX_SITE"
# 启用站点（如果尚未启用）
if [ ! -L "/etc/nginx/sites-enabled/$NGINX_SITE" ]; then
    sudo ln -sf "/etc/nginx/sites-available/$NGINX_SITE" "/etc/nginx/sites-enabled/$NGINX_SITE"
fi
# 测试配置
sudo nginx -t
echo "  ✓ Nginx 配置测试通过"

# ── Step 5: 部署 Systemd 服务 ──
echo "[5/8] 部署 Systemd 服务..."
sudo cp "$SERVICE_SRC" "/etc/systemd/system/$SERVICE_NAME.service"
sudo systemctl daemon-reload
echo "  ✓ Systemd 服务已部署"

# ── Step 6: 创建日志目录 & 设置权限 ──
echo "[6/8] 设置日志目录和权限..."
sudo mkdir -p /var/log/ckdp
sudo touch /var/log/ckdp/backend.log /var/log/ckdp/backend-error.log
sudo chown -R opc:opc /var/log/ckdp

# 确保数据库目录可写
mkdir -p "$APP_DIR/backend/data"
sudo chown -R opc:opc "$APP_DIR/backend/data"
sudo chmod 755 "$APP_DIR/backend/data"

# 确保 admin 目录权限正确
if [ -d "$APP_DIR/admin" ]; then
    sudo chown -R opc:opc "$APP_DIR/admin"
fi

# ── Step 7: 启动服务 & 重载 Nginx ──
echo "[7/8] 启动服务..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
sudo systemctl reload nginx

# 等待服务启动
sleep 3

echo ""
echo "=========================================="
echo "[8/8] 健康检查..."
echo "=========================================="

# 健康检查
HEALTH_OK=true

if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "  ✓ API 健康检查: OK (127.0.0.1:8000/health)"
else
    echo "  ✗ API 健康检查: FAILED"
    HEALTH_OK=false
fi

if curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1/ > /dev/null 2>&1; then
    echo "  ✓ 前端首页: OK (HTTP $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/))"
else
    echo "  ✗ 前端首页: FAILED"
    HEALTH_OK=false
fi

if curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1/pricing > /dev/null 2>&1; then
    echo "  ✓ 定价页面: OK (HTTP $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/pricing))"
else
    echo "  ✗ 定价页面: FAILED"
    HEALTH_OK=false
fi

if curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1/admin/ > /dev/null 2>&1; then
    echo "  ✓ 管理后台: OK (HTTP $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/admin/))"
else
    echo "  ✗ 管理后台: FAILED"
    HEALTH_OK=false
fi

# 安全测试
if curl -sI http://127.0.0.1/.env | head -1 | grep -q "404\|403"; then
    echo "  ✓ 安全: .env 已被禁止访问"
else
    echo "  ! 安全: .env 访问检查未通过 (请手动验证)"
fi

echo ""
if [ "$HEALTH_OK" = true ]; then
    echo "✅ 全部检查通过！部署成功。"
else
    echo "⚠️  部分检查未通过，请查看日志排查:"
    echo "   sudo journalctl -u $SERVICE_NAME -n 50"
    echo "   sudo tail -f /var/log/ckdp/backend.log"
    exit 1
fi
echo ""
echo "  ➤ HTTPS 站点: https://go-aiport.com"
echo "  ➤ API 文档:   https://go-aiport.com/docs"
echo "  ➤ 管理后台:   https://go-aiport.com/admin/"
echo "  ➤ 服务状态:   sudo systemctl status $SERVICE_NAME"
echo "  ➤ 实时日志:   sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "=========================================="
echo "  部署结束: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
