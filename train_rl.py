#!/usr/bin/env python3
"""
RL Agent Training Script

Trains the reflective RL agent on simulated penetration testing environments.
"""

import sys
import os
sys.path.insert(0, "D:/password_guesser")

import logging
import time
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("=" * 60)
print("RL Agent Training")
print("=" * 60)

from rl_agent.environment import PenTestEnvironment
from rl_agent.reflective_agent import ReflectiveRLAgent, ReplayBuffer
from rl_agent.action import ActionSpace
from rl_agent.training import RLTrainer

# Create environment
print("\n[1] Initializing environment...")
env = PenTestEnvironment()

# Create agent
print("[2] Creating reflective RL agent...")
agent = ReflectiveRLAgent(
    state_dim=256,
    action_dim=900,
    learning_rate=0.0003,
    gamma=0.99,
    reflection_frequency=5,
)

print(f"    State dim: 256")
print(f"    Action dim: 900")
print(f"    Learning rate: 0.0003")
print(f"    Reflection enabled: True")

# Create trainer
print("\n[3] Setting up trainer...")
trainer = RLTrainer(
    agent=agent,
    env=env,
    max_steps_per_episode=50,
    train_batch_size=32,
    train_epochs=4,
    eval_frequency=10,
    checkpoint_frequency=50,
    checkpoint_dir="D:/password_guesser/checkpoints/rl",
)

# Run training
N_EPISODES = 50
print(f"\n[4] Starting training for {N_EPISODES} episodes...")
print("-" * 50)

start_time = time.time()

for ep in range(N_EPISODES):
    metrics = trainer.train_episode()

    if (ep + 1) % 5 == 0:
        avg_reward = np.mean([m["episode_reward"] for m in trainer.metrics[-5:]])
        avg_compromised = np.mean([m["compromised_hosts"] for m in trainer.metrics[-5:]])
        avg_loss = np.mean([m["train_loss"] for m in trainer.metrics[-5:]])

        print(f"  Episode {ep+1:3d}/{N_EPISODES} | "
              f"Reward: {metrics['episode_reward']:7.2f} | "
              f"Avg(5): {avg_reward:7.2f} | "
              f"Compromised: {metrics['compromised_hosts']} | "
              f"Creds: {metrics['credentials_found']} | "
              f"Loss: {metrics['train_loss']:.4f}")

    # Periodic evaluation
    if (ep + 1) % 20 == 0:
        eval_metrics = trainer.evaluate(n_episodes=3, deterministic=True)
        print(f"\n  === Evaluation at Episode {ep+1} ===")
        print(f"      Avg Reward: {eval_metrics['avg_reward']:.2f}")
        print(f"      Max Reward: {eval_metrics['max_reward']:.2f}")
        print(f"      Avg Steps: {eval_metrics['avg_steps']:.1f}")
        print(f"      Compromise Rate: {eval_metrics['compromise_rate']:.1%}")

elapsed = time.time() - start_time

# Final evaluation
print("\n" + "=" * 60)
print("Training Complete!")
print("=" * 60)

final_eval = trainer.evaluate(n_episodes=10, deterministic=True)
print(f"\n  Final Evaluation (10 episodes):")
print(f"    Avg Reward: {final_eval['avg_reward']:.2f}")
print(f"    Std Reward: {final_eval['std_reward']:.2f}")
print(f"    Max Reward: {final_eval['max_reward']:.2f}")
print(f"    Avg Steps: {final_eval['avg_steps']:.1f}")
print(f"    Avg Compromised: {final_eval['avg_compromised']:.1f}")
print(f"    Compromise Rate: {final_eval['compromise_rate']:.1%}")

print(f"\n  Training Summary:")
print(f"    Episodes: {N_EPISODES}")
print(f"    Total Time: {elapsed:.1f}s")
print(f"    Best Reward: {trainer.best_reward:.2f}")
print(f"    Total Reflections: {len(agent.reflections)}")

# Save final model
os.makedirs("D:/password_guesser/checkpoints/rl", exist_ok=True)
trainer._save_checkpoint("final_model.pt")
trainer.save_metrics("D:/password_guesser/checkpoints/rl/training_metrics.json")

# Show reward progression
if len(trainer.metrics) >= 10:
    first_10 = np.mean([m["episode_reward"] for m in trainer.metrics[:10]])
    last_10 = np.mean([m["episode_reward"] for m in trainer.metrics[-10:]])
    print(f"\n  Reward Progression:")
    print(f"    First 10 episodes avg: {first_10:.2f}")
    print(f"    Last 10 episodes avg: {last_10:.2f}")
    print(f"    Improvement: {last_10 - first_10:+.2f}")

print("\n" + "=" * 60)
