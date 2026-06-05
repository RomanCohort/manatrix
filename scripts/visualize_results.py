"""
Manatrix 实验可视化脚本
生成论文所需的图表
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import matplotlib

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


def load_results(json_path: str) -> dict:
    """加载实验结果"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def plot_bio_moe_results(results: dict, output_dir: Path):
    """绘制 Bio-MoE 消融实验结果"""
    exp1 = results.get('experiment_1', {})
    analysis = exp1.get('analysis', {})

    if not analysis:
        print("No experiment 1 analysis data")
        return

    # Figure 1: 模型变体对比柱状图
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    models = ['A1', 'A2', 'A3', 'A4']
    model_labels = ['Standard\nMoE', 'Bio-MoE\n(Emotion)', 'Bio-MoE\n(Membrane)', 'Bio-MoE\n(Full)']
    colors = ['#4472C4', '#ED7D31', '#A5A5A5', '#70AD47']

    metrics = [
        ('expert_entropy', 'Expert Selection Entropy', axes[0, 0]),
        ('load_balance', 'Load Balance Score', axes[0, 1]),
        ('response_quality', 'Response Quality', axes[1, 0]),
        ('convergence_steps', 'Convergence Steps', axes[1, 1]),
    ]

    for metric_key, metric_name, ax in metrics:
        if metric_key not in analysis:
            continue

        means = [analysis[metric_key]['means'][m] for m in models]
        stds = [analysis[metric_key]['stds'][m] for m in models]

        bars = ax.bar(model_labels, means, yerr=stds, color=colors, capsize=5, alpha=0.8)
        ax.set_ylabel(metric_name)
        ax.set_title(f'{metric_name} Comparison')

        # 添加数值标签
        for bar, mean, std in zip(bars, means, stds):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.05,
                   f'{mean:.2f}', ha='center', va='bottom', fontsize=9)

        ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Bio-Gated MoE Ablation Study Results', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_dir / 'fig1_bio_moe_ablation.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'fig1_bio_moe_ablation.png'}")

    # Figure 2: 熵和负载均衡的关系
    fig, ax = plt.subplots(figsize=(8, 6))

    for i, model in enumerate(models):
        entropy_mean = analysis['expert_entropy']['means'][model]
        balance_mean = analysis['load_balance']['means'][model]
        ax.scatter(entropy_mean, balance_mean, s=200, c=colors[i], label=model_labels[i], alpha=0.8)

    ax.set_xlabel('Expert Selection Entropy')
    ax.set_ylabel('Load Balance Score')
    ax.set_title('Entropy vs Load Balance Trade-off')
    ax.legend()
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'fig2_entropy_balance.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'fig2_entropy_balance.png'}")


def plot_password_results(results: dict, output_dir: Path):
    """绘制密码猜测实验结果"""
    exp4 = results.get('experiment_4', {})

    if not exp4:
        print("No experiment 4 data")
        return

    # Figure 3: 密码命中率对比
    fig, ax = plt.subplots(figsize=(10, 6))

    baseline = exp4.get('baseline_comparison', {})
    our_rates = exp4.get('hit_rates', {})

    methods = ['MAMBA+DE\n(Ours)', 'PassGPT', 'LSTM', 'PCFG', 'Markov\nChain']
    k_values = ['@100', '@1000', '@10000']

    x = np.arange(len(methods))
    width = 0.25

    for i, k in enumerate(k_values):
        rates = []
        # Our method
        rates.append(our_rates.get(k, 0) * 100)

        # Baseline methods
        for method in ['passgpt', 'lstm', 'pcfg', 'markov_chain']:
            rates.append(baseline.get(method, {}).get(k, 0) * 100)

        bars = ax.bar(x + i * width, rates, width, label=f'Hit Rate {k}')

    ax.set_ylabel('Hit Rate (%)')
    ax.set_title('Password Guessing Hit Rate Comparison')
    ax.set_xticks(x + width)
    ax.set_xticklabels(methods)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'fig3_password_hitrate.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_dir / 'fig3_password_hitrate.png'}")

    # Figure 4: 密码强度分布饼图
    fig, ax = plt.subplots(figsize=(8, 8))

    strength = exp4.get('strength_distribution', {})
    if strength:
        labels = list(strength.keys())
        sizes = list(strength.values())
        colors_pie = ['#FF6B6B', '#FFA500', '#FFD93D', '#6BCB77', '#4D96FF']

        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                           colors=colors_pie, startangle=90)

        ax.set_title('Generated Password Strength Distribution')

        plt.tight_layout()
        plt.savefig(output_dir / 'fig4_password_strength.png', dpi=300, bbox_inches='tight')
        plt.close()
        print(f"Saved: {output_dir / 'fig4_password_strength.png'}")


def generate_latex_tables(results: dict, output_dir: Path):
    """生成 LaTeX 表格"""

    exp1 = results.get('experiment_1', {})
    analysis = exp1.get('analysis', {})

    if not analysis:
        return

    # Table 1: Bio-MoE 消融实验结果表
    latex_table = r"""
\begin{table}[htbp]
\centering
\caption{Bio-Gated MoE Ablation Study Results}
\label{tab:bio_moe_ablation}
\begin{tabular}{lcccc}
\toprule
\textbf{Metric} & \textbf{A1 (Base)} & \textbf{A2 (Emotion)} & \textbf{A3 (Membrane)} & \textbf{A4 (Full)} \\
\midrule
"""

    metrics = [
        ('expert_entropy', 'Expert Entropy'),
        ('load_balance', 'Load Balance'),
        ('response_quality', 'Response Quality'),
        ('convergence_steps', 'Convergence Steps'),
    ]

    for metric_key, metric_name in metrics:
        if metric_key not in analysis:
            continue
        means = analysis[metric_key]['means']
        stds = analysis[metric_key]['stds']

        row = f"{metric_name}"
        for m in ['A1', 'A2', 'A3', 'A4']:
            row += f" & {means[m]:.3f}$\\pm${stds[m]:.3f}"
        row += r" \\" + "\n"
        latex_table += row

    latex_table += r"""
\bottomrule
\end{tabular}
\end{table}
"""

    with open(output_dir / 'table1_bio_moe.tex', 'w', encoding='utf-8') as f:
        f.write(latex_table)
    print(f"Saved: {output_dir / 'table1_bio_moe.tex'}")


def main():
    """主函数"""
    import glob

    # 找到最新的实验结果
    result_files = sorted(glob.glob('results/experiment_results_*.json'), reverse=True)

    if not result_files:
        print("No experiment results found. Run run_experiments.py first.")
        return

    latest_result = result_files[0]
    print(f"Loading results from: {latest_result}")

    results = load_results(latest_result)
    output_dir = Path('results')

    # 生成图表
    plot_bio_moe_results(results, output_dir)
    plot_password_results(results, output_dir)

    # 生成 LaTeX 表格
    generate_latex_tables(results, output_dir)

    print("\n" + "="*50)
    print("Visualization complete!")
    print(f"Output directory: {output_dir}")
    print("="*50)


if __name__ == "__main__":
    main()
