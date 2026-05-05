# 中韩出海数智港 · 即刻部署指南 (DEPLOY_NOW)

**部署顺序**: 阶段1 → 阶段2 → 阶段3 → 阶段4（按优先级递减）
**预计总时间**: 约2小时（含等待时间）
**服务器**: 47.100.160.250 | 用户: opc | 阿里云ECS Ubuntu nginx/1.24.0

---

## 前置条件：SSH连接

当前WSL环境无法SSH到服务器（超时），需要您确认SSH方式：

```bash
# 方式A：密码登录
ssh opc@47.100.160.250
# 需要输入密码（请告诉我密码，或者输入）

# 方式B：使用SSH密钥（推荐）
ssh -i ~/.ssh/your_key opc@47.100.160.250

# 方式C：阿里云控制台VNC
# 登录阿里云 → ECS控制台 → 远程连接 → VNC/Workbench
```

确认SSH可用后，直接从 **阶段1** 开始。

---

## 阶段1：安全修补 & SSL修复（P0 — 立刻修）

**目标**: 修复portal.db和.git暴露、SSL证书错误
**预计时间**: 30分钟
**依赖**: SSH可用

### Step 1.1 — 修复SSL证书

```bash
# SSH到服务器
ssh opc@47.100.160.250

# 运行SSL修复脚本（重新签发证书，覆盖 go-aiport.com + www.go-aiport.com）
cd /var/www/china-korea-digital-port
sudo bash deploy/ssl-fix.sh
```

如果deploy目录还没在服务器上，先手动复制或git clone后运行。

### Step 1.2 — 手动修复nginx安全规则（线上紧急修补）

在服务器上直接编辑当前nginx配置：

```bash
# 备份
sudo cp /etc/nginx/sites-enabled/opc-api /etc/nginx/sites-enabled/opc-api.bak

# 编辑
sudo vim /etc/nginx/sites-enabled/opc-api
```

**在 server block 内添加**：
```nginx
# 拒绝访问敏感文件
location ~ \.(db|sqlite|sqlite3)$ {
    deny all;
    return 404;
}
location ~ /\. {
    deny all;
    return 404;
}
location ~ \.(env|git|log|bak|swp|yml|json)$ {
    deny all;
    return 404;
}
```

**验证并重载**：
```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Step 1.3 — 验证安全修复

```bash
# 确认portal.db 404
curl -sI --insecure https://go-aiport.com/backend/data/portal.db | head -1

# 确认.git/config 404
curl -sI --insecure https://go-aiport.com/.git/config | head -1

# 确认网站仍正常
curl -sI --insecure https://go-aiport.com/ | head -1
```

期望结果：portal.db和.git返回404，首页返回200。

---

## 阶段2：代码提交 & 后端部署（P1 — 今天修）

**目标**: 发布代码安全修复、上线FastAPI后端、启动管理后台和定价页
**预计时间**: 60分钟
**依赖**: 阶段1完成、SSH可用

### Step 2.1 — GitHub Push

**在本地执行**（WSL环境）：

```bash
# 确认代码目录
cd /mnt/d/向海容的知识库/wiki/wiki/记忆宫殿/L3工作室/出海项目/中韩出海数智港/china-korea-digital-port

# 查看当前Git状态
git status

# 添加所有修改（含deploy/目录、backend/修复、.env.example等）
git add -A
git commit -m "fix: 安全修复 + 部署脚本 — 密码移入环境变量、CORS修复、nginx安全规则、systemd服务、一键部署脚本"

# Push到GitHub
git push origin main
```

> ⚠️ 如果SSH key没配置，也可能需要GitHub token登录。

### Step 2.2 — 服务器拉取代码

```bash
# SSH到服务器
ssh opc@47.100.160.250

# 拉取最新代码
cd /var/www/china-korea-digital-port
git pull origin main
```

### Step 2.3 — 配置环境变量

```bash
cd /var/www/china-korea-digital-port

# 创建.env文件（复制示例后修改）
cp .env.example .env

# 编辑.env — 设置生产密码
vim .env
```

**.env 内容参考**：
```
# 管理后台 — 务必修改密码！
ADMIN_USER=admin
ADMIN_PASS=你的强密码（至少16位随机字符）

# Token密钥 — 务必修改！
TOKEN_SECRET=你的随机密钥（至少32位随机字符）

# CORS — 生产环境设置为具体域名
ALLOWED_ORIGINS=https://go-aiport.com,https://www.go-aiport.com

# 数据库目录（可选，默认使用backend/data/）
# DB_DIR=/var/data/ckdp
```

### Step 2.4 — 运行一键部署脚本

```bash
cd /var/www/china-korea-digital-port
sudo bash deploy/deploy.sh
```

部署脚本会自动完成：
- ✅ 安装Python依赖
- ✅ 复制nginx配置并reload
- ✅ 创建systemd服务并启动
- ✅ 执行健康检查

### Step 2.5 — 验证部署

```bash
# 检查服务状态
sudo systemctl status ckdp-backend

# 检查API
curl http://127.0.0.1:8000/health

# 检查网站（通过nginx）
curl -s https://go-aiport.com/health
curl -s https://go-aiport.com/api/v1/pricing

# 检查定价页
curl -s https://go-aiport.com/pricing.html | head -5

# 检查管理后台
curl -s https://go-aiport.com/admin/ | head -5

# 再次确认安全规则生效
curl -sI https://go-aiport.com/backend/data/portal.db | head -1  # 应返回404
curl -sI https://go-aiport.com/.git/config | head -1  # 应返回404
```

**期望结果**：
| 端点 | 预期响应 |
|:-----|:---------|
| https://go-aiport.com/ | 200 index.html（首页） |
| https://go-aiport.com/health | 200 {"status":"ok"} |
| https://go-aiport.com/api/v1/pricing | 200 JSON定价方案 |
| https://go-aiport.com/pricing.html | 200 定价页面 |
| https://go-aiport.com/admin/ | 200 管理后台首页 |
| https://go-aiport.com/backend/data/portal.db | **404** |
| https://go-aiport.com/.git/config | **404** |

---

## 阶段3：代码质量修复（P2 — 本周修）

**目标**: 修复Critical/High级别的代码质量问题
**预计时间**: 2-3小时
**依赖**: 阶段2完成

### 优先级排序

| 优先级 | 问题 | 修复方案 |
|:------:|:-----|:---------|
| 🛑 P0 | 硬编码密码→环境变量 | ✅ **已修复**（阶段2已部署） |
| 🛑 P0 | CORS配置 | ✅ **已修复**（阶段2已部署） |
| 🛑 P0 | portal.db暴露 | ✅ **已修复**（阶段1 nginx deny） |
| 🟠 P1 | 路径遍历风险 | 后端static路由加固或改用StaticFiles |
| 🟠 P1 | 无CSRF防护 | 添加 fastapi-csrf-protect |
| 🟠 P1 | 无登录速率限制 | 添加 slowapi 库 |
| 🟠 P1 | Token存储方式 | localStorage → httpOnly Cookie |
| 🟡 P2 | 无连接池 | 改用 aiosqlite + 异步连接 |
| 🟡 P2 | 无日志系统 | 添加 loguru 配置 |
| 🟡 P2 | 错误信息泄露 | 统一异常处理+环境判断 |
| 🟡 P2 | 重复代码模式 | 提取通用数据库操作函数 |

### 快速修复指南

```bash
# 在本地修复（WSL环境）
cd /mnt/d/.../china-korea-digital-port

# 修复路径遍历（main.py中静态路由分配）
# 修复后 commit & push
git add -A && git commit -m "fix: 路径遍历+日志+错误处理" && git push origin main

# 服务器拉取
ssh opc@47.100.160.250 "cd /var/www/china-korea-digital-port && git pull && sudo systemctl restart ckdp-backend"
```

---

## 阶段4：北极星维度代码实现（P3 — 本月修）

**目标**: 推进各维度的代码缺口
**预计时间**: 取决于功能复杂度
**依赖**: 阶段3完成

| 维度 | 当前 | 目标 | 需要做什么 |
|:-----|:----:|:----:|:-----------|
| A1友虾 | 0% | 50% | 接入友虾6个API（最优先—最多增量） |
| A2链客宝 | 0% | 50% | 链客宝11个功能模块对接（依赖建平） |
| B数字员工 | 0% | 30% | 合规数字员工DEMO代码化（有文档） |
| C商业化 | 3% | 25% | 支付接入(Stripe/支付宝) + 报价生成 |
| E供应链 | 0% | 25% | 合作方管理模块+浩然韩企对接 |

---

## 项目文件结构（部署后）

```
/var/www/china-korea-digital-port/
├── index.html          ← 首页（静态）
├── pricing.html        ← 定价页（静态）
├── favicon.ico
├── admin/
│   └── index.html      ← 管理后台（静态，Alpine.js）
├── css/     style.css
├── js/      main.js
├── backend/
│   ├── main.py         ← FastAPI入口（uvicorn启动）
│   ├── database.py     ← SQLite数据库
│   ├── routers/
│   │   ├── contact.py  ← POST /api/v1/contact
│   │   ├── demo.py     ← POST /api/v1/demo
│   │   ├── pricing.py  ← GET/POST /api/v1/pricing
│   │   └── admin.py    ← 管理后台API
│   └── data/portal.db  ← 数据库
├── deploy/
│   ├── nginx.conf            ← nginx安全配置
│   ├── ckdp-backend.service  ← systemd服务文件
│   ├── deploy.sh             ← 一键部署脚本
│   └── ssl-fix.sh            ← SSL修复脚本
├── .env                      ← 环境变量（包含密码，.gitignore）
├── .env.example              ← 环境变量模板
├── requirements.txt           ← Python依赖
├── DEPLOY.md                  ← 旧部署文档
└── DEPLOY_NOW.md              ← 本部署指南
```

## 流量流向

```
用户 → HTTPS (443) → Nginx (部署nginx.conf)
    ├── /api/*        → proxy_pass → http://127.0.0.1:8000 (FastAPI)
    ├── /health       → proxy_pass → http://127.0.0.1:8000 (FastAPI)
    ├── /admin/       → alias → /var/www/.../admin/index.html (SPA)
    ├── /pricing.html → 静态文件
    ├── /css/, /js/   → 静态文件（缓存1年）
    ├── /             → index.html
    └── *.db, .git, .env → deny all (404)
```

---

## 回退方案

如果部署后出现问题：

```bash
# 回退nginx配置
sudo cp /etc/nginx/sites-enabled/opc-api.bak /etc/nginx/sites-enabled/opc-api
sudo systemctl reload nginx

# 停止后台服务
sudo systemctl stop ckdp-backend
sudo systemctl disable ckdp-backend

# 恢复Git版本
cd /var/www/china-korea-digital-port
git reset --hard HEAD~1
```
