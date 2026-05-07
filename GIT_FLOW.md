# 中韩出海数智港 — Git 分支策略

## 分支结构

本项目采用基于 Git Flow 的分支策略，确保开发流程规范化、发布可追溯。

### 主分支

| 分支 | 用途 | 保护规则 |
|------|------|---------|
| `main` | **生产分支**。只有经过充分测试的稳定版本才能合并到 main。所有线上版本从此分支部署。 | 受保护，禁止直接 push，仅通过 PR 合并 |
| `develop` | **开发主分支**。所有功能开发的基础分支，集成各个功能模块。 | 受保护，禁止直接 push，仅通过 PR 合并 |

### 辅助分支

| 分支模式 | 用途 | 生命周期 | 合并目标 |
|----------|------|---------|---------|
| `feat/*` | **功能开发分支**。从 develop 拉出，开发新功能。 | 临时，功能完成后删除 | `develop` |
| `release/*` | **发布分支**。从 develop 拉出，用于版本发布的准备（bug 修复、文档等）。 | 临时，发布完成后删除 | `main` + `develop` |
| `fix/*` | **紧急修复分支**。从 main 拉出，修复线上紧急问题。 | 临时，修复完成后删除 | `main` + `develop` |

## 工作流程

### 日常开发

```bash
# 1. 从最新的 develop 拉取
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feat/your-feature-name

# 3. 开发... 提交...
git add .
git commit -m "feat: 你的功能描述"

# 4. 推送并创建 PR → develop
git push origin feat/your-feature-name
# → 在 GitHub/GitLab 上创建 Pull Request
```

### 发布流程

```bash
# 1. 从 develop 创建发布分支
git checkout develop
git checkout -b release/v1.x.x

# 2. 版本准备（修复 bug、更新文档、版本号）
git commit -m "chore: release v1.x.x"

# 3. 合并到 main
git checkout main
git merge --no-ff release/v1.x.x
git tag v1.x.x
git push origin main --tags

# 4. 合并回 develop
git checkout develop
git merge --no-ff release/v1.x.x
git push origin develop

# 5. 删除发布分支
git branch -d release/v1.x.x
```

### 紧急修复

```bash
# 1. 从 main 拉出修复分支
git checkout main
git checkout -b fix/critical-issue

# 2. 修复并提交
git commit -m "fix: 紧急修复描述"

# 3. 合并到 main
git checkout main
git merge --no-ff fix/critical-issue
git push origin main

# 4. 合并到 develop
git checkout develop
git merge --no-ff fix/critical-issue
git push origin develop

# 5. 删除修复分支
git branch -d fix/critical-issue
```

## 提交信息规范

使用 Conventional Commits 规范：

- `feat:` 新功能
- `fix:` Bug 修复
- `chore:` 构建/工具/配置变更
- `docs:` 文档变更
- `refactor:` 重构
- `test:` 测试
- `style:` 代码风格变更（不影响逻辑）

示例：
```
feat(crm): 添加线索批量导出功能
fix(admin): 修复登录 token 过期判断
chore: 更新依赖版本
docs: 补充 API 文档
```

## 版本号规则

遵循语义化版本号 (SemVer)：`vMAJOR.MINOR.PATCH`

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向下兼容的新功能
- **PATCH**: 向下兼容的 bug 修复
