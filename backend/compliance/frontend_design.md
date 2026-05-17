# 合规自检工具 — 前端页面设计说明

产品经理: 乘黄 (P8)
版本: 1.0 (2026-05-12)

---

## 1. 页面结构

### 页面路由
- `/compliance-check.html` — 主页面（问卷流程）
- 不需要额外页面，报告PDF通过后端生成下载

### 三阶段交互流

```
阶段1: 问卷答题 ────→ 阶段2: 结果预览 ────→ 阶段3: 填写信息获取报告
                         ↓
                     触发后端 → 返回PDF给用户下载
```

---

## 2. 技术方案

使用项目现有技术栈：**Alpine.js + Tailwind CSS + data-lang-key 双语**

### 数据模型 (Alpine.js x-data)

```javascript
{
  // ── 问卷状态 ──
  currentStep: 0,           // 0=开始页, 1-8=题目, 9=结果预览, 10=填写信息
  answers: {},              // {question_id: option_value}
  questions: [],            // 从API获取的题目数据

  // ── 结果状态 ──
  reportData: null,         // 从后端获取的报告数据
  isSubmitting: false,
  isGenerating: false,

  // ── 用户信息 ──
  companyName: '',
  contactName: '',
  email: '',
  agreePrivacy: false,

  // ── UI状态 ──
  errors: {},
  showStartPage: true,

  // ── 计算属性 ──
  get progress() { ... },           // 进度百分比
  get currentQuestion() { ... },    // 当前题目对象
  get totalScore() { ... },         // 已答题的实时分数预览

  // ── 方法 ──
  init() { ... },                   // 加载题目
  selectOption(qId, value) { ... }, // 选择答案
  nextStep() { ... },               // 下一步
  prevStep() { ... },               // 上一步
  submitAnswers() { ... },          // 提交答案获取报告
  downloadPDF() { ... },            // 下载PDF
  reset() { ... },                  // 重新答题
}
```

### 数据持久化
```javascript
// 使用 localStorage 保存答题进度，防止中途离开丢失
// key: 'compliance_check_progress'
// value: { answers: {...}, currentStep: 3, updatedAt: '...' }
// 进入页面时检查 localStorage 是否有未完成的问卷，提示继续
```

---

## 3. HTML结构设计

### 3.1 开始页 (Step 0)

```html
<div x-show="currentStep === 0" class="...">
  <!-- 标题区 -->
  <h1 data-lang-key="compliance_title">合规健康度自检</h1>
  <p data-lang-key="compliance_desc">8道题，3分钟，了解您的中国市场合规状况</p>

  <!-- 数字员工阵容展示 -->
  <div class="flex space-x-4">
    <template x-for="emp in employees" :key="emp.name">
      <div class="employee-badge">
        <span x-text="emp.icon"></span>
        <span x-text="emp.name"></span>
        <span class="text-xs" x-text="emp.role"></span>
      </div>
    </template>
  </div>

  <!-- 隐私声明 -->
  <label>
    <input type="checkbox" x-model="agreePrivacy">
    <span data-lang-key="compliance_privacy">我已阅读并同意《隐私政策》</span>
  </label>

  <!-- 开始按钮 -->
  <button @click="startQuiz()" :disabled="!agreePrivacy"
          class="btn btn--primary">
    <span data-lang-key="compliance_start">开始自检</span>
  </button>
</div>
```

### 3.2 答题页 (Step 1-8)

```html
<div x-show="currentStep >= 1 && currentStep <= 8" class="...">
  <!-- 进度条 -->
  <div class="progress-bar">
    <div class="progress-fill" :style="`width: ${progress}%`"></div>
  </div>
  <div class="flex justify-between text-sm text-gray-500">
    <span x-text="`${currentStep} / 8`"></span>
    <span x-text="`${progress}%`"></span>
  </div>

  <!-- 题目卡片 -->
  <div class="card">
    <!-- 维度标签 -->
    <div class="dimension-badge">
      <span x-text="currentQuestion.dimension_label"></span>
    </div>

    <!-- 题目 -->
    <h2 class="text-lg font-medium" x-text="currentQuestion.question"></h2>

    <!-- 选项 -->
    <div class="space-y-3 mt-6">
      <template x-for="(opt, idx) in currentQuestion.options" :key="idx">
        <label class="option-card"
               :class="{ 'option-selected': answers[currentQuestion.id] === opt.value }"
               @click="selectOption(currentQuestion.id, opt.value)">
          <input type="radio" :name="`q${currentQuestion.id}`"
                 :value="opt.value"
                 :checked="answers[currentQuestion.id] === opt.value"
                 class="sr-only">
          <span class="option-radio"></span>
          <span x-text="opt.label"></span>
        </label>
      </template>
    </div>

    <!-- 题目底部：对应数字员工信息 -->
    <div class="mt-6 pt-4 border-t text-xs text-gray-400">
      <span data-lang-key="compliance_evaluated_by">本问题由</span>
      <strong x-text="currentQuestion.employee_name"></strong>
      (<span x-text="currentQuestion.employee_role"></span>)
      <span data-lang-key="compliance_evaluated_for">为您评估</span>
    </div>
  </div>

  <!-- 导航按钮 -->
  <div class="flex justify-between mt-6">
    <button @click="prevStep()"
            x-show="currentStep > 1"
            class="btn btn--secondary">
      ← <span data-lang-key="compliance_prev">上一步</span>
    </button>
    <button @click="nextStep()"
            :disabled="answers[currentQuestion.id] === undefined"
            class="btn btn--primary">
      <span x-show="currentStep < 8" data-lang-key="compliance_next">下一步</span>
      <span x-show="currentStep === 8" data-lang-key="compliance_view_result">查看结果</span>
      →
    </button>
  </div>
</div>
```

### 3.3 结果预览页 (Step 9)

```html
<div x-show="currentStep === 9" class="...">
  <!-- 总分大数字 -->
  <div class="score-circle">
    <span class="score-number" x-text="reportData.total_score"></span>
    <span class="score-unit">/ 100</span>
  </div>
  <div class="level-badge" :class="`level-${reportData.level}`">
    <span x-text="`[${reportData.level}] ${reportData.level_label}`"></span>
  </div>

  <!-- 雷达图 (Canvas) -->
  <canvas id="radarChart" width="300" height="300"></canvas>

  <!-- 各维度列表 -->
  <div class="dimension-list">
    <template x-for="dim in reportData.dimensions" :key="dim.id">
      <div class="dimension-row">
        <span class="dim-icon" x-text="dim.status_icon"></span>
        <span class="dim-name" x-text="dim.dimension_label"></span>
        <div class="dim-bar">
          <div class="dim-bar-fill" :style="`width: ${dim.dim_score}%`"
               :class="`bar-${getBarColor(dim.dim_score)}`"></div>
        </div>
        <span class="dim-score" x-text="`${dim.dim_score}分`"></span>
        <span class="dim-status" x-text="dim.status_label"></span>
      </div>
    </template>
  </div>

  <!-- CTA: 获取PDF报告 -->
  <button @click="currentStep = 10" class="btn btn--primary btn--large">
    📄 <span data-lang-key="compliance_get_report">获取完整PDF报告</span>
  </button>

  <div class="text-center">
    <button @click="reset()" class="text-sm text-gray-400 hover:underline">
      ← <span data-lang-key="compliance_retake">重新答题</span>
    </button>
  </div>
</div>
```

### 3.4 信息填写页 (Step 10)

```html
<div x-show="currentStep === 10" class="...">
  <h2 data-lang-key="compliance_info_title">填写信息获取报告</h2>

  <form @submit.prevent="submitAnswers" class="space-y-4">
    <div>
      <label data-lang-key="compliance_company">企业名称（选填）</label>
      <input type="text" x-model="companyName" class="input">
    </div>
    <div>
      <label data-lang-key="compliance_name">联系人姓名（选填）</label>
      <input type="text" x-model="contactName" class="input">
    </div>
    <div>
      <label data-lang-key="compliance_email">电子邮箱 *</label>
      <input type="email" x-model="email" required class="input">
      <span x-show="errors.email" class="text-red-500 text-sm" x-text="errors.email"></span>
    </div>
    <div>
      <label>
        <input type="checkbox" x-model="agreePrivacy" required>
        <span data-lang-key="compliance_privacy_confirm">我已阅读并同意《隐私政策》</span>
      </label>
    </div>

    <button type="submit" :disabled="!email || !agreePrivacy || isGenerating"
            class="btn btn--primary btn--large w-full">
      <span x-show="!isGenerating" data-lang-key="compliance_generate">生成PDF报告</span>
      <span x-show="isGenerating" data-lang-key="compliance_generating">正在生成...</span>
    </button>
  </form>
</div>
```

---

## 4. API对接

在 `compliance-check.html` 中使用 `Alpine.js` 的 `init()` 方法调用：

| 方法 | API路径 | 触发时机 | 说明 |
|------|---------|---------|------|
| GET | `/api/v1/compliance/questions?lang=zh` | 页面加载 | 获取题目（由烛龙实现） |
| POST | `/api/v1/compliance/submit` | 用户填写信息后提交 | 提交答案+用户信息，获取报告token |
| GET | `/api/v1/compliance/report/{token}` | 提交成功后 | 获取报告数据（用于前端展示） |
| GET | `/api/v1/compliance/report/{token}/pdf` | 点击下载 | 下载PDF文件 |

### POST /api/v1/compliance/submit 请求体

```json
{
  "answers": {"1": 0, "2": 1, "3": 2, "4": 0, "5": 1, "6": 2, "7": 0, "8": 1},
  "company_name": "㈜한국테크",
  "contact_name": "김민수",
  "email": "kms@koreatech.co.kr",
  "language": "zh"
}
```

### POST /api/v1/compliance/submit 响应

```json
{
  "success": true,
  "data": {
    "token": "CHC-20260512-A3B4",
    "report_url": "/api/v1/compliance/report/CHC-20260512-A3B4",
    "pdf_url": "/api/v1/compliance/report/CHC-20260512-A3B4/pdf"
  }
}
```

---

## 5. 雷达图实现方案

使用 Canvas 绘制雷达图（纯前端），无需引入额外图表库：

```javascript
function drawRadarChart(canvasId, dimensions) {
  const canvas = document.getElementById(canvasId);
  const ctx = canvas.getContext('2d');
  const cx = 150, cy = 150, r = 120;
  const n = dimensions.length;
  const angleStep = (Math.PI * 2) / n;

  // 绘制六边形网格
  // 绘制各维度轴线
  // 绘制数据区域（填充多边形）
  // 绘制数据点标签
  // 参考: 使用 Math.cos/sin 计算顶点坐标
}
```

详细实现可参考 `compliance-check.html` 中的 `drawRadarChart()` 函数。

---

## 6. 样式设计原则

1. **进度条**：顶部固定，显示当前题号/总数和百分比
2. **选项卡片**：hover时边框高亮，选中时背景色变化（蓝色主题）
3. **维度标签**：每个题目显示所属维度的小标签（如「数据安全」「知识产权」）
4. **数字员工引用**：每题底部展示对应的数字员工头像和名称
5. **结果页**：突出总分大数字，各维度以横向柱状图展示，红色/橙色/绿色标记风险
6. **移动端适配**：选项用全宽卡片式布局，确保手机端单列显示

---

## 7. 交互细节

1. **进度续答**：localStorage 缓存答案，5分钟内重新进入提示继续上次答题
2. **实时评分**：在结果预览页（Step 9）显示实时计算的分值和评级
3. **选完即进**：选择选项后自动进入下一题（或保留「下一步」按钮两种模式均可）
4. **错误处理**：API调用失败时显示友好提示，保留用户答案不丢失
5. **Loading状态**：提交和生成PDF时禁用按钮显示加载动画

---

*文档结束*
