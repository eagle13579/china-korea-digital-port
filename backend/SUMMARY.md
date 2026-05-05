# 中韩出海数智港 Phase 1 — 烛龙技术分析报告

## 项目现状
- 项目路径：`D:/向海容的知识库/wiki/wiki/记忆宫殿/L3工作室/出海项目/中韩出海数智港/china-korea-digital-port/`
- 已完成：静态落地页 (index.html + css/style.css + js/main.js)
- 功能：中韩双语切换、深色/浅色主题、滚动动画、表单（目前仅前端模拟提交）
- 域名：go-aiport.com (CNAME 记录)

## 技术方案核心结论

### 1. 技术栈
**FastAPI + SQLite + SQLModel**
- 选 FastAPI 而非 Flask：异步性能更好、Pydantic 自动校验、自动 API 文档、Phase 2 扩展性好
- 选 SQLite 而非 PostgreSQL：Phase 1 零运维、一个文件搞定、后续迁移只需改连接字符串
- SQLModel 同时做 ORM 和 Pydantic schema，减少重复代码

### 2. 目录结构
```
backend/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 环境变量管理
│   ├── database.py      # SQLite 初始化 (WAL模式)
│   ├── models/          # contact, demo, pricing, payment
│   ├── schemas/         # Pydantic 校验模型
│   ├── routers/         # API 路由
│   ├── services/        # 邮件通知、支付逻辑
│   └── utils/i18n.py    # 双语错误消息
├── data/                # SQLite 数据库文件
├── deploy/              # Nginx配置 + systemd服务
└── requirements.txt
```

### 3. 数据库设计
5张表：contacts (联系表单), demo_requests (预约演示), pricing_plans (定价方案), orders (订单/支付记录)
- 预留了 status 状态机、lang 字段、索引
- 开启 WAL 模式解决并发问题

### 4. 开发步骤 (7.5人天)
1. 后端脚手架搭建 (1天)
2. 联系表单落库 (1天)
3. 预约演示落库 (0.5天)
4. 邮件通知服务 (1天)
5. 定价页面 + API (1天)
6. 支付流程对接 (2天)
7. 部署上线 (1天)

建议分 3 次发布：Release 1 (Week 1, 表单落库) → Release 2 (Week 2, 定价+邮件) → Release 3 (Week 3, 支付+全量)

### 5. 部署方案
Nginx (SSL终结, 静态文件) → proxy_pass /api/* → uvicorn (systemd管理, 127.0.0.1:8000)
- HTTPS 必须 (支付接口要求)
- 安全组开放 22/80/443
- 使用 Let's Encrypt 免费证书

### 6. 关键风险
- SQLite 并发写入：生产 QPS>50 需迁移 PG
- 支付对接复杂度：优先 Stripe (支持中韩支付)
- 阿里云 ECS 25端口封禁：必须用第三方邮件 API (SendGrid/阿里云邮件推送)
- 跨境支付合规：确认 Stripe CNY/KRW 结算支持

## 已修改文件
- `js/main.js`：表单提交从模拟 alert 改为 fetch POST 调用后端 API，增加了双语提示、按钮防重复提交、错误处理

## 创建文件
- `backend/TECHNICAL_PLAN.md`：完整技术方案文档 (18.8K)
- `backend/` 目录已创建

## 备注
- 无法 SSH 到阿里云 ECS (47.100.160.250)，需要先配置 SSH 密钥和网络可达性
- 项目已有 Git 仓库，建议在 backend 开发完成后推送部署
