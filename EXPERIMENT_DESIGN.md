# Manatrix 实验设计方案

**项目**: AI驱动的智能密码猜测与渗透测试框架
**版本**: v3.10.0
**日期**: 2026-06-03

---

## 一、研究问题与实验概述

### 核心研究问题

| RQ | 问题 | 验证目标 | 核心指标 |
|----|------|----------|----------|
| **RQ1** | Bio-Gated MoE 是否优于传统 MoE？ | 创新点有效性 | 专家选择多样性、任务成功率、收敛速度 |
| **RQ2** | 多专家协作是否优于单 LLM？ | 系统增益 | 渗透成功率、建议质量评分 |
| **RQ3** | Reflective RL 是否优于标准 RL？ | 方法创新 | 累积奖励、学习效率、适应性 |
| **RQ4** | 系统在真实环境是否有效？ | 实用性验证 | 成功渗透率、漏洞发现率 |
| **RQ5** | 密码猜测准确率如何？ | 模型性能 | 命中率@k、熵分布 |

### 实验总览

```
实验1: Bio-Gated MoE 消融实验 (核心创新验证)
实验2: 多专家系统对比实验 (系统架构验证)
实验3: 渗透测试基准实验 (实用性验证)
实验4: 密码猜测性能实验 (模型能力验证)
```

---

## 二、实验 1: Bio-Gated MoE 消融实验

### 2.1 实验目的

验证生物门控机制（膜电位 + 情绪状态）对专家路由的贡献。

### 2.2 实验设计

#### 对比组设置

| 组别 | 配置 | 说明 |
|------|------|------|
| **A1 (基线)** | 标准 MoE (softmax 路由) | 传统方法 |
| **A2** | Bio-MoE 无膜电位 | 消融膜电位模块 |
| **A3** | Bio-MoE 无情绪状态 | 消融情绪状态模块 |
| **A4 (完整)** | Bio-MoE 完整版 | 提出的方法 |

#### 评估指标

```python
# 指标1: 专家选择多样性 (Entropy)
def expert_diversity_entropy(gating_weights):
    """
    计算专家选择的熵值
    熵值越高，专家使用越均匀

    H = -Σ p_i * log(p_i)
    """
    avg_gating = gating_weights.mean(dim=0)  # 平均门控权重
    entropy = -(avg_gating * torch.log(avg_gating + 1e-8)).sum()
    return entropy.item()

# 指标2: 任务成功率
success_rate = successful_tasks / total_tasks

# 指标3: 收敛速度 (达到目标性能所需步数)
convergence_steps = steps_to_reach_target_performance

# 指标4: 负载均衡系数
def load_balance_coefficient(expert_usage):
    """
    负载均衡系数
    1.0 = 完美均衡, 0.0 = 极不均衡
    """
    ideal = 1.0 / num_experts
    actual = expert_usage / expert_usage.sum()
    return 1.0 - torch.abs(actual - ideal).sum() / 2
```

### 2.3 实验步骤

```
Step 1: 准备测试数据集
  - 创建 1000 个模拟渗透测试状态
  - 包含不同阶段、不同复杂度的场景

Step 2: 初始化四个模型变体
  - A1: 标准 MoE (d_model=512, num_experts=8, top_k=2)
  - A2: Bio-MoE with use_membrane=False
  - A3: Bio-MoE with use_emotion=False
  - A4: Bio-MoE complete

Step 3: 运行路由测试
  for each model_variant:
    for each test_state:
      # 获取门控权重
      gating_weights = model.gating(state_vector)

      # 记录专家选择
      selected_experts = top_k(gating_weights)

      # 模拟专家响应
      response = get_expert_response(selected_experts, state)

      # 评估响应质量 (人工评分或规则评分)
      quality_score = evaluate_response(response, ground_truth)

Step 4: 统计分析
  - 计算各指标的平均值和标准差
  - 进行显著性检验 (ANOVA + post-hoc)
```

### 2.4 数据收集表格

| 测试ID | 模型变体 | 场景类型 | 专家选择熵 | 负载均衡系数 | 响应质量 | 收敛步数 |
|--------|----------|----------|------------|--------------|----------|----------|
| T001 | A1 | Web渗透 | 1.23 | 0.65 | 3.5 | - |
| T002 | A4 | Web渗透 | 1.89 | 0.92 | 4.2 | - |
| ... | ... | ... | ... | ... | ... | ... |

### 2.5 统计分析方法

```python
import scipy.stats as stats

# ANOVA 检验四组间差异
f_stat, p_value = stats.f_oneway(group_a1, group_a2, group_a3, group_a4)

# 如果 p < 0.05，进行事后检验
from scikit_posthocs import posthoc_tukey
posthoc = posthoc_tukey(data, val_col='metric', group_col='model')

# 效应量 (Cohen's d)
def cohens_d(group1, group2):
    n1, n2 = len(group1), len(group2)
    var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
    pooled_std = np.sqrt(((n1-1)*var1 + (n2-1)*var2) / (n1+n2-2))
    return (np.mean(group1) - np.mean(group2)) / pooled_std
```

### 2.6 预期结果

| 模型 | 专家选择熵 | 负载均衡 | 响应质量 | 相对基线提升 |
|------|------------|----------|----------|--------------|
| A1 (基线) | 1.2 ± 0.3 | 0.60 | 3.2 ± 0.5 | - |
| A2 | 1.5 ± 0.2 | 0.75 | 3.6 ± 0.4 | +12.5% |
| A3 | 1.4 ± 0.2 | 0.70 | 3.4 ± 0.4 | +6.3% |
| **A4 (完整)** | **1.8 ± 0.2** | **0.88** | **4.1 ± 0.3** | **+28.1%** |

---

## 三、实验 2: 多专家系统对比实验

### 3.1 实验目的

验证多专家协作系统相对于单一LLM的优势。

### 3.2 实验设计

#### 对比组设置

| 组别 | 配置 | 说明 |
|------|------|------|
| **B1** | 单一 LLM (无专家) | 直接使用 DeepSeek/GPT-4 |
| **B2** | 单专家 (侦察专家) | 只使用侦察专家 |
| **B3** | 3 专家系统 | 侦察+漏洞+利用 |
| **B4** | 完整 20 专家系统 | 提出的完整方案 |

#### 测试场景

| 场景 | 目标 | 漏洞类型 | 难度 |
|------|------|----------|------|
| DVWA Web | Web应用 | SQLi, XSS, CSRF | 低 |
| Metasploitable2 | Linux服务器 | 多种已知漏洞 | 低-中 |
| HackTheBox Starting Point | 混合环境 | 多种漏洞 | 中 |
| Active Directory Lab | AD域 | Kerberoasting等 | 中-高 |

### 3.3 评估指标

```python
# 指标1: 渗透成功率
penetration_success_rate = successful_penetrations / total_attempts

# 指标2: 完成时间
time_to_completion  # 秒

# 指标3: 发现漏洞数
vulnerabilities_discovered = len(unique_vulns_found)

# 指标4: 建议质量 (1-5分)
def evaluate_advice_quality(advice, ground_truth):
    """
    评估建议质量

    维度:
    - 正确性 (Correctness): 建议是否有效
    - 完整性 (Completeness): 是否覆盖所有必要步骤
    - 专业性 (Professionalism): 工具使用是否恰当
    - 安全性 (Safety): 是否避免触发检测
    """
    scores = {
        'correctness': score_correctness(advice, ground_truth),
        'completeness': score_completeness(advice, ground_truth),
        'professionalism': score_professionalism(advice),
        'safety': score_safety(advice)
    }
    return np.mean(list(scores.values()))

# 指标5: 共识度 (Jaccard相似度)
def calculate_consensus(expert_recommendations):
    """
    计算专家间的共识度
    """
    similarity_matrix = []
    for i, rec1 in enumerate(expert_recommendations):
        for j, rec2 in enumerate(expert_recommendations):
            if i < j:
                # Jaccard相似度
                tools_i = set(rec1.tools_to_use)
                tools_j = set(rec2.tools_to_use)
                jaccard = len(tools_i & tools_j) / len(tools_i | tools_j)
                similarity_matrix.append(jaccard)
    return np.mean(similarity_matrix)
```

### 3.4 实验步骤

```
Step 1: 环境准备
  - 部署 DVWA (Docker)
  - 部署 Metasploitable2 (虚拟机)
  - 注册 HackTheBox 账号

Step 2: 运行渗透测试
  for each system_variant:
    for each test_scenario:
      # 初始化系统
      system = create_system(variant)

      # 开始渗透测试
      start_time = time.time()

      # 执行测试 (最多100步或成功)
      while not success and steps < 100:
        # 获取状态
        state = get_current_state()

        # 获取专家建议
        advice = system.get_advice(state, query)

        # 执行建议
        result = execute_action(advice.recommended_actions)

        # 记录结果
        log_step(state, advice, result)

      end_time = time.time()

      # 记录指标
      record_metrics(
        success=success,
        time=end_time - start_time,
        vulns_found=vulnerabilities_discovered,
        steps=steps
      )

Step 3: 数据分析
  - 计算各指标的均值、标准差
  - 可视化对比
  - 统计检验
```

### 3.5 数据收集表格

| 测试ID | 系统变体 | 场景 | 成功 | 时间(s) | 漏洞数 | 建议质量 | 共识度 |
|--------|----------|------|------|---------|--------|----------|--------|
| E001 | B1 | DVWA | N | - | 1 | 2.5 | - |
| E002 | B4 | DVWA | Y | 120 | 4 | 4.2 | 0.78 |
| E003 | B1 | MS2 | N | - | 2 | 2.1 | - |
| E004 | B4 | MS2 | Y | 180 | 8 | 4.5 | 0.82 |
| ... | ... | ... | ... | ... | ... | ... | ... |

### 3.6 预期结果

| 系统 | 成功率 | 平均时间 | 平均漏洞数 | 建议质量 |
|------|--------|----------|------------|----------|
| B1 (单LLM) | 20% | 300s | 1.5 | 2.3 |
| B2 (单专家) | 35% | 250s | 2.5 | 3.0 |
| B3 (3专家) | 55% | 180s | 4.0 | 3.8 |
| **B4 (20专家)** | **75%** | **150s** | **6.5** | **4.3** |

---

## 四、实验 3: 渗透测试基准实验

### 4.1 实验目的

在标准化测试环境中验证系统的实用性。

### 4.2 测试环境详细配置

#### 4.2.1 Metasploitable2 测试

```bash
# 下载 Metasploitable2
wget https://sourceforge.net/projects/metasploitable/files/Metasploitable2/

# VirtualBox 导入
VBoxManage import Metasploitable2.ova

# 网络配置 (Host-only)
VBoxManage modifyvm "Metasploitable2" --nic1 hostonly --hostonlyadapter1 vboxnet0

# 启动
VBoxManage startvm "Metasploitable2" --type headless

# 默认IP: 192.168.56.101
# 默认账号: msfadmin / msfadmin
```

#### 4.2.2 DVWA 测试

```bash
# Docker 部署
docker run -d --name dvwa \
  -p 8080:80 \
  vulnerables/web-dvwa

# 访问: http://localhost:8080
# 默认账号: admin / password
```

#### 4.2.3 HackTheBox 配置

```bash
# 下载 VPN 配置
# 从 https://www.hackthebox.com/home/htb/access 获取

# 连接 VPN
sudo openvpn your_username.ovpn

# 测试连通性
ping 10.10.10.10  # HTB Starting Point 机器
```

### 4.3 测试用例

#### 4.3.1 DVWA 测试用例

| 用例 | 漏洞类型 | 预期步骤 | 验证标准 |
|------|----------|----------|----------|
| DVWA-01 | SQL Injection (Low) | 1. 检测注入点 2. 枚举数据库 3. 提取用户表 | 成功获取用户凭据 |
| DVWA-02 | SQL Injection (Medium) | 1. POST注入 2. 绕过过滤 | 成功注入 |
| DVWA-03 | XSS Reflected | 1. 注入测试 2. 构造payload | 弹窗成功 |
| DVWA-04 | XSS Stored | 1. 存储注入 2. 获取Cookie | 获取管理员Cookie |
| DVWA-05 | CSRF | 1. 构造恶意页面 2. 诱导点击 | 成功修改密码 |
| DVWA-06 | Command Injection | 1. 命令注入 2. 反弹Shell | 获取Shell |

#### 4.3.2 Metasploitable2 测试用例

| 用例 | 服务 | 端口 | 漏洞 | 验证标准 |
|------|------|------|------|----------|
| MS2-01 | vsftpd | 21 | 后门 | 获取Root Shell |
| MS2-02 | Samba | 445 | 符号链接 | 读取敏感文件 |
| MS2-03 | distcc | 3632 | 命令执行 | 执行任意命令 |
| MS2-04 | UnrealIRCd | 6667 | 后门 | 获取Shell |
| MS2-05 | MySQL | 3306 | 弱口令 | 登录成功 |
| MS2-06 | Apache | 80 | 多种漏洞 | 获取Shell |

### 4.4 自动化测试脚本

```python
import subprocess
import json
import time
from datetime import datetime

class PenetrationTestRunner:
    """渗透测试自动化运行器"""

    def __init__(self, target_ip, system_variant):
        self.target = target_ip
        self.system = system_variant
        self.results = []

    def run_test(self, test_case):
        """运行单个测试用例"""
        start_time = time.time()

        # 初始化状态
        state = {
            "target": self.target,
            "phase": "reconnaissance",
            "services": [],
            "vulnerabilities": [],
            "credentials": [],
            "has_shell": False,
            "is_admin": False
        }

        steps = 0
        max_steps = 50
        success = False

        while steps < max_steps and not success:
            # 获取系统建议
            advice = self.system.get_advice(state)

            # 执行动作
            result = self.execute_action(advice.recommended_actions[0])

            # 更新状态
            state = self.update_state(state, result)
            success = result.get("success", False)

            # 记录
            self.results.append({
                "step": steps,
                "advice": advice.to_dict(),
                "result": result
            })

            steps += 1

        end_time = time.time()

        return {
            "test_case": test_case,
            "success": success,
            "steps": steps,
            "time_seconds": end_time - start_time,
            "final_state": state
        }

    def execute_action(self, action):
        """执行渗透测试动作"""
        tool = action.get("tool", "")
        command = action.get("command", "")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout"}

    def update_state(self, state, result):
        """更新渗透测试状态"""
        # 根据执行结果更新状态
        # 这里需要根据具体输出解析
        return state

# 运行测试
runner = PenetrationTestRunner("192.168.56.101", system)
result = runner.run_test("MS2-01")
print(json.dumps(result, indent=2))
```

### 4.5 数据收集表格

| 用例ID | 环境 | 系统 | 成功 | 步骤数 | 时间(s) | 发现漏洞 | 关键动作 |
|--------|------|------|------|--------|---------|----------|----------|
| RUN-001 | DVWA | B1 | N | 50 | 600 | 1 | nmap扫描 |
| RUN-002 | DVWA | B4 | Y | 12 | 180 | 4 | nmap→nikto→sqlmap |
| RUN-003 | MS2 | B1 | N | 50 | 540 | 2 | 简单扫描 |
| RUN-004 | MS2 | B4 | Y | 8 | 120 | 6 | 多专家协作 |

---

## 五、实验 4: 密码猜测性能实验

### 5.1 实验目的

验证 MAMBA + 差分进化方法在密码猜测任务上的性能。

### 5.2 数据集

#### 公开数据集

| 数据集 | 大小 | 来源 | 获取方式 |
|--------|------|------|----------|
| RockYou | 14,341,564 | 泄露数据 | 公开下载 |
| 000webhost | 15,252,206 | 泄露数据 | 研究可用 |
| LinkedIn (样本) | - | 泄露数据 | 研究申请 |

**注意**: 使用密码数据集进行学术研究需遵守伦理规范，仅用于模型训练和性能评估，不得用于非法目的。

#### 数据预处理

```python
import hashlib
import random

def preprocess_passwords(raw_file, output_file, sample_size=1000000):
    """
    预处理密码数据集

    1. 去重
    2. 过滤无效密码 (长度<4 或 >32)
    3. 随机采样
    """
    passwords = set()

    with open(raw_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            pwd = line.strip()
            if 4 <= len(pwd) <= 32:
                passwords.add(pwd)

    # 随机采样
    if len(passwords) > sample_size:
        passwords = random.sample(passwords, sample_size)

    # 划分训练/测试集
    train_size = int(len(passwords) * 0.8)
    train = random.sample(passwords, train_size)
    test = [p for p in passwords if p not in train]

    return train, test
```

### 5.3 评估指标

```python
import numpy as np
from collections import Counter

def guess_rate_at_k(generated_passwords, test_passwords, k):
    """
    计算 @K 命中率

    Args:
        generated_passwords: 生成的密码列表 (按概率排序)
        test_passwords: 测试集密码
        k: 截断位置

    Returns:
        命中率
    """
    test_set = set(test_passwords)
    top_k = set(generated_passwords[:k])
    hits = len(test_set & top_k)
    return hits / len(test_set)

def calculate_entropy(password, char_sets):
    """
    计算密码熵

    Args:
        password: 密码字符串
        char_sets: 字符集大小 {'lower': 26, 'upper': 26, 'digit': 10, 'special': 32}
    """
    # 确定使用的字符集
    charset_size = 0
    if any(c.islower() for c in password):
        charset_size += char_sets['lower']
    if any(c.isupper() for c in password):
        charset_size += char_sets['upper']
    if any(c.isdigit() for c in password):
        charset_size += char_sets['digit']
    if any(not c.isalnum() for c in password):
        charset_size += char_sets['special']

    # 计算熵
    entropy = len(password) * np.log2(charset_size) if charset_size > 0 else 0
    return entropy

def pattern_distribution(passwords):
    """
    分析密码模式分布

    返回: PCFG模式统计
    """
    patterns = Counter()
    for pwd in passwords:
        pattern = extract_pattern(pwd)  # L4D3S2 -> abc123!@
        patterns[pattern] += 1
    return patterns
```

### 5.4 对比方法

| 方法 | 描述 | 来源 |
|------|------|------|
| Markov Chain | n-gram马尔可夫链 | 基线方法 |
| PCFG | 概率上下文无关语法 | Weir et al. (2009) |
| PassGPT | GPT-2 密码生成 | 现有方法 |
| LSTM-Password | LSTM序列模型 | 现有方法 |
| **MAMBA + DE** | 提出的方法 | 本项目 |

### 5.5 实验配置

```python
# 模型配置
MAMBA_CONFIG = {
    "vocab_size": 128,
    "d_model": 256,
    "n_layers": 4,
    "max_length": 32,
    "dropout": 0.1
}

# 差分进化配置
DE_CONFIG = {
    "population_size": 100,
    "max_generations": 500,
    "mutation_strategies": ["rand/1", "best/1", "current-to-best/1"],
    "crossover_rate": 0.7,
    "adaptation": "SHADE"
}

# 训练配置
TRAINING_CONFIG = {
    "batch_size": 512,
    "learning_rate": 1e-4,
    "epochs": 100,
    "warmup_steps": 1000,
    "gradient_accumulation_steps": 4,
    "amp": True
}
```

### 5.6 数据收集表格

| 方法 | @100 | @1000 | @10000 | @100000 | 平均熵 | 生成速度(pw/s) |
|------|------|-------|--------|---------|--------|----------------|
| Markov | 2.1% | 5.3% | 8.7% | 12.4% | 18.5 | 50000 |
| PCFG | 1.8% | 4.8% | 8.2% | 12.1% | 22.3 | 30000 |
| PassGPT | 2.5% | 6.1% | 10.2% | 15.3% | 19.8 | 1000 |
| LSTM | 2.3% | 5.8% | 9.8% | 14.8% | 20.1 | 5000 |
| **MAMBA+DE** | **3.2%** | **7.5%** | **12.5%** | **18.9%** | **21.5** | **8000** |

---

## 六、统计分析计划

### 6.1 样本量计算

```python
from scipy import stats
import numpy as np

def calculate_sample_size(effect_size, alpha=0.05, power=0.8):
    """
    计算所需样本量

    Args:
        effect_size: 预期效应量 (Cohen's d)
        alpha: 显著性水平
        power: 统计功效
    """
    from scipy.stats import norm

    z_alpha = norm.ppf(1 - alpha/2)
    z_beta = norm.ppf(power)

    n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
    return int(np.ceil(n))

# 假设中等效应量 (d=0.5)
sample_size = calculate_sample_size(0.5)
print(f"每组需要 {sample_size} 个样本")
```

### 6.2 显著性检验

```python
import scipy.stats as stats
from scipy.stats import shapiro, levene

def statistical_analysis(group1, group2, group3=None, group4=None):
    """
    完整的统计分析流程
    """
    results = {}

    # 1. 正态性检验
    _, p_normal = shapiro(group1)
    results['normality'] = p_normal > 0.05

    # 2. 方差齐性检验
    if group3 is None:
        _, p_levene = levene(group1, group2)
    else:
        _, p_levene = levene(group1, group2, group3, group4)
    results['homogeneity'] = p_levene > 0.05

    # 3. 选择适当的检验方法
    if results['normality'] and results['homogeneity']:
        if group3 is None:
            # 独立样本t检验
            t_stat, p_value = stats.ttest_ind(group1, group2)
            results['test'] = 't-test'
        else:
            # 单因素方差分析
            f_stat, p_value = stats.f_oneway(group1, group2, group3, group4)
            results['test'] = 'ANOVA'
    else:
        if group3 is None:
            # Mann-Whitney U检验
            u_stat, p_value = stats.mannwhitneyu(group1, group2)
            results['test'] = 'Mann-Whitney U'
        else:
            # Kruskal-Wallis检验
            h_stat, p_value = stats.kruskal(group1, group2, group3, group4)
            results['test'] = 'Kruskal-Wallis'

    results['p_value'] = p_value
    results['significant'] = p_value < 0.05

    # 4. 效应量
    if group3 is None:
        results['effect_size'] = cohens_d(group1, group2)
    else:
        results['effect_size'] = eta_squared([group1, group2, group3, group4])

    return results
```

### 6.3 可视化模板

```python
import matplotlib.pyplot as plt
import seaborn as sns

def plot_comparison(data, metric_name, save_path):
    """
    绘制对比图
    """
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # 箱线图
    sns.boxplot(data=data, ax=axes[0])
    axes[0].set_title(f'{metric_name} Distribution')
    axes[0].set_xlabel('Model Variant')
    axes[0].set_ylabel(metric_name)

    # 均值柱状图 (带误差棒)
    means = data.mean()
    stds = data.std()
    x = range(len(means))

    axes[1].bar(x, means, yerr=stds, capsize=5, alpha=0.7)
    axes[1].set_title(f'{metric_name} Comparison')
    axes[1].set_xlabel('Model Variant')
    axes[1].set_ylabel(metric_name)
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(data.columns)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()

def plot_convergence(curves, labels, save_path):
    """
    绘制收敛曲线
    """
    plt.figure(figsize=(10, 6))

    for curve, label in zip(curves, labels):
        plt.plot(curve, label=label)

    plt.xlabel('Training Steps')
    plt.ylabel('Performance')
    plt.title('Convergence Comparison')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(save_path, dpi=300)
    plt.close()
```

---

## 七、实验环境与工具

### 7.1 硬件配置

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| GPU | NVIDIA RTX 3060 (12GB) | NVIDIA RTX 4090 (24GB) |
| CPU | 8核 | 16核+ |
| 内存 | 32GB | 64GB |
| 存储 | 500GB SSD | 1TB NVMe SSD |

### 7.2 软件环境

```bash
# 创建 conda 环境
conda create -n manatrix python=3.10
conda activate manatrix

# 安装依赖
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install numpy pandas scipy scikit-learn
pip install matplotlib seaborn
pip install transformers einops
pip install fastapi uvicorn pydantic
pip install pytest pytest-cov

# 安装渗透测试工具
sudo apt install nmap nikto metasploit-framework
pip install python-nmap

# 安装 Docker (用于测试环境)
sudo apt install docker.io docker-compose
```

### 7.3 实验管理工具

```python
# 使用 MLflow 跟踪实验
import mlflow

mlflow.set_experiment("manatrix_benchmark")

with mlflow.start_run():
    mlflow.log_params({
        "model": "BioMoE",
        "num_experts": 8,
        "d_model": 512
    })

    for epoch in range(epochs):
        # 训练...
        mlflow.log_metric("loss", loss, step=epoch)
        mlflow.log_metric("accuracy", acc, step=epoch)

    mlflow.log_artifact("model.pt")
```

---

## 八、实验时间表

| 阶段 | 任务 | 预计时间 |
|------|------|----------|
| **第1周** | 环境搭建、数据准备 | 2天 |
| **第1周** | Bio-MoE 消融实验 | 3天 |
| **第2周** | 多专家对比实验 | 4天 |
| **第3周** | 渗透测试基准实验 | 5天 |
| **第4周** | 密码猜测性能实验 | 4天 |
| **第4周** | 数据分析、可视化 | 3天 |

**总计**: 约 4 周

---

## 九、伦理与安全声明

### 9.1 研究伦理

1. **密码数据集使用**: 仅用于学术研究，不用于非法目的
2. **渗透测试**: 仅在授权环境中进行
3. **数据隐私**: 不存储、不泄露真实用户信息

### 9.2 安全注意事项

```python
# 实验安全配置
SAFETY_CONFIG = {
    "allowed_targets": [
        "192.168.56.0/24",  # 本地测试网络
        "10.10.10.0/24",    # HackTheBox VPN
    ],
    "blocked_targets": [
        "0.0.0.0/0",        # 禁止扫描公网
    ],
    "max_concurrent_scans": 3,
    "rate_limit": "100/s",
}
```

### 9.3 负责任的披露

如果实验过程中发现新的漏洞或安全问题，将按照负责任披露原则：
1. 先报告给厂商
2. 给予合理的修复时间
3. 之后发表研究成果

---

## 十、附录

### 附录 A: 数据收集模板

#### A.1 Bio-MoE 消融实验记录表

```csv
test_id,timestamp,model_variant,scenario_type,expert_entropy,load_balance,response_quality,convergence_steps,notes
T001,2026-06-10T10:00:00,A1,Web,1.23,0.65,3.5,-,基线测试
T002,2026-06-10T10:05:00,A4,Web,1.89,0.92,4.2,-,完整Bio-MoE
```

#### A.2 渗透测试记录表

```csv
run_id,timestamp,environment,system_variant,test_case,success,steps,time_seconds,vulns_found,key_actions
E001,2026-06-15T14:00:00,DVWA,B1,SQLi-Low,N,50,600,1,nmap扫描
E002,2026-06-15T14:10:00,DVWA,B4,SQLi-Low,Y,12,180,4,nmap→nikto→sqlmap
```

### 附录 B: 脚本清单

| 脚本 | 用途 | 位置 |
|------|------|------|
| `run_ablation.py` | 运行消融实验 | `scripts/` |
| `run_benchmark.py` | 运行基准测试 | `scripts/` |
| `analyze_results.py` | 分析实验结果 | `scripts/` |
| `plot_figures.py` | 生成图表 | `scripts/` |
| `setup_test_env.sh` | 配置测试环境 | `scripts/` |

### 附录 C: 参考论文

1. Weir, M., et al. (2009). "Testing metrics for password creation policies by attacking large sets of revealed passwords." CCS.
2. Hitaj, B., et al. (2019). "PassGAN: A Deep Learning Approach for Password Guessing." ESORICS.
3. Fedus, W., et al. (2021). "Switch Transformers: Scaling to Trillion Parameter Models." JMLR.
4. Wang, Z., & Zhang, L. (2026). "Human-AI Collaboration Patterns in Knowledge Work." IJETHE.

---

**文档版本**: v1.0
**最后更新**: 2026-06-03
**作者**: Claude (academic-pipeline orchestrator)
