# 合规自检工具 — 产品设计规格书（乘黄交付）

| 元数据 | 值 |
|--------|-----|
| 文档编号 | PRD-007-Design-Spec |
| 产品名称 | 中韩出海数智港 合规自检工具 |
| 产品经理 | 乘黄 (P8) |
| 技术负责人 | 烛龙 (P8) |
| 版本 | 1.0 (Final) |
| 交付日期 | 2026-05-12 |
| 状态 | ✅ 产品设计已完成，可交付开发 |

---

## 1. 交付物清单

| # | 文件 | 路径 | 说明 | 状态 |
|---|------|------|------|------|
| 1 | 题目数据定义 | `backend/compliance/questions_data.py` | 8道题目的中韩双语文案+选项+评分权重 | ✅ |
| 2 | 评分算法引擎 | `backend/compliance/report_score.py` | 总分计算+评级+行动建议+免责声明 | ✅ |
| 3 | PDF报告模板 | `backend/compliance/report_pdf.py` | reportlab PDF模板（含雷达图可视化） | ✅ |
| 4 | 前端设计说明 | `backend/compliance/frontend_design.md` | HTML+Alpine.js结构+交互说明 | ✅ |
| 5 | 模块入口 | `backend/compliance/__init__.py` | 模块说明 | ✅ |

---

## 2. 评分算法详情

### 2.1 计分规则

```
每题选项分值:  0 (合规) / 1 (轻微) / 2 (关注) / 3 (危险)
满分(原始分):  8题 × 3分 = 24分
转化规则:      总分 = ((24 - 各题原始分之和) / 24) × 100
               → 0-100 分制（100分 = 完全合规）
```

### 2.2 评级标准

| 等级 | 分数区间 | 中文标签 | 韩文标签 | 含义 |
|------|---------|---------|---------|------|
| S | ≥ 85 | 优秀 | 우수 | 合规状况良好 |
| A | 70-84 | 良好 | 양호 | 大部分合规 |
| B | 50-69 | 关注 | 주의 | 存在合规缺口 |
| C | 30-49 | 危险 | 위험 | 重大合规风险 |
| D | < 30 | 紧急 | 긴급 | 需要紧急介入 |

### 2.3 单维度评估逻辑

```
raw_score = 0 → dim_score = 100分 → 状态: ✅ 合规
raw_score = 1 → dim_score = 67分  → 状态: ⚡ 需优化
raw_score = 2 → dim_score = 33分  → 状态: ⚠️ 需改善 → 加入优先建议列表
raw_score = 3 → dim_score = 0分   → 状态: 🔴 立即行动 → 加入优先建议列表
```

### 2.4 优先建议排序

按 raw_score 降序排列（最紧急的排最前），每个建议附带：
- 维度名称 + 分数
- 双语行动建议文案（250字以内，具体可操作）
- 对应数字员工推荐

---

## 3. 8道题设计总览

| # | 维度 | 对应员工 | 问题核心 |
|---|------|---------|---------|
| 1 | 行业准入 | 徐准 (P9) | 是否完成中国市场准入可行性评估？ |
| 2 | 外商投资 | 朴泰俊 (P10) | 是否确定投资架构（WFOE/JV/代表处）？ |
| 3 | 数据安全 | 丹书 (P8) | 是否涉及数据跨境传输？ |
| 4 | 知识产权 | 金镇宇 (P8) | 是否完成中国商标/专利布局？ |
| 5 | 劳动用工 | 李朴 (P8) | 员工劳动合同和社保如何安排？ |
| 6 | 财税 | 朴泰俊 (P10) | 是否了解中国税制和中韩税收协定？ |
| 7 | 签证居留 | 崔敏智 (P7) | 韩国籍员工是否已办工作签证？ |
| 8 | 环保 | 徐准 (P9) | 是否涉及环评/排污许可要求？ |

### 设计原则
- **场景化**：每个选项描述具象场景（"已完成..." "正在进行..." "有计划但..." "未开始..."）
- **韩企视角**：提及"韩国总部派遣"、"WFOE"、"中韩税收协定"等韩企关注点
- **风险递进**：四个选项从完全合规到完全不了解，梯度明显
- **数字员工绑定**：每题对应一位合规数字员工，结果页自然引导咨询

---

## 4. PDF报告页面结构

### 第1页：封面+总分
```
┌─────────────────────────────────┐
│   中韩出海数智港                  │
│   合规健康度评估报告              │
│                                 │
│   企业名称: ㈜한국테크            │
│   报告编号: CHC-20260512-A3B4    │
│   生成日期: 2026-05-12           │
│                                 │
│    ┌─────────────────────┐      │
│    │     62 / 100        │      │
│    │   综合评分           │      │
│    │   [B] 关注           │      │
│    └─────────────────────┘      │
│                                 │
│   您的企业存在明显的合规缺口...   │
└─────────────────────────────────┘
```

### 第2页：维度评分+条形图
```
┌─────────────────────────────────┐
│   各维度评分详情                  │
│                                 │
│   维度       得分   状态   员工   │
│   ────────────────────────────  │
│   ✅ 行业准入   100  合规   徐准 │
│   ⚠️ 数据安全    33  需改善 丹书  │
│   ...                           │
│                                 │
│   雷达图（条形可视化）            │
│   行业准入 ██████████ 100分      │
│   数据安全 ███░░░░░░░  33分      │
│   ...                           │
└─────────────────────────────────┘
```

### 第3页：优先建议+免责声明
```
┌─────────────────────────────────┐
│   优先改进建议                    │
│                                 │
│   1. 数据安全 (33分)             │
│      数据安全是中国合规监管的     │
│      重中之重...                 │
│      — 推荐咨询: 丹书(数据合规官) │
│                                 │
│   2. 财税 (33分)                 │
│      中国税制复杂且监管严格...    │
│      — 推荐咨询: 朴泰俊(投资架构) │
│                                 │
│   ────────────────────────────  │
│   相关数字员工推荐                │
│                                 │
│   徐准  市场准入专家              │
│   朴泰俊 投资架构专家             │
│   丹书  数据合规官               │
│                                 │
│   ※ 本报告由AI数字员工自动生成...  │
└─────────────────────────────────┘
```

---

## 5. 对烛龙的技术接口约定

### 5.1 API 路由

烛龙需要在 `backend/routers/` 中新建 `compliance.py`，注册以下路由：

```python
from fastapi import APIRouter, HTTPException, Query
from backend.database import get_db
from backend.compliance.questions_data import get_questions
from backend.compliance.report_score import generate_report_data, calculate_score
from backend.compliance.report_pdf import generate_report_pdf

router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

@router.get("/questions")
async def get_compliance_questions(lang: str = Query("zh", regex="^(zh|ko)$")):
    """获取合规自检题目"""
    questions = get_questions(language=lang)
    return {"success": True, "data": questions}

@router.post("/submit")
async def submit_compliance_check(data: dict):
    """提交自检答案，生成报告"""
    # 1. 验证数据
    # 2. 评分 -> generate_report_data(answers, company_info, language)
    # 3. 生成PDF -> generate_report_pdf(report_data)
    # 4. 存入数据库 compliance_checks 表
    # 5. 返回 token + 报告URL
    pass

@router.get("/report/{token}")
async def get_report_data(token: str):
    """获取报告数据（JSON格式）"""
    pass

@router.get("/report/{token}/pdf")
async def download_report_pdf(token: str):
    """下载PDF报告"""
    pass
```

### 5.2 数据库表结构

烛龙需要在 `database.py` 中增加 `compliance_checks` 表：

```sql
CREATE TABLE IF NOT EXISTS compliance_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    answers TEXT NOT NULL,          -- JSON: {"1": 0, "2": 1, ...}
    company_name TEXT,
    contact_name TEXT,
    email TEXT NOT NULL,
    language TEXT DEFAULT 'zh',
    total_score REAL,               -- 总分
    score_detail TEXT,              -- JSON: 各维度评分详情
    report_generated INTEGER DEFAULT 0,
    report_downloaded INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3 主入口注册

在 `main.py` 中添加：
```python
from backend.routers import compliance
app.include_router(compliance.router)
```

### 5.4 PDF中文显示

需要安装中文字体。PDF引擎使用系统字体，建议：
```bash
# 安装中文字体（服务器上）
apt-get install fonts-noto-cjk

# 或使用项目现有的 Google Noto Sans CJK
# reportlab 中设置: pdfmetrics.registerFont(TTFont('NotoSansSC', 'NotoSansSC-Regular.otf'))
```

项目中已有 `fonts/` 目录，可复用。

---

## 6. 测试用例

### 6.1 典型场景测试

```
场景A: 完全合规的企业（所有题目选0分选项）
  输入: {1:0,2:0,3:0,4:0,5:0,6:0,7:0,8:0}
  总分: 100分 → 评级: S (优秀)
  优先项: 空

场景B: 典型韩企（有准备但存在数据合规和财税盲区）
  输入: {1:0,2:1,3:2,4:0,5:1,6:2,7:0,8:1}
  总分: 70.8分 → 评级: A (良好)
  优先项: 数据安全(33分)、财税(33分)

场景C: 刚起步的企业（大部分领域未开始）
  输入: {1:2,2:2,3:2,4:3,5:2,6:3,7:2,8:2}
  总分: 29.2分 → 评级: D (紧急)
  优先项: 6项（全部需要改善）

场景D: 选择题溢出保护
  输入: {1:999,2:-1,3:0,4:0,5:0,6:0,7:0,8:0}
  处理: raw_score 被截断到 0-3 范围
```

### 6.2 验证命令

```bash
# 运行测试
cd /path/to/project
PYTHONPATH=. python3 -c "
from backend.compliance.report_score import calculate_score
r = calculate_score({1:0,2:1,3:2,4:0,5:1,6:2,7:0,8:1}, language='ko')
print(f'总分: {r[\"total_score\"]}')
print(f'评级: {r[\"level\"]}-{r[\"level_label\"]}')
print(f'优先项: {len(r[\"priorities\"])}项')
for d in r['dimensions']:
    print(f'  {d[\"status_icon\"]} {d[\"dimension_label\"]}: {d[\"dim_score\"]}분 ({d[\"status_label\"]})')
"
```

---

## 7. 不做清单（设计层面）

- ❌ 不是深度25题问卷（MVP仅8题）
- ❌ 不是实时AI对话式（固定选项，不调用LLM）
- ❌ 不是法律效力证书（标注AI生成仅供参考）
- ❌ 不需要用户注册才能答题（报告才需邮箱）
- ❌ 不保存历史报告（无用户系统）
- ❌ 不嵌入第三方CRM（纯自建线索表）

---

*文档结束 — 乘黄交付给烛龙，请据此实现后端开发*
