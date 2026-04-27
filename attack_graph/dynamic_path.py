"""
Dynamic Attack Path Generation

Real-time attack path reasoning engine inspired by AlphaGo's Monte Carlo
Tree Search (MCTS). The system:

1. Simulates multiple future attack/defense scenarios
2. Evaluates paths by success probability AND stealth
3. Dynamically adapts to real-time reconnaissance results
4. Selects optimal paths balancing speed, success rate, and detectability
"""

import math
import random
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class PathObjective(Enum):
    """Objectives for path selection."""
    FASTEST = "fastest"          # Minimize steps
    STEALTHIEST = "stealthiest"  # Minimize detection probability
    SAFEST = "safest"           # Maximize success probability
    BALANCED = "balanced"        # Balance all factors


@dataclass
class AttackAction:
    """A possible attack action in the tree."""
    action_type: str
    target: str
    tool: str
    params: dict
    cve_id: Optional[str] = None
    technique_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "tool": self.tool,
            "params": self.params,
            "cve_id": self.cve_id,
            "technique_id": self.technique_id,
        }


@dataclass
class SimulatedOutcome:
    """Simulated outcome of an attack action."""
    success: bool
    detection_probability: float
    time_cost: float
    reward: float
    new_state_summary: str
    side_effects: List[str]


@dataclass
class MCTSNode:
    """Node in the Monte Carlo search tree."""
    action: Optional[AttackAction]  # None for root
    parent: Optional['MCTSNode']
    children: List['MCTSNode']

    # Statistics
    visits: int = 0
    total_reward: float = 0.0
    success_count: int = 0
    detection_sum: float = 0.0

    # State at this node
    state_hash: str = ""
    depth: int = 0

    # Heuristic value (prior knowledge)
    prior_probability: float = 0.5

    @property
    def q_value(self) -> float:
        """Average reward (exploitation value)."""
        if self.visits == 0:
            return 0.0
        return self.total_reward / self.visits

    @property
    def success_rate(self) -> float:
        """Success rate from simulations."""
        if self.visits == 0:
            return self.prior_probability
        return self.success_count / self.visits

    @property
    def avg_detection(self) -> float:
        """Average detection probability."""
        if self.visits == 0:
            return 0.5
        return self.detection_sum / self.visits

    def uct_score(self, exploration: float = 1.414) -> float:
        """Upper Confidence Bound for Trees score."""
        if self.visits == 0:
            return float('inf')

        exploitation = self.q_value
        exploration_term = exploration * math.sqrt(
            math.log(self.parent.visits) / self.visits
        ) if self.parent else 0

        return exploitation + exploration_term

    def stealth_uct_score(self, stealth_weight: float = 0.5, exploration: float = 1.0) -> float:
        """UCT score that penalizes detection probability."""
        if self.visits == 0:
            return float('inf')

        exploitation = self.q_value
        stealth_penalty = stealth_weight * self.avg_detection
        exploration_term = exploration * math.sqrt(
            math.log(self.parent.visits) / self.visits
        ) if self.parent else 0

        return exploitation - stealth_penalty + exploration_term


class DefenseSimulator:
    """
    Simulates defensive responses to attack actions.

    Models:
    - SIEM alert generation based on action characteristics
    - EDR behavioral detection patterns
    - Network IDS signature matching
    - Defensive countermeasures (blocking, alerting, honeypots)
    """

    # Detection signatures by action type
    DETECTION_PROFILES = {
        "scan_network": {
            "siem": 0.3,  # SIEM detection probability
            "edr": 0.1,
            "ids": 0.5,
            "noise_level": "high",
        },
        "scan_port": {
            "siem": 0.4,
            "edr": 0.2,
            "ids": 0.6,
            "noise_level": "medium",
        },
        "exploit_vuln": {
            "siem": 0.6,
            "edr": 0.7,
            "ids": 0.5,
            "noise_level": "low",
        },
        "brute_force": {
            "siem": 0.7,
            "edr": 0.3,
            "ids": 0.8,
            "noise_level": "high",
        },
        "lateral_move": {
            "siem": 0.5,
            "edr": 0.8,
            "ids": 0.4,
            "noise_level": "low",
        },
        "priv_escalate": {
            "siem": 0.3,
            "edr": 0.9,
            "ids": 0.1,
            "noise_level": "low",
        },
        "dump_creds": {
            "siem": 0.4,
            "edr": 0.95,
            "ids": 0.2,
            "noise_level": "very_low",
        },
        "exfiltrate": {
            "siem": 0.5,
            "edr": 0.3,
            "ids": 0.7,
            "noise_level": "medium",
        },
    }

    def __init__(self, defense_level: str = "medium"):
        """
        Initialize defense simulator.

        Args:
            defense_level: "low", "medium", "high", "enterprise"
        """
        self.defense_level = defense_level
        self.defense_multiplier = {
            "low": 0.5,
            "medium": 1.0,
            "high": 1.5,
            "enterprise": 2.0,
        }.get(defense_level, 1.0)

        # Track cumulative detection score (alerts trigger above threshold)
        self.cumulative_detection = 0.0
        self.alert_threshold = 5.0  # SIEM alert threshold

    def simulate_detection(self, action: AttackAction) -> float:
        """
        Simulate detection probability for an action.

        Returns:
            Detection probability (0.0 - 1.0)
        """
        profile = self.DETECTION_PROFILES.get(action.action_type, {
            "siem": 0.5, "edr": 0.5, "ids": 0.5, "noise_level": "medium"
        })

        # Base detection from different sensors
        siem_prob = profile["siem"] * self.defense_multiplier
        edr_prob = profile["edr"] * self.defense_multiplier
        ids_prob = profile["ids"] * self.defense_multiplier

        # Combine detection probabilities (union of detections)
        no_detect = (1 - min(1.0, siem_prob)) * (1 - min(1.0, edr_prob)) * (1 - min(1.0, ids_prob))
        detection_prob = 1 - no_detect

        # Adjust for tool characteristics
        tool_name = action.tool.lower()
        if "stealth" in tool_name or "quiet" in tool_name:
            detection_prob *= 0.5
        elif "loud" in tool_name or "aggressive" in tool_name:
            detection_prob *= 1.5

        # Adjust for timing (spread actions = less detection)
        detection_prob = min(1.0, max(0.0, detection_prob))

        return detection_prob

    def simulate_outcome(self, action: AttackAction, state: dict) -> SimulatedOutcome:
        """
        Simulate the full outcome of an attack action including defense response.

        Args:
            action: The attack action
            state: Current state

        Returns:
            SimulatedOutcome with success/failure, detection, etc.
        """
        # Base success probability
        success_prob = self._estimate_success_prob(action, state)

        # Factor in detection
        detection_prob = self.simulate_detection(action)

        # If detected, success probability drops
        if detection_prob > 0.7:
            success_prob *= 0.5  # Defense may respond
        elif detection_prob > 0.5:
            success_prob *= 0.8

        # Simulate success
        success = random.random() < success_prob

        # Calculate reward
        reward_map = {
            "scan_network": 0.5, "scan_port": 0.3,
            "exploit_vuln": 5.0, "brute_force": 3.0,
            "lateral_move": 4.0, "priv_escalate": 3.0,
            "dump_creds": 1.0, "exfiltrate": 2.0,
        }
        reward = reward_map.get(action.action_type, 0.1)
        if not success:
            reward = -0.3

        # Time cost
        time_map = {
            "scan_network": 30, "scan_port": 15,
            "exploit_vuln": 20, "brute_force": 60,
            "lateral_move": 15, "priv_escalate": 10,
            "dump_creds": 5, "exfiltrate": 30,
        }
        time_cost = time_map.get(action.action_type, 10)

        # Side effects
        side_effects = []
        if detection_prob > 0.5:
            side_effects.append("possible_alert")
        if detection_prob > 0.8:
            side_effects.append("likely_detected")
            side_effects.append("defense_may_respond")

        return SimulatedOutcome(
            success=success,
            detection_probability=detection_prob,
            time_cost=time_cost,
            reward=reward,
            new_state_summary=self._generate_state_summary(action, success, state),
            side_effects=side_effects,
        )

    def _estimate_success_prob(self, action: AttackAction, state: dict) -> float:
        """Estimate success probability based on action and state."""
        base_prob = {
            "scan_network": 0.95, "scan_port": 0.9,
            "exploit_vuln": 0.7, "brute_force": 0.3,
            "lateral_move": 0.6, "priv_escalate": 0.5,
            "dump_creds": 0.8, "exfiltrate": 0.85,
        }.get(action.action_type, 0.5)

        # Adjust for known vulnerabilities
        if action.cve_id and state.get("vulnerabilities"):
            known_vulns = [v.get("id", v) if isinstance(v, dict) else v
                          for v in state.get("vulnerabilities", [])]
            if action.cve_id in known_vulns:
                base_prob = min(0.95, base_prob + 0.2)

        # Adjust for compromised hosts (more access = higher success)
        if action.action_type in ("lateral_move", "dump_creds", "priv_escalate"):
            if not state.get("compromised_hosts"):
                base_prob *= 0.3  # Need initial access first

        return base_prob

    def _generate_state_summary(self, action: AttackAction, success: bool, state: dict) -> str:
        """Generate a summary of the new state after an action."""
        if success:
            return f"After {action.action_type} on {action.target}: success"
        return f"After {action.action_type} on {action.target}: failed"

    def reset(self) -> None:
        """Reset cumulative detection score."""
        self.cumulative_detection = 0.0


class DynamicPathGenerator:
    """
    Monte Carlo Tree Search-based dynamic attack path generator.

    Like a Go AI, it:
    1. Expands possible future states (selection)
    2. Simulates random play-outs to estimate value (simulation)
    3. Backpropagates results to update node statistics (backpropagation)
    4. Selects the most promising path (selection)

    Supports multiple objectives: fastest, stealthiest, safest, balanced.
    """

    def __init__(
        self,
        defense_simulator: Optional[DefenseSimulator] = None,
        objective: PathObjective = PathObjective.BALANCED,
        max_depth: int = 6,
        simulations_per_step: int = 100,
        exploration_constant: float = 1.414,
    ):
        """
        Initialize the path generator.

        Args:
            defense_simulator: Defense simulation model
            objective: Path optimization objective
            max_depth: Maximum search depth
            simulations_per_step: Number of MCTS simulations
            exploration_constant: UCT exploration parameter
        """
        self.defense = defense_simulator or DefenseSimulator()
        self.objective = objective
        self.max_depth = max_depth
        self.simulations = simulations_per_step
        self.exploration_constant = exploration_constant

        # Action templates for expansion
        self.action_templates = self._build_action_templates()

    def _build_action_templates(self) -> List[dict]:
        """Build templates for possible actions."""
        return [
            {"action_type": "scan_network", "tool": "nmap", "params": {"scan_type": "ping"}},
            {"action_type": "scan_port", "tool": "nmap", "params": {"scan_type": "service"}},
            {"action_type": "scan_port", "tool": "nmap", "params": {"scan_type": "version"}},
            {"action_type": "exploit_vuln", "tool": "metasploit", "params": {}},
            {"action_type": "brute_force", "tool": "hydra", "params": {"threads": "slow"}},
            {"action_type": "lateral_move", "tool": "crackmapexec", "params": {}},
            {"action_type": "priv_escalate", "tool": "linpeas", "params": {}},
            {"action_type": "dump_creds", "tool": "mimikatz", "params": {}},
            {"action_type": "exfiltrate", "tool": "rclone", "params": {}},
        ]

    def find_best_path(
        self,
        current_state: dict,
        available_actions: List[AttackAction],
        target_goal: str = "full_compromise",
    ) -> Tuple[List[AttackAction], dict]:
        """
        Find the best attack path using MCTS.

        Args:
            current_state: Current penetration test state
            available_actions: List of possible actions
            target_goal: Goal description

        Returns:
            (best_path, analysis_info)
        """
        # Create root node
        root = MCTSNode(
            action=None,
            parent=None,
            children=[],
            state_hash=self._hash_state(current_state),
            depth=0,
        )

        # Run MCTS simulations
        for _ in range(self.simulations):
            # 1. Selection: traverse tree using UCT
            node = self._select(root)

            # 2. Expansion: add child nodes
            if node.visits > 0 and node.depth < self.max_depth:
                self._expand(node, available_actions, current_state)

            # 3. Simulation: random playout
            reward = self._simulate(node, available_actions, current_state)

            # 4. Backpropagation
            self._backpropagate(node, reward)

        # Extract best path
        best_path = self._extract_best_path(root)
        analysis = self._generate_analysis(root, best_path)

        return best_path, analysis

    def _select(self, node: MCTSNode) -> MCTSNode:
        """Select the most promising node to explore."""
        while node.children:
            if self.objective == PathObjective.STEALTHIEST:
                node = max(node.children, key=lambda n: n.stealth_uct_score())
            else:
                node = max(node.children, key=lambda n: n.uct_score(self.exploration_constant))
        return node

    def _expand(self, node: MCTSNode, actions: List[AttackAction], state: dict) -> None:
        """Expand a node by creating child nodes for possible actions."""
        # Filter actions based on state validity
        valid_actions = self._filter_valid_actions(actions, state)

        for action in valid_actions[:5]:  # Limit branching factor
            child = MCTSNode(
                action=action,
                parent=node,
                children=[],
                depth=node.depth + 1,
                prior_probability=self._estimate_prior(action, state),
            )
            node.children.append(child)

    def _simulate(self, node: MCTSNode, actions: List[AttackAction], state: dict) -> float:
        """Run a random simulation from this node to estimate value."""
        total_reward = 0.0
        current_state = dict(state)

        # Simulate from this node's action
        if node.action:
            outcome = self.defense.simulate_outcome(node.action, current_state)
            total_reward += outcome.reward

            if not outcome.success:
                return total_reward  # Failed, stop simulation

        # Random playout for remaining depth
        depth = node.depth
        while depth < self.max_depth:
            valid_actions = self._filter_valid_actions(actions, current_state)
            if not valid_actions:
                break

            action = random.choice(valid_actions)
            outcome = self.defense.simulate_outcome(action, current_state)
            total_reward += outcome.reward

            # Adjust reward based on objective
            if self.objective == PathObjective.STEALTHIEST:
                total_reward -= outcome.detection_probability * 2.0
            elif self.objective == PathObjective.SAFEST:
                if not outcome.success:
                    total_reward -= 1.0

            if not outcome.success:
                break

            depth += 1

        return total_reward

    def _backpropagate(self, node: MCTSNode, reward: float) -> None:
        """Backpropagate simulation results up the tree."""
        while node is not None:
            node.visits += 1
            node.total_reward += reward
            if reward > 0:
                node.success_count += 1
            node = node.parent

    def _extract_best_path(self, root: MCTSNode) -> List[AttackAction]:
        """Extract the best path from the search tree."""
        path = []
        node = root

        while node.children:
            # Select child with best average reward
            if self.objective == PathObjective.STEALTHIEST:
                best_child = max(
                    node.children,
                    key=lambda n: n.q_value - 0.5 * n.avg_detection
                )
            elif self.objective == PathObjective.FASTEST:
                best_child = max(
                    node.children,
                    key=lambda n: n.success_rate / max(1, n.depth)
                )
            else:
                best_child = max(node.children, key=lambda n: n.q_value)

            path.append(best_child.action)
            node = best_child

        return path

    def _generate_analysis(self, root: MCTSNode, best_path: List[AttackAction]) -> dict:
        """Generate analysis of the search results."""
        return {
            "simulations_run": sum(n.visits for n in self._flatten_tree(root)),
            "max_depth_explored": max((n.depth for n in self._flatten_tree(root)), default=0),
            "path_length": len(best_path),
            "path_actions": [a.to_dict() for a in best_path],
            "objective": self.objective.value,
            "estimated_success_rate": self._estimate_path_success(best_path, root),
            "estimated_detection_risk": self._estimate_path_detection(best_path, root),
            "alternative_paths": self._find_alternative_paths(root, count=3),
        }

    def _flatten_tree(self, node: MCTSNode) -> List[MCTSNode]:
        """Flatten tree into list of all nodes."""
        result = [node]
        for child in node.children:
            result.extend(self._flatten_tree(child))
        return result

    def _estimate_path_success(self, path: List[AttackAction], root: MCTSNode) -> float:
        """Estimate overall success probability for a path."""
        if not path:
            return 0.0

        node = root
        success_prob = 1.0

        for action in path:
            child = next((c for c in node.children if c.action == action), None)
            if child and child.visits > 0:
                success_prob *= child.success_rate
            else:
                success_prob *= 0.5  # Unknown
            if child:
                node = child

        return success_prob

    def _estimate_path_detection(self, path: List[AttackAction], root: MCTSNode) -> float:
        """Estimate cumulative detection probability for a path."""
        cumulative = 0.0
        node = root

        for action in path:
            child = next((c for c in node.children if c.action == action), None)
            if child and child.visits > 0:
                cumulative += child.avg_detection
            else:
                cumulative += self.defense.simulate_detection(action)
            if child:
                node = child

        return min(1.0, cumulative / max(1, len(path)))

    def _find_alternative_paths(self, root: MCTSNode, count: int = 3) -> List[List[dict]]:
        """Find alternative paths through the search tree."""
        paths = []

        def dfs(node: MCTSNode, current_path: List[dict]):
            if len(paths) >= count * 2:  # Collect more to filter
                return

            if not node.children:
                if current_path:
                    paths.append(current_path[:])
                return

            # Sort children by visits (most explored first)
            sorted_children = sorted(node.children, key=lambda n: n.visits, reverse=True)

            for i, child in enumerate(sorted_children[:3]):  # Top 3 branches
                current_path.append(child.action.to_dict() if child.action else {})
                dfs(child, current_path)
                current_path.pop()

        dfs(root, [])

        # Return top paths by length and reward
        unique_paths = []
        seen = set()
        for path in paths:
            path_key = str(path)
            if path_key not in seen:
                seen.add(path_key)
                unique_paths.append(path)

        return unique_paths[:count]

    def _filter_valid_actions(self, actions: List[AttackAction], state: dict) -> List[AttackAction]:
        """Filter actions that are valid in the current state."""
        valid = []
        has_shell = state.get("has_shell", False)
        has_admin = state.get("is_admin", False)
        compromised = state.get("compromised_hosts", [])

        for action in actions:
            # Reconnaissance is always valid
            if action.action_type in ("scan_network", "scan_port"):
                valid.append(action)
                continue

            # Exploitation needs discovered hosts
            if action.action_type == "exploit_vuln":
                if state.get("vulnerabilities") or state.get("hosts"):
                    valid.append(action)
                continue

            # Lateral movement needs shell + other hosts
            if action.action_type == "lateral_move":
                if has_shell and len(compromised) >= 1:
                    valid.append(action)
                continue

            # Privilege escalation needs shell
            if action.action_type == "priv_escalate":
                if has_shell and not has_admin:
                    valid.append(action)
                continue

            # Credential dumping needs admin
            if action.action_type == "dump_creds":
                if has_shell:
                    valid.append(action)
                continue

            # Exfiltration needs compromised host
            if action.action_type == "exfiltrate":
                if has_shell:
                    valid.append(action)
                continue

            valid.append(action)

        return valid

    def _estimate_prior(self, action: AttackAction, state: dict) -> float:
        """Estimate prior probability for an action."""
        priors = {
            "scan_network": 0.8, "scan_port": 0.7,
            "exploit_vuln": 0.6, "brute_force": 0.3,
            "lateral_move": 0.5, "priv_escalate": 0.5,
            "dump_creds": 0.7, "exfiltrate": 0.6,
        }
        return priors.get(action.action_type, 0.5)

    def _hash_state(self, state: dict) -> str:
        """Create a hash for state caching."""
        import hashlib
        key = str(sorted(state.items()))
        return hashlib.md5(key.encode()).hexdigest()[:12]


def create_path_generator(
    defense_level: str = "medium",
    objective: str = "balanced",
    simulations: int = 100,
) -> DynamicPathGenerator:
    """
    Create a dynamic path generator.

    Args:
        defense_level: "low", "medium", "high", "enterprise"
        objective: "fastest", "stealthiest", "safest", "balanced"
        simulations: Number of MCTS simulations per step

    Returns:
        Configured DynamicPathGenerator
    """
    defense_sim = DefenseSimulator(defense_level=defense_level)
    obj = PathObjective(objective)

    return DynamicPathGenerator(
        defense_simulator=defense_sim,
        objective=obj,
        simulations_per_step=simulations,
    )
