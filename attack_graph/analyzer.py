"""
Attack Graph Analyzer

Provides analysis capabilities for attack graphs:
- Find attack paths (BFS and A* with heuristic pruning)
- Calculate risk scores
- Identify critical nodes
- Simulate attacks
- Generate mitigations
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import heapq

from .graph import AttackGraph, AttackNode, AttackEdge, NodeType, EdgeType


@dataclass
class AttackPath:
    """Represents a potential attack path."""
    nodes: List[str]
    edges: List[AttackEdge]
    probability: float
    impact: float
    risk_score: float

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": [e.to_dict() for e in self.edges],
            "probability": self.probability,
            "impact": self.impact,
            "risk_score": self.risk_score,
        }


@dataclass
class AttackResult:
    """Result of a simulated attack."""
    success: bool
    path: List[str]
    compromised_nodes: List[str]
    failed_at: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "path": self.path,
            "compromised_nodes": self.compromised_nodes,
            "failed_at": self.failed_at,
            "error": self.error,
        }


@dataclass
class MitigationAction:
    """Recommended mitigation action."""
    target_node: str
    action_type: str
    description: str
    priority: int  # 1 = highest
    estimated_effort: str  # "low", "medium", "high"

    def to_dict(self) -> dict:
        return {
            "target_node": self.target_node,
            "action_type": self.action_type,
            "description": self.description,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
        }


class AttackGraphAnalyzer:
    """Analyzes attack graphs for security insights."""

    def __init__(self):
        self._risk_weights = {
            NodeType.VULNERABILITY: 0.4,
            NodeType.HOST: 0.3,
            NodeType.SERVICE: 0.2,
            NodeType.CREDENTIAL: 0.3,
        }

    def find_attack_paths(
        self,
        graph: AttackGraph,
        target: str,
        max_paths: int = 10,
        min_probability: float = 0.1,
        max_depth: int = 20,
        use_astar: bool = True,
    ) -> List[AttackPath]:
        """
        Find all attack paths to a target node.

        Args:
            graph: Attack graph
            target: Target node ID
            max_paths: Maximum number of paths to return
            min_probability: Minimum path probability threshold
            max_depth: Maximum path depth (pruning parameter)
            use_astar: Use A* search (default True) for better pruning

        Returns paths sorted by risk score (highest first).
        """
        if target not in graph.nodes:
            return []

        network_nodes = [
            n.id for n in graph.nodes.values()
            if n.type == NodeType.NETWORK
        ]

        if not network_nodes:
            return []

        all_paths: List[AttackPath] = []

        for network in network_nodes:
            if use_astar:
                # Use A* search with probability heuristic
                raw_paths = self._find_paths_astar(
                    graph, network, target,
                    max_paths=max_paths,
                    max_depth=max_depth,
                    min_probability=min_probability,
                )
            else:
                # Fallback to BFS
                raw_paths = graph.find_paths(network, target, max_paths=max_paths)

            for raw_path in raw_paths:
                attack_path = self._build_attack_path(graph, raw_path)
                if attack_path.probability >= min_probability:
                    all_paths.append(attack_path)

            # Early termination if we have enough high-quality paths
            if len(all_paths) >= max_paths * 2:
                break

        return sorted(all_paths, key=lambda p: p.risk_score, reverse=True)[:max_paths]

    def _find_paths_astar(
        self,
        graph: AttackGraph,
        source: str,
        target: str,
        max_paths: int = 10,
        max_depth: int = 20,
        min_probability: float = 0.1,
    ) -> List[List[str]]:
        """
        Find attack paths using A* search with heuristic pruning.

        Heuristic: favor paths with higher individual edge probabilities.
        This guides search toward high-quality paths first.
        """
        if source not in graph.nodes or target not in graph.nodes:
            return []

        paths: List[List[str]] = []
        # Priority queue: (negative cumulative probability, path_length, path)
        # We use negative probability because heapq is min-heap
        open_set: List[Tuple[float, int, List[str]]] = [(0.0, 0, [source])]
        visited_paths: Set[frozenset] = set()

        while open_set and len(paths) < max_paths:
            # Pop highest probability path
            neg_prob, length, path = heapq.heappop(open_set)
            current = path[-1]

            # Check if we've reached the target
            if current == target:
                paths.append(path)
                continue

            # Prune by depth
            if length >= max_depth:
                continue

            # Mark as visited (by path set to avoid cycles)
            path_set = frozenset(path)
            if path_set in visited_paths:
                continue
            visited_paths.add(path_set)

            # Expand neighbors
            outgoing = graph.get_outgoing_edges(current)
            if not outgoing:
                continue

            # Sort neighbors by edge probability (best first)
            sorted_edges = sorted(outgoing, key=lambda e: e.probability, reverse=True)

            for edge in sorted_edges:
                neighbor = edge.target
                if neighbor not in path:  # Avoid cycles
                    # Calculate heuristic: estimated best probability to target
                    # Heuristic = edge probability * max possible from neighbor
                    heuristic = edge.probability * 0.95  # Optimistic estimate
                    new_prob = abs(neg_prob) + (-math.log(edge.probability + 1e-10))

                    new_path = path + [neighbor]
                    # Prune if cumulative probability is too low
                    if edge.probability < min_probability * 0.5:
                        continue

                    heapq.heappush(open_set, (-new_prob, length + 1, new_path))

        return paths

    def find_attack_paths_with_diversification(
        self,
        graph: AttackGraph,
        target: str,
        max_paths: int = 10,
        min_probability: float = 0.1,
    ) -> List[AttackPath]:
        """
        Find diverse attack paths covering different entry points.

        Useful for security assessment - finds paths that use different
        vulnerabilities or entry methods rather than variations of the same path.
        """
        if target not in graph.nodes:
            return []

        network_nodes = [
            n.id for n in graph.nodes.values()
            if n.type == NodeType.NETWORK
        ]

        if not network_nodes:
            return []

        # Track which entry nodes/vulns have been covered
        covered_entries: Set[str] = set()
        covered_vulns: Set[str] = set()

        all_paths: List[AttackPath] = []

        for network in network_nodes:
            raw_paths = self._find_paths_astar(
                graph, network, target,
                max_paths=max_paths * 2,  # Find more to filter
                max_depth=20,
                min_probability=min_probability,
            )

            for raw_path in raw_paths:
                attack_path = self._build_attack_path(graph, raw_path)
                if attack_path.probability < min_probability:
                    continue

                # Check diversity
                entry_node = raw_path[0] if raw_path else ""
                vuln_ids = set(
                    e.cve_id for e in attack_path.edges
                    if e.cve_id
                )

                # Skip if too similar to existing paths
                if entry_node in covered_entries and vuln_ids.issubset(covered_vulns):
                    # But still include if it's significantly better
                    if not all_paths or attack_path.risk_score > all_paths[0].risk_score * 1.5:
                        all_paths.append(attack_path)
                        covered_vulns.update(vuln_ids)
                    continue

                all_paths.append(attack_path)
                covered_entries.add(entry_node)
                covered_vulns.update(vuln_ids)

                if len(all_paths) >= max_paths:
                    break

            if len(all_paths) >= max_paths:
                break

        return sorted(all_paths, key=lambda p: p.risk_score, reverse=True)[:max_paths]

    def _build_attack_path(self, graph: AttackGraph, node_path: List[str]) -> AttackPath:
        """Build an AttackPath from node IDs."""
        edges: List[AttackEdge] = []
        prob = 1.0
        impact = 0.0

        for i in range(len(node_path) - 1):
            src, tgt = node_path[i], node_path[i + 1]
            edge = graph.get_edge_by_nodes(src, tgt)
            if edge:
                edges.append(edge)
                prob *= edge.probability
            tgt_node = graph.nodes.get(tgt)
            if tgt_node:
                impact += self._calculate_node_impact(tgt_node)

        risk_score = prob * impact
        return AttackPath(
            nodes=node_path,
            edges=edges,
            probability=prob,
            impact=impact,
            risk_score=risk_score,
        )

    def _calculate_node_impact(self, node: AttackNode) -> float:
        """Calculate impact score for a node."""
        base_impact = 1.0

        if node.type == NodeType.VULNERABILITY:
            severity = node.properties.get("severity", 0)
            base_impact = min(10.0, severity)
        elif node.type == NodeType.HOST:
            base_impact = 5.0
        elif node.type == NodeType.CREDENTIAL:
            base_impact = 7.0
        elif node.type == NodeType.SERVICE:
            base_impact = 3.0

        return base_impact * node.confidence

    def calculate_risk_score(self, graph: AttackGraph) -> float:
        """
        Calculate overall risk score for the graph.

        Higher score = more dangerous attack surface.
        """
        if not graph.nodes:
            return 0.0

        total_risk = 0.0
        for node in graph.nodes.values():
            if node.type == NodeType.VULNERABILITY:
                severity = node.properties.get("severity", 0)
                weight = self._risk_weights.get(node.type, 0.2)
                total_risk += severity * weight * node.confidence

        # Consider graph connectivity
        connectivity = graph.edge_count() / max(1, graph.node_count())
        total_risk *= (1 + connectivity * 0.5)

        return min(100.0, total_risk)

    def find_critical_nodes(
        self,
        graph: AttackGraph,
        top_n: int = 10,
        sample_paths: int = 50,
    ) -> List[AttackNode]:
        """
        Find the most critical nodes using betweenness centrality approximation.

        Critical nodes are those that appear on many attack paths.
        Uses sampling for large graphs to avoid combinatorial explosion.

        Args:
            graph: Attack graph
            top_n: Number of critical nodes to return
            sample_paths: Max paths to sample (controls performance)
        """
        node_scores: Dict[str, float] = {nid: 0.0 for nid in graph.nodes}

        network_nodes = [
            n.id for n in graph.nodes.values()
            if n.type == NodeType.NETWORK
        ]

        # Limit sampling for large graphs
        target_nodes = [
            nid for nid, node in graph.nodes.items()
            if node.type in (NodeType.HOST, NodeType.VULNERABILITY)
        ]

        # If too many targets, sample a representative subset
        if len(target_nodes) > 20:
            import random
            random.seed(42)  # Deterministic sampling
            target_nodes = random.sample(target_nodes, 20)

        paths_sampled = 0
        for target in target_nodes:
            if paths_sampled >= sample_paths:
                break
            for network in network_nodes:
                if paths_sampled >= sample_paths:
                    break
                # Use A* with limited depth for efficiency
                paths = self._find_paths_astar(
                    graph, network, target,
                    max_paths=min(10, sample_paths - paths_sampled),
                    max_depth=15,
                    min_probability=0.05,
                )
                for path in paths:
                    paths_sampled += 1
                    for node_id in path:
                        if node_id in node_scores:
                            node_scores[node_id] += 1.0

        # Sort by score
        sorted_nodes = sorted(
            node_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_n]

        return [graph.nodes[nid] for nid, _ in sorted_nodes if nid in graph.nodes]

    def simulate_attack(
        self,
        graph: AttackGraph,
        path: List[str],
        exploitation_success_prob: float = 0.7,
    ) -> AttackResult:
        """
        Simulate an attack along a given path.

        Returns simulation result with success/failure status.
        """
        import random

        compromised: List[str] = []

        for i, node_id in enumerate(path):
            if node_id not in graph.nodes:
                return AttackResult(
                    success=False,
                    path=path,
                    compromised_nodes=compromised,
                    failed_at=node_id,
                    error=f"Node {node_id} not found",
                )

            node = graph.nodes[node_id]

            # Check if exploitation succeeds
            if node.type == NodeType.VULNERABILITY:
                severity = node.properties.get("severity", 0)
                success_prob = min(0.95, exploitation_success_prob * (severity / 10.0))
                if random.random() > success_prob:
                    return AttackResult(
                        success=False,
                        path=path,
                        compromised_nodes=compromised,
                        failed_at=node_id,
                        error="Exploitation failed",
                    )

            compromised.append(node_id)

        # All nodes compromised
        return AttackResult(
            success=True,
            path=path,
            compromised_nodes=compromised,
        )

    def generate_mitigation(self, graph: AttackGraph) -> List[MitigationAction]:
        """
        Generate prioritized mitigation recommendations.

        Prioritizes actions that block the highest-risk paths.
        """
        mitigations: List[MitigationAction] = []
        critical_nodes = self.find_critical_nodes(graph, top_n=10)
        vuln_nodes = [
            n for n in graph.nodes.values()
            if n.type == NodeType.VULNERABILITY
        ]

        # Sort vulnerabilities by severity
        vuln_nodes.sort(
            key=lambda n: n.properties.get("severity", 0),
            reverse=True,
        )

        priority = 1
        added_mitigations: Set[str] = set()

        # Mitigate high-severity vulnerabilities first
        for vuln in vuln_nodes[:5]:
            cve_id = vuln.properties.get("cve_id", vuln.id)
            key = f"patch_{cve_id}"
            if key not in added_mitigations:
                mitigations.append(MitigationAction(
                    target_node=vuln.id,
                    action_type="patch",
                    description=f"Patch vulnerability {cve_id}: {vuln.name}",
                    priority=priority,
                    estimated_effort="medium" if vuln.properties.get("severity", 0) > 7 else "low",
                ))
                added_mitigations.add(key)
                priority += 1

        # Isolate critical hosts
        for node in critical_nodes:
            if node.type == NodeType.HOST:
                key = f"isolate_{node.id}"
                if key not in added_mitigations:
                    mitigations.append(MitigationAction(
                        target_node=node.id,
                        action_type="isolate",
                        description=f"Isolate or restrict access to {node.name}",
                        priority=priority,
                        estimated_effort="medium",
                    ))
                    added_mitigations.add(key)
                    priority += 1

        # Add network segmentation
        mitigations.append(MitigationAction(
            target_node="network",
            action_type="segment",
            description="Implement network segmentation to limit lateral movement",
            priority=priority,
            estimated_effort="high",
        ))

        return mitigations

    def find_shortest_exploit_path(
        self,
        graph: AttackGraph,
        target_host: str,
    ) -> Optional[AttackPath]:
        """Find the shortest path to exploit a target host."""
        network_nodes = [
            n.id for n in graph.nodes.values()
            if n.type == NodeType.NETWORK
        ]

        shortest: Optional[AttackPath] = None
        for network in network_nodes:
            path_nodes = graph.find_shortest_path(network, target_host)
            if path_nodes:
                attack_path = self._build_attack_path(graph, path_nodes)
                if shortest is None or attack_path.risk_score > shortest.risk_score:
                    shortest = attack_path

        return shortest

    def assess_lateral_movement_risk(
        self,
        graph: AttackGraph,
        compromised_host: str,
    ) -> List[Tuple[str, float]]:
        """
        Assess risk of lateral movement from a compromised host.

        Returns list of (target_host_id, risk_score) pairs.
        """
        risks: List[Tuple[str, float]] = []

        outgoing = graph.get_outgoing_edges(compromised_host)
        for edge in outgoing:
            if edge.type == EdgeType.LATERAL:
                target = edge.target
                if target in graph.nodes:
                    target_node = graph.nodes[target]
                    # Risk based on accessible vulnerabilities
                    vulns = [
                        n for n in graph.nodes.values()
                        if n.type == NodeType.VULNERABILITY
                        and n.properties.get("host") == target_node.properties.get("ip")
                    ]
                    vuln_severity = sum(
                        v.properties.get("severity", 0)
                        for v in vulns
                    )
                    risk = edge.probability * (1 + vuln_severity * 0.1)
                    risks.append((target, risk))

        return sorted(risks, key=lambda x: x[1], reverse=True)
