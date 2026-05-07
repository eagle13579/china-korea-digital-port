# 中韩出海数智港 — 部署操作手册

## 1. 环境概览

| 项目 | 值 |
|------|-----|
| 服务器 | 47.100.160.250 (阿里云 ECS, Ubuntu) |
| 域名 | go-aiport.com / www.go-aiport.com |
| Web 服务器 | Nginx (反向代理 + 静态文件) |
| 后端 | FastAPI (Python 3.12+, Uvicorn, localhost:8000) |
| 数据库 | SQLite (WAL 模式, backend/data/portal.db) |
| SSL | Let's Encrypt (certbot) |
| 系统服务 | systemd (ckdp-backend.service) |

---

## 2. 首次部署（新服务器）

### 2.1 前置条件

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础依赖
sudo apt install -y python3 python3-venv python3-pip nginx git curl

# 安装 certbot（SSL 证书）
sudo apt install -y certbot python3-certbot-nginx
```

### 2.2 克隆代码

```bash
# 创建目标目录并设置权限
sudo mkdir -p /var/www/china-korea-digital-port
sudo chown opc:opc /var/www/china-korea-digital-port

# 克隆代码（请替换 YOUR_USER 为实际 GitHub 用户名）
# 方式 A：从 GitHub 克隆
cd /var/www/china-korea-digital-port
git clone https://github.com/YOUR_USER/china-korea-digital-port.git .

# 方式 B：使用 rsync 从本地拷贝
rsync -avz --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  ./ china-korea-digital-port/ opc@47.100.160.250:/var/www/china-korea-digital-port/
```

### 2.3 配置环境变量

```bash
cd /var/www/china-korea-digital-port

# 创建 .env 文件（重要：设置强密码！）
cat > .env << 'EOF'
# 中韩出海数智港 — 生产环境配置

# 管理员登录凭据（必须修改！）
ADMIN_USERNAME=admin
ADMIN_PASSWORD=ChangeMeToAStrongPassword2026!

# 支付配置（可选，不配置则使用演示模式）
ALIPAY_APP_ID=
ALIPAY_APP_PRIVATE_KEY=certs/alipay_app_private_key.pem
ALIPAY_PUBLIC_KEY=certs/alipay_public_key.pem
ALIPAY_SANDBOX=true
ALIPAY_NOTIFY_URL=https://go-aiport.com/api/v1/payment/notify

# CORS 允许的域名（逗号分隔，生产环境请设置具体域名）
ALLOWED_ORIGINS=https://go-aiport.com,https://www.go-aiport.com

# 数据库目录（默认：backend/data/）
DB_DIR=backend/data

# 邮件服务（可选）
# SMTP_HOST=smtp.example.com
# SMTP_PORT=587
# SMTP_USER=your_email@example.com
# SMTP_PASS=your_password
# NOTIFICATION_EMAIL=admin@go-aiport.com
EOF

# 设置 .env 文件权限
chmod 600 .env
```

### 2.4 运行一键部署脚本

```bash
cd /var/www/china-korea-digital-port
chmod +x deploy/deploy.sh
sudo ./deploy/deploy.sh
```

### 2.5 申请 SSL 证书

```bash
# 方式 A：使用 ssl-fix.sh（首次签发）
sudo ./deploy/ssl-fix.sh

# 方式 B：手动使用 certbot
sudo certbot --nginx \
  -d go-aiport.com \
  -d www.go-aiport.com \
  --non-interactive \
  --agree-tos \
  --email admin@go-aiport.com
```

### 2.6 配置 SSL 自动续期

```bash
# 推荐：使用 certbot 自带的 systemd timer
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer

# 验证 timer 状态
sudo systemctl status certbot.timer

# 测试续期通道
sudo certbot renew --dry-run

# 备用方案：使用 crontab（如果 timer 不可用）
# sudo crontab -e
# 添加：
# 0 3 1,15 * * /var/www/china-korea-digital-port/deploy/ssl-renew.sh
```

---

## 3. 日常部署（更新代码）

### 3.1 一键更新

```bash
cd /var/www/china-korea-digital-port
sudo ./deploy/deploy.sh
```

### 3.2 分步骤手动更新

```bash
# 1. 拉取最新代码
cd /var/www/china-korea-digital-port
git pull origin main

# 2. 更新 Python 依赖
source venv/bin/activate
pip install -r requirements.txt --quiet

# 3. 重启后端服务
sudo systemctl restart ckdp-backend

# 4. 重载 Nginx（如果 nginx.conf 有变更）
# sudo cp deploy/nginx.conf /etc/nginx/sites-available/go-aiport.com
# sudo nginx -t && sudo systemctl reload nginx

# 5. 验证部署
./deploy/check-deploy.sh
```

---

## 4. 服务管理命令

### 4.1 后端服务 (systemd)

```bash
# 查看状态
sudo systemctl status ckdp-backend

# 启动/停止/重启
sudo systemctl start ckdp-backend
sudo systemctl stop ckdp-backend
sudo systemctl restart ckdp-backend

# 查看日志
sudo journalctl -u ckdp-backend -n 50 --no-pager
sudo journalctl -u ckdp-backend -f          # 实时日志

# 日志文件
tail -f /var/log/ckdp/backend.log
tail -f /var/log/ckdp/backend-error.log
```

### 4.2 Nginx

```bash
# 测试配置
sudo nginx -t

# 重载（不中断连接）
sudo systemctl reload nginx

# 重启
sudo systemctl restart nginx

# 查看访问日志
tail -f /var/log/nginx/go-aiport-access.log
tail -f /var/log/nginx/go-aiport-error.log
```

### 4.3 SSL 证书

```bash
# 查看证书信息
sudo openssl x509 -in /etc/letsencrypt/live/go-aiport.com/cert.pem -noout -text | head -20

# 手动续期
sudo certbot renew

# 强制续期（测试用）
sudo certbot renew --force-renewal

# 查看 timer 状态
sudo systemctl status certbot.timer
```

---

## 5. 验证部署

运行验证脚本：

```bash
cd /var/www/china-korea-digital-port
./deploy/check-deploy.sh
```

或使用 curl 手动验证：

```bash
# 验证静态页面
curl -I https://www.go-aiport.com/

# 验证 API 健康检查
curl -s https://www.go-aiport.com/health

# 验证 API 文档
curl -s https://www.go-aiport.com/docs | head -5

# 验证定价页面
curl -s -o /dev/null -w "%{http_code}" https://www.go-aiport.com/pricing

# 验证管理后台
curl -s -o /dev/null -w "%{http_code}" https://www.go-aiport.com/admin/
```

---

## 6. 故障排查

### 6.1 后端 API 返回 404

```bash
# 检查后端服务是否运行
sudo systemctl status ckdp-backend

# 检查后端日志
sudo journalctl -u ckdp-backend -n 50 --no-pager

# 直接测试后端（绕过 Nginx）
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/api/v1/pricing

# 如果后端正常但 Nginx 转发 404，检查 nginx 配置
sudo nginx -t
cat /etc/nginx/sites-enabled/go-aiport.com | grep -A5 "location /api/"
```

### 6.2 Nginx 静态页面正常但 API 报错

```bash
# 可能原因1：后端服务未启动
sudo systemctl restart ckdp-backend

# 可能原因2：Nginx 代理配置错误
# 检查 proxy_pass 地址是否正确
grep "proxy_pass" /etc/nginx/sites-enabled/go-aiport.com

# 可能原因3：防火墙/安全组未放行 localhost:8000（本地通信，不需放行）
```

### 6.3 数据库问题

```bash
# 数据库文件位置
ls -la /var/www/china-korea-digital-port/backend/data/portal.db

# 确保权限正确
sudo chown -R opc:opc /var/www/china-korea-digital-port/backend/data

# 备份数据库
cp /var/www/china-korea-digital-port/backend/data/portal.db /tmp/portal.db.backup
```

---

## 7. 文件结构

```
/var/www/china-korea-digital-port/
├── deploy/
│   ├── deploy.sh              # 一键部署脚本
│   ├── check-deploy.sh        # 部署验证脚本
│   ├── nginx.conf             # Nginx 站点配置
│   ├── ckdp-backend.service   # systemd 服务配置
│   ├── ssl-fix.sh             # SSL 首次签发脚本
│   ├── ssl-renew.sh           # SSL crontab 续期脚本
│   └── README.md              # 本手册
├── backend/
│   ├── main.py                # FastAPI 应用入口
│   ├── database.py            # 数据库模块
│   ├── models.py              # Pydantic 数据模型
│   ├── routers/               # API 路由
│   └── data/                  # SQLite 数据库
├── .env                       # 环境变量（敏感信息，勿提交）
├── index.html                 # 前端首页
├── venv/                      # Python 虚拟环境
└── requirements.txt           # Python 依赖
```
