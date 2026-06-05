# AutoDL 无GPU实例部署指南

## 推荐配置

这个项目不需要GPU，使用CPU实例更省钱。

### 实例选择

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| **镜像** | Ubuntu 22.04 | 稳定版 |
| **GPU** | 无 (CPU实例) | 省钱 |
| **CPU** | 4-8核 | 足够 |
| **内存** | 8-16GB | 足够 |
| **数据盘** | 勾选 | 持久化 |

### 预计费用

- CPU实例: ~0.5-1元/小时
- GPU实例: ~5-20元/小时
- **节省**: 90%以上

---

## 部署步骤

### 1. 创建实例

选择 **"社区镜像"** 或 **"Ubuntu 22.04"**
- 不要选GPU镜像
- 选最便宜的CPU实例

### 2. SSH连接

```bash
# 使用AutoDL提供的SSH命令
ssh -p <端口> root@<地址>
```

### 3. 一键部署

```bash
# 克隆项目
git clone https://github.com/RomanCohort/manatrix.git
cd manatrix

# 运行部署脚本
chmod +x scripts/setup_autodl_full.sh
./scripts/setup_autodl_full.sh
```

### 4. 配置API

```bash
# 编辑配置文件
nano config.yaml

# 添加DeepSeek API Key
# llm:
#   api_key: "sk-xxx"
```

### 5. 运行实验

```bash
# Bio-MoE消融实验 (约30分钟)
python scripts/run_bio_moe_ablation.py

# DVWA测试 (约5分钟)
python labs/scripts/dvwa_test.py

# WebGoat测试 (约5分钟)
python labs/scripts/test_webgoat_local.py
```

---

## 费用估算

| 实验 | 时间 | 费用 (CPU实例) |
|------|------|----------------|
| Bio-MoE消融 | 30分钟 | ~0.5元 |
| DVWA测试 | 5分钟 | ~0.1元 |
| WebGoat测试 | 5分钟 | ~0.1元 |
| **总计** | ~1小时 | **~1元** |

---

## 注意事项

1. **数据持久化**: 结果保存到 `/root/autodl-tmp/`
2. **API费用**: DeepSeek API另计 (~10-20元/实验)
3. **及时关机**: 实验完成后关机

---

*指南生成: 2026-06-05*