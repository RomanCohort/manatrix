"""
Attack Team - Multi-Expert Collaborative Attack Group

A team of penetration testing experts coordinated by LLM for collaborative
decision-making, strategy planning, and coordinated attacks.

Features:
- Team coordination with role-based specialists
- Collaborative planning meetings
- Shared memory and knowledge
- Consensus-based decision making
- Task delegation and tracking
"""

import logging
import time
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict

from models.enums import ExpertType
from models.experts.base import ExpertAdvice
from models.expert_router import ExpertRouter, RoutingDecision

logger = logging.getLogger(__name__)


class TeamRole(Enum):
    """Roles within the attack team."""
    LEADER = "leader"              # Team leader - coordinates and makes final decisions
    RECON = "recon"                # Reconnaissance specialist
    VULN_ANALYST = "vuln_analyst"  # Vulnerability analyst
    EXPLOITER = "exploiter"        # Exploitation specialist
    POST_EX = "post_ex"            # Post-exploitation specialist
    CRED_HUNTER = "cred_hunter"    # Credential specialist
    MOVER = "mover"                # Lateral movement specialist


class MeetingType(Enum):
    """Types of team meetings."""
    BRIEFING = "briefing"        # Initial situation briefing
    PLANNING = "planning"        # Attack planning
    REVIEW = "review"            # Progress review
    DEBRIEF = "debrief"          # Post-operation debrief
    EMERGENCY = "emergency"      # Emergency consultation


@dataclass
class TeamMember:
    """A member of the attack team."""
    name: str
    role: TeamRole
    expert_type: ExpertType
    expertise: List[str]
    confidence: float = 0.5
    tasks_completed: int = 0
    success_rate: float = 0.5

    def __hash__(self):
        return hash(self.name)


@dataclass
class TeamTask:
    """A task assigned to a team member."""
    task_id: str
    description: str
    assigned_to: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    priority: int = 1
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


@dataclass
class TeamMemory:
    """
    Shared memory for the attack team with importance-based filtering.

    Prevents unbounded memory growth by scoring items by importance
    and pruning low-value entries when limits are reached.
    """
    # Memory limits
    MAX_HOSTS = 500
    MAX_SERVICES = 1000
    MAX_VULNERABILITIES = 500
    MAX_CREDENTIALS = 200
    MAX_ATTACK_HISTORY = 500
    MAX_LESSONS = 100
    MAX_DECISIONS = 200

    # Shared knowledge
    discovered_hosts: List[dict] = field(default_factory=list)
    discovered_services: List[dict] = field(default_factory=list)
    discovered_vulnerabilities: List[dict] = field(default_factory=list)
    obtained_credentials: List[dict] = field(default_factory=list)
    compromised_hosts: List[str] = field(default_factory=list)

    # Attack history
    attack_history: List[dict] = field(default_factory=list)

    # Lessons learned
    lessons: List[str] = field(default_factory=list)

    # Team decisions
    decisions: List[dict] = field(default_factory=list)

    def _calculate_importance(self, item: dict, category: str) -> float:
        """
        Calculate importance score for a memory item.

        Returns a score from 0.0 (low) to 1.0 (high).
        """
        score = 0.5  # Base score

        if category == "hosts":
            # Hosts with more services/vulns are more important
            vulns = item.get("vulnerabilities", [])
            services = item.get("ports", item.get("services", {}))
            service_count = len(services) if isinstance(services, (dict, list)) else 0
            score += min(0.3, len(vulns) * 0.1)
            score += min(0.2, service_count * 0.05)

        elif category == "vulnerabilities":
            # Higher CVSS = more important
            cvss = item.get("cvss_score", item.get("severity", 0))
            if isinstance(cvss, (int, float)):
                score += min(0.5, cvss / 10.0)
            severity = item.get("severity", "")
            if severity in ("critical", "high"):
                score += 0.3

        elif category == "credentials":
            # Admin/root credentials are most important
            username = item.get("username", item.get("user", ""))
            if isinstance(username, str):
                if any(admin in username.lower() for admin in ["admin", "root", "system"]):
                    score += 0.4
            privilege = item.get("privilege", "")
            if privilege in ("root", "admin", "system"):
                score += 0.3

        elif category == "services":
            # Critical services are more important
            critical_services = {"ssh", "rdp", "smb", "ldap", "kerberos", "dns"}
            service_name = str(item.get("service", item.get("name", ""))).lower()
            if any(cs in service_name for cs in critical_services):
                score += 0.3

        elif category == "attack_history":
            # Successful attacks and high-reward actions are more important
            if item.get("success", item.get("result") == "success"):
                score += 0.3
            reward = item.get("reward", 0)
            if isinstance(reward, (int, float)) and reward > 0:
                score += min(0.2, reward / 10.0)

        elif category == "lessons":
            # Lessons with more occurrences are more important
            occurrences = item.get("occurrences", 1) if isinstance(item, dict) else 1
            score += min(0.3, occurrences * 0.1)

        elif category == "decisions":
            # Recent and high-consensus decisions are more important
            consensus = item.get("votes", item.get("consensus", 0))
            if isinstance(consensus, (int, float)):
                score += min(0.3, consensus * 0.1)

        return min(1.0, score)

    def _prune_list(self, items: List, category: str, max_size: int) -> List:
        """
        Prune a list to max_size, keeping the most important items.

        Preserves recently added items even if lower importance.
        """
        if len(items) <= max_size:
            return items

        # Always keep the most recent 20% of items
        recent_count = max(1, int(max_size * 0.2))
        recent = items[-recent_count:]

        # Score remaining items
        older = items[:-recent_count]
        scored = [(self._calculate_importance(item, category), item) for item in older]

        # Sort by importance (descending) and keep top
        scored.sort(key=lambda x: x[0], reverse=True)
        keep_count = max_size - recent_count
        kept = [item for _, item in scored[:keep_count]]

        pruned = len(older) - keep_count
        if pruned > 0:
            logger.debug(f"Pruned {pruned} low-importance items from {category}")

        return kept + recent

    def update_from_state(self, state: dict) -> None:
        """Update memory from current state with importance filtering."""
        if state.get("hosts"):
            for host in state["hosts"]:
                if host not in self.discovered_hosts:
                    self.discovered_hosts.append(host)
            self.discovered_hosts = self._prune_list(
                self.discovered_hosts, "hosts", self.MAX_HOSTS
            )

        if state.get("services"):
            for service in state["services"]:
                if service not in self.discovered_services:
                    self.discovered_services.append(service)
            self.discovered_services = self._prune_list(
                self.discovered_services, "services", self.MAX_SERVICES
            )

        if state.get("vulnerabilities"):
            for vuln in state["vulnerabilities"]:
                if vuln not in self.discovered_vulnerabilities:
                    self.discovered_vulnerabilities.append(vuln)
            self.discovered_vulnerabilities = self._prune_list(
                self.discovered_vulnerabilities, "vulnerabilities", self.MAX_VULNERABILITIES
            )

        if state.get("credentials"):
            for cred in state["credentials"]:
                if cred not in self.obtained_credentials:
                    self.obtained_credentials.append(cred)
            self.obtained_credentials = self._prune_list(
                self.obtained_credentials, "credentials", self.MAX_CREDENTIALS
            )

        if state.get("compromised_hosts"):
            for host in state["compromised_hosts"]:
                if host not in self.compromised_hosts:
                    self.compromised_hosts.append(host)

    def add_attack_record(self, record: dict) -> None:
        """Add an attack history record with importance-based pruning."""
        self.attack_history.append(record)
        self.attack_history = self._prune_list(
            self.attack_history, "attack_history", self.MAX_ATTACK_HISTORY
        )

    def add_lesson(self, lesson: str) -> None:
        """Add a lesson with deduplication and importance-based pruning."""
        if lesson not in self.lessons:
            self.lessons.append(lesson)
            self.lessons = self._prune_list(
                self.lessons, "lessons", self.MAX_LESSONS
            )

    def add_decision(self, decision: dict) -> None:
        """Add a team decision with importance-based pruning."""
        self.decisions.append(decision)
        self.decisions = self._prune_list(
            self.decisions, "decisions", self.MAX_DECISIONS
        )

    def get_memory_stats(self) -> dict:
        """Get memory usage statistics."""
        return {
            "hosts": f"{len(self.discovered_hosts)}/{self.MAX_HOSTS}",
            "services": f"{len(self.discovered_services)}/{self.MAX_SERVICES}",
            "vulnerabilities": f"{len(self.discovered_vulnerabilities)}/{self.MAX_VULNERABILITIES}",
            "credentials": f"{len(self.obtained_credentials)}/{self.MAX_CREDENTIALS}",
            "attack_history": f"{len(self.attack_history)}/{self.MAX_ATTACK_HISTORY}",
            "lessons": f"{len(self.lessons)}/{self.MAX_LESSONS}",
            "decisions": f"{len(self.decisions)}/{self.MAX_DECISIONS}",
            "compromised_hosts": len(self.compromised_hosts),
        }

    def to_dict(self) -> dict:
        return {
            "discovered_hosts": self.discovered_hosts,
            "discovered_services": self.discovered_services,
            "discovered_vulnerabilities": self.discovered_vulnerabilities,
            "obtained_credentials": self.obtained_credentials,
            "compromised_hosts": self.compromised_hosts,
            "attack_history": self.attack_history,
            "lessons": self.lessons,
            "decisions": self.decisions,
        }


@dataclass
class MeetingResult:
    """Result of a team meeting."""
    meeting_type: MeetingType
    participants: List[str]
    discussion: str
    decisions: List[dict]
    action_plan: List[dict]
    consensus_level: float
    timestamp: float = field(default_factory=time.time)


class AttackTeam:
    """
    A coordinated team of penetration testing experts.

    The team works together to:
    - Analyze target environments
    - Plan attack strategies
    - Execute coordinated attacks
    - Share knowledge and findings
    - Learn from successes and failures
    """

    # Default team configuration
    DEFAULT_TEAM = [
        {"role": TeamRole.LEADER, "expert_type": ExpertType.VULNERABILITY, "name": "Commander"},
        {"role": TeamRole.RECON, "expert_type": ExpertType.RECONNAISSANCE, "name": "Scout"},
        {"role": TeamRole.VULN_ANALYST, "expert_type": ExpertType.VULNERABILITY, "name": "Analyst"},
        {"role": TeamRole.EXPLOITER, "expert_type": ExpertType.EXPLOITATION, "name": "Striker"},
        {"role": TeamRole.POST_EX, "expert_type": ExpertType.POST_EXPLOITATION, "name": "Ghost"},
        {"role": TeamRole.CRED_HUNTER, "expert_type": ExpertType.CREDENTIAL, "name": "Hunter"},
        {"role": TeamRole.MOVER, "expert_type": ExpertType.LATERAL_MOVEMENT, "name": "Phantom"},
    ]

    def __init__(
        self,
        llm_provider=None,
        rag_retriever=None,
        team_config: List[dict] = None,
    ):
        self.llm = llm_provider
        self.rag = rag_retriever
        self.router = ExpertRouter(llm_provider, rag_retriever)

        # Team members
        self.members: Dict[str, TeamMember] = {}
        self.expert_instances: Dict[str, Any] = {}

        # Shared memory
        self.memory = TeamMemory()

        # Task tracking
        self.tasks: Dict[str, TeamTask] = {}
        self.task_counter = 0

        # Meeting history
        self.meetings: List[MeetingResult] = []

        # Initialize team
        self._init_team(team_config or self.DEFAULT_TEAM)

    def _init_team(self, config: List[dict]) -> None:
        """Initialize team members from configuration."""
        from models.experts import (
            ReconnaissanceExpert,
            VulnerabilityExpert,
            ExploitationExpert,
            PostExploitationExpert,
            CredentialExpert,
            LateralMovementExpert,
        )

        expert_classes = {
            ExpertType.RECONNAISSANCE: ReconnaissanceExpert,
            ExpertType.VULNERABILITY: VulnerabilityExpert,
            ExpertType.EXPLOITATION: ExploitationExpert,
            ExpertType.POST_EXPLOITATION: PostExploitationExpert,
            ExpertType.CREDENTIAL: CredentialExpert,
            ExpertType.LATERAL_MOVEMENT: LateralMovementExpert,
        }

        for member_config in config:
            role = member_config["role"]
            expert_type = member_config["expert_type"]
            name = member_config["name"]

            # Create member
            member = TeamMember(
                name=name,
                role=role,
                expert_type=expert_type,
                expertise=self._get_expertise(expert_type),
            )
            self.members[name] = member

            # Create expert instance
            expert_class = expert_classes.get(expert_type)
            if expert_class:
                expert = expert_class(self.llm, self.rag)
                self.expert_instances[name] = expert
                self.router.register_expert(expert)

        logger.info(f"Initialized attack team with {len(self.members)} members")

    def _get_expertise(self, expert_type: ExpertType) -> List[str]:
        """Get expertise description for an expert type."""
        expertise_map = {
            ExpertType.RECONNAISSANCE: ["scanning", "enumeration", "osint", "network_mapping"],
            ExpertType.VULNERABILITY: ["vulnerability_analysis", "cve_research", "risk_assessment"],
            ExpertType.EXPLOITATION: ["exploit_development", "payload_generation", "bypass_techniques"],
            ExpertType.POST_EXPLOITATION: ["privilege_escalation", "persistence", "data_exfiltration"],
            ExpertType.CREDENTIAL: ["password_cracking", "hash_attack", "credential_harvesting"],
            ExpertType.LATERAL_MOVEMENT: ["network_pivoting", "remote_execution", "session_hijacking"],
        }
        return expertise_map.get(expert_type, [])

    def hold_meeting(
        self,
        meeting_type: MeetingType,
        state: dict,
        context: dict = None,
        specific_question: str = None,
    ) -> MeetingResult:
        """
        Hold a team meeting to discuss situation and make decisions.

        Args:
            meeting_type: Type of meeting
            state: Current penetration test state
            context: Additional context
            specific_question: Optional specific question to discuss

        Returns:
            MeetingResult with decisions and action plan
        """
        # Update memory
        self.memory.update_from_state(state)

        # Determine participants based on meeting type
        participants = self._select_participants(meeting_type, state)

        # Collect input from each participant
        inputs = {}
        for name in participants:
            member = self.members.get(name)
            expert = self.expert_instances.get(name)

            if member and expert:
                try:
                    advice = expert.analyze(state, context)
                    inputs[name] = {
                        "role": member.role.value,
                        "advice": advice,
                        "confidence": advice.confidence,
                    }
                except Exception as e:
                    logger.warning(f"Expert {name} failed to provide input: {e}")

        # Synthesize discussion
        discussion = self._synthesize_discussion(inputs, meeting_type, state, specific_question)

        # Make decisions
        decisions = self._make_decisions(inputs, meeting_type, state)

        # Create action plan
        action_plan = self._create_action_plan(inputs, decisions)

        # Calculate consensus level
        consensus_level = self._calculate_consensus(inputs)

        # Record meeting
        result = MeetingResult(
            meeting_type=meeting_type,
            participants=participants,
            discussion=discussion,
            decisions=decisions,
            action_plan=action_plan,
            consensus_level=consensus_level,
        )
        self.meetings.append(result)

        # Record decisions in memory (using importance-filtered method)
        for decision in decisions:
            self.memory.add_decision(decision)

        return result

    def _assess_complexity(self, state: dict) -> str:
        """
        Assess target complexity based on state indicators.

        Returns:
            "simple", "medium", or "complex"
        """
        score = 0

        hosts = state.get("hosts", [])
        services = state.get("services", [])
        vulns = state.get("vulnerabilities", [])
        compromised = state.get("compromised_hosts", [])
        credentials = state.get("credentials", [])

        # Host count contributes to complexity
        host_count = len(hosts) if isinstance(hosts, list) else len(str(hosts))
        if host_count > 5:
            score += 3
        elif host_count > 2:
            score += 2
        elif host_count > 0:
            score += 1

        # Service diversity
        service_count = len(services) if isinstance(services, list) else len(str(services))
        if service_count > 10:
            score += 2
        elif service_count > 3:
            score += 1

        # Vulnerability count
        vuln_count = len(vulns) if isinstance(vulns, list) else len(str(vulns))
        if vuln_count > 5:
            score += 2
        elif vuln_count > 0:
            score += 1

        # Network topology complexity (multiple compromised hosts = pivot chains)
        if len(compromised) > 2:
            score += 2
        elif len(compromised) > 0:
            score += 1

        # Credential types available
        cred_count = len(credentials) if isinstance(credentials, list) else len(str(credentials))
        if cred_count > 3:
            score += 1

        # Domain environment detection
        if state.get("in_domain"):
            score += 2

        # Multi-stage attack required
        if state.get("has_shell") and not state.get("is_admin"):
            score += 1

        # Classify
        if score >= 8:
            return "complex"
        elif score >= 4:
            return "medium"
        else:
            return "simple"

    def _select_participants(self, meeting_type: MeetingType, state: dict) -> List[str]:
        """
        Select appropriate participants for a meeting.

        Uses complexity-adaptive selection:
        - simple: Commander + 1-2 relevant experts (fast decisions)
        - medium: Commander + 3-4 relevant experts (balanced)
        - complex: Full team (comprehensive analysis)
        """
        complexity = self._assess_complexity(state)
        phase = state.get("phase", "").lower()

        # Leader always participates
        participants = ["Commander"]

        # === Emergency & Debrief: always full team ===
        if meeting_type == MeetingType.EMERGENCY:
            return list(self.members.keys())

        if meeting_type == MeetingType.DEBRIEF:
            # Debrief: include experts who were active
            if state.get("compromised_hosts"):
                participants.extend(["Ghost", "Phantom"])
            if state.get("credentials"):
                participants.append("Hunter")
            if state.get("vulnerabilities"):
                participants.extend(["Analyst", "Striker"])
            if len(participants) == 1:
                return list(self.members.keys())
            return list(set(participants))

        # === Briefing: scale by complexity ===
        if meeting_type == MeetingType.BRIEFING:
            if complexity == "simple":
                # Simple target: Commander + Scout + Analyst
                participants.extend(["Scout", "Analyst"])
            elif complexity == "medium":
                # Medium target: Commander + phase-relevant + supporting
                participants.extend(["Scout", "Analyst", "Striker"])
            else:
                # Complex target: full team briefing
                return list(self.members.keys())
            return list(set(participants))

        # === Planning & Review: phase-based with complexity scaling ===
        phase_experts = {
            "reconnaissance": ["Scout", "Analyst"],
            "scanning": ["Scout", "Analyst"],
            "exploitation": ["Striker", "Analyst"],
            "post_exploitation": ["Ghost", "Hunter"],
            "lateral_movement": ["Phantom", "Hunter"],
            "privilege_escalation": ["Ghost", "Analyst"],
            "credential_attacks": ["Hunter", "Ghost"],
        }

        base_experts = phase_experts.get(phase, ["Scout"])

        if complexity == "simple":
            # Simple: Commander + 1 primary expert
            participants.append(base_experts[0])
        elif complexity == "medium":
            # Medium: Commander + primary + 1 supporting
            participants.extend(base_experts[:2])
            # Add context-aware support
            if state.get("vulnerabilities") and "Analyst" not in participants:
                participants.append("Analyst")
            if state.get("credentials") and "Hunter" not in participants:
                participants.append("Hunter")
        else:
            # Complex: Commander + all phase experts + supporting
            participants.extend(base_experts)

            if meeting_type == MeetingType.REVIEW:
                # Review adds extra context experts
                if state.get("vulnerabilities"):
                    participants.append("Analyst")
                if state.get("credentials"):
                    participants.append("Hunter")
                if state.get("compromised_hosts"):
                    participants.append("Ghost")
            else:
                # Planning adds cross-domain experts
                if "Scout" not in participants:
                    participants.append("Scout")
                if "Striker" not in participants:
                    participants.append("Striker")

        return list(set(participants))

    def _synthesize_discussion(
        self,
        inputs: Dict[str, dict],
        meeting_type: MeetingType,
        state: dict,
        specific_question: str = None,
    ) -> str:
        """Synthesize team discussion into a summary."""
        if not inputs:
            return "No expert input available."

        discussion_parts = [f"=== 团队会议: {meeting_type.value} ===\n"]

        if specific_question:
            discussion_parts.append(f"讨论议题: {specific_question}\n")

        discussion_parts.append("\n各专家意见:\n")

        for name, data in inputs.items():
            role = data["role"]
            advice = data["advice"]
            confidence = data["confidence"]

            discussion_parts.append(f"\n[{name}] ({role}):\n")
            discussion_parts.append(f"  总结: {advice.summary}\n")
            discussion_parts.append(f"  置信度: {confidence:.2f}\n")

            if advice.tools_to_use:
                discussion_parts.append(f"  建议工具: {', '.join(advice.tools_to_use)}\n")

            if advice.warnings:
                discussion_parts.append(f"  警告: {'; '.join(advice.warnings)}\n")

        # LLM synthesis if available
        if self.llm and len(inputs) > 1:
            synthesis = self._get_llm_synthesis(inputs, state, specific_question)
            if synthesis:
                discussion_parts.append(f"\n=== 综合分析 ===\n{synthesis}\n")

        return "".join(discussion_parts)

    def _get_llm_synthesis(self, inputs: Dict[str, dict], state: dict, question: str = None) -> str:
        """Get LLM synthesis of team opinions."""
        try:
            # Build prompt
            prompt = """作为渗透测试团队协调员，请综合以下专家意见并给出建议。

专家意见:
"""
            for name, data in inputs.items():
                advice = data["advice"]
                prompt += f"\n{name} ({data['role']}):\n"
                prompt += f"- 总结: {advice.summary}\n"
                prompt += f"- 推荐行动数: {len(advice.recommended_actions)}\n"
                prompt += f"- 置信度: {data['confidence']:.2f}\n"

            if question:
                prompt += f"\n具体问题: {question}\n"

            prompt += "\n请给出综合建议（200字以内）:"

            response = self.llm.call([{"role": "user", "content": prompt}])
            if response is None:
                logger.warning("LLM synthesis returned None")
                return ""
            content = getattr(response, 'content', None)
            if content is None:
                logger.warning("LLM response has no content attribute")
                return ""
            return content[:500]

        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}")
            return ""

    def _make_decisions(
        self,
        inputs: Dict[str, dict],
        meeting_type: MeetingType,
        state: dict,
    ) -> List[dict]:
        """Make team decisions based on expert inputs."""
        decisions = []

        if not inputs:
            return decisions

        # Aggregate recommended actions
        action_votes: Dict[str, int] = defaultdict(int)
        action_details: Dict[str, dict] = {}

        for name, data in inputs.items():
            advice = data["advice"]
            for action in advice.recommended_actions[:3]:  # Top 3 per expert
                action_key = f"{action.get('type', 'unknown')}:{action.get('tool', '')}"
                action_votes[action_key] += 1
                if action_key not in action_details:
                    action_details[action_key] = action
                    action_details[action_key]["supporters"] = []
                action_details[action_key]["supporters"].append(name)

        # Select actions with most votes
        sorted_actions = sorted(action_votes.items(), key=lambda x: x[1], reverse=True)

        for action_key, votes in sorted_actions[:5]:  # Top 5 actions
            action = action_details[action_key]
            decisions.append({
                "action": action_key,
                "type": action.get("type"),
                "tool": action.get("tool"),
                "description": action.get("description", ""),
                "supporters": action["supporters"],
                "votes": votes,
                "params": action.get("params", {}),
                "priority": 5 - sorted_actions.index((action_key, votes)),  # Higher priority for more votes
            })

        # Record high-priority decision
        if decisions:
            self.memory.add_decision({
                "meeting_type": meeting_type.value,
                "top_decision": decisions[0]["action"],
                "votes": decisions[0]["votes"],
                "timestamp": time.time(),
            })

        return decisions

    def _create_action_plan(self, inputs: Dict[str, dict], decisions: List[dict]) -> List[dict]:
        """Create a prioritized action plan."""
        action_plan = []

        for decision in decisions:
            action_plan.append({
                "action": decision["action"],
                "type": decision.get("type"),
                "tool": decision.get("tool"),
                "description": decision.get("description"),
                "params": decision.get("params", {}),
                "priority": decision.get("priority", 1),
                "assigned_to": decision.get("supporters", ["Unknown"])[0],
            })

        return action_plan

    def _calculate_consensus(self, inputs: Dict[str, dict]) -> float:
        """
        Calculate consensus level among team members using weighted consensus.

        Considers:
        1. Tool overlap (Jaccard similarity)
        2. Semantic similarity of tools (same category = partial match)
        3. Expert confidence weights
        4. Action type alignment

        Returns:
            Consensus level between 0.0 and 1.0
        """
        if len(inputs) <= 1:
            return 1.0

        # Extract tools and actions from each expert
        expert_data = []
        for name, data in inputs.items():
            advice = data["advice"]
            confidence = data.get("confidence", 0.5)
            tools = set(advice.tools_to_use) if advice.tools_to_use else set()
            action_types = set(
                a.get("type", "").lower()
                for a in advice.recommended_actions
            ) if advice.recommended_actions else set()
            expert_data.append({
                "name": name,
                "tools": tools,
                "action_types": action_types,
                "confidence": confidence,
            })

        if not expert_data or all(not e["tools"] and not e["action_types"] for e in expert_data):
            return 0.5

        # Tool category mapping for semantic similarity
        tool_categories = {
            # Reconnaissance tools
            "scan": {"nmap", "masscan", "rustscan", "zmap", "unicornscan"},
            "vuln_scan": {"nikto", "nuclei", "openvas", "nessus", "wpscan", "joomscan"},
            "osint": {"theharvester", "shodan", "censys", "maltego", "spiderfoot"},
            "dns": {"dnsrecon", "dnsenum", "fierce", "sublist3r"},
            # Exploitation tools
            "exploit": {"metasploit", "msfvenom", "searchsploit", "exploitdb"},
            "web_exploit": {"sqlmap", "burpsuite", "gobuster", "dirb", "ffuf"},
            # Credential tools
            "brute_force": {"hydra", "medusa", "ncrack", "patator"},
            "crack": {"hashcat", "john", "ophcrack", "rainbowcrack"},
            "hash_dump": {"mimikatz", "secretsdump", "pwdump", "fgdump", "samdump2"},
            # Post-exploitation tools
            "priv_esc": {"winpeas", "linpeas", "seatbelt", "sharpup", "pspy"},
            "lateral": {"crackmapexec", "psexec", "wmiexec", "evil-winrm", "impacket"},
            "persist": {"sharppersist", "empire", "covenant"},
            # Data exfil
            "exfil": {"rclone", "dns-exfil", "icmp-exfil"},
        }

        def get_tool_category(tool: str) -> Optional[str]:
            """Get category for a tool."""
            tool_lower = tool.lower()
            for category, tools in tool_categories.items():
                if any(t in tool_lower for t in tools):
                    return category
            return None

        def semantic_similarity(tool1: str, tool2: str) -> float:
            """Calculate semantic similarity between two tools."""
            if tool1.lower() == tool2.lower():
                return 1.0

            cat1 = get_tool_category(tool1)
            cat2 = get_tool_category(tool2)

            if cat1 and cat2 and cat1 == cat2:
                return 0.7  # Same category = high similarity

            # Related categories
            related = {
                ("scan", "vuln_scan"): 0.5,
                ("brute_force", "crack"): 0.5,
                ("exploit", "web_exploit"): 0.5,
                ("lateral", "hash_dump"): 0.3,
            }
            if cat1 and cat2:
                pair = (cat1, cat2) if (cat1, cat2) in related else (cat2, cat1)
                if pair in related:
                    return related[pair]

            return 0.0

        # Calculate pairwise weighted consensus
        similarities = []

        for i, expert_i in enumerate(expert_data):
            for expert_j in expert_data[i+1:]:
                # Tool similarity (semantic-aware)
                tools_i = expert_i["tools"]
                tools_j = expert_j["tools"]

                if tools_i and tools_j:
                    # Calculate semantic similarity matrix
                    tool_similarities = []
                    for t1 in tools_i:
                        max_sim = max(
                            (semantic_similarity(t1, t2) for t2 in tools_j),
                            default=0.0
                        )
                        tool_similarities.append(max_sim)

                    tool_consensus = sum(tool_similarities) / len(tool_similarities)
                else:
                    tool_consensus = 0.5  # No tools = neutral

                # Action type similarity
                actions_i = expert_i["action_types"]
                actions_j = expert_j["action_types"]

                if actions_i and actions_j:
                    action_intersection = len(actions_i & actions_j)
                    action_union = len(actions_i | actions_j)
                    action_consensus = action_intersection / action_union if action_union > 0 else 0.5
                else:
                    action_consensus = 0.5

                # Confidence-weighted pair consensus
                weight_i = expert_i["confidence"]
                weight_j = expert_j["confidence"]
                avg_weight = (weight_i + weight_j) / 2

                pair_consensus = (
                    0.6 * tool_consensus +  # Tools matter more
                    0.4 * action_consensus
                ) * avg_weight  # Weight by confidence

                similarities.append(pair_consensus)

        # Overall consensus
        if not similarities:
            return 0.5

        raw_consensus = sum(similarities) / len(similarities)

        # Apply boost for high agreement
        if raw_consensus > 0.7:
            raw_consensus = min(1.0, raw_consensus * 1.1)

        return raw_consensus

    def assign_task(self, description: str, assigned_to: str, priority: int = 1) -> TeamTask:
        """Assign a task to a team member."""
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"

        task = TeamTask(
            task_id=task_id,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
        )
        self.tasks[task_id] = task

        logger.info(f"Task {task_id} assigned to {assigned_to}: {description}")
        return task

    def complete_task(self, task_id: str, result: Any, success: bool = True) -> None:
        """Mark a task as completed."""
        task = self.tasks.get(task_id)
        if task:
            task.status = "completed" if success else "failed"
            task.result = result
            task.completed_at = time.time()

            # Update member stats
            member = self.members.get(task.assigned_to)
            if member:
                member.tasks_completed += 1
                if success:
                    member.success_rate = (
                        (member.success_rate * (member.tasks_completed - 1) + 1.0)
                        / member.tasks_completed
                    )
                else:
                    member.success_rate = (
                        (member.success_rate * (member.tasks_completed - 1))
                        / member.tasks_completed
                    )

            # Record in memory using importance-filtered method
            self.memory.add_attack_record({
                "task_id": task_id,
                "description": task.description,
                "assigned_to": task.assigned_to,
                "success": success,
                "result": result,
            })

    def get_pending_tasks(self) -> List[TeamTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks.values() if t.status == "pending"]

    def get_next_action(self, state: dict) -> Optional[dict]:
        """
        Get the next recommended action based on team consensus.

        Args:
            state: Current state

        Returns:
            Recommended action dict or None
        """
        # Hold a quick planning meeting
        result = self.hold_meeting(MeetingType.PLANNING, state)

        if result.action_plan:
            return result.action_plan[0]

        return None

    def brief_team(self, target: str, initial_info: dict = None) -> MeetingResult:
        """
        Brief the team on a new target.

        Args:
            target: Target identifier
            initial_info: Any initial reconnaissance data

        Returns:
            MeetingResult with initial plan
        """
        state = {
            "target": target,
            "phase": "reconnaissance",
            **(initial_info or {}),
        }

        return self.hold_meeting(MeetingType.BRIEFING, state)

    def debrief(self, state: dict, outcomes: List[dict]) -> MeetingResult:
        """
        Debrief the team after an operation.

        Args:
            state: Final state
            outcomes: List of action outcomes

        Returns:
            MeetingResult with lessons learned
        """
        # Extract lessons from outcomes
        lessons = []
        for outcome in outcomes:
            if outcome.get("success"):
                lessons.append(f"成功: {outcome.get('action', 'unknown')} - {outcome.get('reason', '')}")
            else:
                lessons.append(f"失败: {outcome.get('action', 'unknown')} - {outcome.get('error', '')}")

        for lesson in lessons:
            self.memory.add_lesson(lesson)

        return self.hold_meeting(MeetingType.DEBRIEF, state)

    def emergency_consult(self, state: dict, problem: str) -> MeetingResult:
        """
        Emergency consultation when something goes wrong.

        Args:
            state: Current state
            problem: Description of the problem

        Returns:
            MeetingResult with recommendations
        """
        return self.hold_meeting(
            MeetingType.EMERGENCY,
            state,
            specific_question=problem,
        )

    def get_team_status(self) -> dict:
        """Get current team status."""
        return {
            "members": {
                name: {
                    "role": member.role.value,
                    "confidence": member.confidence,
                    "tasks_completed": member.tasks_completed,
                    "success_rate": member.success_rate,
                }
                for name, member in self.members.items()
            },
            "memory_summary": {
                "hosts_discovered": len(self.memory.discovered_hosts),
                "vulnerabilities_found": len(self.memory.discovered_vulnerabilities),
                "credentials_obtained": len(self.memory.obtained_credentials),
                "hosts_compromised": len(self.memory.compromised_hosts),
                "lessons_learned": len(self.memory.lessons),
            },
            "pending_tasks": len(self.get_pending_tasks()),
            "meetings_held": len(self.meetings),
        }


def create_attack_team(llm_provider=None, rag_retriever=None) -> AttackTeam:
    """Create an attack team with default configuration."""
    return AttackTeam(llm_provider=llm_provider, rag_retriever=rag_retriever)
