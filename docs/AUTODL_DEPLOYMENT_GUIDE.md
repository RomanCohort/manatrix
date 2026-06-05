# AutoDL 云服务器部署指南

## 部署目的

在AutoDL云服务器上运行渗透测试实验，用于论文数据验证。

---

## 1. 创建实例

### 推荐配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 镜像 | Ubuntu 22.04 / Kali Linux | 安全测试首选 |
| GPU | RTX 3090 / 4090 | LLM推理需要 |
| CPU | 8核+ | 多任务处理 |
| 内存 | 32GB+ | 大模型加载 |
| 数据盘 | 勾选 | 数据持久化 |

### 镜像选择

**选项A: Ubuntu 22.04 (推荐)**
```bash
# 基础镜像，需要安装工具
```

**选项B: Kali Linux**
```bash
# 预装安全工具
```

---

## 2. 连接实例

### SSH连接

```bash
# AutoDL提供SSH命令
ssh -p <端口> root@<地址>

# 或使用密码连接
ssh root@<地址> -p <端口>
# 密码在控制台查看
```

---

## 3. 环境安装

### 3.1 基础工具

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y git curl wget python3 python3-pip openjdk-17-jdk

# 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker
```

### 3.2 安全工具

```bash
# 安装nmap
apt install -y nmap

# 安装sqlmap
pip3 install sqlmap

# 安装metasploit (可选)
apt install -y metasploit-framework

# 安装hydra
apt install -y hydra
```

### 3.3 Python环境

```bash
# 安装Python依赖
pip3 install requests pyyaml numpy
```

---

## 4. 部署项目

### 4.1 克隆项目

```bash
# 创建工作目录
mkdir -p /root/workspace
cd /root/workspace

# 克隆项目 (如果有Git仓库)
# git clone <your-repo-url>

# 或上传项目文件
# 使用SCP或AutoDL文件管理上传
```

### 4.2 上传项目文件

**方法1: SCP上传**
```bash
# 本地执行
scp -P <端口> -r D:/password_guesser root@<地址>:/root/workspace/
```

**方法2: AutoDL文件管理**
- 登录AutoDL控制台
- 进入"文件存储"
- 上传项目文件夹

---

## 5. 启动靶机环境

### 5.1 WebGoat

```bash
# 拉取镜像
docker pull webgoat/webgoat

# 启动WebGoat
docker run -d -p 8080:8080 -p 9090:9090 --name webgoat webgoat/webgoat

# 访问
# http://<公网IP>:8080/WebGoat
```

### 5.2 DVWA

```bash
# 拉取镜像
docker pull vulnerables/web-dvwa

# 启动DVWA
docker run -d -p 80:80 --name dvwa vulnerables/web-dvwa

# 访问
# http://<公网IP>/DVWA
# 账号: admin/password
```

### 5.3 Metasploitable2

```bash
# 下载镜像 (需要VMware/VirtualBox)
# 在AutoDL上使用Docker版本替代

# 使用vulhub靶场
git clone https://github.com/vulhub/vulhub.git
cd vulhub
```

---

## 6. 运行实验

### 6.1 配置API

```bash
# 编辑配置文件
nano /root/workspace/password_guesser/config.yaml

# 添加DeepSeek API Key
# llm:
#   provider: deepseek
#   api_key: "your-api-key"
```

### 6.2 运行测试

```bash
cd /root/workspace/password_guesser

# 运行Expert Routing测试
python scripts/run_real_expert_test.py

# 运行Bio-MoE消融实验
python scripts/run_bio_moe_ablation.py

# 运行密码猜测测试
python scripts/run_password_comparison_fixed.py

# 运行WebGoat测试
python labs/scripts/test_webgoat_local.py
```

---

## 7. 获取公网访问

### 7.1 AutoDL端口映射

```bash
# 在AutoDL控制台 -> 自定义服务 -> 开启端口
# 添加端口: 8080, 80, 9090

# 获取访问链接
# http://<区域>-<实例ID>.autodl.pro:<端口>
```

### 7.2 SSH隧道 (备选)

```bash
# 本地创建隧道
ssh -L 8080:localhost:8080 -p <端口> root@<地址>
```

---

## 8. 数据持久化

### 8.1 保存到数据盘

```bash
# AutoDL数据盘挂载在 /root/autodl-tmp
# 将结果保存到此目录

cp -r /root/workspace/password_guesser/results /root/autodl-tmp/
```

### 8.2 下载结果

```bash
# 方法1: SCP下载
scp -P <端口> -r root@<地址>:/root/autodl-tmp/results D:/password_guesser/

# 方法2: AutoDL文件管理下载
```

---

## 9. 成本优化

### 9.1 使用竞价实例

- 竞价实例价格更低
- 可能被回收，注意保存数据

### 9.2 及时关机

```bash
# 实验完成后在控制台关机
# 或使用定时任务
```

---

## 10. 一键部署脚本

创建 `setup_autodl.sh`:

```bash
#!/bin/bash

echo "=== AutoDL Environment Setup ==="

# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y git curl wget python3 python3-pip openjdk-17-jdk nmap

# 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker

# 安装Python依赖
pip3 install requests pyyaml numpy

# 启动WebGoat
docker pull webgoat/webgoat
docker run -d -p 8080:8080 -p 9090:9090 --name webgoat webgoat/webgoat

# 启动DVWA
docker pull vulnerables/web-dvwa
docker run -d -p 80:80 --name dvwa vulnerables/web-dvwa

echo "=== Setup Complete ==="
echo "WebGoat: http://<公网IP>:8080/WebGoat"
echo "DVWA: http://<公网IP>/DVWA"
```

运行:
```bash
chmod +x setup_autodl.sh
./setup_autodl.sh
```

---

## 检查清单

- [ ] 创建AutoDL实例
- [ ] SSH连接成功
- [ ] 安装Docker
- [ ] 安装Python依赖
- [ ] 上传项目文件
- [ ] 配置API Key
- [ ] 启动WebGoat
- [ ] 启动DVWA
- [ ] 运行测试脚本
- [ ] 保存结果到数据盘

---

*指南生成: 2026-06-05*