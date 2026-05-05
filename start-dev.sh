#!/bin/bash
# 启动脚本 - 中韩出海数智港 本地开发环境
PROJ="/mnt/d/向海容的知识库/wiki/wiki/记忆宫殿/L3工作室/出海项目/中韩出海数智港/china-korea-digital-port"
cd "$PROJ" || exit 1

echo "=== 中韩出海数智港 - 启动开发环境 ==="
echo "项目路径: $PROJ"
echo ""

# 检查 Python 依赖
echo "1. 检查依赖..."
python3 -c "import fastapi" 2>/dev/null && echo "   fastapi ✅" || { pip3 install fastapi uvicorn pydantic --break-system-packages -q && echo "   fastapi 已安装 ✅"; }

# 启动后端
echo ""
echo "2. 启动 FastAPI 后端 (端口 8088)..."
pkill -f "uvicorn backend.main" 2>/dev/null
sleep 1
nohup python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8088 > /tmp/portal.log 2>&1 &
sleep 3

# 验证
if curl -s http://localhost:8088/ > /dev/null 2>&1; then
    echo "   FastAPI 启动成功 ✅"
else
    echo "   FastAPI 启动失败 ❌"
    cat /tmp/portal.log
    exit 1
fi

echo ""
echo "=== 已就绪 ==="
echo "首页:     http://localhost:8088/index.html"
echo "定价页:   http://localhost:8088/pricing.html"
echo "管理后台: http://localhost:8088/admin/index.html"
echo ""
echo "管理后台账号: admin / admin123"
echo ""
echo "按 Ctrl+C 停止后端"
wait
