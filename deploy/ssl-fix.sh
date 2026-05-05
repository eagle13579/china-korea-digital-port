#!/usr/bin/env bash
# ============================================================
# SSL 证书修复脚本 — 重新签发 Let's Encrypt 证书
# 问题: 当前证书 SAN 只有 www.go-aiport.com，缺少 go-aiport.com（不带 www）
# 修复: 重新签发包含两个域名的证书
# 
# 使用方式:
#   chmod +x deploy/ssl-fix.sh
#   sudo ./deploy/ssl-fix.sh
# ============================================================
set -euo pipefail

echo ""
echo "=========================================="
echo "  SSL 证书修复 — 重新签发 Let's Encrypt"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

# ── Step 1: 检查 certbot 是否安装 ──
echo "[1/4] 检查 certbot..."
if ! command -v certbot &> /dev/null; then
    echo "  ! certbot 未安装，正在安装..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq certbot python3-certbot-nginx
    echo "  ✓ certbot 安装完成"
else
    echo "  ✓ certbot 已安装 ($(certbot --version 2>&1))"
fi

# ── Step 2: 备份当前证书 ──
echo "[2/4] 备份现有证书..."
BACKUP_DIR="/etc/letsencrypt/backup/$(date +%Y%m%d_%H%M%S)"
if [ -d "/etc/letsencrypt/live/go-aiport.com" ]; then
    sudo mkdir -p "$BACKUP_DIR"
    sudo cp -r "/etc/letsencrypt/live/go-aiport.com" "$BACKUP_DIR/"
    echo "  ✓ 证书已备份到: $BACKUP_DIR"
    echo "  ✓ 当前证书信息:"
    sudo openssl x509 -in /etc/letsencrypt/live/go-aiport.com/cert.pem -noout -subject -dates -ext subjectAltName 2>/dev/null || true
else
    echo "  ! 未找到现有证书，将创建新证书"
fi

# ── Step 3: 重新签发证书 ──
echo "[3/4] 重新签发 SSL 证书..."
echo "  域名: go-aiport.com, www.go-aiport.com"
echo "  使用 nginx 插件模式..."

# 执行 certbot
sudo certbot --nginx \
    -d go-aiport.com \
    -d www.go-aiport.com \
    --non-interactive \
    --agree-tos \
    --email admin@go-aiport.com \
    --redirect \
    --force-renewal 2>&1 || {
        echo ""
        echo "  ! 证书签发失败，尝试交互式模式..."
        sudo certbot --nginx \
            -d go-aiport.com \
            -d www.go-aiport.com
    }

echo ""
echo "  ✓ 证书签发完成"
echo "  新证书 SAN:"
sudo openssl x509 -in /etc/letsencrypt/live/go-aiport.com/cert.pem -noout -ext subjectAltName 2>/dev/null || true

# ── Step 4: 验证证书并重载 Nginx ──
echo "[4/4] 验证并重载 Nginx..."
sudo nginx -t
sudo systemctl reload nginx
echo "  ✓ Nginx 配置验证通过，已重载"

echo ""
echo "=========================================="
echo "  SSL 证书修复完成"
echo "=========================================="
echo ""
echo "  证书路径:"
echo "    Fullchain: /etc/letsencrypt/live/go-aiport.com/fullchain.pem"
echo "    Privkey:   /etc/letsencrypt/live/go-aiport.com/privkey.pem"
echo ""
echo "  验证 HTTPS 访问:"
echo "    curl -I https://go-aiport.com"
echo "    curl -I https://www.go-aiport.com"
echo ""
echo "  证书自动续期 (systemd timer):"
echo "    sudo systemctl status certbot.timer"
echo "    sudo certbot renew --dry-run"
echo ""
echo "=========================================="
echo "  完成时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
