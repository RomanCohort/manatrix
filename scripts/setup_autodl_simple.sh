#!/bin/bash
# AutoDL 容器环境部署脚本 (简化版)
# 适配AutoDL容器环境，不依赖lsb_release
# 使用: chmod +x scripts/setup_autodl_simple.sh && ./scripts/setup_autodl_simple.sh

set -e

echo "========================================"
echo "  AutoDL 容器环境部署 (简化版)"
echo "========================================"
echo ""

# ==================== 清理错误的源文件 ====================
echo "[1/7] 清理Docker源文件..."
rm -f /etc/apt/sources.list.d/docker.list
apt update -qq

# ==================== 安装基础工具 ====================
echo "[2/7] 安装基础工具..."
apt install -y -qq \
    git curl wget \
    python3 python3-pip \
    openjdk-17-jdk \
    nmap jq || true

# 安装lsb-release (如果缺失)
apt install -y -qq lsb-release || true

# ==================== 安装Docker ====================
echo "[3/7] 安装Docker..."

# 检查Docker是否已安装
if command -v docker &> /dev/null; then
    echo "    Docker已安装"
else
    echo "    安装Docker..."

    # 直接下载安装脚本
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh

    echo "    Docker安装完成"
fi

# 启动Docker (容器内直接启动dockerd)
echo "    启动Docker守护进程..."
if ! pgrep -x "dockerd" > /dev/null; then
    nohup dockerd > /tmp/dockerd.log 2>&1 &
    sleep 10
fi

# 检查Docker是否正常
if docker info > /dev/null 2>&1; then
    echo "    Docker运行正常"
else
    echo "    [-] Docker启动失败，请检查日志: /tmp/dockerd.log"
fi

# ==================== 创建工作目录 ====================
echo "[4/7] 创建工作目录..."
mkdir -p /root/workspace
mkdir -p /root/autodl-tmp/results

# ==================== 克隆项目 ====================
echo "[5/7] 克隆项目..."
cd /root/workspace

if [ -d "manatrix" ]; then
    cd manatrix
    git pull origin master || true
else
    git clone https://github.com/RomanCohort/manatrix.git
    cd manatrix
fi

# ==================== 安装Python依赖 ====================
echo "[6/7] 安装Python依赖..."
pip3 install -q \
    requests \
    pyyaml \
    numpy \
    flask \
    scipy || true

# ==================== 启动靶机 ====================
echo "[7/7] 启动靶机环境..."

echo ""
echo ">>> 启动 DVWA..."
docker pull vulnerables/web-dvwa:latest || docker pull vulnerables/web-dvwa
docker rm -f dvwa 2>/dev/null || true
docker run -d --name dvwa -p 80:80 vulnerables/web-dvwa
echo "    DVWA完成"

echo ""
echo ">>> 启动 WebGoat..."
docker pull webgoat/webgoat:latest || docker pull webgoat/webgoat
docker rm -f webgoat 2>/dev/null || true
docker run -d --name webgoat -p 8080:8080 -p 9090:9090 webgoat/webgoat
echo "    WebGoat完成"

echo ""
echo ">>> 启动 bwapp..."
docker pull raesene/bwapp:latest || docker pull raesene/bwapp
docker rm -f bwapp 2>/dev/null || true
docker run -d --name bwapp -p 8081:80 raesene/bwapp
echo "    bwapp完成"

# ==================== 状态检查 ====================
echo ""
echo "========================================"
echo "  环境检查"
echo "========================================"

echo ""
echo "Docker容器:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker ps

echo ""
echo "========================================"
echo "  访问信息"
echo "========================================"

echo ""
echo "靶机地址 (AutoDL控制台开端口):"
echo "  DVWA:    端口80 → /DVWA (admin/password)"
echo "  WebGoat: 端口8080 → /WebGoat (guest/guest)"
echo "  bwapp:   端口8081 → /bWAPP (bee/bug)"

echo ""
echo "========================================"
echo "  下一步"
echo "========================================"

echo ""
echo "1. 配置API:"
echo "   nano /root/workspace/manatrix/config.yaml"
echo "   llm.api_key: \"your-key\""

echo ""
echo "2. 运行实验:"
echo "   cd /root/workspace/manatrix"
echo "   python scripts/run_bio_moe_ablation.py"
echo "   python labs/scripts/dvwa_test.py"

echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"