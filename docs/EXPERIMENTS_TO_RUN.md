# 需要补充的实验清单

根据数据合规性检查，以下实验需要补充：

---

## 实验状态总览

| 实验 | 数据表 | 当前状态 | 优先级 |
|------|--------|----------|--------|
| Bio-MoE消融实验 | Table 1 | ❌ 需补充 | 高 |
| 渗透测试成功率 | Table 2-3 | ⚠️ 需靶机 | 高 |
| 密码猜测对比 | Table 4-6 | ✅ 已修正 | - |
| Expert Routing | Table 2b | ✅ 已验证 | - |

---

## 🔴 高优先级实验

### 1. Bio-MoE 消融实验 (Table 1)

**目的**: 验证Bio-MoE架构各组件贡献

**实验配置**:
- A1 (Baseline): 无膜电位、无情绪状态
- A2 (Emotion): 仅情绪状态
- A3 (Membrane): 仅膜电位
- A4 (Full): 完整Bio-MoE

**数据需要**:
- Expert Entropy (专家熵)
- Load Balance (负载均衡)
- Response Quality (响应质量)
- Convergence Steps (收敛步数)

**实验规模**: n=400 (10场景 × 4配置 × 10次)

**脚本**: `scripts/run_bio_moe_ablation.py`

**运行方式**:
```bash
# AutoDL上运行
python scripts/run_bio_moe_ablation.py

# 预计时间: 30-60分钟 (API调用)
```

---

### 2. 渗透测试实验 (Table 2-3)

**目的**: 验证多专家系统渗透测试效果

**实验配置**:
- B1: 单LLM
- B2: 单专家
- B3: 3专家
- B4: 20专家

**靶机环境**:
- ✅ DVWA (Docker)
- ✅ WebGoat (Docker)
- ⚠️ Metasploitable2 (需VM)
- ⚠️ Windows Server (需许可证)

**数据需要**:
- 各环境成功率
- 平均测试时间
- 发现漏洞数

**脚本**:
- `labs/scripts/dvwa_test.py`
- `labs/scripts/test_webgoat_local.py`

**运行方式**:
```bash
# 在AutoDL上启动靶机
docker run -d -p 80:80 --name dvwa vulnerables/web-dvwa
docker run -d -p 8080:8080 --name webgoat webgoat/webgoat

# 运行测试
python labs/scripts/dvwa_test.py
python labs/scripts/test_webgoat_local.py
```

---

## 🟡 中优先级实验

### 3. 统计显著性测试

**目的**: 验证实验结果统计显著性

**需要计算**:
- Chi-squared test (卡方检验)
- Fisher's exact test
- Confidence intervals (置信区间)
- Cohen's d (效应量)

**脚本**: 需创建 `scripts/statistical_analysis.py`

---

## 🟢 已完成实验

### ✅ Expert Routing (Table 2b)

**状态**: 已验证
**文件**: `results/real_expert_results_20260605_150123.json`
**数据**: 64次DeepSeek API实验

### ✅ 密码猜测 (Table 4-6)

**状态**: 已修正
**文件**: `results/password_comparison_fixed_20260605_154041.json`
**数据**: 25目标密码测试

---

## AutoDL运行步骤

### Step 1: 克隆项目

```bash
git clone https://github.com/RomanCohort/manatrix.git
cd manatrix
```

### Step 2: 配置环境

```bash
chmod +x scripts/setup_autodl.sh
./scripts/setup_autodl.sh
```

### Step 3: 配置API

```bash
# 编辑config.yaml
nano config.yaml

# 添加DeepSeek API Key
# llm:
#   api_key: "your-api-key"
```

### Step 4: 运行实验

```bash
# 1. Bio-MoE消融实验 (优先)
python scripts/run_bio_moe_ablation.py

# 2. DVWA测试
python labs/scripts/dvwa_test.py

# 3. WebGoat测试
python labs/scripts/test_webgoat_local.py
```

### Step 5: 保存结果

```bash
# 结果自动保存到 results/
# 复制到数据盘
cp -r results /root/autodl-tmp/
```

---

## 预计时间

| 实验 | 预计时间 | API调用 |
|------|----------|---------|
| Bio-MoE消融 | 30-60分钟 | 400次 |
| DVWA测试 | 5-10分钟 | 0次 |
| WebGoat测试 | 5-10分钟 | 0次 |
| **总计** | **约1小时** | **400次** |

---

## 实验优先级排序

1. **Bio-MoE消融实验** (Table 1) - 最重要，论文核心
2. **DVWA/WebGoat测试** (Table 2-3) - 重要，有靶机环境
3. **统计显著性分析** - 补充材料

---

*清单生成: 2026-06-05*