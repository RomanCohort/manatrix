"""
TTP Graph Construction System

This module implements an Attack TTP (Tactics, Techniques, Procedures) Graph
Construction system that automatically maps successful attack sequences to an
enriched TTP graph, visualizing relationships and contextual conditions between
different TTPs. Based on MITRE ATT&CK but more fine-grained.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TTPTactic(Enum):
    """
    MITRE ATT&CK tactics plus custom extended tactics for fine-grained modeling.
    """
    # MITRE ATT&CK Enterprise tactics
    RECONNAISSANCE = auto()
    RESOURCE_DEVELOPMENT = auto()
    INITIAL_ACCESS = auto()
    EXECUTION = auto()
    PERSISTENCE = auto()
    PRIVILEGE_ESCALATION = auto()
    DEFENSE_EVASION = auto()
    CREDENTIAL_ACCESS = auto()
    DISCOVERY = auto()
    LATERAL_MOVEMENT = auto()
    COLLECTION = auto()
    COMMAND_AND_CONTROL = auto()
    EXFILTRATION = auto()
    IMPACT = auto()

    # Custom extended tactics for fine-grained modeling
    TARGET_ACQUISITION = auto()
    WEAPONIZATION = auto()
    DELIVERY = auto()
    INSTALLATION = auto()
    C2_ESTABLISHMENT = auto()
    ACTIONS_ON_OBJECTIVES = auto()
    DATA_MANIPULATION = auto()
    SERVICE_DISRUPTION = auto()
    PASS_THE_HASH = auto()
    BRUTE_FORCE = auto()
    CREDENTIAL_DUMPING = auto()
    KEYLOGGING = auto()
    PASSIVE_DISCOVERY = auto()
    ACTIVE_DISCOVERY = auto()
    TRUST_EXPLOITATION = auto()
    HASH_INJECTION = auto()
    REMOTE_EXECUTION = auto()
    LOCAL_EXECUTION = auto()

    @classmethod
    def from_string(cls, tactic_str: str) -> "TTPTactic":
        """Convert a string to TTPTactic enum, case-insensitive."""
        tactic_str = tactic_str.upper().replace("-", "_").replace(" ", "_")
        try:
            return cls[tactic_str]
        except KeyError:
            logger.warning(f"Unknown tactic '{tactic_str}', defaulting to INITIAL_ACCESS")
            return cls.INITIAL_ACCESS

    def to_mitre_tactic(self) -> Optional[str]:
        """Convert custom tactics to MITRE ATT&CK tactic names if applicable."""
        mitre_mapping = {
            TTPTactic.RECONNAISSANCE: "Reconnaissance",
            TTPTactic.RESOURCE_DEVELOPMENT: "Resource Development",
            TTPTactic.INITIAL_ACCESS: "Initial Access",
            TTPTactic.EXECUTION: "Execution",
            TTPTactic.PERSISTENCE: "Persistence",
            TTPTactic.PRIVILEGE_ESCALATION: "Privilege Escalation",
            TTPTactic.DEFENSE_EVASION: "Defense Evasion",
            TTPTactic.CREDENTIAL_ACCESS: "Credential Access",
            TTPTactic.DISCOVERY: "Discovery",
            TTPTactic.LATERAL_MOVEMENT: "Lateral Movement",
            TTPTactic.COLLECTION: "Collection",
            TTPTactic.COMMAND_AND_CONTROL: "Command and Control",
            TTPTactic.EXFILTRATION: "Exfiltration",
            TTPTactic.IMPACT: "Impact",
        }
        return mitre_mapping.get(self)


@dataclass
class TTPNode:
    """
    Represents a TTP (Tactic, Technique, Procedure) node in the attack graph.

    Attributes:
        technique_id: Unique identifier (e.g., "T1190.001")
        name: Human-readable name of the technique
        tactic: The tactical category this technique belongs to
        description: Detailed description of the technique
        prerequisites: List of prerequisites for this technique to be effective
        effectiveness: Score 0-1 representing historical effectiveness
        stealth_rating: Score 0-1 representing how stealthy the technique is
        detection_difficulty: Score 0-1 representing detection difficulty
        observed_count: Number of times this technique has been observed
        success_count: Number of successful uses of this technique
        context_conditions: List of contextual conditions where this technique applies
    """
    technique_id: str
    name: str
    tactic: TTPTactic
    description: str = ""
    prerequisites: List[str] = field(default_factory=list)
    effectiveness: float = 0.5
    stealth_rating: float = 0.5
    detection_difficulty: float = 0.5
    observed_count: int = 0
    success_count: int = 0
    context_conditions: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate node attributes after initialization."""
        if not self.technique_id:
            raise ValueError("technique_id cannot be empty")
        self.effectiveness = max(0.0, min(1.0, self.effectiveness))
        self.stealth_rating = max(0.0, min(1.0, self.stealth_rating))
        self.detection_difficulty = max(0.0, min(1.0, self.detection_difficulty))
        self.observed_count = max(0, self.observed_count)
        self.success_count = max(0, min(self.success_count, self.observed_count))

    @property
    def success_rate(self) -> float:
        """Calculate the success rate of this technique."""
        if self.observed_count == 0:
            return 0.0
        return self.success_count / self.observed_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "technique_id": self.technique_id,
            "name": self.name,
            "tactic": self.tactic.name,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "effectiveness": self.effectiveness,
            "stealth_rating": self.stealth_rating,
            "detection_difficulty": self.detection_difficulty,
            "observed_count": self.observed_count,
            "success_count": self.success_count,
            "context_conditions": self.context_conditions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TTPNode":
        """Create TTPNode from dictionary representation."""
        return cls(
            technique_id=data["technique_id"],
            name=data["name"],
            tactic=TTPTactic[data["tactic"]],
            description=data.get("description", ""),
            prerequisites=data.get("prerequisites", []),
            effectiveness=data.get("effectiveness", 0.5),
            stealth_rating=data.get("stealth_rating", 0.5),
            detection_difficulty=data.get("detection_difficulty", 0.5),
            observed_count=data.get("observed_count", 0),
            success_count=data.get("success_count", 0),
            context_conditions=data.get("context_conditions", []),
        )


@dataclass
class TTPEdge:
    """
    Represents a relationship between two TTPs in the attack graph.

    Attributes:
        source_technique: Technique ID of the source node
        target_technique: Technique ID of the target node
        relationship: Type of relationship between techniques
        confidence: Score 0-1 representing confidence in this relationship
        observed_count: Number of times this relationship has been observed
    """
    source_technique: str
    target_technique: str
    relationship: str  # "enables", "follows", "requires", "alternative", "complements"
    confidence: float = 0.5
    observed_count: int = 0

    VALID_RELATIONSHIPS = {"enables", "follows", "requires", "alternative", "complements"}

    def __post_init__(self) -> None:
        """Validate edge attributes after initialization."""
        if not self.source_technique or not self.target_technique:
            raise ValueError("Source and target technique IDs cannot be empty")
        if self.relationship not in self.VALID_RELATIONSHIPS:
            logger.warning(
                f"Invalid relationship type '{self.relationship}', using 'follows'"
            )
            self.relationship = "follows"
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.observed_count = max(0, self.observed_count)

    def to_dict(self) -> Dict[str, Any]:
        """Convert edge to dictionary representation."""
        return {
            "source_technique": self.source_technique,
            "target_technique": self.target_technique,
            "relationship": self.relationship,
            "confidence": self.confidence,
            "observed_count": self.observed_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TTPEdge":
        """Create TTPEdge from dictionary representation."""
        return cls(
            source_technique=data["source_technique"],
            target_technique=data["target_technique"],
            relationship=data["relationship"],
            confidence=data.get("confidence", 0.5),
            observed_count=data.get("observed_count", 0),
        )


class TTPGraph:
    """
    Graph-based representation of TTP relationships and mappings.

    This class manages nodes (techniques) and edges (relationships) to build
    an attack knowledge graph that can be enriched from observed attack sessions.
    """

    def __init__(self) -> None:
        """Initialize an empty TTP graph."""
        self.nodes: Dict[str, TTPNode] = {}
        self.edges: List[TTPEdge] = []
        self._adjacency_list: Dict[str, List[Tuple[str, TTPEdge]]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[Tuple[str, TTPEdge]]] = defaultdict(list)
        self._technique_chains_cache: Dict[Tuple[str, str], List[List[str]]] = {}
        logger.info("Initialized empty TTPGraph")

    def add_technique(self, technique: TTPNode) -> None:
        """
        Add a technique node to the graph.

        Args:
            technique: TTPNode to add to the graph
        """
        self.nodes[technique.technique_id] = technique
        self._invalidate_cache()
        logger.debug(f"Added technique: {technique.technique_id}")

    def add_relationship(self, edge: TTPEdge) -> None:
        """
        Add a relationship edge to the graph.

        Args:
            edge: TTPEdge to add to the graph

        Raises:
            ValueError: If source or target technique does not exist in graph
        """
        if edge.source_technique not in self.nodes:
            logger.warning(
                f"Source technique '{edge.source_technique}' not in graph, adding it"
            )
            self.add_technique(
                TTPNode(
                    technique_id=edge.source_technique,
                    name=edge.source_technique,
                    tactic=TTPTactic.INITIAL_ACCESS,
                )
            )
        if edge.target_technique not in self.nodes:
            logger.warning(
                f"Target technique '{edge.target_technique}' not in graph, adding it"
            )
            self.add_technique(
                TTPNode(
                    technique_id=edge.target_technique,
                    name=edge.target_technique,
                    tactic=TTPTactic.EXECUTION,
                )
            )

        self.edges.append(edge)
        self._adjacency_list[edge.source_technique].append(
            (edge.target_technique, edge)
        )
        self._reverse_adjacency[edge.target_technique].append(
            (edge.source_technique, edge)
        )
        self._invalidate_cache()
        logger.debug(
            f"Added relationship: {edge.source_technique} -> {edge.relationship} -> "
            f"{edge.target_technique}"
        )

    def map_attack_sequence(self, actions: List[Dict[str, Any]]) -> List[str]:
        """
        Map a sequence of actions to corresponding technique IDs.

        Uses pattern matching and heuristics to map raw actions to known techniques.

        Args:
            actions: List of action dictionaries containing action metadata

        Returns:
            List of technique IDs corresponding to the input actions
        """
        mapper = AttackSequenceMapper(self)
        return mapper.map_sequence(actions)

    def enrich_from_session(self, session_data: Dict[str, Any]) -> int:
        """
        Enrich the graph with data from a penetration testing session.

        Args:
            session_data: Dictionary containing session information with keys:
                - actions: List of actions taken during the session
                - success: Boolean indicating if the session was successful
                - techniques_used: Optional list of known techniques
                - targets: Optional list of targets
                - results: Optional results of actions

        Returns:
            Number of techniques enriched/added from the session
        """
        enriched_count = 0
        techniques_mapped = self.map_attack_sequence(session_data.get("actions", []))

        for i, tech_id in enumerate(techniques_mapped):
            if tech_id not in self.nodes:
                self.add_technique(
                    TTPNode(
                        technique_id=tech_id,
                        name=tech_id,
                        tactic=self._infer_tactic_from_action(
                            session_data.get("actions", [{}])[i]
                            if i < len(session_data.get("actions", []))
                            else {},
                        ),
                    )
                )
                enriched_count += 1

            node = self.nodes[tech_id]
            node.observed_count += 1
            if session_data.get("success", False):
                node.success_count += 1

            self._update_effectiveness_from_session(node, session_data)

            if i > 0:
                prev_tech = techniques_mapped[i - 1]
                self._add_observed_relationship(prev_tech, tech_id)

        logger.info(
            f"Enriched graph with {enriched_count} new techniques from session"
        )
        return enriched_count

    def _infer_tactic_from_action(self, action: Dict[str, Any]) -> TTPTactic:
        """Infer the tactic based on action metadata."""
        action_type = action.get("type", "").lower()
        target = action.get("target", "").lower()

        if "scan" in action_type or "recon" in action_type:
            return TTPTactic.RECONNAISSANCE
        elif "exploit" in action_type or "brute" in action_type:
            return TTPTactic.EXPLOITATION
        elif "access" in action_type or "login" in action_type:
            return TTPTactic.CREDENTIAL_ACCESS
        elif "move" in action_type or "lateral" in action_type:
            return TTPTactic.LATERAL_MOVEMENT
        elif "execute" in action_type or "run" in action_type:
            return TTPTactic.EXECUTION
        elif "elevate" in action_type or "priv" in action_type:
            return TTPTactic.PRIVILEGE_ESCALATION
        elif "exfil" in action_type or "steal" in action_type:
            return TTPTactic.EXFILTRATION
        else:
            return TTPTactic.INITIAL_ACCESS

    def _update_effectiveness_from_session(
        self, node: TTPNode, session_data: Dict[str, Any]
    ) -> None:
        """Update effectiveness metrics based on session data."""
        if "effectiveness_score" in session_data:
            node.effectiveness = (
                node.effectiveness * 0.8 + session_data["effectiveness_score"] * 0.2
            )
        if "stealth_score" in session_data:
            node.stealth_rating = (
                node.stealth_rating * 0.8 + session_data["stealth_score"] * 0.2
            )
        if "detection_score" in session_data:
            node.detection_difficulty = (
                node.detection_difficulty * 0.8 + session_data["detection_score"] * 0.2
            )

    def _add_observed_relationship(
        self, source: str, target: str, relationship: str = "follows"
    ) -> None:
        """Add or update an observed relationship between techniques."""
        existing_edge = None
        for edge in self.edges:
            if edge.source_technique == source and edge.target_technique == target:
                existing_edge = edge
                break

        if existing_edge:
            existing_edge.observed_count += 1
            existing_edge.confidence = min(
                1.0, existing_edge.confidence + 0.1 / existing_edge.observed_count
            )
        else:
            self.add_relationship(
                TTPEdge(
                    source_technique=source,
                    target_technique=target,
                    relationship=relationship,
                    confidence=0.5,
                    observed_count=1,
                )
            )

    def find_technique_chains(
        self, start: str, goal: str, max_depth: int = 10
    ) -> List[List[str]]:
        """
        Find all possible chains of techniques from start to goal.

        Uses BFS to find all paths within the maximum depth.

        Args:
            start: Starting technique ID
            goal: Target technique ID
            max_depth: Maximum depth to search (default 10)

        Returns:
            List of technique chains (each chain is a list of technique IDs)
        """
        cache_key = (start, goal)
        if cache_key in self._technique_chains_cache:
            return self._technique_chains_cache[cache_key]

        if start == goal:
            return [[start]]

        chains: List[List[str]] = []
        visited: Dict[str, int] = defaultdict(int)

        def dfs(current: str, path: List[str], depth: int) -> None:
            if depth > max_depth:
                return
            if current == goal:
                chains.append(path.copy())
                return

            for neighbor, _ in self._adjacency_list.get(current, []):
                if visited[neighbor] < 3:
                    visited[neighbor] += 1
                    path.append(neighbor)
                    dfs(neighbor, path, depth + 1)
                    path.pop()
                    visited[neighbor] -= 1

        dfs(start, [start], 0)
        self._technique_chains_cache[cache_key] = chains
        logger.debug(f"Found {len(chains)} chains from {start} to {goal}")
        return chains

    def get_technique_context(self, technique_id: str) -> Dict[str, Any]:
        """
        Get the context surrounding a technique including predecessors and successors.

        Args:
            technique_id: The technique ID to get context for

        Returns:
            Dictionary containing the technique and its context
        """
        if technique_id not in self.nodes:
            logger.warning(f"Technique {technique_id} not found in graph")
            return {}

        node = self.nodes[technique_id]
        predecessors = [
            (src, edge.relationship)
            for src, edge in self._reverse_adjacency.get(technique_id, [])
        ]
        successors = [
            (tgt, edge.relationship)
            for tgt, edge in self._adjacency_list.get(technique_id, [])
        ]

        return {
            "technique": node.to_dict(),
            "predecessors": [
                {"technique_id": p[0], "relationship": p[1]}
                for p in predecessors
            ],
            "successors": [
                {"technique_id": s[0], "relationship": s[1]}
                for s in successors
            ],
            "total_predecessors": len(predecessors),
            "total_successors": len(successors),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about the TTP graph.

        Returns:
            Dictionary containing graph statistics
        """
        tactic_counts: Dict[str, int] = defaultdict(int)
        total_relationships: Dict[str, int] = defaultdict(int)

        for node in self.nodes.values():
            tactic_counts[node.tactic.name] += 1

        for edge in self.edges:
            total_relationships[edge.relationship] += 1

        total_success_rate = 0.0
        if self.nodes:
            for node in self.nodes.values():
                if node.observed_count > 0:
                    total_success_rate += node.success_rate
            avg_success_rate = total_success_rate / len(self.nodes)
        else:
            avg_success_rate = 0.0

        return {
            "total_techniques": len(self.nodes),
            "total_relationships": len(self.edges),
            "tactics_distribution": dict(tactic_counts),
            "relationship_types": dict(total_relationships),
            "average_success_rate": round(avg_success_rate, 3),
            "most_observed_technique": self._get_most_observed(),
            "most_effective_technique": self._get_most_effective(),
            "stealthiest_technique": self._get_stealthiest(),
        }

    def _get_most_observed(self) -> Optional[Dict[str, Any]]:
        """Get the most observed technique."""
        if not self.nodes:
            return None
        most_observed = max(self.nodes.values(), key=lambda n: n.observed_count)
        return {"technique_id": most_observed.technique_id, "count": most_observed.observed_count}

    def _get_most_effective(self) -> Optional[Dict[str, Any]]:
        """Get the technique with highest effectiveness score."""
        if not self.nodes:
            return None
        most_effective = max(
            self.nodes.values(), key=lambda n: n.effectiveness * n.observed_count
        )
        return {"technique_id": most_effective.technique_id, "score": most_effective.effectiveness}

    def _get_stealthiest(self) -> Optional[Dict[str, Any]]:
        """Get the stealthiest technique based on stealth rating and detection difficulty."""
        if not self.nodes:
            return None
        stealthiest = max(
            self.nodes.values(),
            key=lambda n: (n.stealth_rating + (1 - n.detection_difficulty)) / 2,
        )
        return {
            "technique_id": stealthiest.technique_id,
            "stealth_rating": stealthiest.stealth_rating,
            "detection_difficulty": stealthiest.detection_difficulty,
        }

    def to_mermaid(self) -> str:
        """
        Generate Mermaid diagram code for visualizing the TTP graph.

        Returns:
            String containing Mermaid diagram code
        """
        lines = ["graph TD"]

        tactic_colors = {
            TTPTactic.RECONNAISSANCE: "subgraph",
            TTPTactic.INITIAL_ACCESS: "subgraph",
            TTPTactic.EXECUTION: "subgraph",
            TTPTactic.PERSISTENCE: "subgraph",
            TTPTactic.PRIVILEGE_ESCALATION: "subgraph",
            TTPTactic.DEFENSE_EVASION: "subgraph",
            TTPTactic.CREDENTIAL_ACCESS: "subgraph",
            TTPTactic.DISCOVERY: "subgraph",
            TTPTactic.LATERAL_MOVEMENT: "subgraph",
            TTPTactic.COLLECTION: "subgraph",
            TTPTactic.COMMAND_AND_CONTROL: "subgraph",
            TTPTactic.EXFILTRATION: "subgraph",
            TTPTactic.IMPACT: "subgraph",
        }

        tactic_nodes: Dict[str, List[str]] = defaultdict(list)
        for node in self.nodes.values():
            tactic_nodes[node.tactic.name].append(node.technique_id)

        node_ids: Dict[str, str] = {}
        for i, (node_id, _) in enumerate(self.nodes.items()):
            safe_id = f"T{i}"
            node_ids[node_id] = safe_id

        for tactic, nodes in tactic_nodes.items():
            lines.append(f"    subgraph {tactic}")
            for node_id in nodes:
                safe_id = node_ids[node_id]
                node = self.nodes[node_id]
                effectiveness_bar = "█" * int(node.effectiveness * 10)
                lines.append(
                    f'        {safe_id}["{node.name} ({node.technique_id})\\nEff: {effectiveness_bar}"]'
                )
            lines.append("    end")

        edge_styles = {
            "enables": "-->",
            "follows": "-.->",
            "requires": "-->|requires|",
            "alternative": "-.->",
            "complements": "==>=>",
        }

        for edge in self.edges:
            src_id = node_ids.get(edge.source_technique, "")
            tgt_id = node_ids.get(edge.target_technique, "")
            if src_id and tgt_id:
                arrow = edge_styles.get(edge.relationship, "-->")
                label = f"|{edge.relationship}|" if "|" not in arrow else ""
                lines.append(f"    {src_id} {arrow} {label} {tgt_id}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the graph to a dictionary representation.

        Returns:
            Dictionary containing all nodes and edges
        """
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
            },
        }

    def save(self, path: str) -> None:
        """
        Save the graph to a JSON file.

        Args:
            path: File path to save the graph to
        """
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved TTP graph to {path}")

    def load(self, path: str) -> None:
        """
        Load the graph from a JSON file.

        Args:
            path: File path to load the graph from

        Raises:
            FileNotFoundError: If the file does not exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Graph file not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.nodes = {}
        self.edges = []
        self._adjacency_list.clear()
        self._reverse_adjacency.clear()

        for node_data in data.get("nodes", []):
            node = TTPNode.from_dict(node_data)
            self.nodes[node.technique_id] = node

        for edge_data in data.get("edges", []):
            edge = TTPEdge.from_dict(edge_data)
            self.edges.append(edge)
            self._adjacency_list[edge.source_technique].append(
                (edge.target_technique, edge)
            )
            self._reverse_adjacency[edge.target_technique].append(
                (edge.source_technique, edge)
            )

        logger.info(f"Loaded TTP graph from {path}")


class AttackSequenceMapper:
    """
    Maps attack actions to TTP technique IDs.

    This class analyzes raw actions and maps them to known techniques using
    pattern matching, keyword recognition, and heuristics.
    """

    def __init__(self, ttp_graph: TTPGraph) -> None:
        """
        Initialize the mapper with a TTP graph.

        Args:
            ttp_graph: The TTP graph to use for mapping
        """
        self.ttp_graph = ttp_graph
        self._action_patterns: Dict[str, List[Tuple[str, float]]] = self._build_patterns()
        logger.debug("Initialized AttackSequenceMapper")

    def _build_patterns(self) -> Dict[str, List[Tuple[str, float]]]:
        """Build action patterns for technique mapping."""
        patterns: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        for node in self.ttp_graph.nodes.values():
            keywords = self._extract_keywords(node.name, node.description)
            for keyword in keywords:
                patterns[keyword.lower()].append((node.technique_id, node.effectiveness))

        return patterns

    def _extract_keywords(self, name: str, description: str) -> List[str]:
        """Extract keywords from name and description."""
        import re
        text = f"{name} {description}".lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)
        return list(set(words))

    def map_action_to_technique(self, action: Dict[str, Any]) -> Optional[str]:
        """
        Map a single action to a technique ID.

        Args:
            action: Action dictionary containing action metadata

        Returns:
            Technique ID if mapping found, None otherwise
        """
        action_type = action.get("type", "").lower()
        target = action.get("target", "").lower()
        tool = action.get("tool", "").lower()
        result = action.get("result", "").lower()

        candidates: Dict[str, float] = {}

        for pattern, techniques in self._action_patterns.items():
            if pattern in action_type or pattern in target or pattern in tool:
                for tech_id, effectiveness in techniques:
                    candidates[tech_id] = candidates.get(tech_id, 0) + effectiveness

        if not candidates:
            candidates = self._heuristic_mapping(action)

        if candidates:
            best_technique = max(candidates.items(), key=lambda x: x[1])
            return best_technique[0]

        return self._default_mapping(action)

    def _heuristic_mapping(self, action: Dict[str, Any]) -> Dict[str, float]:
        """Use heuristics to map action to technique."""
        candidates: Dict[str, float] = {}
        action_type = action.get("type", "").lower()
        target = action.get("target", "").lower()

        if any(k in action_type for k in ["brute", "crack", "guess", "dict"]):
            candidates["T1110"] = 0.8
        if any(k in action_type for k in ["inject", "passthrough"]):
            candidates["T1550"] = 0.7
        if any(k in action_type for k in ["dump", "extract", "steal"]):
            candidates["T1003"] = 0.7
        if any(k in action_type for k in ["scan", "enum", "recon"]):
            candidates["T1018"] = 0.6
        if any(k in action_type for k in ["exec", "run", "command"]):
            candidates["T1059"] = 0.7
        if any(k in target for k in ["password", "hash", "credential"]):
            candidates["T1078"] = 0.6

        return candidates

    def _default_mapping(self, action: Dict[str, Any]) -> str:
        """Return default technique based on action type."""
        action_type = action.get("type", "").lower()

        if "access" in action_type:
            return "T1078"
        elif "exec" in action_type:
            return "T1059"
        elif "scan" in action_type:
            return "T1018"
        elif "brute" in action_type:
            return "T1110"
        else:
            return "T1190"

    def map_sequence_to_chain(
        self, actions: List[Dict[str, Any]]
    ) -> List[Tuple[str, float]]:
        """
        Map a sequence of actions to technique chains with confidence scores.

        Args:
            actions: List of action dictionaries

        Returns:
            List of tuples (technique_id, confidence_score)
        """
        mapped_techniques: List[Tuple[str, float]] = []

        for action in actions:
            tech_id = self.map_action_to_technique(action)
            if tech_id:
                confidence = self._calculate_confidence(action, tech_id)
                mapped_techniques.append((tech_id, confidence))

        return mapped_techniques

    def _calculate_confidence(self, action: Dict[str, Any], tech_id: str) -> float:
        """Calculate confidence score for a technique mapping."""
        if tech_id not in self.ttp_graph.nodes:
            return 0.5

        node = self.ttp_graph.nodes[tech_id]
        base_confidence = node.effectiveness

        action_type = action.get("type", "").lower()
        if any(k in action_type for k in node.name.lower().split()):
            base_confidence = min(1.0, base_confidence + 0.2)

        return base_confidence

    def map_sequence(self, actions: List[Dict[str, Any]]) -> List[str]:
        """
        Map a sequence of actions to technique IDs (simplified interface).

        Args:
            actions: List of action dictionaries

        Returns:
            List of technique IDs
        """
        return [tech_id for tech_id, _ in self.map_sequence_to_chain(actions)]