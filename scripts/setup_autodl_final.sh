#!/bin/bash
# AutoDL 容器环境部署脚本 (最终版)
# AutoDL镜像通常已预装Docker，直接检查使用
# 使用: chmod +x scripts/setup_autodl_final.sh && ./scripts/setup_autodl_final.sh

set -e

echo "========================================"
echo "  AutoDL 环境部署 (最终版)"
echo "========================================"
echo ""

# ==================== 检查Docker ====================
echo "[1/5] 检查Docker..."

# AutoDL镜像通常已预装Docker
if command -v docker &> /dev/null; then
    echo "    Docker已安装: $(docker --version)"
else
    echo "    Docker未安装，尝试备用安装..."

    # 备用方案: 使用阿里云脚本
    curl -fsSL https://get.docker.com | sh || {
        echo "    [-] 网络受限，跳过Docker安装"
        echo "    [*] 请联系AutoDL客服或使用预装Docker的镜像"
    }
fi

# 启动Docker守护进程
if command -v docker &> /dev/null; then
    echo "    启动Docker守护进程..."

    # 容器内直接启动dockerd
    if ! pgrep -x "dockerd" > /dev/null; then
        nohup dockerd --storage-driver=vfs > /tmp/dockerd.log 2>&1 &
        sleep 15
    fi

    # 检查状态
    if docker info > /dev/null 2>&1; then
        echo "    Docker运行正常 ✓"
    else
        echo "    [-] Docker可能需要特权模式"
        echo "    [*] AutoDL创建实例时选择'特权模式'选项"
    fi
fi

# ==================== 创建工作目录 ====================
echo ""
echo "[2/5] 创建工作目录..."
mkdir -p /root/workspace
mkdir -p /root/autodl-tmp/results

# ==================== 克隆项目 ====================
echo ""
echo "[3/5] 克隆项目..."
cd /root/workspace

if [ -d "manatrix" ]; then
    cd manatrix
    git pull origin master || echo "    拉取失败，使用现有版本"
else
    git clone https://github.com/RomanCohort/manatrix.git || {
        echo "    [-] GitHub克隆失败"
        echo "    [*] 请手动上传项目文件"
    }
    cd manatrix
fi

# ==================== 安装Python依赖 ====================
echo ""
echo "[4/5] 安装Python依赖..."
pip3 install -q requests pyyaml numpy flask scipy || echo "    部分依赖安装失败"

# ==================== 启动靶机 (如果Docker可用) ====================
echo ""
echo "[5/5] 启动靶机环境..."

if docker info > /dev/null 2>&1; then
    echo ">>> 启动 DVWA..."
    docker rm -f dvwa 2>/dev/null || true
    docker run -d --name dvwa -p 80:80 vulnerables/web-dvwa || echo "    DVWA启动失败"
    echo "    DVWA完成"

    echo ""
    echo ">>> 启动 WebGoat..."
    docker rm -f webgoat 2>/dev/null || true
    docker run -d --name webgoat -p 8080:8080 -p 9090:9090 webgoat/webgoat || echo "    WebGoat启动失败"
    echo "    WebGoat完成"

    echo ""
    echo ">>> 启动 bwapp..."
    docker rm -f bwapp 2>/dev/null || true
    docker run -d --name bwapp -p 8081:80 raesene/bwapp || echo "    bwapp启动失败"
    echo "    bwapp完成"

    echo ""
    echo "Docker容器:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker ps
else
    echo "    [-] Docker不可用，跳过靶机启动"
    echo "    [*] 建议使用预装Docker的AutoDL镜像"
fi

# ==================== 结果 ====================
echo ""
echo "========================================"
echo "  部署结果"
echo "========================================"

echo ""
echo "项目位置: /root/workspace/manatrix"
echo "结果目录: /root/autodl-tmp/results"

echo ""
echo "========================================"
echo "  下一步"
echo "========================================"

echo ""
echo "1. 配置API Key:"
echo "   nano /root/workspace/manatrix/config.yaml"
echo "   llm.api_key: \"sk-xxx\""

echo ""
echo "2. 运行实验:"
echo "   cd /root/workspace/manatrix"
echo "   python scripts/run_bio_moe_ablation.py"

echo ""
if docker info > /dev/null 2>&1; then
    echo "靶机访问:"
    echo "  DVWA:    端口80 (admin/password)"
    echo "  WebGoat: 端口8080 (guest/guest)"
    echo ""
    echo "AutoDL控制台开端口后访问"
else
    echo "[!] Docker不可用，请:"
    echo "  - 使用预装Docker的镜像"
    echo "  - 或开启特权模式"
fi

echo ""
echo "========================================"
echo "  完成!"
echo "========================================"