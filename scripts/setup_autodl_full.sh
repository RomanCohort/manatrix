#!/bin/bash
# AutoDL 完整环境部署脚本
# 包含: Docker、靶机环境、Python依赖、项目克隆
# 使用: chmod +x scripts/setup_autodl_full.sh && ./scripts/setup_autodl_full.sh

set -e

echo "========================================"
echo "  AutoDL 渗透测试环境完整部署"
echo "========================================"
echo ""

# ==================== 系统更新 ====================
echo "[1/7] 更新系统..."
apt update -qq
apt upgrade -y -qq

# ==================== 安装基础工具 ====================
echo "[2/7] 安装基础工具..."
apt install -y -qq \
    git curl wget \
    python3 python3-pip python3-venv \
    openjdk-17-jdk \
    nmap \
    netcat-openbsd \
    jq

# ==================== 安装Docker ====================
echo "[3/7] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo "    Docker安装完成"
else
    echo "    Docker已安装"
fi

# ==================== 创建工作目录 ====================
echo "[4/7] 创建工作目录..."
mkdir -p /root/workspace
mkdir -p /root/autodl-tmp/results
mkdir -p /root/autodl-tmp/logs

# ==================== 克隆项目 ====================
echo "[5/7] 克隆项目..."
cd /root/workspace

if [ -d "manatrix" ]; then
    echo "    项目已存在，更新..."
    cd manatrix
    git pull origin master
else
    echo "    克隆新项目..."
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
    scipy

# 如果项目有requirements.txt
if [ -f "requirements.txt" ]; then
    pip3 install -q -r requirements.txt
fi

# ==================== 启动靶机环境 ====================
echo "[7/7] 启动靶机环境..."

echo ""
echo "    >>> 启动 DVWA..."
docker pull vulnerables/web-dvwa:latest
docker rm -f dvwa 2>/dev/null || true
docker run -d \
    --name dvwa \
    -p 80:80 \
    --restart unless-stopped \
    vulnerables/web-dvwa
echo "    DVWA 启动完成"

echo ""
echo "    >>> 启动 WebGoat..."
docker pull webgoat/webgoat:latest
docker rm -f webgoat 2>/dev/null || true
docker run -d \
    --name webgoat \
    -p 8080:8080 \
    -p 9090:9090 \
    --restart unless-stopped \
    webgoat/webgoat
echo "    WebGoat 启动完成"

echo ""
echo "    >>> 启动 bwapp (备用靶场)..."
docker pull raesene/bwapp:latest
docker rm -f bwapp 2>/dev/null || true
docker run -d \
    --name bwapp \
    -p 8081:80 \
    --restart unless-stopped \
    raesene/bwapp
echo "    bwapp 启动完成"

# ==================== 等待服务启动 ====================
echo ""
echo "[*] 等待服务启动 (30秒)..."
sleep 30

# ==================== 检查服务状态 ====================
echo ""
echo "========================================"
echo "  环境检查"
echo "========================================"

echo ""
echo "Docker容器状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Java版本:"
java -version 2>&1 | head -1

echo ""
echo "Python版本:"
python3 --version

echo ""
echo "项目位置:"
ls -la /root/workspace/manatrix/scripts/*.py | head -10

# ==================== 获取公网IP ====================
echo ""
echo "========================================"
echo "  访问信息"
echo "========================================"

PUBLIC_IP=$(curl -s ifconfig.me || echo "<公网IP>")

echo ""
echo "靶机访问地址:"
echo "  DVWA:     http://${PUBLIC_IP}:80/DVWA"
echo "  WebGoat:  http://${PUBLIC_IP}:8080/WebGoat"
echo "  bwapp:    http://${PUBLIC_IP}:8081/bWAPP"

echo ""
echo "默认账号:"
echo "  DVWA:     admin / password"
echo "  WebGoat:  guest / guest (或注册新用户)"
echo "  bwapp:    bee / bug"

echo ""
echo "========================================"
echo "  下一步操作"
echo "========================================"

echo ""
echo "1. 配置API Key:"
echo "   nano /root/workspace/manatrix/config.yaml"
echo "   添加: llm.api_key: \"your-deepseek-key\""

echo ""
echo "2. 运行实验:"
echo "   cd /root/workspace/manatrix"
echo "   python scripts/run_bio_moe_ablation.py    # Bio-MoE消融实验"
echo "   python labs/scripts/dvwa_test.py          # DVWA测试"
echo "   python labs/scripts/test_webgoat_local.py # WebGoat测试"

echo ""
echo "3. 查看结果:"
echo "   ls /root/workspace/manatrix/results/"

echo ""
echo "4. 保存到数据盘:"
echo "   cp -r results /root/autodl-tmp/"

echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"