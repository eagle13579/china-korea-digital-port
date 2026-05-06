#!/usr/bin/env bash
# =============================================================================
# recover-git-to-origin.sh
# 中韩出海数智港 - Git仓库恢复/同步脚本
# 用途：SSH到服务器后执行，恢复/同步线上Git仓库，并验证安全配置
# 目标服务器：47.100.160.250 (阿里云ECS Ubuntu)
# 部署路径：/var/www/china-korea-digital-port/
# =============================================================================
set -euo pipefail

# ─── 颜色定义 ───
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

DEPLOY_DIR="/var/www/china-korea-digital-port"
REMOTE_ORIGIN="origin"
BACKUP_DIR="/tmp/china-korea-digital-port-backup"

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  中韩出海数智港 — Git仓库恢复/同步脚本${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# ─── Step 1: 检查部署目录 ───
echo -e "${YELLOW}[1/6] 检查部署目录...${NC}"
if [ ! -d "$DEPLOY_DIR" ]; then
    echo -e "${RED}✗ 部署目录 $DEPLOY_DIR 不存在！${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 部署目录存在: $DEPLOY_DIR${NC}"

cd "$DEPLOY_DIR"

# ─── Step 2: 确认Git仓库 ───
echo ""
echo -e "${YELLOW}[2/6] 确认Git仓库状态...${NC}"
if [ ! -d ".git" ]; then
    echo -e "${RED}✗ 不是Git仓库（.git目录不存在）${NC}"
    echo "尝试初始化Git仓库..."
    echo "是否要从远程clone？请手动执行："
    echo "  cd /var/www && sudo mv china-korea-digital-port china-korea-digital-port.bak"
    echo "  sudo git clone <your-repo-url> china-korea-digital-port"
    exit 1
fi

echo -e "${GREEN}✓ 是Git仓库${NC}"

# 检查远程仓库配置
REMOTE_URL=$(git remote get-url "$REMOTE_ORIGIN" 2>/dev/null || echo "")
if [ -z "$REMOTE_URL" ]; then
    echo -e "${YELLOW}⚠ 未配置远程仓库 origin${NC}"
    echo "请手动添加远程仓库："
    echo "  cd $DEPLOY_DIR && git remote add origin <your-repo-url>"
    exit 1
fi
echo -e "${GREEN}✓ 远程仓库: $REMOTE_URL${NC}"

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
echo -e "${GREEN}✓ 当前分支: $CURRENT_BRANCH${NC}"

# ─── Step 3: 备份工作区 ───
echo ""
echo -e "${YELLOW}[3/6] 备份当前工作区（防止合并冲突丢失数据）...${NC}"
BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
tar -czf "$BACKUP_DIR/$BACKUP_NAME/working-copy.tar.gz" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='venv' \
    --exclude='*.pyc' \
    . 2>/dev/null || true
echo -e "${GREEN}✓ 备份完成: $BACKUP_DIR/$BACKUP_NAME/working-copy.tar.gz${NC}"

# ─── Step 4: 拉取最新代码 ───
echo ""
echo -e "${YELLOW}[4/6] 拉取最新代码...${NC}"
git fetch --all --tags 2>&1 || {
    echo -e "${RED}✗ fetch 失败，请检查网络或认证配置${NC}"
    exit 1
}
echo -e "${GREEN}✓ fetch 完成${NC}"

# 尝试 stash 本地修改后 pull
STASH_NEEDED=false
if ! git diff --quiet HEAD 2>/dev/null; then
    STASH_NEEDED=false
    echo -e "${YELLOW}⚠ 存在本地未提交的修改${NC}"
    echo -e "${YELLOW}  执行 git stash 后 pull${NC}"
    git stash push -m "auto-stash-before-recover-$(date +%Y%m%d%H%M%S)" 2>&1 || true
    STASH_NEEDED=true
fi

# 执行 pull (rebase 模式，保持历史整洁)
git pull --rebase "$REMOTE_ORIGIN" "$CURRENT_BRANCH" 2>&1 || {
    echo -e "${RED}✗ pull 失败，可能存在冲突${NC}"
    echo "请手动解决冲突后重试，或强制重置："
    echo "  git fetch origin"
    echo "  git reset --hard origin/$CURRENT_BRANCH"
    echo "警告：强制重置会丢失所有本地修改！"
    exit 1
}
echo -e "${GREEN}✓ 代码已同步到最新版本${NC}"

# 恢复 stash
if [ "$STASH_NEEDED" = true ]; then
    git stash pop 2>&1 || true
    echo -e "${GREEN}✓ 本地修改已恢复${NC}"
fi

# ─── Step 5: 验证 .gitignore ───
echo ""
echo -e "${YELLOW}[5/6] 验证 .gitignore 和安全文件...${NC}"
if [ -f ".gitignore" ]; then
    echo -e "${GREEN}✓ .gitignore 存在${NC}"
    # 检查关键规则
    for pattern in "__pycache__/" "venv/" ".env" "*.db"; do
        if grep -q "$pattern" .gitignore 2>/dev/null; then
            echo -e "  ${GREEN}✓ 规则 '$pattern' 已配置${NC}"
        else
            echo -e "  ${YELLOW}⚠ 规则 '$pattern' 未在 .gitignore 中配置${NC}"
        fi
    done
else
    echo -e "${RED}✗ .gitignore 不存在！${NC}"
    echo "创建 .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
venv/
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
EOF
    echo -e "${GREEN}✓ .gitignore 已创建${NC}"
fi

echo ""

# ─── Step 6: 验证 .htaccess 和文件保护 ───
echo -e "${YELLOW}[6/6] 验证 .htaccess 和敏感文件保护...${NC}"

# .htaccess 检查
if [ -f ".htaccess" ]; then
    echo -e "${GREEN}✓ .htaccess 存在${NC}"
    echo "  内容预览："
    head -20 .htaccess | sed 's/^/  /'
else
    echo -e "${YELLOW}ℹ .htaccess 不存在（Nginx 环境通常不需要，由 nginx.conf 替代）${NC}"
fi

# 检查敏感目录/文件是否被 git 追踪
echo ""
echo "检查敏感文件是否被Git追踪..."
SENSITIVE_PATTERNS="*.db *.sqlite .env .env.* config.json *.key *.pem"
SENSITIVE_FOUND=false
for pattern in $SENSITIVE_PATTERNS; do
    TRACKED=$(git ls-files "$pattern" 2>/dev/null || true)
    if [ -n "$TRACKED" ]; then
        echo -e "${RED}⚠ 敏感文件被Git追踪: $(echo "$TRACKED" | tr '\n' ' ')${NC}"
        SENSITIVE_FOUND=true
    fi
done

if [ "$SENSITIVE_FOUND" = false ]; then
    echo -e "${GREEN}✓ 未发现敏感文件被Git追踪${NC}"
fi

# 检查 .git 目录权限（应禁止web访问）
echo ""
echo "检查 .git 目录保护..."
if [ -d ".git" ]; then
    GIT_PERMS=$(stat -c "%a" .git 2>/dev/null || stat -f "%A" .git 2>/dev/null || echo "unknown")
    echo -e "${GREEN}✓ .git 目录权限: $GIT_PERMS${NC}"
    echo -e "${YELLOW}  ⚠ 重要：确保 nginx 配置中有 'location ~ /\\.' 禁止访问隐藏文件${NC}"
    echo -e "${YELLOW}     验证：curl -v https://go-aiport.com/.git/config 应返回 404${NC}"
fi

# ─── 完成 ───
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Git仓库恢复/同步完成！${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "✅ 当前状态："
echo "  目录: $DEPLOY_DIR"
echo "  分支: $CURRENT_BRANCH"
echo "  最新提交: $(git log --oneline -1 2>/dev/null || echo 'N/A')"
echo ""
echo "⚠ 后续操作建议："
echo "  1. 验证 nginx 安全规则是否已应用："
echo "     curl -I https://go-aiport.com/.git/config"
echo "     curl -I https://go-aiport.com/.env"
echo "     curl -I https://go-aiport.com/backend/data/portal.db"
echo "  2. 检查后端服务是否正常运行："
echo "     curl -s http://127.0.0.1:8000/health"
echo "  3. 如有必要，重启后端服务："
echo "     sudo systemctl restart opc-api  # 或 supervisorctl restart opc-api"
echo ""
