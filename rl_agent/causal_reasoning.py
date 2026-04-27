"""
Causal Reasoning and Post-Mortem Analysis System

Enables the AI to reason about causal relationships in penetration testing:
- Why did an exploit succeed or fail?
- What chain of decisions led to compromise?
- Root cause analysis after failures
- Structured post-mortems after sessions

Supports building causal graphs from action-result sequences, identifying
confounding factors, and generating counterfactual scenarios.
"""

import json
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class OutcomeType(Enum):
    """Classification of action outcomes."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ConfidenceLevel(Enum):
    """Confidence level for causal assessments."""
    HIGH = "high"      # 0.8 - 1.0
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # 0.0 - 0.5


@dataclass
class CausalLink:
    """
    Represents a cause-effect relationship between actions and outcomes.

    Attributes:
        cause: The action or condition that preceded the effect
        effect: The resulting state change
        strength: Causal strength from 0 (weak) to 1 (strong)
        evidence: List of supporting observations
        alternative_explanations: Other possible causes for the effect
        temporal_order: Position in the action sequence
        intermediate_steps: Any steps between cause and effect
    """
    cause: str
    effect: str
    strength: float = 0.5
    evidence: List[str] = field(default_factory=list)
    alternative_explanations: List[str] = field(default_factory=list)
    temporal_order: int = 0
    intermediate_steps: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and clamp strength value."""
        self.strength = max(0.0, min(1.0, self.strength))

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level based on strength."""
        if self.strength >= 0.8:
            return ConfidenceLevel.HIGH
        elif self.strength >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "cause": self.cause,
            "effect": self.effect,
            "strength": self.strength,
            "evidence": self.evidence,
            "alternative_explanations": self.alternative_explanations,
            "temporal_order": self.temporal_order,
            "intermediate_steps": self.intermediate_steps,
            "confidence_level": self.confidence_level.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CausalLink':
        """Deserialize from dictionary."""
        return cls(
            cause=data["cause"],
            effect=data["effect"],
            strength=data.get("strength", 0.5),
            evidence=data.get("evidence", []),
            alternative_explanations=data.get("alternative_explanations", []),
            temporal_order=data.get("temporal_order", 0),
            intermediate_steps=data.get("intermediate_steps", []),
        )


@dataclass
class CausalChain:
    """
    A sequence of linked causes representing a causal pathway.

    Tracks how a series of actions led to an outcome, including:
    - The chain of causal links
    - Overall confidence in the chain
    - Whether this chain was critical to success
    """
    links: List[CausalLink] = field(default_factory=list)
    overall_confidence: float = 0.0
    critical_path: bool = False
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    outcome: OutcomeType = OutcomeType.UNKNOWN
    description: str = ""

    def __post_init__(self) -> None:
        """Calculate overall confidence if not set."""
        if not self.links:
            return
        if self.overall_confidence == 0.0 and self.links:
            # Use geometric mean of link strengths
            product = 1.0
            for link in self.links:
                product *= max(0.01, link.strength)
            self.overall_confidence = product ** (1.0 / len(self.links))

    @property
    def strength(self) -> float:
        """Get the weakest link strength (bottleneck)."""
        if not self.links:
            return 0.0
        return min(link.strength for link in self.links)

    @property
    def critical_links(self) -> List[int]:
        """Get indices of links with low strength (potential failure points)."""
        return [
            i for i, link in enumerate(self.links)
            if link.strength < 0.5
        ]

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "links": [link.to_dict() for link in self.links],
            "overall_confidence": self.overall_confidence,
            "critical_path": self.critical_path,
            "chain_id": self.chain_id,
            "outcome": self.outcome.value,
            "description": self.description,
            "weakest_link": self.strength,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CausalChain':
        """Deserialize from dictionary."""
        outcome = OutcomeType(data.get("outcome", "unknown"))
        chain = cls(
            links=[CausalLink.from_dict(l) for l in data.get("links", [])],
            overall_confidence=data.get("overall_confidence", 0.0),
            critical_path=data.get("critical_path", False),
            chain_id=data.get("chain_id", str(uuid.uuid4())[:8]),
            outcome=outcome,
            description=data.get("description", ""),
        )
        return chain

    def add_link(self, link: CausalLink) -> None:
        """Add a link and recalculate confidence."""
        self.links.append(link)
        # Recalculate overall confidence
        product = 1.0
        for l in self.links:
            product *= max(0.01, l.strength)
        self.overall_confidence = product ** (1.0 / len(self.links))


@dataclass
class KeyDecision:
    """Record of a significant decision point."""
    decision: str
    rationale: str
    outcome: str
    alternatives_considered: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'KeyDecision':
        return cls(**data)


@dataclass
class PostMortemEntry:
    """
    Structured post-mortem record for a penetration testing session.

    Contains comprehensive analysis of:
    - Session metadata and outcome
    - Causal chains leading to success/failure
    - Key decision points and their rationale
    - Identified failure modes
    - Root cause analysis
    - Recommendations for improvement
    """
    session_id: str
    timestamp: float = field(default_factory=time.time)
    objective: str = ""
    outcome: str = "unknown"  # success/failure/partial
    causal_chains: List[CausalChain] = field(default_factory=list)
    key_decisions: List[KeyDecision] = field(default_factory=list)
    failure_modes: List[str] = field(default_factory=list)
    root_cause: str = ""
    recommendations: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    actions_taken: int = 0
    targets_compromised: int = 0
    objectives_achieved: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if the overall outcome was successful."""
        return self.outcome == "success"

    @property
    def partial_success(self) -> bool:
        """Check if the outcome was partial success."""
        return self.outcome == "partial"

    @property
    def failure(self) -> bool:
        """Check if the outcome was a failure."""
        return self.outcome == "failure"

    @property
    def critical_chain(self) -> Optional[CausalChain]:
        """Get the critical path chain if any."""
        for chain in self.causal_chains:
            if chain.critical_path:
                return chain
        return None

    @property
    def summary(self) -> str:
        """Get a one-line summary of the post-mortem."""
        return (
            f"Session {self.session_id}: {self.outcome.upper()} - "
            f"{self.root_cause[:100] if self.root_cause else 'No root cause identified'}"
        )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "timestamp_readable": datetime.fromtimestamp(self.timestamp).isoformat(),
            "objective": self.objective,
            "outcome": self.outcome,
            "causal_chains": [chain.to_dict() for chain in self.causal_chains],
            "key_decisions": [d.to_dict() for d in self.key_decisions],
            "failure_modes": self.failure_modes,
            "root_cause": self.root_cause,
            "recommendations": self.recommendations,
            "duration_seconds": self.duration_seconds,
            "actions_taken": self.actions_taken,
            "targets_compromised": self.targets_compromised,
            "objectives_achieved": self.objectives_achieved,
            "metadata": self.metadata,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PostMortemEntry':
        """Deserialize from dictionary."""
        return cls(
            session_id=data["session_id"],
            timestamp=data.get("timestamp", time.time()),
            objective=data.get("objective", ""),
            outcome=data.get("outcome", "unknown"),
            causal_chains=[
                CausalChain.from_dict(c) for c in data.get("causal_chains", [])
            ],
            key_decisions=[
                KeyDecision.from_dict(d) for d in data.get("key_decisions", [])
            ],
            failure_modes=data.get("failure_modes", []),
            root_cause=data.get("root_cause", ""),
            recommendations=data.get("recommendations", []),
            duration_seconds=data.get("duration_seconds", 0.0),
            actions_taken=data.get("actions_taken", 0),
            targets_compromised=data.get("targets_compromised", 0),
            objectives_achieved=data.get("objectives_achieved", []),
            metadata=data.get("metadata", {}),
        )


class CausalReasoner:
    """
    Analyzes causal relationships in penetration testing sessions.

    Capabilities:
    - Build causal graphs from action-result sequences
    - Identify root causes of failures
    - Detect confounding factors
    - Generate counterfactual scenarios
    - Produce structured post-mortems
    """

    def __init__(self, min_link_strength: float = 0.3):
        """
        Initialize the causal reasoner.

        Args:
            min_link_strength: Minimum strength for a causal link to be included
        """
        self.min_link_strength = min_link_strength
        self._causal_patterns: Dict[str, str] = self._init_causal_patterns()

    def _init_causal_patterns(self) -> Dict[str, str]:
        """Initialize known causal patterns for penetration testing."""
        return {
            # Reconnaissance patterns
            "port_scan": "service_discovery",
            "service_discovery": "vulnerability_identification",
            "vulnerability_scan": "vulnerability_identification",

            # Exploitation patterns
            "exploit_vuln": "initial_access",
            "initial_access": "credential_access",
            "credential_dump": "credential_access",

            # Movement patterns
            "lateral_move": "privilege_escalation",
            "pass_the_hash": "privilege_escalation",
            "privilege_escalation": "data_access",

            # Data access patterns
            "data_access": "data_exfiltration",
            "data_exfiltration": "mission_completion",

            # Failure patterns
            "authentication_failure": "exploitation_failure",
            "connection_timeout": "network_blocking",
            "exploitation_timeout": "exploitation_failure",
        }

    def build_causal_graph(
        self,
        actions: List[dict],
        results: List[dict],
    ) -> CausalChain:
        """
        Build a causal chain from action-result sequences.

        Args:
            actions: List of action dictionaries with 'type', 'target', 'parameters'
            results: List of result dictionaries with 'outcome', 'details', 'timestamp'

        Returns:
            CausalChain representing the causal pathway
        """
        if len(actions) != len(results):
            logger.warning(
                f"Action/result count mismatch: {len(actions)} actions vs {len(results)} results"
            )
            # Pad with empty results if needed
            while len(results) < len(actions):
                results.append({
                    "outcome": "unknown",
                    "details": "No result recorded",
                    "timestamp": time.time(),
                })

        chain = CausalChain()
        previous_outcome = None

        for i, (action, result) in enumerate(zip(actions, results)):
            action_type = action.get("type", "unknown")
            action_target = action.get("target", "")
            outcome = result.get("outcome", "unknown")
            details = result.get("details", "")

            # Determine causal link properties
            cause = self._format_action_cause(action_type, action_target, action)
            effect = self._format_result_effect(outcome, details, action_target)

            # Calculate strength based on outcome
            strength = self._calculate_link_strength(action, result)

            # Find alternative explanations
            alternatives = self._find_alternatives(action, result)

            # Get supporting evidence
            evidence = self._gather_evidence(action, result, previous_outcome)

            # Determine if this is part of a known causal pattern
            expected_effect = self._causal_patterns.get(action_type, "")

            link = CausalLink(
                cause=cause,
                effect=effect,
                strength=strength,
                evidence=evidence,
                alternative_explanations=alternatives,
                temporal_order=i,
            )

            # Add intermediate steps for multi-step exploits
            if expected_effect and expected_effect != effect:
                link.intermediate_steps.append(expected_effect)

            chain.add_link(link)
            previous_outcome = outcome

        # Determine overall outcome
        final_outcomes = [r.get("outcome", "unknown") for r in results]
        if all(o == "success" for o in final_outcomes):
            chain.outcome = OutcomeType.SUCCESS
        elif any(o == "success" for o in final_outcomes):
            chain.outcome = OutcomeType.PARTIAL
        else:
            chain.outcome = OutcomeType.FAILURE

        # Mark as critical path if this led to success
        chain.critical_path = chain.outcome == OutcomeType.SUCCESS

        # Generate description
        chain.description = self._generate_chain_description(chain)

        logger.info(
            f"Built causal chain with {len(chain.links)} links, "
            f"confidence: {chain.overall_confidence:.2f}"
        )

        return chain

    def _format_action_cause(
        self,
        action_type: str,
        target: str,
        action: dict,
    ) -> str:
        """Format an action as a cause string."""
        parts = [f"Action: {action_type}"]

        if target:
            parts.append(f"Target: {target}")

        params = action.get("parameters", {})
        if params:
            param_str = ", ".join(f"{k}={v}" for k, v in params.items())
            parts.append(f"Parameters: {param_str}")

        return "; ".join(parts)

    def _format_result_effect(
        self,
        outcome: str,
        details: str,
        target: str,
    ) -> str:
        """Format a result as an effect string."""
        parts = [f"Outcome: {outcome.upper()}"]

        if details:
            # Truncate long details
            detail_str = details[:200] + "..." if len(details) > 200 else details
            parts.append(f"Details: {detail_str}")

        if target:
            parts.append(f"On target: {target}")

        return "; ".join(parts)

    def _calculate_link_strength(
        self,
        action: dict,
        result: dict,
    ) -> float:
        """Calculate the strength of a causal link."""
        outcome = result.get("outcome", "unknown")

        # Base strength from outcome
        if outcome == "success":
            base_strength = 0.9
        elif outcome == "partial":
            base_strength = 0.5
        else:
            base_strength = 0.3

        # Adjust based on evidence quality
        details = result.get("details", "")
        evidence_count = len(result.get("evidence", []))

        if evidence_count >= 3:
            base_strength += 0.1
        elif evidence_count == 0 and not details:
            base_strength -= 0.2

        # Adjust based on action parameters
        params = action.get("parameters", {})
        if params.get("severity", 0) >= 9.0:
            base_strength += 0.05  # High severity exploits are stronger

        return max(0.0, min(1.0, base_strength))

    def _find_alternatives(
        self,
        action: dict,
        result: dict,
    ) -> List[str]:
        """Find alternative explanations for the result."""
        alternatives = []
        action_type = action.get("type", "")
        outcome = result.get("outcome", "")

        # Common alternative explanations based on action type
        alternative_templates = {
            "exploit_vuln": [
                "Vulnerability may have been patched",
                "Target may be using intrusion detection",
                "Exploit payload may have been filtered",
                "Network segmentation may have blocked lateral movement",
            ],
            "port_scan": [
                "Firewall may be blocking scan traffic",
                "Ports may have been filtered since last check",
                "IDS may be detecting and blocking scan",
            ],
            "brute_force": [
                "Account may be locked after attempts",
                "Password policy may be stronger than expected",
                "Rate limiting may be in effect",
            ],
            "phishing": [
                "Target may have security awareness training",
                "Email filter may have caught the payload",
                "Target may be using multi-factor authentication",
            ],
        }

        if action_type in alternative_templates:
            if outcome == "failure":
                alternatives = alternative_templates[action_type][:3]
            else:
                alternatives = alternative_templates[action_type][:1]

        return alternatives

    def _gather_evidence(
        self,
        action: dict,
        result: dict,
        previous_outcome: Optional[str],
    ) -> List[str]:
        """Gather evidence supporting the causal link."""
        evidence = []

        # Explicit evidence from result
        if result.get("evidence"):
            evidence.extend(result.get("evidence", []))

        # Evidence from output/targets affected
        if result.get("targets_affected"):
            evidence.append(
                f"Targets affected: {len(result['targets_affected'])}"
            )

        # Evidence from output/files created
        if result.get("files_created"):
            evidence.append(
                f"Files/directories accessed: {len(result['files_created'])}"
            )

        # Evidence from credentials found
        if result.get("credentials_found"):
            evidence.append(
                f"Credentials found: {len(result['credentials_found'])}"
            )

        # Sequential evidence
        if previous_outcome == "success":
            evidence.append("Built on previous successful action")

        return evidence

    def _generate_chain_description(self, chain: CausalChain) -> str:
        """Generate a human-readable description of the chain."""
        if not chain.links:
            return "No causal chain established"

        action_types = [link.cause.split(";")[0].replace("Action: ", "")
                       for link in chain.links]
        sequence = " -> ".join(action_types)

        outcome_str = chain.outcome.value.upper()
        return f"[{outcome_str}] {sequence}"

    def find_root_cause(
        self,
        failure_event: dict,
        causal_chain: CausalChain,
    ) -> str:
        """
        Find the root cause of a failure event.

        Args:
            failure_event: Dictionary describing the failure
            causal_chain: The causal chain leading to or including the failure

        Returns:
            String describing the identified root cause
        """
        failure_type = failure_event.get("type", "unknown")
        failure_details = failure_event.get("details", "")

        logger.info(f"Analyzing root cause for failure: {failure_type}")

        # Look for the weakest link in the causal chain
        weakest_link_idx = -1
        weakest_strength = 1.0

        for i, link in enumerate(causal_chain.links):
            if link.strength < weakest_strength:
                weakest_strength = link.strength
                weakest_link_idx = i

        # Build root cause explanation
        if weakest_link_idx >= 0:
            root_link = causal_chain.links[weakest_link_idx]

            root_cause_parts = [
                f"Root cause identified at step {weakest_link_idx + 1}:",
                f"Cause: {root_link.cause}",
                f"Effect: {root_link.effect}",
                f"Strength: {root_link.strength:.2f} ({root_link.confidence_level.value})",
            ]

            if root_link.alternative_explanations:
                root_cause_parts.append(
                    f"Alternative explanations: {'; '.join(root_link.alternative_explanations)}"
                )

            # Check for known failure patterns
            known_failures = self._check_known_failure_pattern(
                failure_type, causal_chain
            )
            if known_failures:
                root_cause_parts.append(f"Known failure pattern: {known_failures}")

            return "\n".join(root_cause_parts)

        # Fallback if no weak link found
        return (
            f"Root cause could not be precisely determined. "
            f"Failure type: {failure_type}. Details: {failure_details[:200]}"
        )

    def _check_known_failure_pattern(
        self,
        failure_type: str,
        causal_chain: CausalChain,
    ) -> Optional[str]:
        """Check if this matches a known failure pattern."""
        known_patterns = {
            "exploitation_failure": [
                "Missing prerequisite reconnaissance",
                "Incorrect exploit selection",
                "Target patching or mitigation",
            ],
            "authentication_failure": [
                "Weak credential guessing strategy",
                "Missing credential reuse from previous compromise",
                "Multi-factor authentication in use",
            ],
            "network_blocking": [
                "Insufficient network reconnaissance",
                "Firewall or IDS blocking traffic",
                "Network segmentation not accounted for",
            ],
            "privilege_escalation_failure": [
                "No obvious privilege escalation path",
                "Patch level too current for exploits",
                "AppLocker or similar controls in place",
            ],
        }

        if failure_type in known_patterns:
            # Check if any of our links mention these patterns
            for link in causal_chain.links:
                link_text = (link.cause + link.effect).lower()
                for pattern in known_patterns[failure_type]:
                    if any(word in link_text for word in pattern.split()[:2]):
                        return pattern

        return None

    def generate_postmortem(self, session_data: dict) -> PostMortemEntry:
        """
        Generate a structured post-mortem from session data.

        Args:
            session_data: Dictionary containing:
                - session_id: Session identifier
                - objective: What the session aimed to achieve
                - actions: List of actions taken
                - results: List of results
                - decisions: List of key decisions
                - start_time: Session start timestamp
                - end_time: Session end timestamp

        Returns:
            PostMortemEntry with full analysis
        """
        session_id = session_data.get("session_id", str(uuid.uuid4())[:8])
        logger.info(f"Generating post-mortem for session {session_id}")

        # Extract data with defaults
        actions = session_data.get("actions", [])
        results = session_data.get("results", [])
        decisions = session_data.get("decisions", [])
        objective = session_data.get("objective", "")
        start_time = session_data.get("start_time", time.time())
        end_time = session_data.get("end_time", time.time())

        # Build causal chains
        causal_chains = []

        # Main causal chain from all actions
        main_chain = self.build_causal_graph(actions, results)
        main_chain.critical_path = True
        causal_chains.append(main_chain)

        # Check for failure chains
        failures = [
            (i, r) for i, r in enumerate(results)
            if r.get("outcome") in ("failure", "unknown")
        ]

        if failures:
            # Build failure-specific chains
            failure_chain = self._build_failure_chain(actions, results, failures)
            if failure_chain:
                causal_chains.append(failure_chain)

        # Determine outcome
        if main_chain.outcome == OutcomeType.SUCCESS:
            outcome = "success"
        elif main_chain.outcome == OutcomeType.PARTIAL:
            outcome = "partial"
        else:
            outcome = "failure"

        # Generate key decisions
        key_decisions = []
        for decision in decisions:
            if isinstance(decision, dict):
                key_decisions.append(KeyDecision(
                    decision=decision.get("decision", ""),
                    rationale=decision.get("rationale", ""),
                    outcome=decision.get("outcome", ""),
                    alternatives_considered=decision.get("alternatives", []),
                ))

        # Identify failure modes
        failure_modes = self._identify_failure_modes(main_chain, failures)

        # Find root cause
        root_cause = ""
        if failures:
            failure_event = failures[0][1]
            root_cause = self.find_root_cause(failure_event, main_chain)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            main_chain, failure_modes, root_cause
        )

        # Count objectives achieved
        objectives_achieved = []
        if outcome == "success":
            objectives_achieved = [objective] if objective else ["Primary objective achieved"]
        elif outcome == "partial":
            objectives_achieved = session_data.get("partial_objectives", [])

        # Count targets compromised
        targets_compromised = 0
        for result in results:
            if result.get("outcome") == "success":
                if result.get("targets_affected"):
                    targets_compromised += len(result["targets_affected"])
                else:
                    targets_compromised += 1

        postmortem = PostMortemEntry(
            session_id=session_id,
            timestamp=end_time,
            objective=objective,
            outcome=outcome,
            causal_chains=causal_chains,
            key_decisions=key_decisions,
            failure_modes=failure_modes,
            root_cause=root_cause,
            recommendations=recommendations,
            duration_seconds=end_time - start_time,
            actions_taken=len(actions),
            targets_compromised=targets_compromised,
            objectives_achieved=objectives_achieved,
            metadata=session_data.get("metadata", {}),
        )

        logger.info(
            f"Generated post-mortem: {outcome} - "
            f"{len(causal_chains)} chains, {len(recommendations)} recommendations"
        )

        return postmortem

    def _build_failure_chain(
        self,
        actions: List[dict],
        results: List[dict],
        failures: List[Tuple[int, dict]],
    ) -> Optional[CausalChain]:
        """Build a causal chain focusing on failures."""
        if not failures:
            return None

        failure_chain = CausalChain(outcome=OutcomeType.FAILURE)

        # Include actions leading up to and including failures
        first_failure_idx = failures[0][0]

        for i in range(max(0, first_failure_idx - 2), len(actions)):
            if i < len(results):
                action = actions[i]
                result = results[i]

                action_type = action.get("type", "unknown")
                cause = self._format_action_cause(
                    action_type,
                    action.get("target", ""),
                    action,
                )
                effect = self._format_result_effect(
                    result.get("outcome", ""),
                    result.get("details", ""),
                    action.get("target", ""),
                )

                # Lower strength for failures
                strength = 0.3 if result.get("outcome") == "failure" else 0.5

                link = CausalLink(
                    cause=cause,
                    effect=effect,
                    strength=strength,
                    evidence=self._gather_evidence(action, result, None),
                    alternative_explanations=self._find_alternatives(action, result),
                    temporal_order=i,
                )

                failure_chain.add_link(link)

        failure_chain.critical_path = False
        failure_chain.description = self._generate_chain_description(failure_chain)

        return failure_chain

    def _identify_failure_modes(
        self,
        chain: CausalChain,
        failures: List[Tuple[int, dict]],
    ) -> List[str]:
        """Identify specific failure modes from the chain."""
        failure_modes = []

        for i, link in enumerate(chain.links):
            if link.strength < self.min_link_strength:
                # Extract failure mode from link
                cause_text = link.cause.lower()

                if "exploit" in cause_text:
                    failure_modes.append(f"Exploitation failure at step {i + 1}")
                elif "scan" in cause_text:
                    failure_modes.append(f"Reconnaissance failure at step {i + 1}")
                elif "auth" in cause_text or "credential" in cause_text:
                    failure_modes.append(f"Authentication failure at step {i + 1}")
                elif "network" in cause_text or "connect" in cause_text:
                    failure_modes.append(f"Network connectivity failure at step {i + 1}")
                else:
                    failure_modes.append(f"Unknown failure mode at step {i + 1}")

        # Add specific failure modes from failure events
        for _, failure in failures:
            failure_type = failure.get("type", "unknown")
            if failure_type not in [m.lower() for m in failure_modes]:
                failure_modes.append(failure_type)

        return list(set(failure_modes))  # Remove duplicates

    def _generate_recommendations(
        self,
        chain: CausalChain,
        failure_modes: List[str],
        root_cause: str,
    ) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        # Analyze weakest links
        for i, link in enumerate(chain.links):
            if link.strength < 0.5:
                cause_text = link.cause.lower()

                if "exploit" in cause_text:
                    recommendations.append(
                        f"Review exploit selection at step {i + 1}: "
                        f"Consider alternative exploits or more reconnaissance"
                    )
                elif "scan" in cause_text:
                    recommendations.append(
                        f"Improve reconnaissance at step {i + 1}: "
                        f"Try different scanning techniques or timing"
                    )
                elif "credential" in cause_text or "brute" in cause_text:
                    recommendations.append(
                        f"Review credential attack strategy at step {i + 1}: "
                        f"Consider credential reuse or password spraying"
                    )

        # Based on failure modes
        for mode in failure_modes:
            if "exploit" in mode.lower():
                recommendations.append(
                    "Consider alternative exploitation techniques or targets"
                )
            if "recon" in mode.lower() or "scan" in mode.lower():
                recommendations.append(
                    "Improve reconnaissance: gather more information before attacking"
                )
            if "auth" in mode.lower():
                recommendations.append(
                    "Try credential reuse from other compromised systems"
                )

        # General recommendations based on outcome
        if chain.outcome == OutcomeType.FAILURE:
            recommendations.append(
                "Consider starting with lower-risk reconnaissance activities"
            )
            recommendations.append(
                "Review target hardening and security controls before exploitation"
            )
        elif chain.outcome == OutcomeType.PARTIAL:
            recommendations.append(
                "Focus on completing partial compromises before moving laterally"
            )

        # Remove duplicate recommendations
        seen = set()
        unique_recs = []
        for rec in recommendations:
            rec_lower = rec.lower()
            if rec_lower not in seen:
                seen.add(rec_lower)
                unique_recs.append(rec)

        return unique_recs

    def explain_failure(self, chain: CausalChain) -> str:
        """
        Generate a human-readable explanation of why a chain failed.

        Args:
            chain: The causal chain to explain

        Returns:
            Human-readable explanation string
        """
        if not chain.links:
            return "No causal chain to analyze."

        explanation_lines = [
            "=" * 60,
            "FAILURE ANALYSIS",
            "=" * 60,
            "",
        ]

        # Overall summary
        explanation_lines.append(f"Chain Outcome: {chain.outcome.value.upper()}")
        explanation_lines.append(f"Overall Confidence: {chain.overall_confidence:.2f}")
        explanation_lines.append(f"Chain ID: {chain.chain_id}")
        explanation_lines.append("")

        # Identify the failure point
        weak_links = chain.critical_links
        if weak_links:
            explanation_lines.append("FAILURE POINTS IDENTIFIED:")
            for idx in weak_links:
                link = chain.links[idx]
                explanation_lines.append(f"  Step {idx + 1}: {link.cause[:80]}")
                explanation_lines.append(f"    -> {link.effect[:80]}")
                explanation_lines.append(f"    -> Strength: {link.strength:.2f} (weak)")
                if link.alternative_explanations:
                    explanation_lines.append(
                        f"    -> Possible reasons: {'; '.join(link.alternative_explanations[:2])}"
                    )
                explanation_lines.append("")
        else:
            explanation_lines.append("No obvious weak links identified.")
            explanation_lines.append("")

        # Step-by-step breakdown
        explanation_lines.append("CHAIN BREAKDOWN:")
        explanation_lines.append("-" * 40)
        for i, link in enumerate(chain.links):
            status = "OK" if link.strength >= 0.5 else "WEAK"
            explanation_lines.append(f"[Step {i + 1}] [{status}] {link.strength:.2f}")
            explanation_lines.append(f"  Cause: {link.cause[:70]}")
            explanation_lines.append(f"  Effect: {link.effect[:70]}")
            if link.evidence:
                explanation_lines.append(f"  Evidence: {'; '.join(link.evidence[:2])}")
            explanation_lines.append("")

        # Root cause hypothesis
        explanation_lines.append("ROOT CAUSE HYPOTHESIS:")
        explanation_lines.append("-" * 40)
        if weak_links:
            weakest_idx = weak_links[0]
            weakest = chain.links[weakest_idx]
            explanation_lines.append(
                f"The failure likely occurred at step {weakest_idx + 1}:"
            )
            explanation_lines.append(f"  {weakest.cause}")
            explanation_lines.append("")
            if weakest.alternative_explanations:
                explanation_lines.append("Alternative explanations to investigate:")
                for alt in weakest.alternative_explanations[:3]:
                    explanation_lines.append(f"  - {alt}")
        else:
            explanation_lines.append(
                "The failure may be due to factors not captured in this chain."
            )

        explanation_lines.append("")
        explanation_lines.append("=" * 60)

        return "\n".join(explanation_lines)

    def identify_counterfactuals(self, chain: CausalChain) -> List[str]:
        """
        Generate counterfactual scenarios (what if) based on the chain.

        Args:
            chain: The causal chain to analyze

        Returns:
            List of counterfactual scenario descriptions
        """
        counterfactuals = []

        for i, link in enumerate(chain.links):
            cause_text = link.cause.lower()

            # What if we had different reconnaissance?
            if "scan" in cause_text or "recon" in cause_text:
                counterfactuals.append(
                    f"What if we had performed more thorough reconnaissance before "
                    f"step {i + 1}? This might have revealed hidden security controls."
                )

            # What if we had chosen a different exploit?
            if "exploit" in cause_text:
                counterfactuals.append(
                    f"What if we had used a different exploit technique at step {i + 1}? "
                    f"Alternative exploits might have bypassed existing mitigations."
                )

            # What if we had better credentials?
            if "credential" in cause_text or "brute" in cause_text:
                counterfactuals.append(
                    f"What if we had obtained stronger credentials earlier? "
                    f"Credential reuse from another compromised system might have helped."
                )

            # What if timing was different?
            if "timeout" in cause_text or "delay" in cause_text:
                counterfactuals.append(
                    f"What if we had waited longer or tried at a different time? "
                    f"Security controls might have been temporarily relaxed."
                )

            # What if we had pivoted to a different target?
            if link.strength < 0.4:
                counterfactuals.append(
                    f"What if we had pivoted to a different target at step {i + 1}? "
                    f"This target may have been more hardened than others."
                )

        # General counterfactuals based on outcome
        if chain.outcome == OutcomeType.FAILURE:
            counterfactuals.extend([
                "What if we had established persistence earlier in the session?",
                "What if we had focused on a different attack vector entirely?",
                "What if we had performed the attack during off-hours when monitoring is reduced?",
            ])

        # Remove very similar counterfactuals
        unique_counterfactuals = []
        seen_phrases = set()
        for cf in counterfactuals:
            # Check for duplicates based on first 50 characters
            key = cf[:50].lower()
            if key not in seen_phrases:
                seen_phrases.add(key)
                unique_counterfactuals.append(cf)

        return unique_counterfactuals

    def detect_confounding_factors(self, actions: List[dict]) -> List[dict]:
        """
        Detect potential confounding factors in action sequences.

        Confounding factors are variables that may affect both the action
        and the outcome, potentially masking true causal relationships.

        Args:
            actions: List of action dictionaries

        Returns:
            List of detected confounding factors with explanations
        """
        confounders = []

        # Check for temporal confounds
        timestamps = [
            a.get("timestamp", 0) for a in actions
            if a.get("timestamp")
        ]

        if len(timestamps) >= 2:
            time_diffs = [
                timestamps[i + 1] - timestamps[i]
                for i in range(len(timestamps) - 1)
            ]
            avg_time_diff = sum(time_diffs) / len(time_diffs) if time_diffs else 0

            # Very rapid actions might indicate systemic issues
            if avg_time_diff < 1.0:
                confounders.append({
                    "type": "temporal",
                    "description": "Actions occurring too rapidly",
                    "impact": "May indicate automated detection or system issues",
                    "suggestion": "Consider adding delays between actions",
                })

        # Check for action type patterns
        action_types = [a.get("type", "") for a in actions]

        # Same action repeated suggests lack of adaptation
        for action_type in set(action_types):
            count = action_types.count(action_type)
            if count >= 3:
                # Find positions
                positions = [
                    i for i, at in enumerate(action_types) if at == action_type
                ]
                confounders.append({
                    "type": "action_pattern",
                    "description": f"Repeated action type: {action_type}",
                    "count": count,
                    "positions": positions,
                    "impact": "Repeating same action suggests lack of strategy adaptation",
                    "suggestion": "Try different approaches after repeated failures",
                })

        # Check for missing prerequisites
        has_recon = any("scan" in at or "recon" in at for at in action_types)
        has_exploit = any("exploit" in at for at in action_types)

        if has_exploit and not has_recon:
            confounders.append({
                "type": "missing_prerequisite",
                "description": "Exploitation without prior reconnaissance",
                "impact": "May lead to suboptimal exploit selection",
                "suggestion": "Perform reconnaissance before exploitation",
            })

        # Check for credential patterns
        has_credential_dump = any(
            "credential" in at or "dump" in at for at in action_types
        )
        has_lateral = any("lateral" in at for at in action_types)

        if has_lateral and not has_credential_dump:
            confounders.append({
                "type": "missing_prerequisite",
                "description": "Lateral movement without credential gathering",
                "impact": "May limit movement options",
                "suggestion": "Gather credentials before attempting lateral movement",
            })

        # Check for environmental changes
        targets = [a.get("target", "") for a in actions]
        unique_targets = set(targets)

        if len(unique_targets) > 10:
            confounders.append({
                "type": "target_diversity",
                "description": "High target diversity across actions",
                "unique_targets": len(unique_targets),
                "impact": "May indicate scattered approach without focus",
                "suggestion": "Focus on completing compromise of one target before moving to others",
            })

        logger.info(f"Detected {len(confounders)} potential confounding factors")

        return confounders


class CausalGraphVisualizer:
    """
    Generates visualizations for causal chains.

    Supports multiple output formats including Mermaid diagrams.
    """

    @staticmethod
    def to_mermaid(chain: CausalChain) -> str:
        """
        Generate a Mermaid flowchart from a causal chain.

        Args:
            chain: The causal chain to visualize

        Returns:
            Mermaid diagram code as a string
        """
        lines = [
            "flowchart TD",
            "    %% Causal Chain Visualization",
            f"    %% Chain ID: {chain.chain_id}",
            f"    %% Outcome: {chain.outcome.value.upper()}",
            f"    %% Confidence: {chain.overall_confidence:.2f}",
            "",
        ]

        # Add styling classes
        lines.append("    %% Styling")
        lines.append("    classDef success fill:#90EE90,stroke:#228B22,stroke-width:2px")
        lines.append("    classDef failure fill:#FFB6C1,stroke:#DC143C,stroke-width:2px")
        lines.append("    classDef partial fill:#FFFACD,stroke:#DAA520,stroke-width:2px")
        lines.append("    classDef weak stroke:#808080,stroke-dasharray:5 5")
        lines.append("")

        # Create nodes
        for i, link in enumerate(chain.links):
            # Create node IDs
            cause_id = f"cause{i}"
            effect_id = f"effect{i}"

            # Style based on strength
            if link.strength >= 0.7:
                style_class = "success" if chain.outcome == OutcomeType.SUCCESS else "partial"
            elif link.strength >= 0.4:
                style_class = "partial"
            else:
                style_class = "failure"

            # Format labels (escape special characters)
            cause_label = link.cause.replace('"', "'").replace('\n', ' ')[:60]
            effect_label = link.effect.replace('"', "'").replace('\n', ' ')[:60]

            # Add cause node
            lines.append(f"    {cause_id}[[\"{cause_label}\"]]")

            # Add effect node
            lines.append(f"    {effect_id}[\"{effect_label}\"]")

            # Add edge
            lines.append(f"    {cause_id} --> |\"{link.strength:.2f}\"| {effect_id}")

            # Apply styling
            lines.append(f"    class {effect_id} {style_class}")

            # Add weak styling if applicable
            if link.strength < 0.5:
                lines.append(f"    class {cause_id},{effect_id} weak")

            lines.append("")

        # Add legend
        lines.append("    %% Legend")
        lines.append("    subgraph LEGEND [Legend]")
        lines.append("        L1[Success / High Confidence]")
        lines.append("        L2[Partial Success / Medium Confidence]")
        lines.append("        L3[Failure / Low Confidence]")
        lines.append("    end")
        lines.append("    class L1 success")
        lines.append("    class L2 partial")
        lines.append("    class L3 failure")

        return "\n".join(lines)

    @staticmethod
    def to_ascii(chain: CausalChain) -> str:
        """
        Generate an ASCII art representation of a causal chain.

        Args:
            chain: The causal chain to visualize

        Returns:
            ASCII diagram as a string
        """
        lines = [
            "=" * 70,
            f"CAUSAL CHAIN: {chain.chain_id}",
            f"Outcome: {chain.outcome.value.upper():<10} Confidence: {chain.overall_confidence:.2f}",
            "=" * 70,
            "",
        ]

        for i, link in enumerate(chain.links):
            strength_bar = "█" * int(link.strength * 10) + "░" * (10 - int(link.strength * 10))

            lines.append(f"Step {i + 1}:")
            lines.append(f"  [{strength_bar}] {link.strength:.2f}")

            # Cause
            cause_text = link.cause[:65]
            lines.append(f"  CAUSE: {cause_text}")

            # Effect
            effect_text = link.effect[:65]
            lines.append(f"  EFFECT: {effect_text}")

            # Evidence summary
            if link.evidence:
                lines.append(f"  EVIDENCE: {len(link.evidence)} item(s)")

            # Alternatives summary
            if link.alternative_explanations:
                lines.append(f"  ALTERNATIVES: {len(link.alternative_explanations)} possible")

            # Weak link warning
            if link.strength < 0.5:
                lines.append(f"  ⚠ WARNING: Weak link - potential failure point")

            lines.append("")

            if i < len(chain.links) - 1:
                lines.append("  |")
                lines.append("  v")
                lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def to_dict(chain: CausalChain) -> dict:
        """
        Export chain as a dictionary suitable for JSON serialization.

        Args:
            chain: The causal chain to export

        Returns:
            Dictionary representation
        """
        return chain.to_dict()

    @staticmethod
    def to_text_report(postmortem: PostMortemEntry) -> str:
        """
        Generate a comprehensive text report from a post-mortem.

        Args:
            postmortem: The post-mortem entry

        Returns:
            Formatted text report
        """
        lines = [
            "=" * 70,
            "PENETRATION TESTING POST-MORTEM REPORT",
            "=" * 70,
            "",
            f"Session ID: {postmortem.session_id}",
            f"Timestamp: {datetime.fromtimestamp(postmortem.timestamp).strftime('%Y-%m-%d %H:%M:%S')}",
            f"Objective: {postmortem.objective}",
            f"Outcome: {postmortem.outcome.upper()}",
            "",
            "-" * 70,
            "SESSION STATISTICS",
            "-" * 70,
            f"Duration: {postmortem.duration_seconds:.1f} seconds",
            f"Actions Taken: {postmortem.actions_taken}",
            f"Targets Compromised: {postmortem.targets_compromised}",
            f"Objectives Achieved: {', '.join(postmortem.objectives_achieved) if postmortem.objectives_achieved else 'None'}",
            "",
        ]

        if postmortem.causal_chains:
            lines.extend([
                "-" * 70,
                "CAUSAL CHAINS",
                "-" * 70,
                "",
            ])
            for i, chain in enumerate(postmortem.causal_chains):
                lines.append(f"Chain {i + 1} ({chain.chain_id}):")
                lines.append(f"  Description: {chain.description}")
                lines.append(f"  Outcome: {chain.outcome.value}")
                lines.append(f"  Confidence: {chain.overall_confidence:.2f}")
                lines.append(f"  Critical Path: {'Yes' if chain.critical_path else 'No'}")
                lines.append(f"  Links: {len(chain.links)}")
                lines.append(f"  Weakest Link: {chain.strength:.2f}")
                lines.append("")

        if postmortem.key_decisions:
            lines.extend([
                "-" * 70,
                "KEY DECISIONS",
                "-" * 70,
                "",
            ])
            for i, decision in enumerate(postmortem.key_decisions):
                lines.append(f"{i + 1}. {decision.decision}")
                lines.append(f"   Rationale: {decision.rationale}")
                lines.append(f"   Outcome: {decision.outcome}")
                if decision.alternatives_considered:
                    lines.append(f"   Alternatives: {', '.join(decision.alternatives_considered)}")
                lines.append("")

        if postmortem.failure_modes:
            lines.extend([
                "-" * 70,
                "FAILURE MODES IDENTIFIED",
                "-" * 70,
                "",
            ])
            for mode in postmortem.failure_modes:
                lines.append(f"  - {mode}")
            lines.append("")

        if postmortem.root_cause:
            lines.extend([
                "-" * 70,
                "ROOT CAUSE ANALYSIS",
                "-" * 70,
                "",
            ])
            lines.append(postmortem.root_cause)
            lines.append("")

        if postmortem.recommendations:
            lines.extend([
                "-" * 70,
                "RECOMMENDATIONS",
                "-" * 70,
                "",
            ])
            for i, rec in enumerate(postmortem.recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        lines.extend([
            "=" * 70,
            "END OF REPORT",
            "=" * 70,
        ])

        return "\n".join(lines)


# Convenience functions
def analyze_session(session_data: dict) -> PostMortemEntry:
    """
    Analyze a session and generate a post-mortem.

    Args:
        session_data: Session data dictionary

    Returns:
        PostMortemEntry with full analysis
    """
    reasoner = CausalReasoner()
    return reasoner.generate_postmortem(session_data)


def explain_and_visualize(chain: CausalChain) -> Tuple[str, str]:
    """
    Generate both an explanation and Mermaid visualization.

    Args:
        chain: The causal chain to analyze

    Returns:
        Tuple of (explanation, mermaid_diagram)
    """
    reasoner = CausalReasoner()
    visualizer = CausalGraphVisualizer()

    explanation = reasoner.explain_failure(chain)
    mermaid = visualizer.to_mermaid(chain)

    return explanation, mermaid
