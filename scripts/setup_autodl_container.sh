#!/bin/bash
# AutoDL 容器环境部署脚本 (无systemd版本)
# 适配AutoDL容器环境，不使用systemd
# 使用: chmod +x scripts/setup_autodl_container.sh && ./scripts/setup_autodl_container.sh

set -e

echo "========================================"
echo "  AutoDL 容器环境部署 (无systemd)"
echo "========================================"
echo ""

# ==================== 系统更新 ====================
echo "[1/6] 更新系统..."
apt update -qq
apt upgrade -y -qq

# ==================== 安装基础工具 ====================
echo "[2/6] 安装基础工具..."
apt install -y -qq \
    git curl wget \
    python3 python3-pip \
    openjdk-17-jdk \
    nmap \
    netcat-openbsd \
    jq \
    ca-certificates \
    gnupg

# ==================== 安装Docker (容器内方式) ====================
echo "[3/6] 安装Docker..."
if ! command -v docker &> /dev/null; then
    # 使用阿里云镜像源
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt update -qq
    apt install -y -qq docker-ce docker-ce-cli containerd.io

    # 直接启动dockerd (不使用systemd)
    dockerd > /tmp/dockerd.log 2>&1 &
    sleep 5

    echo "    Docker安装完成"
else
    echo "    Docker已安装"
    # 确保dockerd运行
    if ! pgrep -x "dockerd" > /dev/null; then
        dockerd > /tmp/dockerd.log 2>&1 &
        sleep 5
    fi
fi

# ==================== 创建工作目录 ====================
echo "[4/6] 创建工作目录..."
mkdir -p /root/workspace
mkdir -p /root/autodl-tmp/results
mkdir -p /root/autodl-tmp/logs

# ==================== 克隆项目 ====================
echo "[5/6] 克隆项目..."
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
echo "[6/6] 安装Python依赖..."
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
echo ""
echo "========================================"
echo "  启动靶机环境"
echo "========================================"

# 等待Docker就绪
echo "[*] 等待Docker就绪..."
sleep 10

# 检查Docker是否正常
if ! docker info > /dev/null 2>&1; then
    echo "[-] Docker未就绪，尝试重启..."
    pkill dockerd
    dockerd > /tmp/dockerd.log 2>&1 &
    sleep 15
fi

echo ""
echo ">>> 启动 DVWA..."
docker pull vulnerables/web-dvwa:latest
docker rm -f dvwa 2>/dev/null || true
docker run -d \
    --name dvwa \
    -p 80:80 \
    vulnerables/web-dvwa
echo "    DVWA 启动完成"

echo ""
echo ">>> 启动 WebGoat..."
docker pull webgoat/webgoat:latest
docker rm -f webgoat 2>/dev/null || true
docker run -d \
    --name webgoat \
    -p 8080:8080 \
    -p 9090:9090 \
    webgoat/webgoat
echo "    WebGoat 启动完成"

echo ""
echo ">>> 启动 bwapp..."
docker pull raesene/bwapp:latest
docker rm -f bwapp 2>/dev/null || true
docker run -d \
    --name bwapp \
    -p 8081:80 \
    raesene/bwapp
echo "    bwapp 启动完成"

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

# ==================== 获取公网IP ====================
echo ""
echo "========================================"
echo "  访问信息"
echo "========================================"

# AutoDL使用内部端口映射
echo ""
echo "靶机访问 (需要在AutoDL控制台开启端口):"
echo "  DVWA:     http://<公网地址>:80/DVWA"
echo "  WebGoat:  http://<公网地址>:8080/WebGoat"
echo "  bwapp:    http://<公网地址>:8081/bWAPP"

echo ""
echo "AutoDL端口映射:"
echo "  控制台 -> 自定义服务 -> 开启端口 80, 8080, 8081"

echo ""
echo "默认账号:"
echo "  DVWA:     admin / password"
echo "  WebGoat:  guest / guest"
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
echo "   python scripts/run_bio_moe_ablation.py"
echo "   python labs/scripts/dvwa_test.py"
echo "   python labs/scripts/test_webgoat_local.py"

echo ""
echo "3. 保存结果:"
echo "   cp -r results /root/autodl-tmp/"

echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"