# 中韩出海数智港 - UI/UX 设计规范文档

> 版本: v1.0 | 最后更新: 2026-05-07

---

## 目录

1. [品牌色彩体系](#1-品牌色彩体系)
2. [排版规范](#2-排版规范)
3. [间距系统](#3-间距系统)
4. [组件规范](#4-组件规范)
5. [动效规范](#5-动效规范)
6. [深色/浅色主题切换规范](#6-深色浅色主题切换规范)
7. [中韩双语布局注意事项](#7-中韩双语布局注意事项)
8. [新增英文语言后的三语布局注意事项](#8-新增英文语言后的三语布局注意事项)

---

## 1. 品牌色彩体系

项目采用 CSS 自定义属性（CSS Variables）管理色彩，支持深色/浅色双主题切换。

### 1.1 深色主题（默认）

| CSS 变量 | 色值 | 用途 |
|----------|------|------|
| `--bg-primary` | `#0A0A0F` | 页面主背景色 |
| `--bg-secondary` | `#12121A` | 卡片/区域二级背景色 |
| `--bg-tertiary` | `#1A1A25` | 输入框/三级背景色 |
| `--accent-primary` | `#8B5CF6` | 主品牌色（紫色） |
| `--accent-secondary` | `#06B6D4` | 辅助品牌色（青色） |
| `--accent-gradient` | `linear-gradient(135deg, #8B5CF6, #06B6D4, #10B981)` | 品牌渐变色（紫→青→绿） |
| `--text-primary` | `#F1F5F9` | 主文本色（近白色） |
| `--text-secondary` | `#94A3B8` | 次要文本色 |
| `--text-muted` | `#64748B` | 弱化文本色 |
| `--glass-bg` | `rgba(255, 255, 255, 0.03)` | 玻璃拟态背景 |
| `--glass-border` | `rgba(255, 255, 255, 0.08)` | 玻璃拟态边框 |
| `--glass-shadow` | `0 8px 32px rgba(0, 0, 0, 0.3)` | 玻璃拟态阴影 |

### 1.2 浅色主题（body.light-mode）

| CSS 变量 | 色值 | 用途 |
|----------|------|------|
| `--bg-primary` | `#F8FAFC` | 页面主背景色 |
| `--bg-secondary` | `#FFFFFF` | 卡片/区域二级背景色 |
| `--bg-tertiary` | `#F1F5F9` | 输入框/三级背景色 |
| `--text-primary` | `#1E293B` | 主文本色 |
| `--text-secondary` | `#475569` | 次要文本色 |
| `--text-muted` | `#94A3B8` | 弱化文本色 |
| `--glass-bg` | `rgba(0, 0, 0, 0.03)` | 玻璃拟态背景 |
| `--glass-border` | `rgba(0, 0, 0, 0.1)` | 玻璃拟态边框 |
| `--glass-shadow` | `0 8px 32px rgba(0, 0, 0, 0.1)` | 玻璃拟态阴影 |

注意：浅色模式下 accent 色值保持不变，仅改变背景和文本色系。

### 1.3 色彩使用原则

- **主品牌色** `#8B5CF6`：用于按钮、链接悬停、图标、焦点指示
- **渐变色**：用于标题文字（gradient-text）、CTA 按钮、进度条装饰
- **玻璃拟态**：卡片、导航栏、表单使用 `backdrop-filter: blur(20px)` 增强层次感
- **对比度要求**：主文本与背景对比度需 ≥ 4.5:1（符合 WCAG AA 标准）

---

## 2. 排版规范

### 2.1 字体栈

```css
--font-heading: 'Inter', sans-serif;
--font-body: 'Inter', sans-serif;
```

- **英文/韩文数字**：Inter（无衬线可变字体）
- **中文**：系统回退至 `sans-serif`
- **韩文**：Inter 对韩文支持良好，可考虑补充 `'Noto Sans KR'` 作为韩文后备字体

### 2.2 字号层级

| 层级 | 字体大小 | 字重 | 使用场景 |
|------|----------|------|----------|
| Display | 48px | 700 (Bold) | Hero 区域主标题 |
| H1 | 36px | 700 (Bold) | Section 主标题 |
| H2 | 24px | 600 (Semi-Bold) | 服务组标题、弹窗标题 |
| H3 | 20px | 600 (Semi-Bold) | 功能卡片标题 |
| H4 | 18px | 600 (Semi-Bold) | 服务项标题 |
| Body Large | 20px | 400 (Regular) | Hero 副标题 |
| Body | 16px | 400 (Regular) | 正文、段落、按钮文本 |
| Body Small | 14px | 400 (Regular) / 500 (Medium) | 表单标签、特征描述、页脚链接 |
| Caption | 13px | 400 (Regular) | 版权信息、法律声明 |

### 2.3 行高

| 层级 | 行高 | 说明 |
|------|------|------|
| 标题（Display/H1） | 1.2 | 紧凑排列 |
| 标题（H2-H4） | 1.3 | 适中排列 |
| 正文 | 1.6 | 标准阅读行高 |
| 小字 | 1.7 | 版权等小字号区域 |

### 2.4 字体颜色层级

- `--text-primary`：正文标题、导航链接
- `--text-secondary`：副标题、描述文本、表单辅助文字
- `--text-muted`：版权信息、免责声明

---

## 3. 间距系统

### 3.1 Section 间距

```css
--spacing-section: 120px;
```

- 每个 section 的上下内边距统一为 120px
- 移动端（≤768px）缩减为 80px（hero）或保持合理间距
- Section 之间可通过背景色（`--bg-secondary`）交替区分

### 3.2 Element 间距

```css
--spacing-element: 24px;
```

通用元素间距参考：

| 间距 | 值 | 使用场景 |
|------|----|----------|
| 微间距 | 8px | 语言按钮、导航链接间距 |
| 小间距 | 12-16px | 页脚链接、表单内部、徽标间距 |
| 中间距 | 24px | 卡片内容间距、表单组间距、功能网格间距 |
| 大间距 | 32-40px | 卡片间距、CTA 间距、页脚网格间距 |
| 特大间距 | 60px | Section 内两栏布局间距 |

### 3.3 容器宽度

- 最大宽度：`1400px`
- 内边距：`0 24px`（桌面）、`0 16px`（移动端）

### 3.4 响应式断点

| 断点 | 说明 |
|------|------|
| ≤1200px | 两栏布局切换为单栏 |
| ≤768px | 导航折叠、字号缩减、间距缩小 |

---

## 4. 组件规范

### 4.1 导航栏（Header）

| 属性 | 值 |
|------|-----|
| 定位 | `fixed top:0`，z-index: 1000 |
| 背景 | `rgba(10,10,15,0.9)` + `backdrop-filter: blur(20px)` |
| 底部边框 | `1px solid var(--glass-border)` |
| 内边距 | `20px 0` |
| 语言按钮 | 6px 12px 内边距，6px 圆角，悬停聚焦主色 |
| 主题切换按钮 | 40x40px 圆形，带边框 |
| Logo | 24px，700 字重，渐变色文本 |
| 导航链接间距 | `gap: 32px`，带下划线悬停动效 |
| 过渡 | `--transition-normal` |

**浅色模式**：导航栏背景变为 `rgba(255,255,255,0.9)`。

### 4.2 卡片（Card）

通用卡片（feature__card / stat__card / service__item）：

| 属性 | 值 |
|------|-----|
| 背景 | `var(--glass-bg)` + `backdrop-filter: blur(20px)` |
| 边框 | `1px solid var(--glass-border)` |
| 圆角 | 12px（小）/ 16px（大） |
| 内边距 | 32-40px（桌面），24-32px（移动端） |
| 悬停效果 | `translateY(-4px)` + 阴影增强 + 顶部渐变条展开 |
| 过渡 | `--transition-normal` |

**Feature Card 特殊动效**：
- 悬停时 `scale(1.02)` 轻微放大
- 图标 `scale(1.1) rotate(5deg)` 互动效果
- 顶部渐变条从 `scaleX(0)` → `scaleX(1)`

**Service Item 特殊动效**：
- 悬停时 `translateX(8px)` 向右滑入
- 边框变为 `var(--accent-primary)`

### 4.3 按钮（Button）

| 类型 | 属性 |
|------|------|
| 通用 | `display: inline-flex`，`12px 24px` 内边距，8px 圆角，16px 字体，600 字重 |
| Primary | 渐变色背景，白色文字，`0 4px 12px rgba(139,92,246,0.3)` 阴影 |
| Primary 悬停 | `translateY(-2px)`，阴影增强至 `0 6px 16px ...` |
| Secondary | 玻璃拟态背景，主文本色，1px 边框 |
| Secondary 悬停（深色） | `rgba(255,255,255,0.08)` 背景加深 |
| Secondary 悬停（浅色） | `rgba(0,0,0,0.08)` 背景加深 |

**语言按钮（lang-btn）**：
- 默认：玻璃背景，次要文本色，6px 圆角
- 悬停：文本色变为主色，边框变为主色
- 激活：渐变色背景，白色文字

### 4.4 表单（Form）

| 元素 | 属性 |
|------|------|
| 输入框/文本域 | `100%` 宽度，`12px 16px` 内边距，`--bg-tertiary` 背景，8px 圆角 |
| 聚焦态 | 移除默认 outline，边框变为主色，`box-shadow: 0 0 0 3px rgba(139,92,246,0.1)` |
| 标签 | 14px，500 字重，与输入框间距 8px |
| 表单组间距 | `margin-bottom: 24px` |
| Textarea | 最小高度 120px，可垂直调整大小 |
| 表单卡片 | 玻璃拟态背景，16px 圆角，40px 内边距 |

**只读输入框**（modal 内）：
- 背景使用 `--glass-bg`，`cursor: not-allowed`，`opacity: 0.7`

### 4.5 Toast 组件

| 属性 | 值 |
|------|-----|
| 容器 | `fixed top: 20px right: 20px`，z-index: 9999 |
| 布局 | 纵向排列，gap: 12px，`pointer-events: none` |
| 动画 | 建议 fade-in/slide-in 动效（需补充实现） |

### 4.6 Modal 弹窗

| 属性 | 值 |
|------|-----|
| 遮罩层 | `rgba(0,0,0,0.6)` + `backdrop-filter: blur(4px)` |
| 内容框 | `--bg-secondary` 背景，20px 圆角，32px 内边距 |
| 最大宽度 | 520px（桌面），margin: 10px（移动端） |
| 入场动画 | `modalIn`：从 `scale(0.95) translateY(10px)` → 正常 |
| 关闭按钮 | 32x32px 圆形，悬停变为主色 |

### 4.7 图标（Feature Icon）

- 尺寸：60x60px
- 圆角：12px
- 背景：渐变色
- 图标大小：24px
- 悬停：`scale(1.1) rotate(5deg)`

---

## 5. 动效规范

### 5.1 过渡时间

| CSS 变量 | 值 | cubic-bezier | 适用场景 |
|----------|-----|--------------|----------|
| `--transition-fast` | 150ms | `cubic-bezier(0.4, 0, 0.2, 1)` | 导航链接悬停、语言按钮切换、输入框聚焦 |
| `--transition-normal` | 250ms | `cubic-bezier(0.4, 0, 0.2, 1)` | 按钮悬停、卡片悬停、主题切换、组件过渡 |
| `--transition-slow` | 400ms | `cubic-bezier(0.4, 0, 0.2, 1)` | 页面入场动画、大区域过渡 |

### 5.2 悬停效果汇总

| 组件 | 效果 |
|------|------|
| Primary Button | `translateY(-2px)` + 阴影加深 |
| Secondary Button | `translateY(-2px)` + 背景加深 |
| Feature Card | `translateY(-4px) scale(1.02)` + 阴影 + 顶部渐变条 |
| Stat Card | `translateY(-4px)` + 阴影 + 顶部渐变条 |
| Service Item | `translateX(8px)` + 阴影 + 边框变色 |
| Navigation Link | 颜色变为主色 + 下划线渐变展开 |
| Social Icon | 背景变为渐变色 + `translateY(-2px)` |
| Info Item | `translateY(-4px)` + 阴影 |
| Feature Icon | `scale(1.1) rotate(5deg)` |
| Modal Close | 背景变为主色，文字变白 |

### 5.3 关键帧动画

| 动画名 | 说明 | 参数 |
|--------|------|------|
| `pulse` | Hero 圆形呼吸动画 | 3s ease-in-out infinite |
| `fadeIn` | 通用淡入 | 0.8s ease-out |
| `fadeInUp` | 上浮淡入 | 0.8s ease-out |
| `modalIn` | 弹窗入场 | 0.3s ease |

### 5.4 滚动效果

- 导航栏滚动后添加阴影：`box-shadow: 0 4px 20px rgba(0,0,0,0.3)`（通过 `.scrolled` 类）

---

## 6. 深色/浅色主题切换规范

### 6.1 切换机制

通过给 `body` 添加/移除 `.light-mode` 类实现主题切换：

```javascript
// 推荐实现方式
const themeBtn = document.querySelector('.theme-btn');
themeBtn.addEventListener('click', () => {
    document.body.classList.toggle('light-mode');
    // 可选：保存偏好到 localStorage
    localStorage.setItem('theme', 
        document.body.classList.contains('light-mode') ? 'light' : 'dark'
    );
});
```

### 6.2 CSS 覆盖规则

- 浅色主题样式写在 `body.light-mode` 选择器下
- 深色主题为默认值（`:root` 中定义）
- 所有显式使用 hard-coded 颜色值的地方（如 `rgba(10,10,15,0.9)` 导航栏背景）都需要提供浅色模式覆盖

### 6.3 已覆盖的浅色组件

- Header 背景：`rgba(255,255,255,0.9)`
- Hero 光晕：`rgba(139,92,246,0.05)` 
- 按钮（secondary）：背景加深使用 `rgba(0,0,0,0.08)`
- 语言按钮、Logo、导航链接：保持不变（使用变量）

### 6.4 需要检查的硬编码颜色

以下位置使用了硬编码颜色，主题切换时需要特别注意：
- `rgba(139, 92, 246, 0.3)` / `rgba(139, 92, 246, 0.4)` — 按钮阴影
- `rgba(139, 92, 246, 0.1)` — 输入框聚焦
- `rgba(139, 92, 246, 0.5)` — Hero 图标阴影
- `rgba(0, 0, 0, 0.3)` / `rgba(0, 0, 0, 0.4)` — 滚动阴影/弹窗阴影
- `rgba(0, 0, 0, 0.6)` — 弹窗遮罩

### 6.5 持久化策略

- 推荐使用 `localStorage` 存储用户主题偏好
- 页面加载时读取存储值并设置相应主题
- 遵循系统主题偏好可作为增强体验（`prefers-color-scheme` 媒体查询）

---

## 7. 中韩双语布局注意事项

### 7.1 字符长度差异

韩文文本通常比中文长 **20-30%**，在设计布局时需要预留空间。

| 场景 | 中文 | 韩文（预计长度） |
|------|------|-----------------|
| 导航链接 | "服务内容" (4字) | "서비스 내용" (8-9字符) |
| 按钮文案 | "立即咨询" (4字) | "지금 문의하기" (9-10字符) |
| Hero 标题 | "AI智能出海" (6字) | "AI 스마트 해외 진출" (14-15字符) |

### 7.2 布局应对策略

1. **导航栏**：
   - 导航链接使用 `gap` 而非固定宽度，允许自然扩展
   - 韩文导航项预留额外 30% 空间
   - 语言切换按钮区域保持紧凑

2. **按钮**：
   - 按钮使用 `padding` + `min-width` 而非固定宽度
   - 韩文按钮文案控制在 10 字符以内，避免按钮过长

3. **卡片/网格**：
   - 使用 `auto-fit` / `minmax` 弹性网格，而非固定列宽
   - 标题区域预留换行空间
   - 韩文标题建议使用 `word-break: keep-all`

4. **标题和副标题**：
   - 韩文标题行高适当增加（建议 1.4-1.5）
   - Hero 标题区域预留足够垂直空间

5. **表单标签**：
   - 采用标签在上、输入框在下的纵向布局（而非左右排列）
   - 避免因韩文标签过长导致布局错乱

### 7.3 字体建议

- **韩文主字体**：`'Noto Sans KR', 'Inter', sans-serif`
- 中文优先使用系统字体 `'PingFang SC', 'Microsoft YaHei', sans-serif`
- 使用 CSS `font-display: swap` 确保字体加载期间文本可见

---

## 8. 新增英文语言后的三语布局注意事项

### 8.1 语言长度对比

| 语言 | 相对长度 | 特点 |
|------|---------|------|
| 中文 | 基准（最短） | 每个字符信息密度高 |
| 英文 | 中文的 150-200% | 单词间有空格分隔 |
| 韩文 | 中文的 120-130% | 有隔写空格 |

### 8.2 三语布局核心原则

1. **弹性容器**：所有文本容器应使用 `min-width: 0` + `word-break: break-word` 防止溢出
2. **不要使用固定宽度**：语言切换时文本长度变化大，必须使用弹性/自适应布局
3. **行高调整**：英文和韩文在相同字号下，建议行高增加 0.1-0.2

### 8.3 导航栏三语适配

导航栏在三语切换时挑战最大，建议：

```
中文: "服务内容"      → 4字符
英文: "Services"      → 8字符  
韩文: "서비스 소개"   → 9字符含空格
```

**策略**：
- 桌面端：导航项间距使用 `gap: 24-32px`，而非固定宽度
- 移动端：使用汉堡菜单折叠，避免空间不足
- 考虑对长文本导航项启用 `font-size: 14px`（缩小字号）

### 8.4 Hero 区域三语适配

- Hero 标题设计为最多容纳 20 英文单词的宽度
- 英文标题建议控制在 8-12 个单词以内
- 副标题预留 2-3 行显示空间

### 8.5 按钮文案规范

| 功能 | 中文 | 英文 (EN) | 韩文 (KO) |
|------|------|-----------|-----------|
| 立即咨询 | 立即咨询 | Contact Now | 지금 문의하기 |
| 开始使用 | 开始使用 | Get Started | 시작하기 |
| 了解更多 | 了解更多 | Learn More | 자세히 보기 |
| 免费试用 | 免费试用 | Free Trial | 무료 체험 |
| 提交表单 | 提交 | Submit | 제출 |
| 取消 | 取消 | Cancel | 취소 |
| 搜索 | 搜索 | Search | 검색 |

### 8.6 全局 CSS 文本处理

```css
/* 推荐的三语文本处理 */
[lang="en"] {
    word-break: normal;
    hyphens: auto;
}

[lang="ko"] {
    word-break: keep-all;
    line-height: 1.7; /* 略高于中文 */
}

/* 通用防止溢出 */
.text-ellipsis {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
```

### 8.7 字体加载优先级

```css
/* 三语字体栈推荐 */
:root {
    --font-zh: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', sans-serif;
    --font-en: 'Inter', 'Segoe UI', sans-serif;
    --font-ko: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}

/* 根据 lang 属性切换 */
[lang="zh"] { font-family: var(--font-zh); }
[lang="en"] { font-family: var(--font-en); }
[lang="ko"] { font-family: var(--font-ko); }
```

### 8.8 布局测试清单

- [ ] 三语切换后导航栏不换行/不溢出
- [ ] 按钮文案在三语下完整显示
- [ ] 卡片标题在三语下不截断
- [ ] Hero 副标题在三语下布局稳定
- [ ] 表单标签在三语下对齐正确
- [ ] Footer 链接在三语下不重叠
- [ ] 移动端菜单在三语下完整显示
- [ ] 所有语言切换后页面无布局抖动

---

> 本设计规范是项目 UI/UX 的权威参考，所有新组件和页面设计应遵循此规范。如有矛盾，以 CSS 变量和实际代码实现为准。
