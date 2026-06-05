#!/bin/bash
# AutoDL一键部署脚本
# 使用方法: chmod +x setup_autodl.sh && ./setup_autodl.sh

echo "========================================"
echo "  AutoDL 安全测试环境一键部署"
echo "========================================"

# 1. 更新系统
echo "[*] 更新系统..."
apt update && apt upgrade -y

# 2. 安装基础工具
echo "[*] 安装基础工具..."
apt install -y git curl wget python3 python3-pip openjdk-17-jdk nmap

# 3. 安装Docker
echo "[*] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
fi

# 4. 安装Python依赖
echo "[*] 安装Python依赖..."
pip3 install requests pyyaml numpy flask -q

# 5. 创建工作目录
echo "[*] 创建工作目录..."
mkdir -p /root/workspace/password_guesser
mkdir -p /root/autodl-tmp/results

# 6. 启动WebGoat
echo "[*] 启动WebGoat..."
docker pull webgoat/webgoat
docker run -d -p 8080:8080 -p 9090:9090 --name webgoat webgoat/webgoat

# 7. 启动DVWA
echo "[*] 启动DVWA..."
docker pull vulnerables/web-dvwa
docker run -d -p 80:80 --name dvwa vulnerables/web-dvwa

# 8. 等待服务启动
echo "[*] 等待服务启动..."
sleep 10

# 9. 检查服务状态
echo ""
echo "========================================"
echo "  环境检查"
echo "========================================"

echo ""
echo "Docker状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "Java版本:"
java -version 2>&1 | head -1

echo ""
echo "Python版本:"
python3 --version

echo ""
echo "========================================"
echo "  部署完成!"
echo "========================================"
echo ""
echo "访问地址:"
echo "  WebGoat: http://<公网IP>:8080/WebGoat"
echo "  DVWA:    http://<公网IP>/DVWA"
echo ""
echo "默认账号:"
echo "  WebGoat: guest/guest"
echo "  DVWA:    admin/password"
echo ""
echo "数据保存:"
echo "  将结果保存到: /root/autodl-tmp/results/"
echo ""