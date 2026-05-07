#!/usr/bin/env bash
# ============================================================
# 中韩出海数智港 — 部署验证脚本
# 检查：服务状态 + SSL + Nginx + API 响应
#
# 使用方式:
#   ./deploy/check-deploy.sh [--verbose]
# ============================================================
set -euo pipefail

# ── 颜色 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── 配置 ──
APP_DIR="/var/www/china-korea-digital-port"
SERVICE_NAME="ckdp-backend"
DOMAIN="go-aiport.com"
DOMAIN_WWW="www.go-aiport.com"
API_BASE="http://127.0.0.1:8000"
NGINX_SITE="go-aiport.com"

# 参数
VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

# ── 状态追踪 ──
PASS=0
FAIL=0
WARN=0

pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    PASS=$((PASS + 1))
}

fail() {
    echo -e "  ${RED}✗${NC} $1"
    FAIL=$((FAIL + 1))
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    WARN=$((WARN + 1))
}

info() {
    echo -e "  ${CYAN}→${NC} $1"
}

header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
}

# ════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}==========================================${NC}"
echo -e "${CYAN}  中韩出海数智港 — 部署验证${NC}"
echo -e "${CYAN}  时间: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${CYAN}==========================================${NC}"

# ──────────── 1. 系统检查 ────────────
header "1. 系统环境"

# Nginx
if command -v nginx &> /dev/null; then
    NGINX_VER=$(nginx -v 2>&1 | awk '{print $3}')
    pass "Nginx 已安装 ($NGINX_VER)"
else
    fail "Nginx 未安装"
fi

# Python
if command -v python3 &> /dev/null; then
    PY_VER=$(python3 --version 2>&1)
    pass "Python 已安装 ($PY_VER)"
else
    fail "Python 未安装"
fi

# Certbot
if command -v certbot &> /dev/null; then
    CERT_VER=$(certbot --version 2>&1)
    pass "Certbot 已安装 ($CERT_VER)"
else
    warn "Certbot 未安装（SSL 无法自动续期）"
fi

# ──────────── 2. 项目目录 ────────────
header "2. 项目目录"

if [ -d "$APP_DIR" ]; then
    pass "项目目录存在: $APP_DIR"
else
    fail "项目目录不存在: $APP_DIR"
fi

if [ -d "$APP_DIR/backend" ]; then
    pass "后端目录存在"
else
    fail "后端目录不存在"
fi

if [ -f "$APP_DIR/.env" ]; then
    pass ".env 文件存在"
    if $VERBOSE; then
        # 检查关键变量（不输出值）
        for var in ADMIN_USERNAME ADMIN_PASSWORD; do
            if grep -q "^${var}=" "$APP_DIR/.env" 2>/dev/null; then
                info "$var 已配置"
            else
                warn "$var 未配置"
            fi
        done
    fi
else
    fail ".env 文件不存在 — 后端无法启动"
fi

if [ -d "$APP_DIR/venv" ]; then
    pass "Python 虚拟环境存在"
    if $VERBOSE; then
        PYTHON_PATH="$APP_DIR/venv/bin/python"
        if [ -f "$PYTHON_PATH" ]; then
            VER=$("$PYTHON_PATH" --version 2>&1)
            info "虚拟环境 Python: $VER"
        fi
    fi
else
    fail "Python 虚拟环境不存在"
fi

if [ -f "$APP_DIR/backend/data/portal.db" ]; then
    DB_SIZE=$(du -h "$APP_DIR/backend/data/portal.db" 2>/dev/null | cut -f1)
    pass "数据库文件存在 (大小: ${DB_SIZE:-unknown})"
else
    warn "数据库文件不存在（首次启动会自动创建）"
fi

# ──────────── 3. Systemd 服务 ────────────
header "3. Systemd 服务"

if systemctl is-enabled "$SERVICE_NAME" &>/dev/null; then
    pass "服务已启用 (enabled)"
else
    warn "服务未启用 (not enabled)"
fi

if systemctl is-active "$SERVICE_NAME" &>/dev/null; then
    pass "服务正在运行 (active)"
    # 显示 uptime
    UPTIME=$(systemctl show "$SERVICE_NAME" -p ActiveEnterTimestamp --value 2>/dev/null || echo "unknown")
    info "启动时间: $UPTIME"
else
    fail "服务未运行 (inactive)"
    # 显示最后几条日志
    warn "最近日志:"
    sudo journalctl -u "$SERVICE_NAME" -n 5 --no-pager 2>/dev/null | while read -r line; do
        info "$line"
    done
fi

# ──────────── 4. Nginx 配置 ────────────
header "4. Nginx 配置"

if [ -f "/etc/nginx/sites-available/$NGINX_SITE" ]; then
    pass "Nginx 站点配置存在 (sites-available)"
else
    fail "Nginx 站点配置不存在 (sites-available)"
fi

if [ -L "/etc/nginx/sites-enabled/$NGINX_SITE" ]; then
    pass "Nginx 站点已启用 (sites-enabled)"
else
    fail "Nginx 站点未启用 (sites-enabled)"
fi

# 测试 nginx 配置
if sudo nginx -t 2>&1 | grep -q "test is successful"; then
    pass "Nginx 配置语法正确"
else
    fail "Nginx 配置语法错误"
    sudo nginx -t 2>&1
fi

# 检查 proxy_pass 配置
if grep -q "proxy_pass http://127.0.0.1:8000" "/etc/nginx/sites-enabled/$NGINX_SITE" 2>/dev/null; then
    pass "API 代理配置正确 (127.0.0.1:8000)"
else
    fail "API 代理配置缺失或错误"
fi

# ──────────── 5. SSL 证书 ────────────
header "5. SSL 证书"

CERT_DIR="/etc/letsencrypt/live/go-aiport.com"
if [ -d "$CERT_DIR" ]; then
    pass "SSL 证书目录存在"

    if [ -f "$CERT_DIR/fullchain.pem" ]; then
        CERT_EXPIRY=$(sudo openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        # 计算剩余天数
        EXPIRY_EPOCH=$(sudo openssl x509 -in "$CERT_DIR/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2 | date -f - +%s 2>/dev/null || echo "0")
        NOW_EPOCH=$(date +%s)
        if [ "$EXPIRY_EPOCH" -gt "$NOW_EPOCH" ] 2>/dev/null; then
            DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))
            if [ "$DAYS_LEFT" -gt 30 ]; then
                pass "证书有效期充足: $CERT_EXPIRY (剩余 ${DAYS_LEFT}天)"
            elif [ "$DAYS_LEFT" -gt 7 ]; then
                warn "证书即将到期: $CERT_EXPIRY (剩余 ${DAYS_LEFT}天)"
            else
                fail "证书即将过期: $CERT_EXPIRY (仅剩 ${DAYS_LEFT}天！)"
            fi
        else
            fail "证书已过期: $CERT_EXPIRY"
        fi
    else
        fail "fullchain.pem 不存在"
    fi

    # 检查 SAN（主题备用名称）
    if $VERBOSE; then
        SAN=$(sudo openssl x509 -in "$CERT_DIR/cert.pem" -noout -ext subjectAltName 2>/dev/null | grep -o 'DNS:[^,]*' || echo "")
        info "证书 SAN: $SAN"
    fi
else
    fail "SSL 证书未安装 — 请运行 sudo ./deploy/ssl-fix.sh"
fi

# 检查 certbot timer
if systemctl is-active certbot.timer &>/dev/null 2>&1; then
    NEXT_RUN=$(systemctl show certbot.timer -p NextElapseUSecRealtime --value 2>/dev/null || echo "unknown")
    pass "Certbot 自动续期 timer 已启用"
    info "下次续期检查: $NEXT_RUN"
else
    warn "Certbot timer 未启用 — SSL 证书不会自动续期"
    info "执行: sudo systemctl enable certbot.timer && sudo systemctl start certbot.timer"
fi

# ──────────── 6. 后端 API 检查 ────────────
header "6. 后端 API"

# 健康检查 (直接访问后端)
if curl -sf "$API_BASE/health" > /dev/null 2>&1; then
    HEALTH=$(curl -s "$API_BASE/health")
    pass "后端健康检查: OK ($HEALTH)"
else
    fail "后端健康检查: FAILED (127.0.0.1:8000 无响应)"
fi

# API 端点检查
API_ENDPOINTS=(
    "/api/v1/pricing"
    "/api/v1/digital-employees"
    "/api/v1/compliance/questions"
)

for endpoint in "${API_ENDPOINTS[@]}"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE$endpoint" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ]; then
        pass "API $endpoint → $HTTP_CODE"
    else
        warn "API $endpoint → $HTTP_CODE (期望 200)"
        if $VERBOSE; then
            RESP=$(curl -s "$API_BASE$endpoint" 2>/dev/null | head -c 200)
            info "响应: $RESP"
        fi
    fi
done

# ──────────── 7. Nginx 代理检查 ────────────
header "7. Nginx 代理 (通过 localhost)"

# 健康检查通过 Nginx
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    pass "Nginx 代理 /health → $HTTP_CODE"
else
    fail "Nginx 代理 /health → $HTTP_CODE (期望 200)"
fi

# 静态文件
for page in "/" "/pricing" "/pricing.html" "/admin/" "/demo" "/compliance-check"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1$page" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
        pass "静态页面 $page → $HTTP_CODE"
    else
        warn "静态页面 $page → $HTTP_CODE (期望 200)"
    fi
done

# API 通过 Nginx
for endpoint in "/api/v1/pricing" "/api/v1/digital-employees"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1$endpoint" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        pass "Nginx 代理 API $endpoint → $HTTP_CODE"
    else
        fail "Nginx 代理 API $endpoint → $HTTP_CODE (期望 200)"
    fi
done

# ──────────── 8. SSL/HTTPS 检查 ────────────
header "8. HTTPS 访问"

for domain in "$DOMAIN" "$DOMAIN_WWW"; do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://$domain/" --connect-timeout 5 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ]; then
        pass "HTTPS $domain/ → $HTTP_CODE"
    elif [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
        pass "HTTPS $domain/ → $HTTP_CODE (重定向)"
    else
        warn "HTTPS $domain/ → $HTTP_CODE (期望 200)"
    fi
done

# HTTP → HTTPS 重定向检查
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/" --connect-timeout 5 2>/dev/null || echo "000")
REDIRECT_URL=$(curl -s -o /dev/null -w "%{redirect_url}" "http://$DOMAIN/" --connect-timeout 5 2>/dev/null || echo "")
if [ "$HTTP_CODE" = "301" ] || [ "$HTTP_CODE" = "302" ]; then
    pass "HTTP → HTTPS 重定向: $HTTP_CODE → $REDIRECT_URL"
else
    warn "HTTP → HTTPS 重定向: $HTTP_CODE (期望 301/302)"
fi

# ──────────── 9. 安全规则检查 ────────────
header "9. 安全规则"

# .env 文件应该被禁止访问
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/.env" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "403" ]; then
    pass ".env 访问被拒绝 (HTTP $HTTP_CODE)"
else
    warn ".env 返回 HTTP $HTTP_CODE (应返回 404 或 403)"
fi

# 数据库文件
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/portal.db" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "403" ]; then
    pass "数据库文件访问被拒绝 (HTTP $HTTP_CODE)"
else
    warn "数据库文件返回 HTTP $HTTP_CODE (应返回 404 或 403)"
fi

# Git 目录
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1/.git/config" 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "403" ]; then
    pass ".git 目录访问被拒绝 (HTTP $HTTP_CODE)"
else
    fail ".git 目录可访问！(HTTP $HTTP_CODE) 安全风险！"
fi

# ──────────── 10. 日志目录 ────────────
header "10. 日志"

if [ -d "/var/log/ckdp" ]; then
    pass "日志目录存在: /var/log/ckdp"
    for log_file in backend.log backend-error.log ssl-renew.log; do
        if [ -f "/var/log/ckdp/$log_file" ]; then
            LOG_SIZE=$(du -h "/var/log/ckdp/$log_file" 2>/dev/null | cut -f1)
            info "$log_file (大小: ${LOG_SIZE:-0})"
        fi
    done
else
    warn "日志目录不存在 (部署脚本会自动创建)"
fi

if [ -f "/var/log/nginx/go-aiport-access.log" ]; then
    pass "Nginx 访问日志存在"
else
    warn "Nginx 访问日志不存在"
fi

if [ -f "/var/log/nginx/go-aiport-error.log" ]; then
    pass "Nginx 错误日志存在"
else
    warn "Nginx 错误日志不存在"
fi

# ════════════════════════════════════════════════════════════
# 总结
# ════════════════════════════════════════════════════════════
header "检查结果总结"

TOTAL=$((PASS + FAIL + WARN))

echo -e "  ${GREEN}通过: $PASS${NC}"
echo -e "  ${RED}失败: $FAIL${NC}"
echo -e "  ${YELLOW}警告: $WARN${NC}"
echo -e "  ${CYAN}共计: $TOTAL${NC}"

echo ""
if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
    echo -e "${GREEN}✅ 全部检查通过！部署状态正常。${NC}"
elif [ "$FAIL" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  检查完成，存在 $WARN 个警告（非关键问题）。${NC}"
else
    echo -e "${RED}✗ 存在 $FAIL 个失败项，请排查修复！${NC}"
    echo ""
    echo -e "${YELLOW}快速排查建议:${NC}"
    echo "  1) sudo systemctl status ckdp-backend"
    echo "  2) sudo journalctl -u ckdp-backend -n 30"
    echo "  3) sudo nginx -t"
    echo "  4) curl -s http://127.0.0.1:8000/health"
    echo "  5) ./deploy/deploy.sh"
fi
echo ""
