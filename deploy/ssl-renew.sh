#!/usr/bin/env bash
# ============================================================
# SSL 证书自动续期脚本 (cronjob 版)
# 用于 Let's Encrypt 证书的自动续期 + Nginx 重载
# 
# 安装 cronjob:
#   sudo crontab -e
#   添加以下行（每天凌晨3点检查，每月1号和15号强制续期）:
#   0 3 1,15 * * /var/www/china-korea-digital-port/deploy/ssl-renew.sh
#
# 或使用 certbot 自带的 systemd timer（推荐）:
#   sudo systemctl enable certbot.timer
#   sudo systemctl start certbot.timer
# ============================================================
set -euo pipefail

# ── 配置 ──
DOMAINS="go-aiport.com,www.go-aiport.com"
CERT_NAME="go-aiport.com"
NGINX_SITE="go-aiport.com"
LOG_FILE="/var/log/ckdp/ssl-renew.log"
ADMIN_EMAIL="admin@go-aiport.com"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=========================================="
log "SSL 证书续期检查 — 开始"
log "域名: $DOMAINS"
log "=========================================="

# ── Step 1: 检查 certbot ──
if ! command -v certbot &> /dev/null; then
    log "! certbot 未安装，尝试自动安装..."
    sudo apt-get update -qq && sudo apt-get install -y -qq certbot python3-certbot-nginx
    if ! command -v certbot &> /dev/null; then
        log "✗ certbot 安装失败，请手动安装后重试"
        exit 1
    fi
    log "✓ certbot 安装完成"
fi

# ── Step 2: 检查现有证书 ──
CERT_DIR="/etc/letsencrypt/live/$CERT_NAME"
if [ ! -d "$CERT_DIR" ]; then
    log "! 未找到现有证书，将创建新证书..."
    sudo certbot --nginx \
        -d go-aiport.com \
        -d www.go-aiport.com \
        --non-interactive \
        --agree-tos \
        --email "$ADMIN_EMAIL" \
        --redirect 2>&1 | tee -a "$LOG_FILE"
    log "✓ 新证书签发完成"
else
    # ── Step 3: 检查证书到期日 ──
    EXPIRY=$(sudo openssl x509 -in "$CERT_DIR/cert.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
    EXPIRY_EPOCH=$(sudo openssl x509 -in "$CERT_DIR/cert.pem" -noout -enddate 2>/dev/null | cut -d= -f2 | date -f - +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

    log "当前证书到期日: $EXPIRY"
    log "剩余天数: ${DAYS_LEFT:-未知}"

    # 如果证书在30天内到期，执行续期
    if [ "$DAYS_LEFT" -le 30 ] 2>/dev/null; then
        log "证书即将到期，执行续期..."
        sudo certbot renew --nginx --non-interactive --agree-tos --email "$ADMIN_EMAIL" 2>&1 | tee -a "$LOG_FILE"
        log "✓ 证书续期完成"
    else
        log "证书有效期充足，无需续期"
        # 仍执行 dry-run 以验证续期通道
        sudo certbot renew --dry-run 2>&1 | tee -a "$LOG_FILE" || true
    fi
fi

# ── Step 4: 验证并重载 Nginx ──
log "验证 Nginx 配置并重载..."
if sudo nginx -t 2>&1 | tee -a "$LOG_FILE"; then
    sudo systemctl reload nginx || sudo nginx -s reload
    log "✓ Nginx 已重载"
else
    log "✗ Nginx 配置验证失败！请手动检查"
    exit 1
fi

log "=========================================="
log "SSL 证书续期检查 — 完成"
log "=========================================="
