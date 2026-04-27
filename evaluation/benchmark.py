"""
Pentest System Evaluation Benchmark

Evaluates the effectiveness of the penetration testing system using:
- Predefined scenarios based on real-world environments
- Multiple metrics (success rate, efficiency, false positives)
- Comparison with baseline strategies
- Progress tracking over time

Usage:
    benchmark = PentestBenchmark()
    results = benchmark.run_full_evaluation(agent, num_episodes=10)
    benchmark.print_report(results)
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ScenarioType(Enum):
    """Types of benchmark scenarios."""
    METASPLOITABLE = "metasploitable"
    CTF_EASY = "ctf_easy"
    CTF_MEDIUM = "ctf_medium"
    ADVERSARIAL = "adversarial"
    REALISTIC = "realistic"


@dataclass
class BenchmarkScenario:
    """A benchmark scenario for evaluation."""
    scenario_id: str
    name: str
    description: str
    scenario_type: ScenarioType
    difficulty: float  # 0.0 - 1.0

    # Target configuration
    hosts: List[dict]
    flags: List[dict]  # Flags to capture: {id, description, points}
    expected_actions: int  # Expected number of actions for optimal solution
    optimal_reward: float  # Expected reward for optimal play

    # Constraints
    max_steps: int = 100
    time_limit: float = 600.0  # seconds
    max_attempts: int = 3

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "scenario_type": self.scenario_type.value,
            "difficulty": self.difficulty,
            "flags": self.flags,
            "expected_actions": self.expected_actions,
            "optimal_reward": self.optimal_reward,
            "max_steps": self.max_steps,
            "time_limit": self.time_limit,
        }


@dataclass
class EpisodeResult:
    """Result of a single evaluation episode."""
    scenario_id: str
    episode: int

    # Success metrics
    success: bool
    flags_captured: List[str]
    flag_count: int
    total_flags: int

    # Efficiency metrics
    steps_taken: int
    actions_per_flag: float
    duration: float
    time_per_step: float

    # Quality metrics
    total_reward: float
    efficiency_score: float  # optimal_steps / actual_steps
    flags_per_minute: float

    # Error metrics
    failed_actions: int
    false_positives: int  # Actions that didn't contribute to success

    # State at completion
    final_state: dict
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "episode": self.episode,
            "success": self.success,
            "flags_captured": self.flags_captured,
            "flag_count": self.flag_count,
            "total_flags": self.total_flags,
            "steps_taken": self.steps_taken,
            "actions_per_flag": self.actions_per_flag,
            "duration": self.duration,
            "time_per_step": self.time_per_step,
            "total_reward": self.total_reward,
            "efficiency_score": self.efficiency_score,
            "flags_per_minute": self.flags_per_minute,
            "failed_actions": self.failed_actions,
            "false_positives": self.false_positives,
            "timestamp": self.timestamp,
        }


@dataclass
class ScenarioResult:
    """Aggregated results for a scenario across multiple episodes."""
    scenario_id: str
    scenario_name: str

    # Aggregate statistics
    episodes: int
    success_rate: float
    mean_reward: float
    std_reward: float
    mean_steps: float
    mean_duration: float
    mean_efficiency: float

    # Performance distribution
    min_reward: float
    max_reward: float
    median_steps: float

    # Detailed episode results
    episode_results: List[EpisodeResult]

    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "episodes": self.episodes,
            "success_rate": self.success_rate,
            "mean_reward": self.mean_reward,
            "std_reward": self.std_reward,
            "mean_steps": self.mean_steps,
            "mean_duration": self.mean_duration,
            "mean_efficiency": self.mean_efficiency,
            "min_reward": self.min_reward,
            "max_reward": self.max_reward,
            "median_steps": self.median_steps,
            "timestamp": self.timestamp,
        }


class PentestBenchmark:
    """
    Benchmark framework for evaluating pentest system effectiveness.

    Provides:
    - Predefined benchmark scenarios
    - Episode evaluation and result tracking
    - Scenario-level aggregation
    - Comparison with baselines
    - Progress tracking over time
    """

    # Predefined benchmark scenarios
    DEFAULT_SCENARIOS = [
        # === Metasploitable-style scenarios ===
        BenchmarkScenario(
            scenario_id="meta_basic",
            name="Metasploitable Basic",
            description="Single vulnerable host with common vulnerabilities",
            scenario_type=ScenarioType.METASPLOITABLE,
            difficulty=0.3,
            hosts=[
                {
                    "ip": "192.168.56.10",
                    "os": "Linux",
                    "ports": {21: "ftp", 22: "ssh", 23: "telnet", 80: "http"},
                    "vulnerabilities": ["CVE-2006-2072"],
                    "credential": {"root": "toor"},
                    "data": ["flag.txt"],
                }
            ],
            flags=[
                {"id": "flag_root_access", "description": "Gain root access", "points": 10}
            ],
            expected_actions=5,
            optimal_reward=10.0,
        ),
        BenchmarkScenario(
            scenario_id="meta_multi",
            name="Metasploitable Multi-Host",
            description="Multiple hosts requiring lateral movement",
            scenario_type=ScenarioType.METASPLOITABLE,
            difficulty=0.5,
            hosts=[
                {
                    "ip": "192.168.56.10",
                    "os": "Linux",
                    "ports": {80: "http"},
                    "vulnerabilities": ["CVE-2006-2072"],
                    "credential": {"user": "user"},
                    "data": [],
                },
                {
                    "ip": "192.168.56.11",
                    "os": "Linux",
                    "ports": {22: "ssh", 3306: "mysql"},
                    "vulnerabilities": [],
                    "credential": {"root": "root"},
                    "data": ["flag.txt"],
                },
            ],
            flags=[
                {"id": "flag_first_host", "description": "Compromise first host", "points": 5},
                {"id": "flag_second_host", "description": "Move to second host", "points": 10},
            ],
            expected_actions=12,
            optimal_reward=15.0,
        ),
        # === CTF-style scenarios ===
        BenchmarkScenario(
            scenario_id="ctf_web_basic",
            name="CTF Web Basic",
            description="Web application with SQL injection",
            scenario_type=ScenarioType.CTF_EASY,
            difficulty=0.4,
            hosts=[
                {
                    "ip": "10.0.0.20",
                    "os": "Linux",
                    "ports": {80: "http", 443: "https"},
                    "vulnerabilities": [],
                    "services": {
                        "http": {"framework": "apache", "version": "2.4"}
                    },
                    "credential": {},
                    "data": ["database.sql"],
                }
            ],
            flags=[
                {"id": "flag_sql_injection", "description": "SQL injection success", "points": 10}
            ],
            expected_actions=8,
            optimal_reward=10.0,
        ),
        BenchmarkScenario(
            scenario_id="ctf_chain",
            name="CTF Attack Chain",
            description="Multi-stage chain: recon -> exploit -> privesc -> exfil",
            scenario_type=ScenarioType.CTF_MEDIUM,
            difficulty=0.6,
            hosts=[
                {
                    "ip": "10.0.0.30",
                    "os": "Linux",
                    "ports": {22: "ssh", 80: "http", 443: "https"},
                    "vulnerabilities": ["CVE-2019-10149"],
                    "credential": {"www-data": "www"},
                    "data": [],
                },
                {
                    "ip": "10.0.0.31",
                    "os": "Windows",
                    "ports": {445: "smb"},
                    "vulnerabilities": [],
                    "credential": {"administrator": "Pass123"},
                    "data": ["flag.txt"],
                },
            ],
            flags=[
                {"id": "flag_shell", "description": "Get initial shell", "points": 5},
                {"id": "flag_privesc", "description": "Privilege escalation", "points": 10},
                {"id": "flag_data", "description": "Data exfiltration", "points": 15},
            ],
            expected_actions=20,
            optimal_reward=30.0,
        ),
        # === Adversarial scenario ===
        BenchmarkScenario(
            scenario_id="adv_defended",
            name="Defended Environment",
            description="Target with active defenses (rate limiting, IDS alerts)",
            scenario_type=ScenarioType.ADVERSARIAL,
            difficulty=0.8,
            hosts=[
                {
                    "ip": "172.16.0.10",
                    "os": "Linux",
                    "ports": {22: "ssh", 80: "http", 443: "https"},
                    "vulnerabilities": ["CVE-2021-44228"],
                    "credential": {"admin": "weakpass"},
                    "data": ["sensitive.db"],
                }
            ],
            flags=[
                {"id": "flag_compromise", "description": "Compromise target", "points": 20},
                {"id": "flag_evade", "description": "Evade detection", "points": 15},
            ],
            expected_actions=25,
            optimal_reward=35.0,
        ),
        # === Realistic scenario ===
        BenchmarkScenario(
            scenario_id="real_corporate",
            name="Corporate Network",
            description="Realistic corporate network with DC, file server, workstation",
            scenario_type=ScenarioType.REALISTIC,
            difficulty=0.7,
            hosts=[
                {
                    "ip": "10.10.0.5",
                    "os": "Windows",
                    "ports": {445: "smb", 3389: "rdp", 389: "ldap"},
                    "vulnerabilities": ["CVE-2017-0144"],
                    "credential": {"Administrator": "Guest123!"},
                    "data": [],
                },
                {
                    "ip": "10.10.0.10",
                    "os": "Linux",
                    "ports": {22: "ssh", 80: "http"},
                    "vulnerabilities": ["CVE-2019-10149"],
                    "credential": {"ubuntu": "ubuntu"},
                    "data": [],
                },
                {
                    "ip": "10.10.0.100",
                    "os": "Windows",
                    "ports": {445: "smb", 139: "netbios"},
                    "vulnerabilities": [],
                    "credential": {"user": "Summer2024!"},
                    "data": ["flag.txt"],
                },
            ],
            flags=[
                {"id": "flag_dc", "description": "Compromise domain controller", "points": 25},
                {"id": "flag_files", "description": "Access file server", "points": 15},
                {"id": "flag_workstation", "description": "Compromise workstation", "points": 10},
            ],
            expected_actions=40,
            optimal_reward=50.0,
        ),
    ]

    def __init__(
        self,
        scenarios: List[BenchmarkScenario] = None,
        results_dir: str = "data/benchmark_results",
    ):
        """
        Initialize benchmark framework.

        Args:
            scenarios: List of scenarios to evaluate (defaults to DEFAULT_SCENARIOS)
            results_dir: Directory to store benchmark results
        """
        self.scenarios = scenarios or self.DEFAULT_SCENARIOS
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

        # Results storage
        self._results: Dict[str, ScenarioResult] = {}
        self._episode_history: List[EpisodeResult] = []

        logger.info(f"Benchmark initialized with {len(self.scenarios)} scenarios")

    def get_scenario(self, scenario_id: str) -> Optional[BenchmarkScenario]:
        """Get a scenario by ID."""
        for s in self.scenarios:
            if s.scenario_id == scenario_id:
                return s
        return None

    def list_scenarios(self) -> List[dict]:
        """List all available scenarios."""
        return [s.to_dict() for s in self.scenarios]

    def run_scenario(
        self,
        agent,  # The RL agent or planner to evaluate
        scenario_id: str,
        env_class,  # Environment class
        num_episodes: int = 5,
        verbose: bool = True,
    ) -> ScenarioResult:
        """
        Run evaluation for a single scenario.

        Args:
            agent: The agent to evaluate
            scenario_id: ID of scenario to run
            env_class: Environment class to instantiate
            num_episodes: Number of evaluation episodes
            verbose: Print progress

        Returns:
            ScenarioResult with aggregated metrics
        """
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        if verbose:
            logger.info(f"Evaluating scenario: {scenario.name} ({scenario.scenario_id})")

        episode_results: List[EpisodeResult] = []

        for episode in range(num_episodes):
            if verbose:
                print(f"  Episode {episode + 1}/{num_episodes}")

            result = self._run_episode(agent, scenario, env_class)
            episode_results.append(result)
            self._episode_history.append(result)

        # Aggregate results
        aggregated = self._aggregate_results(scenario, episode_results)
        self._results[scenario_id] = aggregated

        return aggregated

    def _run_episode(
        self,
        agent,
        scenario: BenchmarkScenario,
        env_class,
    ) -> EpisodeResult:
        """Run a single evaluation episode."""
        start_time = time.time()

        # Create environment with scenario hosts
        env = env_class(hosts=scenario.hosts)
        state = env.reset()

        steps_taken = 0
        total_reward = 0.0
        failed_actions = 0
        false_positives = 0
        flags_captured: List[str] = []
        initial_flags = set()

        for step in range(scenario.max_steps):
            steps_taken += 1

            # Select action (deterministic for fair evaluation)
            action, action_idx = agent.select_action(state, env=env, deterministic=True)

            # Execute
            next_state, reward, done, info = env.step(action)
            total_reward += reward

            # Track failed actions
            if reward < 0:
                failed_actions += 1

            # Track false positives (successful actions that didn't advance goal)
            if reward > 0 and not any(
                f["id"] in flags_captured
                for f in scenario.flags
                if self._check_flag_completion(f["id"], info)
            ):
                false_positives += 1

            state = next_state

            if done:
                break

        duration = time.time() - start_time

        # Calculate metrics
        flag_count = len(flags_captured)
        total_flags = len(scenario.flags)
        success = flag_count == total_flags

        actions_per_flag = steps_taken / max(1, flag_count) if flag_count > 0 else steps_taken
        time_per_step = duration / max(1, steps_taken)
        efficiency_score = scenario.expected_actions / max(1, steps_taken)
        flags_per_minute = flag_count / max(0.1, duration / 60.0)

        return EpisodeResult(
            scenario_id=scenario.scenario_id,
            episode=len(self._episode_history),
            success=success,
            flags_captured=flags_captured,
            flag_count=flag_count,
            total_flags=total_flags,
            steps_taken=steps_taken,
            actions_per_flag=actions_per_flag,
            duration=duration,
            time_per_step=time_per_step,
            total_reward=total_reward,
            efficiency_score=efficiency_score,
            flags_per_minute=flags_per_minute,
            failed_actions=failed_actions,
            false_positives=false_positives,
            final_state=state.to_dict() if hasattr(state, 'to_dict') else {},
        )

    def _check_flag_completion(self, flag_id: str, info: dict) -> bool:
        """Check if a flag has been completed based on action result."""
        # This is a simplified check - real implementation would be more sophisticated
        return info.get("success", False)

    def _aggregate_results(
        self,
        scenario: BenchmarkScenario,
        episode_results: List[EpisodeResult],
    ) -> ScenarioResult:
        """Aggregate episode results into scenario result."""
        import statistics

        rewards = [r.total_reward for r in episode_results]
        steps = [r.steps_taken for r in episode_results]
        efficiencies = [r.efficiency_score for r in episode_results]
        success_count = sum(1 for r in episode_results if r.success)

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            episodes=len(episode_results),
            success_rate=success_count / len(episode_results) if episode_results else 0,
            mean_reward=statistics.mean(rewards) if rewards else 0,
            std_reward=statistics.stdev(rewards) if len(rewards) > 1 else 0,
            mean_steps=statistics.mean(steps) if steps else 0,
            mean_duration=statistics.mean(r.duration for r in episode_results),
            mean_efficiency=statistics.mean(efficiencies) if efficiencies else 0,
            min_reward=min(rewards) if rewards else 0,
            max_reward=max(rewards) if rewards else 0,
            median_steps=statistics.median(steps) if steps else 0,
            episode_results=episode_results,
        )

    def run_full_evaluation(
        self,
        agent,
        env_class,
        scenario_filter: List[str] = None,
        num_episodes: int = 5,
        verbose: bool = True,
    ) -> Dict[str, ScenarioResult]:
        """
        Run evaluation across all scenarios.

        Args:
            agent: The agent to evaluate
            env_class: Environment class
            scenario_filter: Optional list of scenario IDs to include
            num_episodes: Episodes per scenario
            verbose: Print progress

        Returns:
            Dict of scenario_id -> ScenarioResult
        """
        scenarios_to_run = self.scenarios
        if scenario_filter:
            scenarios_to_run = [
                s for s in self.scenarios if s.scenario_id in scenario_filter
            ]

        if verbose:
            logger.info(
                f"Running full evaluation: {len(scenarios_to_run)} scenarios, "
                f"{num_episodes} episodes each"
            )

        results = {}
        for scenario in scenarios_to_run:
            result = self.run_scenario(
                agent=agent,
                scenario_id=scenario.scenario_id,
                env_class=env_class,
                num_episodes=num_episodes,
                verbose=verbose,
            )
            results[scenario.scenario_id] = result

        # Save results
        self._save_results(results)

        return results

    def compare_baselines(
        self,
        baseline_results: Dict[str, float],
        current_results: Dict[str, float],
    ) -> dict:
        """
        Compare current system performance against baselines.

        Args:
            baseline_results: Dict of scenario_id -> success_rate
            current_results: Dict of scenario_id -> success_rate

        Returns:
            Comparison summary
        """
        comparison = {
            "overall_improvement": 0.0,
            "scenario_comparisons": [],
        }

        total_improvement = 0.0
        scenarios_compared = 0

        for scenario_id, baseline_rate in baseline_results.items():
            current_rate = current_results.get(scenario_id, 0)
            improvement = current_rate - baseline_rate
            total_improvement += improvement
            scenarios_compared += 1

            comparison["scenario_comparisons"].append({
                "scenario_id": scenario_id,
                "baseline": baseline_rate,
                "current": current_rate,
                "improvement": improvement,
            })

        if scenarios_compared > 0:
            comparison["overall_improvement"] = total_improvement / scenarios_compared

        return comparison

    def print_report(self, results: Dict[str, ScenarioResult]) -> None:
        """Print a formatted evaluation report."""
        print("\n" + "=" * 80)
        print("PENTEST SYSTEM EVALUATION REPORT")
        print("=" * 80)
        print(f"Generated: {datetime.now().isoformat()}")
        print(f"Total Scenarios: {len(results)}")
        print()

        overall_success = []
        overall_efficiency = []

        for scenario_id, result in results.items():
            print(f"\n--- Scenario: {result.scenario_name} ---")
            print(f"Success Rate: {result.success_rate:.1%}")
            print(f"Mean Reward: {result.mean_reward:.2f} (std: {result.std_reward:.2f})")
            print(f"Mean Steps: {result.mean_steps:.1f}")
            print(f"Mean Efficiency: {result.mean_efficiency:.2f}")
            print(f"Duration: {result.mean_duration:.1f}s")

            overall_success.append(result.success_rate)
            overall_efficiency.append(result.mean_efficiency)

        print("\n" + "-" * 80)
        print("OVERALL METRICS")
        print("-" * 80)
        print(f"Mean Success Rate: {sum(overall_success) / len(overall_success):.1%}")
        print(f"Mean Efficiency: {sum(overall_efficiency) / len(overall_efficiency):.2f}")
        print()

    def _save_results(self, results: Dict[str, ScenarioResult]) -> None:
        """Save results to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.results_dir, f"benchmark_{timestamp}.json")

        data = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "results": {
                sid: result.to_dict() for sid, result in results.items()
            },
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {filename}")

    def get_progress_summary(self) -> dict:
        """Get progress summary of all evaluated scenarios."""
        return {
            "total_scenarios": len(self.scenarios),
            "evaluated_scenarios": len(self._results),
            "total_episodes": len(self._episode_history),
            "scenarios_evaluated": list(self._results.keys()),
        }


def quick_benchmark(
    agent,
    env_class,
    difficulty: str = "easy",
    num_episodes: int = 3,
) -> dict:
    """
    Run a quick benchmark with filtered scenarios.

    Args:
        agent: Agent to evaluate
        env_class: Environment class
        difficulty: "easy", "medium", "hard", or "all"
        num_episodes: Episodes per scenario

    Returns:
        Quick benchmark summary
    """
    benchmark = PentestBenchmark()

    filters = {
        "easy": ["meta_basic", "ctf_web_basic"],
        "medium": ["meta_multi", "ctf_chain"],
        "hard": ["adv_defended", "real_corporate"],
        "all": None,
    }

    scenario_filter = filters.get(difficulty)

    results = benchmark.run_full_evaluation(
        agent=agent,
        env_class=env_class,
        scenario_filter=scenario_filter,
        num_episodes=num_episodes,
        verbose=True,
    )

    benchmark.print_report(results)
    return results