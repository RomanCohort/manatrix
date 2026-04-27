"""
Hierarchical Campaign Planner

Implements a hierarchical reinforcement learning framework for campaign-level
penetration testing planning. The system operates at two levels:

1. High-Level Agent (Strategist):
   - Defines abstract campaign objectives (e.g., "Obtain Domain Admin")
   - Decomposes goals into tactical phases
   - Monitors campaign progress and adapts strategy

2. Low-Level Expert System (Tacticians):
   - Executes specific tactics within each phase
   - Uses specialized expert modules for reconnaissance, exploitation, etc.
   - Reports outcomes back to high-level planner

This enables coherent multi-step, multi-host attack planning.
"""

import json
import logging
import time
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from collections import defaultdict
import random

logger = logging.getLogger(__name__)


class CampaignPhase(Enum):
    """High-level phases of a penetration test campaign."""
    RECONNAISSANCE = "reconnaissance"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command_and_control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


class CampaignObjective(Enum):
    """High-level campaign objectives."""
    FULL_COMPROMISE = "full_compromise"
    DOMAIN_ADMIN = "domain_admin"
    DATA_EXFILTRATION = "data_exfiltration"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"
    INFORMATION_GATHERING = "information_gathering"


@dataclass
class TacticalTask:
    """A tactical task to be executed by low-level experts."""
    task_id: str
    phase: CampaignPhase
    objective: str
    description: str
    target: str
    assigned_expert: str
    priority: int
    status: str = "pending"  # pending, in_progress, completed, failed, blocked
    result: Optional[dict] = None
    retry_count: int = 0
    max_retries: int = 2
    prerequisites: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "phase": self.phase.value,
            "objective": self.objective,
            "description": self.description,
            "target": self.target,
            "assigned_expert": self.assigned_expert,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "retry_count": self.retry_count,
            "prerequisites": self.prerequisites,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class CampaignState:
    """Current state of a campaign."""
    campaign_id: str
    objective: CampaignObjective
    current_phase: CampaignPhase
    completed_phases: List[CampaignPhase]
    active_tasks: List[str]
    completed_tasks: List[str]
    blocked_tasks: List[str]

    # Achievements
    hosts_discovered: List[str]
    hosts_compromised: List[str]
    credentials_obtained: List[dict]
    privileges_achieved: Dict[str, str]  # host -> privilege level
    data_collected: List[str]

    # Metrics
    total_actions: int
    successful_actions: int
    failed_actions: int
    campaign_reward: float

    # Timestamps
    started_at: float
    last_activity: float

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "objective": self.objective.value,
            "current_phase": self.current_phase.value,
            "completed_phases": [p.value for p in self.completed_phases],
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "blocked_tasks": self.blocked_tasks,
            "hosts_discovered": self.hosts_discovered,
            "hosts_compromised": self.hosts_compromised,
            "credentials_obtained": self.credentials_obtained,
            "privileges_achieved": self.privileges_achieved,
            "data_collected": self.data_collected,
            "total_actions": self.total_actions,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "campaign_reward": self.campaign_reward,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
        }


@dataclass
class CampaignPlan:
    """A strategic plan for achieving a campaign objective."""
    objective: CampaignObjective
    phases: List[dict]  # List of phase configurations
    success_criteria: List[str]  # Conditions for success
    fallback_plans: List[dict]  # Alternative approaches
    estimated_steps: int
    risk_level: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "objective": self.objective.value,
            "phases": self.phases,
            "success_criteria": self.success_criteria,
            "fallback_plans": self.fallback_plans,
            "estimated_steps": self.estimated_steps,
            "risk_level": self.risk_level,
            "created_at": self.created_at,
        }


class HighLevelPolicy:
    """
    High-level policy network for strategic decision making.

    Decides:
    - Which phase to focus on
    - When to transition between phases
    - How to decompose objectives into tactical tasks
    - When to abandon/fallback a campaign
    """

    def __init__(self, llm_planner=None):
        self.llm_planner = llm_planner
        self.phase_transition_history: List[dict] = []

        # Phase transition rules (learned from experience)
        self.phase_sequence = [
            CampaignPhase.RECONNAISSANCE,
            CampaignPhase.INITIAL_ACCESS,
            CampaignPhase.EXECUTION,
            CampaignPhase.PERSISTENCE,
            CampaignPhase.PRIVILEGE_ESCALATION,
            CampaignPhase.CREDENTIAL_ACCESS,
            CampaignPhase.DISCOVERY,
            CampaignPhase.LATERAL_MOVEMENT,
            CampaignPhase.COLLECTION,
            CampaignPhase.EXFILTRATION,
        ]

        # Success indicators for each phase
        self.phase_success_indicators = {
            CampaignPhase.RECONNAISSANCE: lambda s: len(s.hosts_discovered) > 0,
            CampaignPhase.INITIAL_ACCESS: lambda s: len(s.hosts_compromised) > 0,
            CampaignPhase.PRIVILEGE_ESCALATION: lambda s: any(
                p in ("root", "system", "admin", "administrator")
                for p in s.privileges_achieved.values()
            ),
            CampaignPhase.LATERAL_MOVEMENT: lambda s: len(s.hosts_compromised) > 1,
            CampaignPhase.CREDENTIAL_ACCESS: lambda s: len(s.credentials_obtained) > 0,
            CampaignPhase.EXFILTRATION: lambda s: len(s.data_collected) > 0,
        }

    def select_phase(self, state: CampaignState) -> CampaignPhase:
        """
        Select the current phase to focus on.

        Considers:
        - Current achievements
        - Success indicators for each phase
        - Phase transition history
        """
        # Check if current phase is complete
        if state.current_phase in self.phase_success_indicators:
            if self.phase_success_indicators[state.current_phase](state):
                # Phase complete, move to next
                return self._get_next_phase(state)

        # Check if we need to backtrack
        for prev_phase in reversed(state.completed_phases):
            if prev_phase in self.phase_success_indicators:
                if not self.phase_success_indicators[prev_phase](state):
                    # Previous phase no longer satisfied, backtrack
                    logger.info(f"Backtracking to phase: {prev_phase.value}")
                    return prev_phase

        return state.current_phase

    def _get_next_phase(self, state: CampaignState) -> CampaignPhase:
        """Get the next phase in sequence."""
        current_idx = self.phase_sequence.index(state.current_phase) \
            if state.current_phase in self.phase_sequence else -1

        for i in range(current_idx + 1, len(self.phase_sequence)):
            next_phase = self.phase_sequence[i]
            if next_phase not in state.completed_phases:
                return next_phase

        # All phases complete, stay at current
        return state.current_phase

    def decompose_objective(
        self,
        objective: CampaignObjective,
        state: CampaignState,
        available_hosts: List[str],
    ) -> List[TacticalTask]:
        """
        Decompose a high-level objective into tactical tasks.

        Uses LLM for strategic decomposition when available.
        """
        tasks = []

        if objective == CampaignObjective.DOMAIN_ADMIN:
            tasks = self._decompose_domain_admin(state, available_hosts)
        elif objective == CampaignObjective.FULL_COMPROMISE:
            tasks = self._decompose_full_compromise(state, available_hosts)
        elif objective == CampaignObjective.DATA_EXFILTRATION:
            tasks = self._decompose_data_exfil(state, available_hosts)
        elif objective == CampaignObjective.LATERAL_MOVEMENT:
            tasks = self._decompose_lateral(state, available_hosts)
        else:
            tasks = self._decompose_generic(objective, state, available_hosts)

        return tasks

    def _decompose_domain_admin(self, state: CampaignState, hosts: List[str]) -> List[TacticalTask]:
        """Decompose 'obtain domain admin' objective."""
        tasks = []
        task_counter = 0

        # Phase 1: Identify domain controller
        if not any("dc" in h.lower() or "domain" in h.lower() for h in state.hosts_discovered):
            tasks.append(TacticalTask(
                task_id=f"task_{task_counter}",
                phase=CampaignPhase.DISCOVERY,
                objective="Identify domain controller",
                description="Scan network to identify domain controller",
                target="network",
                assigned_expert="Scout",
                priority=1,
                prerequisites=[],
            ))
            task_counter += 1

        # Phase 2: Get initial access
        for host in hosts:
            if host not in state.hosts_compromised:
                tasks.append(TacticalTask(
                    task_id=f"task_{task_counter}",
                    phase=CampaignPhase.INITIAL_ACCESS,
                    objective=f"Compromise {host}",
                    description=f"Gain initial access to {host}",
                    target=host,
                    assigned_expert="Striker",
                    priority=2,
                    prerequisites=[],
                ))
                task_counter += 1
                break  # One initial foothold

        # Phase 3: Credential harvesting
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.CREDENTIAL_ACCESS,
            objective="Harvest domain credentials",
            description="Dump credentials from compromised host",
            target="compromised_host",
            assigned_expert="Hunter",
            priority=3,
            prerequisites=[f"task_{task_counter - 1}"],
        ))
        task_counter += 1

        # Phase 4: Lateral movement to DC
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.LATERAL_MOVEMENT,
            objective="Move to domain controller",
            description="Use harvested credentials to access DC",
            target="domain_controller",
            assigned_expert="Phantom",
            priority=4,
            prerequisites=[f"task_{task_counter - 1}"],
        ))
        task_counter += 1

        # Phase 5: Domain admin
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.PRIVILEGE_ESCALATION,
            objective="Obtain domain admin",
            description="Escalate to domain admin privileges",
            target="domain_controller",
            assigned_expert="Ghost",
            priority=5,
            prerequisites=[f"task_{task_counter - 1}"],
        ))

        return tasks

    def _decompose_full_compromise(self, state: CampaignState, hosts: List[str]) -> List[TacticalTask]:
        """Decompose 'full network compromise' objective."""
        tasks = []
        task_counter = 0

        # Reconnaissance
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.RECONNAISSANCE,
            objective="Network reconnaissance",
            description="Discover all hosts in target network",
            target="network",
            assigned_expert="Scout",
            priority=1,
        ))
        task_counter += 1

        # Exploit each host
        for i, host in enumerate(hosts):
            if host not in state.hosts_compromised:
                tasks.append(TacticalTask(
                    task_id=f"task_{task_counter}",
                    phase=CampaignPhase.INITIAL_ACCESS,
                    objective=f"Compromise {host}",
                    description=f"Gain access to {host}",
                    target=host,
                    assigned_expert="Striker",
                    priority=2 + i,
                    prerequisites=[f"task_0"],
                ))
                task_counter += 1

        return tasks

    def _decompose_data_exfil(self, state: CampaignState, hosts: List[str]) -> List[TacticalTask]:
        """Decompose 'data exfiltration' objective."""
        tasks = []
        task_counter = 0

        # Find data sources
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.DISCOVERY,
            objective="Locate sensitive data",
            description="Scan for databases, file shares, sensitive files",
            target="network",
            assigned_expert="Scout",
            priority=1,
        ))
        task_counter += 1

        # Access and collect
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.COLLECTION,
            objective="Collect target data",
            description="Access and stage target data for exfiltration",
            target="data_source",
            assigned_expert="Ghost",
            priority=2,
            prerequisites=[f"task_0"],
        ))
        task_counter += 1

        # Exfiltrate
        tasks.append(TacticalTask(
            task_id=f"task_{task_counter}",
            phase=CampaignPhase.EXFILTRATION,
            objective="Exfiltrate data",
            description="Transfer collected data to external location",
            target="exfil_target",
            assigned_expert="Phantom",
            priority=3,
            prerequisites=[f"task_{task_counter - 1}"],
        ))

        return tasks

    def _decompose_lateral(self, state: CampaignState, hosts: List[str]) -> List[TacticalTask]:
        """Decompose 'lateral movement' objective."""
        tasks = []
        task_counter = 0

        if len(state.hosts_compromised) == 0:
            tasks.append(TacticalTask(
                task_id=f"task_{task_counter}",
                phase=CampaignPhase.INITIAL_ACCESS,
                objective="Get initial foothold",
                description="Compromise at least one host",
                target=hosts[0] if hosts else "unknown",
                assigned_expert="Striker",
                priority=1,
            ))
            task_counter += 1

        # Credential gathering for lateral movement
        if len(state.credentials_obtained) == 0:
            tasks.append(TacticalTask(
                task_id=f"task_{task_counter}",
                phase=CampaignPhase.CREDENTIAL_ACCESS,
                objective="Gather credentials",
                description="Extract credentials from compromised host",
                target="compromised_host",
                assigned_expert="Hunter",
                priority=2,
                prerequisites=[f"task_0"] if task_counter > 0 else [],
            ))
            task_counter += 1

        # Move to other hosts
        for i, host in enumerate(hosts):
            if host not in state.hosts_compromised:
                tasks.append(TacticalTask(
                    task_id=f"task_{task_counter}",
                    phase=CampaignPhase.LATERAL_MOVEMENT,
                    objective=f"Move to {host}",
                    description=f"Lateral movement to {host}",
                    target=host,
                    assigned_expert="Phantom",
                    priority=3 + i,
                    prerequisites=[f"task_{task_counter - 1}"],
                ))
                task_counter += 1

        return tasks

    def _decompose_generic(self, objective: CampaignObjective, state: CampaignState, hosts: List[str]) -> List[TacticalTask]:
        """Generic decomposition for unknown objectives."""
        return [
            TacticalTask(
                task_id="task_0",
                phase=CampaignPhase.RECONNAISSANCE,
                objective=str(objective.value),
                description=f"Execute reconnaissance for {objective.value}",
                target="network",
                assigned_expert="Scout",
                priority=1,
            )
        ]

    def should_transition(self, state: CampaignState) -> Tuple[bool, str]:
        """
        Decide if phase transition is warranted.

        Returns: (should_transition, reason)
        """
        current_phase = state.current_phase

        # Check if stuck on too many failures
        recent_failures = state.failed_actions - (
            state.total_actions - state.successful_actions - state.failed_actions
        )
        if recent_failures > 5:
            return True, "too_many_failures"

        # Check phase success indicators
        if current_phase in self.phase_success_indicators:
            if self.phase_success_indicators[current_phase](state):
                return True, "phase_objective_achieved"

        # Check if blocked too long
        if len(state.blocked_tasks) > 3:
            return True, "multiple_blocked_tasks"

        return False, ""

    def should_abort(self, state: CampaignState) -> Tuple[bool, str]:
        """
        Decide if campaign should be aborted.

        Returns: (should_abort, reason)
        """
        # Too many total failures
        if state.failed_actions > 20:
            return True, "excessive_failures"

        # No progress for too many actions
        if state.total_actions > 50 and len(state.hosts_compromised) == 0:
            return True, "no_progress"

        # All tasks blocked
        if len(state.blocked_tasks) > 0 and len(state.active_tasks) == 0:
            return True, "all_tasks_blocked"

        return False, ""


class LowLevelExecutor:
    """
    Low-level task executor using specialized experts.

    Executes tactical tasks within a phase, using the appropriate
    expert module for each task type.
    """

    def __init__(self, expert_router, tool_orchestrator=None):
        self.expert_router = expert_router
        self.tool_orchestrator = tool_orchestrator
        self.execution_history: List[dict] = []

    def execute_task(
        self,
        task: TacticalTask,
        state: dict,
        env=None,
    ) -> Tuple[bool, dict]:
        """
        Execute a tactical task using the assigned expert.

        Args:
            task: The tactical task to execute
            state: Current state dictionary
            env: Optional environment for simulation

        Returns:
            (success, result_dict)
        """
        task.status = "in_progress"
        task.started_at = time.time()

        result = {
            "task_id": task.task_id,
            "phase": task.phase.value,
            "target": task.target,
            "started_at": task.started_at,
        }

        try:
            # Get expert advice
            expert_advice = self._get_expert_advice(task, state)

            # Execute recommended actions
            execution_result = self._execute_actions(
                expert_advice,
                task.target,
                env,
            )

            result["expert_advice"] = {
                "summary": expert_advice.summary if expert_advice else "",
                "tools": expert_advice.tools_to_use if expert_advice else [],
            }
            result["actions_taken"] = execution_result.get("actions", [])
            result["success"] = execution_result.get("success", False)

            task.status = "completed" if result["success"] else "failed"
            task.result = result

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            task.status = "failed"
            task.result = result
            logger.error(f"Task execution failed: {e}", exc_info=True)

        task.completed_at = time.time()
        result["completed_at"] = task.completed_at
        result["duration"] = task.completed_at - task.started_at

        self.execution_history.append(result)
        return result["success"], result

    def _get_expert_advice(self, task: TacticalTask, state: dict):
        """Get advice from the appropriate expert."""
        if not self.expert_router:
            return None

        # Map task phase to expert type
        phase_expert_map = {
            CampaignPhase.RECONNAISSANCE: "reconnaissance",
            CampaignPhase.INITIAL_ACCESS: "exploitation",
            CampaignPhase.EXECUTION: "exploitation",
            CampaignPhase.PERSISTENCE: "post_exploitation",
            CampaignPhase.PRIVILEGE_ESCALATION: "post_exploitation",
            CampaignPhase.DEFENSE_EVASION: "post_exploitation",
            CampaignPhase.CREDENTIAL_ACCESS: "credential",
            CampaignPhase.DISCOVERY: "reconnaissance",
            CampaignPhase.LATERAL_MOVEMENT: "lateral_movement",
            CampaignPhase.COLLECTION: "post_exploitation",
            CampaignPhase.EXFILTRATION: "post_exploitation",
        }

        query = f"{task.objective}: {task.description}"

        routing_result = self.expert_router.route_query(
            query=query,
            state=state,
        )

        return routing_result.get("primary_advice")

    def _execute_actions(self, expert_advice, target: str, env=None) -> dict:
        """Execute recommended actions from expert advice."""
        result = {
            "actions": [],
            "success": False,
        }

        if not expert_advice or not expert_advice.recommended_actions:
            return result

        for action_spec in expert_advice.recommended_actions[:3]:  # Top 3 actions
            action_result = {
                "type": action_spec.get("type"),
                "tool": action_spec.get("tool"),
                "params": action_spec.get("params", {}),
                "success": False,
            }

            # Simulate or execute
            if env:
                # Use environment for simulation
                from rl_agent.action import PenTestAction, ActionType

                action_type = self._map_action_type(action_spec.get("type", ""))
                if action_type:
                    action = PenTestAction(
                        type=action_type,
                        target=target,
                        parameters=action_spec.get("params", {}),
                    )

                    _, reward, done, info = env.step(action)
                    action_result["reward"] = reward
                    action_result["success"] = reward > 0
                    action_result["info"] = info

            result["actions"].append(action_result)

        # Overall success if any action succeeded
        result["success"] = any(a["success"] for a in result["actions"])

        return result

    def _map_action_type(self, type_str: str):
        """Map string action type to ActionType enum."""
        from rl_agent.action import ActionType

        mapping = {
            "scan": ActionType.SCAN_PORT,
            "scan_network": ActionType.SCAN_NETWORK,
            "exploit": ActionType.EXPLOIT_VULN,
            "brute_force": ActionType.BRUTE_FORCE,
            "lateral_move": ActionType.LATERAL_MOVE,
            "priv_escalate": ActionType.PRIV_ESCALATE,
            "dump_creds": ActionType.DUMP_CREDS,
            "exfiltrate": ActionType.EXFILTRATE,
        }

        type_lower = type_str.lower()
        for key, action_type in mapping.items():
            if key in type_lower:
                return action_type

        return None


class HierarchicalCampaignPlanner:
    """
    Main hierarchical campaign planner integrating high-level strategy
    and low-level execution.

    Usage:
        planner = HierarchicalCampaignPlanner(
            objective=CampaignObjective.DOMAIN_ADMIN,
            expert_router=router,
            llm_planner=llm_planner,
        )
        planner.initialize(hosts, env)
        result = planner.run_campaign()
    """

    def __init__(
        self,
        expert_router=None,
        tool_orchestrator=None,
        llm_planner=None,
        max_campaign_steps: int = 500,
        enable_human_oversight: bool = False,
    ):
        """
        Initialize the hierarchical planner.

        Args:
            expert_router: Expert router for low-level execution
            tool_orchestrator: Tool orchestrator for execution
            llm_planner: LLM attack planner for strategic decisions
            max_campaign_steps: Maximum steps per campaign
            enable_human_oversight: Enable human approval for critical decisions
        """
        self.expert_router = expert_router
        self.tool_orchestrator = tool_orchestrator
        self.llm_planner = llm_planner

        # Policy networks
        self.high_level_policy = HighLevelPolicy(llm_planner=llm_planner)
        self.low_level_executor = LowLevelExecutor(
            expert_router=expert_router,
            tool_orchestrator=tool_orchestrator,
        )

        # Campaign state
        self.campaign_state: Optional[CampaignState] = None
        self.campaign_plan: Optional[CampaignPlan] = None
        self.task_queue: List[TacticalTask] = []
        self.max_campaign_steps = max_campaign_steps

        # Human oversight
        self.enable_human_oversight = enable_human_oversight
        self.pending_approval: Optional[dict] = None

        # Statistics
        self.campaign_history: List[dict] = []

    def initialize(
        self,
        objective: CampaignObjective,
        hosts: List[str],
        env=None,
    ) -> None:
        """
        Initialize a new campaign.

        Args:
            objective: Campaign objective
            hosts: List of target hosts
            env: Optional environment for simulation
        """
        import uuid

        campaign_id = f"campaign_{int(time.time())}_{uuid.uuid4().hex[:8]}"

        self.campaign_state = CampaignState(
            campaign_id=campaign_id,
            objective=objective,
            current_phase=CampaignPhase.RECONNAISSANCE,
            completed_phases=[],
            active_tasks=[],
            completed_tasks=[],
            blocked_tasks=[],
            hosts_discovered=list(hosts),
            hosts_compromised=[],
            credentials_obtained=[],
            privileges_achieved={},
            data_collected=[],
            total_actions=0,
            successful_actions=0,
            failed_actions=0,
            campaign_reward=0.0,
            started_at=time.time(),
            last_activity=time.time(),
        )

        self.env = env

        # Create initial plan
        self.campaign_plan = self._create_campaign_plan(objective, hosts)
        self.task_queue = self.high_level_policy.decompose_objective(
            objective=objective,
            state=self.campaign_state,
            available_hosts=hosts,
        )

        logger.info(
            f"Campaign initialized: {campaign_id} "
            f"Objective: {objective.value} "
            f"Tasks: {len(self.task_queue)}"
        )

    def _create_campaign_plan(self, objective: CampaignObjective, hosts: List[str]) -> CampaignPlan:
        """Create a strategic campaign plan."""
        # Default plan structure
        phases = [
            {"phase": "reconnaissance", "priority": 1, "required": True},
            {"phase": "initial_access", "priority": 2, "required": True},
        ]

        if objective in [CampaignObjective.DOMAIN_ADMIN, CampaignObjective.FULL_COMPROMISE]:
            phases.extend([
                {"phase": "credential_access", "priority": 3, "required": True},
                {"phase": "lateral_movement", "priority": 4, "required": True},
                {"phase": "privilege_escalation", "priority": 5, "required": True},
            ])

        if objective == CampaignObjective.DATA_EXFILTRATION:
            phases.extend([
                {"phase": "collection", "priority": 5, "required": True},
                {"phase": "exfiltration", "priority": 6, "required": True},
            ])

        success_criteria = self._get_success_criteria(objective)

        return CampaignPlan(
            objective=objective,
            phases=phases,
            success_criteria=success_criteria,
            fallback_plans=[],
            estimated_steps=len(hosts) * 5,
            risk_level="medium",
        )

    def _get_success_criteria(self, objective: CampaignObjective) -> List[str]:
        """Get success criteria for an objective."""
        criteria_map = {
            CampaignObjective.DOMAIN_ADMIN: [
                "Obtained domain admin privileges",
                "Compromised domain controller",
            ],
            CampaignObjective.FULL_COMPROMISE: [
                "All hosts compromised",
                "Admin/root privileges on all hosts",
            ],
            CampaignObjective.DATA_EXFILTRATION: [
                "Target data collected",
                "Data exfiltrated successfully",
            ],
            CampaignObjective.LATERAL_MOVEMENT: [
                "Moved to at least 2 additional hosts",
            ],
        }
        return criteria_map.get(objective, ["Objective completed"])

    def step(self) -> Tuple[bool, dict]:
        """
        Execute one campaign step.

        Returns:
            (done, step_info)
        """
        if not self.campaign_state or not self.task_queue:
            return True, {"reason": "no_campaign"}

        self.campaign_state.total_actions += 1
        self.campaign_state.last_activity = time.time()

        # Check for abort conditions
        should_abort, abort_reason = self.high_level_policy.should_abort(self.campaign_state)
        if should_abort:
            logger.warning(f"Campaign aborted: {abort_reason}")
            return True, {"reason": f"aborted: {abort_reason}"}

        # Check for phase transition
        should_transition, transition_reason = self.high_level_policy.should_transition(
            self.campaign_state
        )
        if should_transition:
            next_phase = self.high_level_policy.select_phase(self.campaign_state)
            if next_phase != self.campaign_state.current_phase:
                logger.info(f"Phase transition: {self.campaign_state.current_phase.value} -> {next_phase.value}")
                if self.campaign_state.current_phase not in self.campaign_state.completed_phases:
                    self.campaign_state.completed_phases.append(self.campaign_state.current_phase)
                self.campaign_state.current_phase = next_phase

        # Select next task
        task = self._select_next_task()
        if not task:
            return True, {"reason": "no_available_tasks"}

        # Check prerequisites
        if not self._check_prerequisites(task):
            task.status = "blocked"
            self.campaign_state.blocked_tasks.append(task.task_id)
            return False, {"reason": "task_blocked", "task_id": task.task_id}

        # Execute task
        success, result = self.low_level_executor.execute_task(
            task=task,
            state=self._build_state_dict(),
            env=self.env,
        )

        # Update campaign state
        self._update_campaign_state(task, result)

        # Check campaign completion
        done = self._check_completion()

        return done, {
            "task_id": task.task_id,
            "success": success,
            "phase": task.phase.value,
            "result": result,
        }

    def _select_next_task(self) -> Optional[TacticalTask]:
        """Select the next task to execute."""
        available = [
            t for t in self.task_queue
            if t.status == "pending"
            and self._check_prerequisites(t)
        ]

        if not available:
            return None

        # Sort by priority
        available.sort(key=lambda t: t.priority)
        return available[0]

    def _check_prerequisites(self, task: TacticalTask) -> bool:
        """Check if task prerequisites are satisfied."""
        for prereq in task.prerequisites:
            prereq_task = next(
                (t for t in self.task_queue if t.task_id == prereq),
                None
            )
            if prereq_task and prereq_task.status != "completed":
                return False
        return True

    def _build_state_dict(self) -> dict:
        """Build state dictionary for expert consultation."""
        if not self.campaign_state:
            return {}

        return {
            "phase": self.campaign_state.current_phase.value,
            "hosts": self.campaign_state.hosts_discovered,
            "compromised_hosts": self.campaign_state.hosts_compromised,
            "credentials": self.campaign_state.credentials_obtained,
            "privileges": self.campaign_state.privileges_achieved,
            "has_shell": len(self.campaign_state.hosts_compromised) > 0,
            "is_admin": any(
                p in ("root", "system", "admin", "administrator")
                for p in self.campaign_state.privileges_achieved.values()
            ),
        }

    def _update_campaign_state(self, task: TacticalTask, result: dict) -> None:
        """Update campaign state based on task result."""
        if result.get("success"):
            self.campaign_state.successful_actions += 1
            self.campaign_state.campaign_reward += 1.0
            self.campaign_state.completed_tasks.append(task.task_id)

            # Update achievements based on task phase
            if task.phase == CampaignPhase.INITIAL_ACCESS:
                if task.target not in self.campaign_state.hosts_compromised:
                    self.campaign_state.hosts_compromised.append(task.target)

            elif task.phase == CampaignPhase.CREDENTIAL_ACCESS:
                creds = result.get("credentials_found", [])
                self.campaign_state.credentials_obtained.extend(creds)

            elif task.phase == CampaignPhase.PRIVILEGE_ESCALATION:
                self.campaign_state.privileges_achieved[task.target] = "admin"

            elif task.phase == CampaignPhase.EXFILTRATION:
                data = result.get("data_exfiltrated", [])
                self.campaign_state.data_collected.extend(data)

        else:
            self.campaign_state.failed_actions += 1
            self.campaign_state.campaign_reward -= 0.3

            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = "pending"
            else:
                self.campaign_state.blocked_tasks.append(task.task_id)

    def _check_completion(self) -> bool:
        """Check if campaign objective is achieved."""
        if not self.campaign_plan:
            return False

        # Check all success criteria
        for criterion in self.campaign_plan.success_criteria:
            if not self._evaluate_criterion(criterion):
                return False

        return True

    def _evaluate_criterion(self, criterion: str) -> bool:
        """Evaluate if a success criterion is met."""
        criterion_lower = criterion.lower()

        if "domain admin" in criterion_lower:
            return any(
                p in ("domain_admin", "enterprise_admin")
                for p in self.campaign_state.privileges_achieved.values()
            )

        if "all hosts" in criterion_lower:
            return len(self.campaign_state.hosts_compromised) == len(
                self.campaign_state.hosts_discovered
            )

        if "exfiltrated" in criterion_lower:
            return len(self.campaign_state.data_collected) > 0

        return False

    def run_campaign(self, max_steps: int = None) -> dict:
        """
        Run the campaign to completion.

        Args:
            max_steps: Maximum steps (default from constructor)

        Returns:
            Campaign result dictionary
        """
        max_steps = max_steps or self.max_campaign_steps

        for step in range(max_steps):
            done, info = self.step()

            if done:
                break

        result = {
            "campaign_id": self.campaign_state.campaign_id if self.campaign_state else "",
            "objective": self.campaign_state.objective.value if self.campaign_state else "",
            "completed": self._check_completion(),
            "total_steps": step + 1,
            "successful_actions": self.campaign_state.successful_actions if self.campaign_state else 0,
            "failed_actions": self.campaign_state.failed_actions if self.campaign_state else 0,
            "campaign_reward": self.campaign_state.campaign_reward if self.campaign_state else 0,
            "hosts_compromised": self.campaign_state.hosts_compromised if self.campaign_state else [],
            "credentials_obtained": len(self.campaign_state.credentials_obtained) if self.campaign_state else 0,
            "final_state": self.campaign_state.to_dict() if self.campaign_state else {},
        }

        self.campaign_history.append(result)
        return result

    def get_campaign_status(self) -> dict:
        """Get current campaign status."""
        if not self.campaign_state:
            return {"status": "no_campaign"}

        return {
            "campaign_id": self.campaign_state.campaign_id,
            "objective": self.campaign_state.objective.value,
            "current_phase": self.campaign_state.current_phase.value,
            "completed_phases": [p.value for p in self.campaign_state.completed_phases],
            "active_tasks": len([t for t in self.task_queue if t.status == "in_progress"]),
            "pending_tasks": len([t for t in self.task_queue if t.status == "pending"]),
            "completed_tasks": len(self.campaign_state.completed_tasks),
            "blocked_tasks": len(self.campaign_state.blocked_tasks),
            "hosts_compromised": len(self.campaign_state.hosts_compromised),
            "campaign_reward": self.campaign_state.campaign_reward,
        }


def create_campaign_planner(
    expert_router=None,
    llm_planner=None,
    objective: str = "full_compromise",
) -> HierarchicalCampaignPlanner:
    """
    Create a campaign planner with default configuration.

    Args:
        expert_router: Expert router instance
        llm_planner: LLM attack planner instance
        objective: Campaign objective string

    Returns:
        Configured HierarchicalCampaignPlanner
    """
    objective_enum = CampaignObjective(objective)

    return HierarchicalCampaignPlanner(
        expert_router=expert_router,
        llm_planner=llm_planner,
    )
