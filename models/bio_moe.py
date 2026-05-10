"""
Bio-Gated Mixture of Experts (MoE 2.0)

类生物门控混合专家模型 - 模拟生物神经元的门控机制

核心思想:
1. 膜电位(Membrane Potential): 历史状态的累积权重，类似于神经元的长期记忆
2. 情绪状态(Emotional State): 系统当前的"状态"影响路由决策
3. 动态门控(Dynamic Gating): 不仅取决于输入内容，还取决于系统当前的膜电位

与传统MoE的区别:
- 传统MoE: 静态或浅层动态路由，仅基于输入内容
- 生物MoE: 基于输入 + 历史累积状态 + 情绪状态的三维路由
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
import math


@dataclass
class BioMoEConfig:
    """Bio-Gated MoE Configuration"""
    d_model: int = 512              # 模型维度
    num_experts: int = 8         # 专家数量
    top_k: int = 2              # 激活的专家数量
    gating_type: str = "bio"       # "bio", "standard", "noise"

    # 膜电位参数
    membrane_decay: float = 0.9     # 膜电位衰减率 (类似遗忘) - 更强遗忘
    membrane_update: float = 0.3   # 膜电位更新率 - 更大更新
    initial_potential: float = 0.5  # 初始膜电位 - 初始值

    # 情绪状态参数
    num_emotion_states: int = 4       # 情绪状态维度
    emotion_decay: float = 0.85    # 情绪状态衰减 - 更弱衰减
    emotion_update: float = 0.3    # 情绪更新系数 - 更大

    # 门控参数
    temperature: float = 1.0       # 门控温度
    dropout: float = 0.0           # 专家 dropout

    # 自动反馈参数
    auto_feedback: bool = True           # 启用自动反馈
    feedback_confidence_threshold: float = 0.7  # 置信度阈值


class MembranePotential(nn.Module):
    """
    膜电位模块 - 模拟神经元的累积状态

    生物原理:
    - 神经元通过突触传递信号，逐渐累积形成膜电位
    - 膜电位会随时间衰减(遗忘)
    - 膜电位影响后续信号的门控(易化/抑制)

    实现:
    - 维护每个专家的累积权重
    - 基于历史使用模式和成功/失败反馈更新
    - 提供稳态正则化(避免过度使用单个专家)
    """

    def __init__(self, num_experts: int, d_model: int, config: BioMoEConfig):
        super().__init__()

        self.num_experts = num_experts
        self.d_model = d_model
        self.config = config

        # 专家使用权重 (累积的使用频率)
        # 形状: [num_experts]
        self.expert_weights = nn.Parameter(
            torch.ones(num_experts) * config.initial_potential
        )

        # 专家成功权重 (基于成功使用经验)
        # 形状: [num_experts]
        self.success_weights = nn.Parameter(
            torch.zeros(num_experts)
        )

        # 专家间的抑制/易化系数
        # 正值 = 易化(更容易激活), 负值 = 抑制(更难激活)
        # 形状: [num_experts, num_experts]
        self.inter_expert_modulation = nn.Parameter(
            torch.randn(num_experts, num_experts) * 0.01
        )

        # 门控 MLP 用于从状态生成调制系数
        # 使用 d_model 作为输入，确保兼容
        self.state_to_modulation = nn.Linear(d_model, num_experts, bias=False)
        # 初始化为小值
        torch.nn.init.normal_(self.state_to_modulation.weight, std=0.01)
        self.state_to_modulation.weight.data *= 0.01

    def get_expert_potential(self, input_states: torch.Tensor) -> torch.Tensor:
        """
        获取每个专家的基础电位，考虑长期累积效应

        Args:
            input_states: 输入状态 [batch, d_model]

        Returns:
            expert_potential: 每个专家的基础电位 [batch, num_experts]
        """
        batch_size = input_states.size(0)

        # 确保输入形状正确 [batch, d_model]
        if input_states.dim() == 3:
            input_states = input_states.mean(dim=1)

        # 基础电位 = 使用频率的倒数 (少用的专家更容易被选中)
        usage_penalty = torch.sigmoid(self.expert_weights)  # [num_experts]
        base_potential = 1.0 - usage_penalty  # [num_experts]

        # 成功加成
        success_bonus = torch.tanh(self.success_weights) * 0.5

        # 专家间调制
        modulation = torch.matmul(
            usage_penalty.unsqueeze(0),
            self.inter_expert_modulation
        )  # [1, num_experts]

        # 最终电位 - 扩展到 batch 维度
        potential = base_potential.unsqueeze(0) + success_bonus.unsqueeze(0)  # [1, num_experts]
        potential = potential + modulation  # [1, num_experts]

        # 扩展到 batch 维度 [batch, num_experts]
        potential = potential.expand(batch_size, -1)

        return potential  # [batch, num_experts]

    def update_after_selection(
        self,
        selected_experts: torch.Tensor,
        success: Optional[torch.Tensor] = None,
        batch_size: Optional[int] = None,
        output: Optional[torch.Tensor] = None,
        target: Optional[torch.Tensor] = None
    ):
        """
        基于使用结果更新膜电位 (简化版)
        """
        # 展平为 1D
        if selected_experts.dim() > 1:
            experts_flat = selected_experts.view(-1)
        else:
            experts_flat = selected_experts

        batch_size = experts_flat.size(0)

        with torch.no_grad():
            for expert_idx in range(self.num_experts):
                usage_count = (experts_flat == expert_idx).sum().item()
                update = usage_count / batch_size * self.config.membrane_update

                current = self.expert_weights.data[expert_idx]
                self.expert_weights.data[expert_idx] = (
                    current * self.config.membrane_decay + update
                )

    def get_exploration_bonus(self) -> torch.Tensor:
        """
        获取探索奖励向量，鼓励使用不熟悉的专家

        Returns:
            exploration_bonus: [num_experts]
        """
        # _entropy 最高(最不熟悉)的专家获得最高奖励
        weights = torch.sigmoid(self.expert_weights)
        entropy = -(weights * torch.log(weights + 1e-8) +
                   (1 - weights) * torch.log(1 - weights + 1e-8))
        return entropy / entropy.sum()


class EmotionalState(nn.Module):
    """
    情绪状态模块 - 模拟系统的"心理状态"

    生物原理:
    - 人类的决策受情绪状态影响(急躁时更容易冒险)
    - 情绪状态会随时间变化
    - 情绪状态可以影响注意力分配

    情绪维度:
    - 唤醒度(Arousal): 系统激活程度
    - 效价(Valence): 正面/负面
    - 支配度(Dominance): 控制感
    - 注意力(Persistence): 专注程度
    """

    def __init__(self, config: BioMoEConfig):
        super().__init__()

        self.config = config
        self.num_emotion_states = config.num_emotion_states

        # 情绪状态向量 [4] = [Arousal, Valence, Dominance, Persistence]
        # 范围: [-1, 1]
        self.state = nn.Parameter(
            torch.zeros(config.num_emotion_states)
        )

        # 情绪到门控偏置的映射
        # 4维情绪 -> 专家选择偏置
        self.emotion_to_bias = nn.Linear(
            config.num_emotion_states,
            config.num_experts,
            bias=False
        )

    def get_state(self) -> torch.Tensor:
        """获��当前情绪状态"""
        return torch.tanh(self.state)

    def update(
        self,
        context: torch.Tensor,
        reward: Optional[torch.Tensor] = None,
        delta_time: float = 1.0,
        output: Optional[torch.Tensor] = None,
        target: Optional[torch.Tensor] = None
    ):
        """
        自动更新情绪状态 (内置反馈机制)

        Args:
            context: 上下文嵌入 [d_model]
            reward: 奖励信号 (成功=1, 失败=-1)，如果为None则自动计算
            delta_time: 时间步长
            output: 模型输出的logits，用于自动计算置信度
            target: 目标token，用于计算准确率
        """
        # 自动计算reward（如果未提供）
        if reward is None:
            if output is not None and target is not None:
                # 计算预测准确率
                pred = output.argmax(dim=-1)
                correct = (pred == target).float()
                reward = correct.mean() * 2 - 1  # 映射到 [-1, 1]
            else:
                # 无信息时保持中性
                reward = 0.0

        # 更新唤醒度 (兴奋度)
        arousal_update = abs(reward) * self.config.emotion_update
        self.state.data[0] = self.state.data[0] + arousal_update * delta_time

        # 更新效价 (正/负)
        self.state.data[1] = self.state.data[1] + reward * self.config.emotion_update * delta_time

        # 更新支配度 (控制感) - 基于自信程度
        if output is not None:
            confidence = F.softmax(output, dim=-1).max(dim=-1)[0].mean()
            dominance_update = (confidence - 0.5) * 0.1 * delta_time
            self.state.data[2] = self.state.data[2] + dominance_update

        # 自然衰减
        self.state.data *= self.config.emotion_decay

    def get_bias(self) -> torch.Tensor:
        """
        获取情绪偏置向量

        Returns:
            bias: [num_experts]
        """
        state = self.get_state()  # [4]
        return self.emotion_to_bias(state)

    def get_arousal_modulation(self) -> float:
        """
        获取唤醒度调制系数

        高唤醒度 -> 更高的探索/更低的 exploit
        低唤醒度 -> 更高的 exploit/更低的探索

        Returns:
            modulation: float in [0, 1]
        """
        arousal = torch.sigmoid(self.state[0])
        return arousal.item()


class BioGating(nn.Module):
    """
    生物门控机制

    结合三种信号进行路由决策:
    1. 输入内容信号 (Content-based)
    2. 膜电位信号 (History-based)
    3. 情绪状态信号 (Emotion-based)

    公式:
    G(x, m, e) = softmax(Content(x) + α·Membrane(m) + β·Emotion(e))

    其中:
    - Content(x): 标准MoE门控
    - Membrane(m): 膜电位调节
    - Emotion(e): 情绪偏置
    """

    def __init__(
        self,
        d_model: int,
        num_experts: int,
        config: BioMoEConfig
    ):
        super().__init__()

        self.d_model = d_model
        self.num_experts = num_experts
        self.config = config

        # 标准门控网络
        self.gate = nn.Sequential(
            nn.Linear(d_model, num_experts),
            nn.Tanh(),
            nn.Linear(num_experts, num_experts)
        )

        # 膜电位模块
        self.membrane = MembranePotential(num_experts, d_model, config)

        # 情绪状态模块
        self.emotion = EmotionalState(config)

        # 可学习的门控权重
        self.content_weight = nn.Parameter(torch.tensor(1.0))
        self.membrane_weight = nn.Parameter(torch.tensor(0.3))
        self.emotion_weight = nn.Parameter(torch.tensor(0.2))

    def forward(
        self,
        x: torch.Tensor,
        use_membrane: bool = True,
        use_emotion: bool = True
    ) -> Tuple[torch.Tensor, Dict]:
        """
        计算门控权重

        Args:
            x: 输入 [batch, seq_len, d_model] 或 [batch, d_model]
            use_membrane: 是否使用膜电位
            use_emotion: 是否使用情绪状态

        Returns:
            gating_weights: 门控权重 [batch, num_experts]
            info: 调试信息
        """
        # 适配不同输入形状
        if x.dim() == 3:
            x_flat = x.mean(dim=1)  # [batch, d_model]
        else:
            x_flat = x

        batch_size = x_flat.size(0)

        # 1. 内容门控
        content_gate = self.gate(x_flat)  # [batch, num_experts]

        gating_weights = self.content_weight * content_gate

        info = {
            "content": content_gate.mean(dim=0).detach().cpu(),
            "exploration_bonus": self.membrane.get_exploration_bonus().detach().cpu()
        }

        # 2. 膜电位门控
        if use_membrane:
            membrane_potential = self.membrane.get_expert_potential(x_flat)  # [batch, num_experts]
            gating_weights = gating_weights + self.membrane_weight * membrane_potential
            info["membrane"] = membrane_potential.mean(dim=0).detach().cpu()

        # 3. 情绪状态门控
        if use_emotion:
            emotion_bias = self.emotion.get_bias()  # [num_experts]
            gating_weights = gating_weights + self.emotion_weight * emotion_bias.unsqueeze(0)
            info["emotion"] = emotion_bias.detach().cpu()
            info["arousal"] = self.emotion.get_arousal_modulation()

        # 软最大化
        if self.config.temperature != 1.0:
            gating_weights = gating_weights / self.config.temperature

        gating_weights = F.softmax(gating_weights, dim=-1)

        info["final"] = gating_weights.mean(dim=0).detach().cpu()

        return gating_weights, info

    def reset_emotion(self):
        """重置情绪状态"""
        nn.init.zeros_(self.emotion.state)


class BioExpert(nn.Module):
    """
    生物专家模块

    每个专家都有自己的"专长"和"偏好"
    """

    def __init__(self, d_model: int, expert_id: int):
        super().__init__()

        self.d_model = d_model
        self.expert_id = expert_id

        # 专长建模
        self.specialization = nn.Parameter(
            torch.randn(d_model) * 0.01
        )

        # 专家内部网络
        self.net = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d_model * 2, d_model),
            nn.LayerNorm(d_model)
        )

        # 残差连接
        self.residual = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: 输入 [batch, d_model]

        Returns:
            输出 [batch, d_model]
        """
        return self.net(x) + self.residual(x)

    def get_specialization(self) -> torch.Tensor:
        """获取专长向量"""
        return self.specialization


class BioMoE(nn.Module):
    """
    生物门控混合专家模型 (MoE 2.0)

    结合:
    - 多个专用专家
    - 生物门控机制(内容 + 膜电位 + 情绪)
    - 辅助损耗(负载均衡)
    """

    def __init__(self, config: BioMoEConfig):
        super().__init__()

        self.config = config
        self.d_model = config.d_model
        self.num_experts = config.num_experts
        self.top_k = config.top_k

        # 专家列表
        self.experts = nn.ModuleList([
            BioExpert(config.d_model, i)
            for i in range(config.num_experts)
        ])

        # 生物门控
        self.gating = BioGating(
            config.d_model,
            config.num_experts,
            config
        )

        # 专家使用的统计
        self.register_buffer("expert_usage", torch.zeros(config.num_experts))

        # 负载均衡辅助
        self.load_factor = nn.Parameter(torch.tensor(0.01))

    def forward(
        self,
        x: torch.Tensor,
        use_membrane: bool = True,
        use_emotion: bool = True,
        return_gating_info: bool = False,
        enable_auto_feedback: bool = True,
        target: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Dict]:
        """
        前向传播 (内置自动反馈机制)

        Args:
            x: 输入 [batch, seq_len, d_model] 或 [batch, d_model]
            use_membrane: 是否使用膜电位路由
            use_emotion: 是否使用情绪状态路由
            return_gating_info: 是否返回门控信息
            enable_auto_feedback: 启用自动反馈
            target: 目标token，用于自动计算成功

        Returns:
            output: 输出
            info: 调试信息
        """
        original_shape = x.shape
        is_3d = x.dim() == 3

        if is_3d:
            batch_size, seq_len, _ = x.shape
            x_flat = x.view(-1, self.d_model)
            gating_input = x_flat
        else:
            x_flat = x
            batch_size = x.size(0)
            gating_input = x_flat

        # 获取门控权重
        gating_weights, info = self.gating(
            gating_input,
            use_membrane=use_membrane,
            use_emotion=use_emotion
        )

        gating_dist = gating_weights  # 保存用于反馈

        # 选择 top-k 专家
        top_k_weights, top_k_indices = torch.topk(
            gating_weights,
            self.top_k,
            dim=-1
        )

        # 归一化
        top_k_weights = top_k_weights / top_k_weights.sum(dim=-1, keepdim=True)

        # === 自动反馈机制 ===
        if enable_auto_feedback and self.config.auto_feedback:
            # 自动更新膜电位 (基于选择频率)
            self.gating.membrane.update_after_selection(
                selected_experts=top_k_indices,
                output=gating_dist,
                target=target
            )

            # 自动更新情绪 (基于置信度)
            max_conf = gating_dist.max(dim=-1)[0].mean()
            reward_signal = (max_conf - 0.5) * 2  # [-1, 1]
            self.gating.emotion.update(
                context=gating_input.mean(dim=0),
                reward=reward_signal
            )

        # 更新使用统计
        for expert_id in range(self.num_experts):
            usage = (top_k_indices == expert_id).sum().item()
            self.expert_usage[expert_id] += usage

        # 专家输出
        expert_outputs = torch.stack([
            expert(x_flat) for expert in self.experts
        ], dim=1)

        # 加权合并
        output = torch.zeros_like(x_flat)

        for i in range(self.top_k):
            expert_idx_i = top_k_indices[:, i]
            weight_i = top_k_weights[:, i]

            for b in range(batch_size):
                e_id = expert_idx_i[b]
                w = weight_i[b]
                output[b] += expert_outputs[b, e_id] * w

        # 恢复形状
        if is_3d:
            output = output.view(batch_size, seq_len, self.d_model)
        else:
            output = output.view(batch_size, self.d_model)

        # 辅助损耗 (负载均衡)
        aux_loss = self._compute_load_balancing_loss(gating_weights)

        info["aux_loss"] = aux_loss.item()

        if return_gating_info:
            return output, info
        return output, {"output": output}

    def _compute_load_balancing_loss(
        self,
        gating_weights: torch.Tensor
    ) -> torch.Tensor:
        """
        计算负载均衡辅助损耗

        鼓励均匀使用所有专家
        """
        # 批次平均门控
        avg_gating = gating_weights.mean(dim=0)  # [num_experts]

        # 熵损耗 (鼓励均匀分布)
        entropy_loss = -(
            avg_gating * torch.log(avg_gating + 1e-8)
        ).sum()

        return self.load_factor * entropy_loss

    def reset_state(self):
        """重置网络状态"""
        # 重置情绪状态
        self.gating.reset_emotion()

    def get_expert_specializations(self) -> List[torch.Tensor]:
        """获取所有专家的专长向量"""
        return [expert.get_specialization() for expert in self.experts]

    def get_usage_stats(self) -> torch.Tensor:
        """获取专家使用统计"""
        return self.expert_usage

    def reset_usage_stats(self):
        """重置使用统计"""
        self.expert_usage.zero_()


class AdaptiveBioMoE(nn.Module):
    """
    适配性生物MoE - 根据任务动态调整门控权重

    在推理时根据任务特征动态调整:
    - 膜电位权重
    - 情绪状态影响
    - 专家选择策略
    """

    def __init__(self, config: BioMoEConfig):
        super().__init__()

        self.base_moe = BioMoE(config)
        self.config = config

        # 任务适配网络
        self.task_adapter = nn.Sequential(
            nn.Linear(config.d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 3)  # [membrane_weight, emotion_weight, temperature]
        )

    def forward(
        self,
        x: torch.Tensor,
        task_context: Optional[torch.Tensor] = None,
        return_gating_info: bool = True
    ) -> Tuple[torch.Tensor, Dict]:
        """
        前向传播，带任务适应

        Args:
            x: 输入 [batch, d_model]
            task_context: 任务上下文 [batch, d_model]

        Returns:
            output: 输出 [batch, d_model]
            info: 门控信息
        """
        # 默认参数
        use_membrane = True
        use_emotion = True

        if task_context is not None:
            # 从任务上下文预测参数
            adapter_output = self.task_adapter(task_context.mean(dim=1))

            # 动态调整
            membrane_weight = torch.sigmoid(adapter_output[:, 0])
            emotion_weight = torch.sigmoid(adapter_output[:, 1])
            temperature = 0.5 + adapter_output[:, 2] * 1.5

            # 临时调整门控权重
            original_membrane = self.base_moe.gating.membrane_weight.data.clone()
            original_emotion = self.base_moe.gating.emotion_weight.data.clone()
            original_temp = self.base_moe.gating.config.temperature

            # 根据批次应用
            self.base_moe.gating.membrane_weight.data = (
                original_membrane * membrane_weight.mean()
            )
            self.base_moe.gating.emotion_weight.data = (
                original_emotion * emotion_weight.mean()
            )
            self.base_moe.gating.config.temperature = temperature.mean().item()

            use_membrane = membrane_weight.mean() > 0.3
            use_emotion = emotion_weight.mean() > 0.3

            output, info = self.base_moe(
                x,
                use_membrane=use_membrane,
                use_emotion=use_emotion,
                return_gating_info=return_gating_info
            )

            # 恢复
            self.base_moe.gating.membrane_weight.data = original_membrane
            self.base_moe.gating.emotion_weight.data = original_emotion
            self.base_moe.gating.config.temperature = original_temp

        else:
            output, info = self.base_moe(
                x,
                use_membrane=use_membrane,
                use_emotion=use_emotion,
                return_gating_info=return_gating_info
            )

        return output, info


def create_bio_moe(config: dict) -> BioMoE:
    """工厂函数：从配置创建生物MoE"""
    moe_config = BioMoEConfig(
        d_model=config.get("d_model", 512),
        num_experts=config.get("num_experts", 8),
        top_k=config.get("top_k", 2),
        gating_type=config.get("gating_type", "bio"),
        membrane_decay=config.get("membrane_decay", 0.95),
        membrane_update=config.get("membrane_update", 0.1),
        emotion_decay=config.get("emotion_decay", 0.9),
        temperature=config.get("temperature", 1.0)
    )

    return BioMoE(moe_config)


# ==================== 示例和测试 ====================

def demo():
    """演示生物MoE"""
    print("="*60)
    print("Bio-Gated MoE 2.0 演示")
    print("="*60)

    # 配置
    config = BioMoEConfig(
        d_model=128,
        num_experts=8,
        top_k=2,
        temperature=1.0
    )

    # 模型
    model = BioMoE(config)
    print(f"\n模型参数量: {sum(p.numel() for p in model.parameters()):,}")

    # 模拟输入
    batch_size = 4
    x = torch.randn(batch_size, 32, config.d_model)

    # 前向传播
    print("\n--- 第一次前向传播 ---")
    output, info = model(x, return_gating_info=True)
    print(f"输出形状: {output.shape}")
    print(f"门控信息: {list(info.keys())}")
    print(f"内容门控: {info['content'][:3]}")
    print(f"探索奖励: {info['exploration_bonus'][:3]}")

    # 模拟多次调用，观察膜电位变化
    print("\n--- 模拟多次调用，观察膜电位变化 ---")
    for i in range(5):
        x = torch.randn(batch_size, config.d_model)
        gating, _ = model.gating(x)
        top_experts = torch.topk(gating, config.top_k, dim=-1)[1]
        print(f"第{i+1}次: 选中专家 {top_experts[0].tolist()}")

    # 情绪状态
    print("\n--- 情绪状态 ---")
    emotion = model.gating.emotion
    state = emotion.get_state()
    print(f"当前情绪状态: {state}")
    print(f"唤醒度调制: {emotion.get_arousal_modulation():.3f}")

    # 专家使用统计
    print("\n--- 专家使用统计 ---")
    usage = model.get_usage_stats()
    print(f"使用统计: {usage}")

    # 专家专长
    print("\n--- 专家专长 ---")
    specs = model.get_expert_specializations()
    print(f"专长向量形状: {specs[0].shape}")

    print("\n" + "="*60)
    print("演示完成")
    print("="*60)


if __name__ == "__main__":
    demo()