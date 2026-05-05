# 中韩出海数智港 — 生产部署方案

> 域名: go-aiport.com
> 服务器: 47.100.160.250 (阿里云ECS, Ubuntu)
> Web: Nginx/1.24.0, SSL已配置 (Let's Encrypt)
> 后端: FastAPI + SQLite (Uvicorn)
> 仓库: github.com/eagle13579/china-korea-digital-port

---

## 目录

1. [当前状态分析](#1-当前状态分析)
2. [准备工作：GitHub Push](#2-准备工作github-push)
3. [服务器端部署流程](#3-服务器端部署流程)
4. [Nginx 配置（集成方案）](#4-nginx-配置集成方案)
5. [后端进程管理（Systemd）](#5-后端进程管理systemd)
6. [新页面路由策略（定价页 + 管理后台）](#6-新页面路由策略定价页--管理后台)
7. [一键部署脚本](#7-一键部署脚本)
8. [验证清单](#8-验证清单)
9. [回滚方案](#9-回滚方案)

---

## 1. 当前状态分析

### 线上现状 (go-aiport.com)

| 项目 | 状态 |
|------|------|
| index.html | ~20KB, SPA单页应用, 存在但不完全同本地 |
| nginx 配置 | 404 回退到 index.html (try_files $uri $uri/ /index.html) |
| /api/* 反向代理 | 尚未配置到 FastAPI |
| pricing.html | 不存在（访问返回首页） |
| admin/index.html | 不存在（访问返回首页） |
| 后端 FastAPI | 未部署运行 |

### 本地开发目录结构

```
china-korea-digital-port/
├── index.html          # 主站首页 (~21KB)
├── pricing.html        # 定价页面 (~10KB)
├── admin/
│   └── index.html      # 管理后台 (~18KB)
├── css/
│   └── style.css       # 样式
├── js/
│   └── main.js         # 前端逻辑
├── backend/
│   ├── main.py         # FastAPI入口
│   ├── database.py     # SQLite + 建表
│   ├── models.py       # Pydantic模型
│   ├── routers/
│   │   ├── contact.py  # 联系表单API
│   │   ├── demo.py     # 预约演示API
│   │   ├── pricing.py  # 定价查询API
│   │   └── admin.py    # 管理后台API (登录/线索/统计)
│   └── data/           # SQLite数据库目录
├── requirements.txt    # Python依赖
├── CNAME              # go-aiport.com
└── README.md
```

### API 路由一览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/contact` | POST | 提交联系表单 |
| `/api/v1/demo` | POST | 预约演示 |
| `/api/v1/pricing` | GET | 获取定价方案列表 |
| `/api/v1/pricing/inquiry` | POST | 提交定价咨询 |
| `/api/v1/admin/login` | POST | 管理员登录 |
| `/api/v1/admin/leads` | GET | 获取线索列表 |
| `/api/v1/admin/leads/{table}/{id}` | GET | 线索详情 |
| `/api/v1/admin/leads/{table}/{id}/status` | PATCH | 更新线索状态 |
| `/api/v1/admin/stats` | GET | 获取统计 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | API文档 (Swagger) |

> 注: 管理后台硬编码用户名/密码 — `admin / admin123`。上线前请修改 admin.py 中的 `ADMIN_PASS`。

---

## 2. 准备工作：GitHub Push

本地项目已关联 `eagle13579/china-korea-digital-port`，当前有未提交的修改：

```bash
# 未staged的修改: css/style.css, index.html, js/main.js
# 未跟踪的文件: admin/, backend/, pricing.html, requirements.txt
```

### 2.1 添加 .gitignore

在项目根目录创建 `.gitignore`:

```
# Python
__pycache__/
*.py[cod]
backend/venv/
*.egg-info/

# Database
*.db
*.db-shm
*.db-wal

# IDE
.idea/
.vscode/
*.swp

# OS
.DS_Store
Thumbs.db

# Environment
.env
```

### 2.2 Push 到 GitHub

```bash
cd /path/to/china-korea-digital-port

# 添加所有新文件
git add .
git status   # 确认包含: admin/ backend/ pricing.html requirements.txt .gitignore

# 提交
git commit -m "feat: 添加后端API + 定价页 + 管理后台

- FastAPI后端: 联系表单/预约演示/定价查询/管理后台
- pricing.html: 三档定价方案页面
- admin/index.html: 线索管理后台 (Alpine.js + Tailwind)
- Nginx反向代理 /api/* 到 FastAPI"

# Push
git push origin main
```

> 如果 SSH key 未配置，可用 HTTPS:
> ```bash
> git remote set-url origin https://github.com/eagle13579/china-korea-digital-port.git
> git push origin main
> # 会提示输入 GitHub 用户名和 Personal Access Token
> ```

---

## 3. 服务器端部署流程

### 3.1 SSH 登录

```bash
ssh opc@47.100.160.250
```

### 3.2 安装依赖

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx git curl sqlite3
```

### 3.3 Clone / Pull 代码

```bash
# 设定部署目录
sudo mkdir -p /var/www/china-korea-digital-port
sudo chown opc:opc /var/www/china-korea-digital-port

# 首次：clone
cd /var/www/china-korea-digital-port
git clone https://github.com/eagle13579/china-korea-digital-port.git .

# 后续更新：pull
cd /var/www/china-korea-digital-port
git pull origin main
```

### 3.4 设置 Python 虚拟环境

```bash
cd /var/www/china-korea-digital-port
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install uvicorn[standard]
```

### 3.5 测试后端启动

```bash
cd /var/www/china-korea-digital-port
source venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
curl http://127.0.0.1:8000/health
# 应返回 {"status":"ok"}
kill %1   # 停止测试进程
```

---

## 4. Nginx 配置（集成方案）

### 核心思路

线上已有 nginx 站点配置（go-aiport.com），要点是：
- **不破坏现有站点** — 保留已有 index.html 和 SPA 路由
- **新增 API 反向代理** — `/api/*` → FastAPI（127.0.0.1:8000）
- **新增静态页面** — `pricing.html` 和 `admin/` 直接由 nginx 提供
- **调整 fallback 规则** — 现有 `try_files $uri $uri/ /index.html` 会导致 `/admin/` 也被 fallback，需增加精准路由

### 4.1 找到现有 nginx 配置

```bash
sudo nginx -t  # 测试配置，确认配置文件路径
sudo ls /etc/nginx/sites-enabled/
sudo ls /etc/nginx/sites-available/
```

### 4.2 配置内容

创建/更新 `/etc/nginx/sites-available/go-aiport.com`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name go-aiport.com www.go-aiport.com;

    # Let's Encrypt 验证（保持已有配置）
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # HTTP → HTTPS 重定向
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name go-aiport.com www.go-aiport.com;

    # SSL 证书（Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/go-aiport.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/go-aiport.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    server_tokens off;

    # 静态文件根目录
    root /var/www/china-korea-digital-port;
    index index.html;

    # ──────────── API 反向代理 ────────────
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        client_max_body_size 20M;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }

    # API 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    # ──────────── 管理后台 ────────────
    # admin/index.html 是静态文件，直接由 nginx 提供
    location /admin/ {
        try_files $uri $uri/ /admin/index.html;
    }

    # ──────────── 定价页 ────────────
    # pricing.html 是静态文件，直接由 nginx 提供
    location /pricing {
        try_files $uri /pricing.html;
    }
    location /pricing.html {
        # 直接命中静态文件
    }

    # ──────────── 静态资源缓存 ────────────
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
        log_not_found off;
    }

    # ──────────── SPA 路由回退 ────────────
    # 仅对非 /api/ /admin/ /pricing 路径回退到 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ──────────── 安全 ────────────
    location ~ /\. {
        deny all;
        access_log off;
    }
    location ~* \.(env|git|log|bak|swp|sqlite|db)$ {
        deny all;
        return 404;
    }

    # 日志
    access_log /var/log/nginx/go-aiport-access.log;
    error_log  /var/log/nginx/go-aiport-error.log;
}
```

### 4.3 启用配置

```bash
# 如果已有配置，备份
sudo cp /etc/nginx/sites-available/go-aiport.com /etc/nginx/sites-available/go-aiport.com.bak.$(date +%Y%m%d)

# 写入新配置（或用 vim/nano 编辑）
sudo tee /etc/nginx/sites-available/go-aiport.com > /dev/null << 'NGINX_EOF'
# ... 粘贴上述配置 ...
NGINX_EOF

# 测试并重载
sudo nginx -t
sudo systemctl reload nginx
```

### 4.4 关键改动说明（不破坏已有站点）

| 改动 | 说明 |
|------|------|
| 新增 `location /api/` | 反向代理到 FastAPI:8000 |
| 新增 `location /admin/` | 提供管理后台静态文件 |
| 新增 `location /pricing` | 提供定价页静态文件 |
| 保持 `location /` | SPA 回退到 index.html（已有行为不变） |
| 更新 root 路径 | 从旧目录改为 `/var/www/china-korea-digital-port` |

---

## 5. 后端进程管理（Systemd）

推荐使用 Systemd（Ubuntu 默认，比 Supervisor 更轻量）。

### 5.1 创建 Service 文件

```bash
sudo tee /etc/systemd/system/ckdp-backend.service > /dev/null << 'EOF'
[Unit]
Description=中韩出海数智港 Backend API (FastAPI)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/china-korea-digital-port
Environment=PATH=/var/www/china-korea-digital-port/venv/bin
ExecStart=/var/www/china-korea-digital-port/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5
StartLimitInterval=0
StartLimitBurst=3

# 日志
StandardOutput=append:/var/log/ckdp-backend.log
StandardError=append:/var/log/ckdp-backend-error.log

[Install]
WantedBy=multi-user.target
EOF
```

### 5.2 创建日志目录及权限

```bash
sudo mkdir -p /var/log/ckdp
sudo touch /var/log/ckdp/backend.log /var/log/ckdp/backend-error.log
sudo chown -R www-data:www-data /var/log/ckdp

# 数据库目录权限（backend/data/ 需要写入）
sudo chown -R www-data:www-data /var/www/china-korea-digital-port/backend/data
sudo chmod 755 /var/www/china-korea-digital-port/backend/data
```

### 5.3 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable ckdp-backend
sudo systemctl start ckdp-backend

# 检查状态
sudo systemctl status ckdp-backend

# 查看日志
sudo journalctl -u ckdp-backend -f
tail -f /var/log/ckdp/backend.log
```

### 5.4 常用管理命令

```bash
sudo systemctl restart ckdp-backend   # 重启
sudo systemctl stop ckdp-backend      # 停止
sudo systemctl start ckdp-backend     # 启动
sudo journalctl -u ckdp-backend -n 50 # 最近50行日志
```

### 5.5 日志轮转

```bash
sudo tee /etc/logrotate.d/ckdp-backend > /dev/null << 'EOF'
/var/log/ckdp/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

---

## 6. 新页面路由策略（定价页 + 管理后台）

### 原理说明

项目使用 SPA 路由模式：所有未匹配路径 fallback 到 `index.html`。
这意味着浏览器访问 `/pricing` 或 `/admin/` 时，nginx 会先：

1. 查找 `/pricing.html` / `/admin/index.html` 物理文件
2. 找到则直接返回
3. 找不到则 fallback 到 `/index.html`（首页）

### 具体表现

| URL | 线上当前行为 | 部署后行为 |
|-----|-------------|-----------|
| `/` | 首页 ✓ | 首页 ✓ |
| `/pricing` | 返回首页（无pricing.html） | 显示定价页面 |
| `/pricing.html` | 返回首页 | 显示定价页面 |
| `/admin/` | 返回首页 | 显示管理后台 |
| `/admin/index.html` | 返回首页 | 显示管理后台 |
| `/api/v1/...` | 502/404（无后端） | 正确返回 API 数据 |
| `/some-random-path` | 返回首页（SPA回退） | 返回首页（SPA回退） ✓ |

### JS 导航处理

如果前端 JS 中有 SPA 式路由（如点击"定价"按钮用 JS 跳转），需要确保导航使用 `<a href="/pricing">` 而不是 hash 路由或 JS 模拟跳转。

检查 `index.html` 中定价链接的写法：

```html
<!-- ✅ 正确：真实 URL 跳转 -->
<a href="/pricing.html">定价方案</a>
或
<a href="/pricing">定价方案</a>

<!-- ❌ 错误：hash 路由 -->
<a href="#pricing">定价方案</a>
```

如果现有代码使用 `#` 跳转（锚点），需要修改为真实路径跳转。

---

## 7. 一键部署脚本

在项目根目录创建 `deploy-prod.sh`（在**服务器**上运行）：

```bash
#!/usr/bin/env bash
# 中韩出海数智港 — 生产部署脚本
set -euo pipefail

APP_DIR="/var/www/china-korea-digital-port"
SERVICE_NAME="ckdp-backend"

echo "===== 部署开始: $(date) ====="

# 1. 拉取最新代码
cd $APP_DIR
git pull origin main

# 2. 更新 Python 依赖
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 3. 更新权限
sudo chown -R www-data:www-data $APP_DIR/backend/data

# 4. 重启后端
sudo systemctl restart $SERVICE_NAME
sleep 2

# 5. 重载 Nginx
sudo nginx -t
sudo systemctl reload nginx

# 6. 健康检查
echo ""
echo "--- 健康检查 ---"
curl -sf http://127.0.0.1:8000/health && echo " ✓ API 正常" || echo " ✗ API 异常"
curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1/ && echo " ✓ 前端正常" || echo " ✗ 前端异常"
curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1/pricing && echo " ✓ 定价页正常" || echo " ✗ 定价页异常"
curl -sf -o /dev/null -w "%{http_code}" http://127.0.0.1/admin/ && echo " ✓ 管理后台正常" || echo " ✗ 管理后台异常"

echo "===== 部署完成: $(date) ====="
```

使用方式：

```bash
# 服务器上
chmod +x deploy-prod.sh
sudo ./deploy-prod.sh
```

---

## 8. 验证清单

部署完成后，逐项验证：

### 8.1 基础访问

```bash
# 首页
curl -sI https://go-aiport.com/ | head -1
# 预期: HTTP/2 200

# 定价页
curl -sI https://go-aiport.com/pricing | head -1
# 预期: HTTP/2 200
curl -sI https://go-aiport.com/pricing.html | head -1
# 预期: HTTP/2 200

# 管理后台
curl -sI https://go-aiport.com/admin/ | head -1
# 预期: HTTP/2 200
```

### 8.2 API 健康检查

```bash
curl https://go-aiport.com/health
# 预期: {"status":"ok"}

curl https://go-aiport.com/api/v1/pricing
# 预期: {"success":true,"plans":[...]}
```

### 8.3 表单提交测试

```bash
curl -X POST https://go-aiport.com/api/v1/contact \
  -H "Content-Type: application/json" \
  -d '{"name":"测试用户","email":"test@example.com","message":"测试消息"}'
# 预期: {"success":true,"message":"感谢您的咨询！..."}
```

### 8.4 SPA 回退

```bash
curl -sI https://go-aiport.com/任意不存在的路径 | head -1
# 预期: HTTP/2 200 (返回 index.html 内容)
# 不应是 404
```

### 8.5 安全

```bash
# .git 目录应被禁止
curl -sI https://go-aiport.com/.git/config
# 预期: HTTP/2 403 或 404

# 数据库文件应被禁止
curl -sI https://go-aiport.com/backend/data/portal.db
# 预期: HTTP/2 404
```

---

## 9. 回滚方案

### 9.1 代码回滚

```bash
cd /var/www/china-korea-digital-port
git log --oneline -10          # 查看提交历史
git reset --hard <PREVIOUS_HASH>  # 回滚到指定版本
sudo systemctl restart ckdp-backend
```

### 9.2 Nginx 配置回滚

```bash
sudo cp /etc/nginx/sites-available/go-aiport.com.bak.<DATE> \
        /etc/nginx/sites-available/go-aiport.com
sudo nginx -t
sudo systemctl reload nginx
```

### 9.3 完整回滚

```bash
# 停用后端
sudo systemctl stop ckdp-backend
sudo systemctl disable ckdp-backend

# 恢复 nginx 配置（去掉 API 代理和新页面路由）
# ... 还原到备份版本 ...

# 重启 nginx
sudo systemctl restart nginx
```

---

## 附录 A：快速部署命令汇总

```bash
# === 本地（开发者电脑）===
# 1. 提交代码
cd /path/to/china-korea-digital-port
git add .
git commit -m "feat: 完整后端 + 新页面"
git push origin main

# === 服务器（ssh opc@47.100.160.250）===
# 2. 首次部署
sudo apt-get install -y python3 python3-pip python3-venv nginx git sqlite3
sudo mkdir -p /var/www/china-korea-digital-port
sudo chown opc:opc /var/www/china-korea-digital-port
cd /var/www/china-korea-digital-port
git clone https://github.com/eagle13579/china-korea-digital-port.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install uvicorn[standard]

# 3. 配置 systemd 服务
# （参考第5节，创建 /etc/systemd/system/ckdp-backend.service）

# 4. 配置 nginx
# （参考第4节，更新 /etc/nginx/sites-available/go-aiport.com）
sudo nginx -t && sudo systemctl reload nginx

# 5. 启动后端
sudo systemctl daemon-reload
sudo systemctl enable --now ckdp-backend

# 6. 验证
curl http://127.0.0.1:8000/health
curl -I https://go-aiport.com/
curl -I https://go-aiport.com/pricing
curl -I https://go-aiport.com/admin/
```

## 附录 B：常见问题

**Q: 阿里云ECS安全组需要开放哪些端口？**
A: 只需 80 (HTTP) 和 443 (HTTPS)。后端 FastAPI 监听 127.0.0.1:8000，无需开放到公网。

**Q: SQLite 在生产环境够用吗？**
A: 对于中韩出海数智港的初期阶段（日咨询量 < 1000 条），SQLite WAL 模式完全够用。如需扩容，后期可迁移到 PostgreSQL。

**Q: 如何修改管理后台密码？**
A: 编辑 `backend/routers/admin.py`，修改 `ADMIN_PASS = "admin123"` 为强密码，然后 `sudo systemctl restart ckdp-backend`。

**Q: 数据库文件在哪里？**
A: `backend/data/portal.db`（相对于项目根目录）。备份策略建议每日 cron 复制到 `/data/backups/`。

**Q: 如果线上已有 index.html 和本地不同怎么办？**
A: 线上 index.html 部署后会覆盖为 Git 仓库版本。如果线上有用户自定义修改，先在本地合并或备份线上版本。建议首次部署前在服务器上 `cp index.html index.html.bak.$(date +%Y%m%d)`。
