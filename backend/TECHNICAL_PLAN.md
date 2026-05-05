# 中韩出海数智港 - Phase 1 技术方案

> 作者：烛龙 (P8 研发工程师)
> 日期：2026-05-04
> 前置：静态官网已完成 (HTML+CSS+JS, 中韩双语, 深色/浅色主题)

---

## 一、技术栈选择

### 1.1 FastAPI vs Flask

| 维度 | FastAPI | Flask |
|------|---------|-------|
| 性能 | 异步原生, 性能高 | WSGI同步, 需额外配异步 |
| 文档 | 自动生成 OpenAPI/Swagger | 需手动配 Flasgger |
| 类型安全 | 原生 Pydantic 校验 | 需额外配 marshmallow |
| 学习成本 | 中等 (需理解 async) | 低 |
| 生态成熟度 | 较新但社区活跃 | 极成熟 |

**结论：选 FastAPI。** 理由：
- Phase 1是起步，但Phase 2-3会有更多API（用户系统、数据分析），FastAPI的可扩展性更好
- Pydantic 模型可直接用于表单校验和数据库 ORM (SQLModel)
- 自动生成的中韩双语 API 文档方便后续协作和前端对接
- 阿里云 ECS 部署通过 uvicorn/gunicorn 加 systemd 即可，运维成本与 Flask 相当

### 1.2 辅助库选型

```
fastapi           # web框架
uvicorn[standard]  # ASGI服务器
sqlmodel          # SQLite ORM (SQLAlchemy+Pydantic融合)
python-multipart  # 表单解析
pydantic          # 数据校验 (FastAPI自带)
jinja2            # 如果需要服务端渲染定价页 (可选, 建议纯前端)
httpx             # 异步HTTP客户端 (后续支付回调用)
stripe / alipay-sdk-python  # 支付 (Phase 1.2)
python-jose[cryptography]   # JWT (后续用户系统)
```

---

## 二、目录结构

```
china-korea-digital-port/
├── index.html                 # 前端静态页面 (已有)
├── css/style.css              # 样式 (已有)
├── js/main.js                 # 前端JS (已有)
├── backend/                   # ★ 后端代码目录 (新建)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app 入口
│   │   ├── config.py          # 配置管理 (环境变量)
│   │   ├── database.py        # 数据库连接与初始化
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── contact.py     # 联系表单模型
│   │   │   ├── demo.py        # 预约演示模型
│   │   │   ├── pricing.py     # 定价/订阅模型
│   │   │   └── payment.py     # 支付记录模型
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── contact.py     # 联系表单 Pydantic schema
│   │   │   ├── demo.py
│   │   │   └── payment.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── contact.py     # POST /api/v1/contact
│   │   │   ├── demo.py        # POST /api/v1/demo
│   │   │   ├── pricing.py     # GET /api/v1/pricing
│   │   │   └── payment.py     # POST /api/v1/payment, webhook
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── email.py       # 邮件通知服务
│   │   │   └── payment.py     # 支付逻辑
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── i18n.py        # 双语错误消息
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_contact.py
│   │   ├── test_demo.py
│   │   └── test_payment.py
│   ├── data/                  # SQLite 数据库文件目录
│   │   └── .gitkeep
│   ├── requirements.txt
│   ├── .env.example           # 环境变量模板
│   └── deploy/
│       ├── nginx-backend.conf # Nginx 反向代理配置
│       └── fastapi.service    # systemd 服务单元
├── pricing.html               # 定价页面 (新增)
├── checkout.html              # 付款页面 (新增)
├── css/
│   └── pricing.css            # 定价页样式 (新增)
└── js/
    └── pricing.js             # 定价页交互 (新增)
```

---

## 三、数据库设计 (SQLite)

### 3.1 表结构

```sql
-- 联系表单 (P1-2)
CREATE TABLE contacts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       VARCHAR(200) NOT NULL,
    contact_name  VARCHAR(100) NOT NULL,
    phone         VARCHAR(50)  NOT NULL,
    email         VARCHAR(200) NOT NULL,
    message       TEXT,
    source        VARCHAR(20)  DEFAULT 'website',  -- website, landing, referral
    lang          VARCHAR(5)   DEFAULT 'zh-CN',     -- 提交时使用的语言
    status        VARCHAR(20)  DEFAULT 'new',       -- new, contacted, converted, closed
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- 预约演示 (P1-2)
CREATE TABLE demo_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       VARCHAR(200) NOT NULL,
    contact_name  VARCHAR(100) NOT NULL,
    email         VARCHAR(200) NOT NULL,
    phone         VARCHAR(50),
    preferred_date DATE,
    preferred_time VARCHAR(20),  -- 时间段
    notes         TEXT,
    lang          VARCHAR(5)   DEFAULT 'zh-CN',
    status        VARCHAR(20)  DEFAULT 'pending',   -- pending, confirmed, completed, cancelled
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- 定价方案 (P1-4)
CREATE TABLE pricing_plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name_zh       VARCHAR(100) NOT NULL,   -- 中文名称
    name_ko       VARCHAR(100) NOT NULL,   -- 韩文名称
    slug          VARCHAR(50)  UNIQUE NOT NULL,  -- basic, pro, enterprise
    price_monthly DECIMAL(10,2),
    price_yearly  DECIMAL(10,2),
    currency      VARCHAR(3)   DEFAULT 'CNY',
    features_zh   TEXT,          -- JSON array of features in Chinese
    features_ko   TEXT,          -- JSON array of features in Korean
    is_active     BOOLEAN      DEFAULT 1,
    sort_order    INTEGER      DEFAULT 0,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- 订单/支付记录 (P1-4)
CREATE TABLE orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no        VARCHAR(50) UNIQUE NOT NULL,  -- 订单号
    plan_id         INTEGER REFERENCES pricing_plans(id),
    company         VARCHAR(200) NOT NULL,
    contact_name    VARCHAR(100) NOT NULL,
    email           VARCHAR(200) NOT NULL,
    phone           VARCHAR(50),
    billing_type    VARCHAR(10)  NOT NULL,  -- monthly, yearly
    amount          DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3)   DEFAULT 'CNY',
    payment_method  VARCHAR(30),              -- stripe, alipay, wechat, bank_transfer
    payment_status  VARCHAR(20)  DEFAULT 'pending',  -- pending, paid, failed, refunded
    transaction_id  VARCHAR(200),             -- 第三方支付平台交易ID
    paid_at         TIMESTAMP,
    lang            VARCHAR(5)   DEFAULT 'zh-CN',
    notes           TEXT,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_status ON contacts(status);
CREATE INDEX idx_demo_status ON demo_requests(status);
CREATE INDEX idx_orders_order_no ON orders(order_no);
CREATE INDEX idx_orders_email ON orders(email);
CREATE INDEX idx_orders_payment_status ON orders(payment_status);
```

### 3.2 数据库设计说明

1. **为什么不选 MySQL/PostgreSQL？**
   - Phase 1 日均请求 < 1000，SQLite 完全够用
   - 零运维，不需要额外装数据库服务
   - 部署简单：一个文件，备份也一样
   - 后续迁移到 PostgreSQL 时，SQLModel 的 ORM 层只需改连接字符串

2. **SQLite 并发注意**：
   - FastAPI 异步模式下，用 `sqlite:///data/portal.db?check_same_thread=False`
   - 生产配置 WAL 模式：`PRAGMA journal_mode=WAL;`
   - 日活几千没问题，超过 1W 日活再考虑迁移 PG

---

## 四、API 设计

### 4.1 联系表单 API

```
POST /api/v1/contact
Content-Type: application/json

Request:
{
  "company": "某科技有限公司",
  "contact_name": "张三",
  "phone": "13800138000",
  "email": "zhang@example.com",
  "message": "想了解韩国市场准入服务",
  "lang": "zh-CN"
}

Response 201:
{
  "code": 0,
  "message": "提交成功 / 제출 성공",
  "data": { "id": 1 }
}
```

### 4.2 预约演示 API

```
POST /api/v1/demo
Content-Type: application/json

Request:
{
  "company": "某科技",
  "contact_name": "张三",
  "email": "zhang@example.com",
  "phone": "13800138000",
  "preferred_date": "2026-05-10",
  "preferred_time": "14:00-15:00",
  "notes": "韩国电商方向"
}

Response 201:
{
  "code": 0,
  "message": "预约成功",
  "data": { "id": 1 }
}
```

### 4.3 定价方案 API

```
GET /api/v1/pricing?lang=zh-CN

Response:
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "name": "基础版",
      "slug": "basic",
      "price_monthly": 0,
      "price_yearly": 0,
      "currency": "CNY",
      "features": ["AI市场报告月报", "基础数据分析", ...],
      "is_free": true
    },
    ...
  ]
}
```

### 4.4 支付 API

```
POST /api/v1/payment/create
Content-Type: application/json

Request:
{
  "plan_id": 2,
  "billing_type": "monthly",
  "company": "某科技",
  "contact_name": "张三",
  "email": "zhang@example.com",
  "phone": "13800138000"
}

Response:
{
  "code": 0,
  "data": {
    "order_no": "ORD20260504001",
    "amount": 299.00,
    "currency": "CNY",
    "payment_url": "https://...",    // 跳转到支付网关
    "expires_at": "2026-05-04T22:30:00"
  }
}

POST /api/v1/payment/webhook  (第三方支付回调)
```

---

## 五、开发步骤与工作量预估

### Step 1: 后端脚手架搭建 (1人天)

- 创建 backend 目录结构
- FastAPI app 入口 main.py
- config.py 环境变量管理
- database.py SQLite 初始化 + WAL 模式
- requirements.txt
- .env.example
- 验证：`uvicorn app.main:app --reload` 能跑起来，访问 /docs 看到 Swagger

### Step 2: 联系表单落库 (1人天)

- Contact model (sqlmodel)
- ContactCreate schema (pydantic)
- POST /api/v1/contact router
- 表单数据校验 (中国手机号格式、邮箱格式)
- 防重提交 (同一邮箱 5分钟内不重复)
- 修改前端 js/main.js 表单提交逻辑：从 alert 改为 fetch POST
- 验证：提交表单 → 检查 SQLite 数据行

### Step 3: 预约演示落库 (0.5人天)

- DemoRequest model
- POST /api/v1/demo router
- 前端 "预约演示" 表单或弹窗组件
- 验证同上

### Step 4: 邮件通知服务 (1人天)

- 配置 SMTP（阿里云邮件推送 / SendGrid / QQ邮箱）
- 新表单提交时发送通知邮件给销售团队
- 双语邮件模板（根据表单 lang 字段）
- 验证：提交表单 → 收到通知邮件

### Step 5: 定价页面 + API (1人天)

- pricing_plans 表预置种子数据（basic/free, pro, enterprise）
- GET /api/v1/pricing API
- pricing.html 页面（中韩双语，复用主题风格）
- 方案比较表格、功能列表、CTA按钮
- 验证：页面渲染正确，价格数据来自 API

### Step 6: 支付流程 (2人天)

- orders model
- POST /api/v1/payment/create
- 对接支付网关（推荐 Stripe Alipay/WeChat 或 支付宝国际）
- checkout.html 页面（订单确认、支付方式选择）
- 支付回调 webhook 处理
- 支付成功/失败页面
- 验证：模拟支付 → 订单状态更新正确

### Step 7: 部署与上线 (1人天)

- nginx-backend.conf 反向代理配置 (/api/ 转发到 localhost:8000)
- fastapi.service systemd 单元
- 阿里云安全组开放 8000 端口
- SSL 证书（HTTPS必须，支付接口需要）
- 验证：全链路测试

### 总计工作量: ~7.5 人天

| 步骤 | 内容 | 人天 |
|------|------|------|
| 1 | 后端脚手架 | 1 |
| 2 | 联系表单落库 | 1 |
| 3 | 预约演示落库 | 0.5 |
| 4 | 邮件通知 | 1 |
| 5 | 定价页面 | 1 |
| 6 | 支付流程 | 2 |
| 7 | 部署上线 | 1 |
| **合计** | | **7.5** |

---

## 六、关键风险与权衡

### 6.1 风险

| # | 风险 | 概率 | 影响 | 应对方案 |
|---|------|------|------|----------|
| 1 | **SQLite 并发写入瓶颈** | 低 | 中 | 初期足够；监控连接数，QPS>50 时迁移 PostgreSQL |
| 2 | **支付对接复杂度** | 中 | 高 | 优先 Stripe（国际支持中韩支付）；支付宝国际作为备选 |
| 3 | **跨境支付合规** | 中 | 高 | 确认 Stripe 是否支持 CNY/KRW 结算；备选方案用 Ping++ |
| 4 | **前端表单改造成本** | 低 | 低 | 现有 form 是纯静态，改 fetch 提交即可，改动量小 |
| 5 | **邮件送达率** | 中 | 中 | 阿里云 ECS 25端口默认封禁，必须用第三方邮件 API (SendGrid/Alibaba Cloud DirectMail) |
| 6 | **中韩双语错误提示** | 低 | 低 | 在 backend utils/i18n.py 集中管理双语消息 |

### 6.2 权衡决策

1. **SSR vs CSR 定价页**
   - 推荐纯前端渲染 (CSR)，复用现有主题系统
   - 定价数据从 API 获取，flexible 便于后续改价
   - 不需要额外配 Jinja2

2. **单体 vs 微服务**
   - Phase 1 坚决单体。就几个 API 拆微服务纯属过度工程
   - 等后续用户系统、AI 引擎独立时再考虑拆

3. **支付走前端 SDK 还是后端 API**
   - 强制走后端 API：前端 create → 后端返回 payment_url → 前端跳转
   - 不在前端暴露 API 密钥，安全

4. **表单验证前后端都做**
   - 前端做用户体验（即时提示）
   - 后端做安全保障（最终校验）
   - 绝对信任后端校验，前端只是辅助

5. **数据库版本管理**
   - Phase 1 不做 Alembic 迁移工具
   - 直接 SQLModel 的 create_all()，表结构变动时手动处理
   - Phase 2 引入 Alembic

---

## 七、部署方案 (阿里云 ECS)

### 7.1 架构图

```
用户浏览器
    │
    ▼
阿里云 ECS 47.100.160.250:443
    │
    ▼
Nginx (80→443 重定向, SSL 终结)
    ├── / → /root/project/china-korea-digital-port/* (静态文件)
    └── /api/* → proxy_pass http://127.0.0.1:8000 (FastAPI)
                            │
                            ▼
                       uvicorn (systemd 管理)
                            │
                            ▼
                       SQLite (/data/portal.db)
```

### 7.2 部署步骤

```bash
# 1. 服务器初始化
apt update && apt upgrade -y
apt install -y nginx python3 python3-pip python3-venv git

# 2. 上传代码 / 从 Git 拉取
cd /root
git clone https://github.com/xxx/china-korea-digital-port.git

# 3. Python 虚拟环境
cd /root/china-korea-digital-port/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 创建数据目录
mkdir -p data
chmod 755 data

# 5. 配置环境变量
cp .env.example .env
# 编辑 .env: SECRET_KEY, SMTP 配置, 支付密钥等

# 6. 配置 systemd 服务
cp deploy/fastapi.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable fastapi
systemctl start fastapi
systemctl status fastapi

# 7. 配置 Nginx
cp deploy/nginx-backend.conf /etc/nginx/sites-enabled/china-korea-digital-port
nginx -t && systemctl reload nginx

# 8. SSL 证书 (Let's Encrypt)
apt install -y certbot python3-certbot-nginx
certbot --nginx -d go-aiport.com

# 9. 配置防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 7.3 Nginx 配置要点

```nginx
server {
    listen 80;
    server_name go-aiport.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name go-aiport.com;

    ssl_certificate /etc/letsencrypt/live/go-aiport.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/go-aiport.com/privkey.pem;

    # 静态文件 (前端页面)
    root /root/china-korea-digital-port;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }

    # 静态资源缓存
    location /css/ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
    location /js/ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

### 7.4 Systemd 服务单元

```ini
[Unit]
Description=China Korea Digital Port - FastAPI
After=network.target

[Service]
User=root
WorkingDirectory=/root/china-korea-digital-port/backend
ExecStart=/root/china-korea-digital-port/backend/venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 --port 8000 \
    --workers 2 --limit-max-requests 10000
Restart=always
RestartSec=5
EnvironmentFile=/root/china-korea-digital-port/backend/.env

[Install]
WantedBy=multi-user.target
```

---

## 八、特别建议

### 8.1 小步快跑，不要一次上线全部

建议分成 3 次发布：
1. **Release 1 (Week 1)**：Step 1-3 → 联系表单 + 预约演示落库上线
2. **Release 2 (Week 2)**：Step 4-5 → 邮件通知 + 定价页面上线
3. **Release 3 (Week 3)**：Step 6-7 → 支付流程 + 全量上线

### 8.2 安全问题

**绝对不要**:
- 不要把 `.env` 文件提交到 Git
- 不要把 SQLite 文件放在 web 根目录可访问路径
- 不要在 Nginx 的 root 下暴露 /data/ 目录

**必须做**:
- HTTPS only (Let's Encrypt 免费)
- CORS 限制 (只允许 go-aiport.com)
- 表单提交 Rate Limit (同一 IP 每小时最多 10 次)
- 支付 webhook 验证签名

### 8.3 后续 Phase 2 扩展预留

数据库设计已经预留了扩展字段和状态机。Phase 2 可以自然扩展：
- `users` 表 → 用户登录注册
- `contacts` 增加 `assigned_to` → CRM 分配
- `orders` 增加 `invoice_id` → 发票系统
- 从 SQLite 迁移到 PostgreSQL → 改一行连接字符串
