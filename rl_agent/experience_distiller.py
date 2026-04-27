"""
Automated Experience Distillation and Generalization System

Uses LLM to automatically analyze penetration test sessions, extract generalizable
attack patterns, tool combination techniques, and product-specific vulnerability
configuration patterns. Converts these into structured knowledge to feed back to
the RAG database and expert system.
"""

import json
import logging
import time
import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class AttackPattern:
    """
    A generalized attack pattern extracted from successful sessions.

    Represents a reusable attack methodology that can be applied
    to similar target configurations.
    """
    pattern_id: str
    name: str
    description: str
    prerequisites: List[str]  # Required conditions before execution
    steps: List[dict]  # Ordered attack steps with actions
    success_conditions: List[str]  # How to verify success
    applicability: List[str]  # When to use this pattern
    confidence: float  # 0-1, based on success rate
    source_sessions: List[str]  # Session IDs where this was observed

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'AttackPattern':
        return cls(**data)

    def to_rag_document(self) -> dict:
        """Convert to RAG document format for knowledge storage."""
        content = f"""# Attack Pattern: {self.name}

## Description
{self.description}

## Prerequisites
{chr(10).join(f"- {p}" for p in self.prerequisites)}

## Attack Steps
{self._format_steps()}

## Success Conditions
{chr(10).join(f"- {c}" for c in self.success_conditions)}

## Applicability
{chr(10).join(f"- {a}" for a in self.applicability)}

## Confidence: {self.confidence:.2f}
"""
        return {
            "id": self.pattern_id,
            "content": content,
            "doc_type": "attack_pattern",
            "metadata": {
                "name": self.name,
                "confidence": self.confidence,
                "prerequisites": self.prerequisites,
                "source_sessions": self.source_sessions,
            }
        }

    def _format_steps(self) -> str:
        """Format steps as markdown."""
        lines = []
        for i, step in enumerate(self.steps, 1):
            action = step.get("action", "unknown")
            target = step.get("target", "")
            tool = step.get("tool", "")
            lines.append(f"{i}. {action}" + (f" -> {target}" if target else "") +
                        (f" (tool: {tool})" if tool else ""))
        return chr(10).join(lines)


@dataclass
class ToolCombination:
    """
    A successful combination of tools used in sequence.

    Captures effective tool chaining patterns that lead to
    successful exploitation or objective completion.
    """
    combo_id: str
    tools: List[str]  # Ordered tool chain
    purpose: str  # What this combination achieves
    success_rate: float  # Historical success rate
    context: str  # When this combination is effective

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ToolCombination':
        return cls(**data)

    def to_rag_document(self) -> dict:
        """Convert to RAG document format."""
        content = f"""# Tool Combination: {' -> '.join(self.tools)}

## Purpose
{self.purpose}

## Tool Sequence
{chr(10).join(f"{i+1}. {tool}" for i, tool in enumerate(self.tools))}

## Success Rate
{self.success_rate:.1%}

## Effective Context
{self.context}
"""
        return {
            "id": self.combo_id,
            "content": content,
            "doc_type": "tool_combination",
            "metadata": {
                "tools": self.tools,
                "success_rate": self.success_rate,
                "purpose": self.purpose,
            }
        }


@dataclass
class VulnerabilityConfig:
    """
    Product-specific vulnerability configuration pattern.

    Captures misconfigurations and their exploitation methods
    for specific product/version combinations.
    """
    config_id: str
    product: str
    version: str
    misconfiguration: str  # The specific misconfiguration
    exploitation_method: str  # How to exploit it
    detection_difficulty: float  # 0-1, higher = harder to detect

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'VulnerabilityConfig':
        return cls(**data)

    def to_rag_document(self) -> dict:
        """Convert to RAG document format."""
        content = f"""# Vulnerability Configuration: {self.product} {self.version}

## Misconfiguration
{self.misconfiguration}

## Exploitation Method
{self.exploitation_method}

## Detection Difficulty
{self.detection_difficulty:.1f}/1.0

## Product
- Product: {self.product}
- Version: {self.version}
"""
        return {
            "id": self.config_id,
            "content": content,
            "doc_type": "vuln_config",
            "metadata": {
                "product": self.product,
                "version": self.version,
                "detection_difficulty": self.detection_difficulty,
            }
        }


class ExperienceDistiller:
    """
    Automated Experience Distillation and Generalization System.

    Analyzes penetration test sessions to extract:
    - Generalized attack patterns
    - Effective tool combinations
    - Product-specific vulnerability configurations

    Uses LLM for intelligent analysis when available, falls back
    to rule-based pattern extraction otherwise.
    """

    # Pattern templates for rule-based extraction
    SUCCESS_PATTERNS = [
        (r"ssh.*brute.*force", "SSH Brute Force Attack"),
        (r"smb.*enum", "SMB Enumeration"),
        (r"sql.*inject", "SQL Injection Attack"),
        (r"buffer.*overflow", "Buffer Overflow Exploit"),
        (r"privilege.*escalat", "Privilege Escalation"),
        (r"lateral.*move", "Lateral Movement"),
        (r"credential.*dump", "Credential Dumping"),
        (r"pass.*spray", "Password Spraying"),
        (r"kerberos.*attack", "Kerberos Attack"),
        (r"deserialization", "Deserialization Attack"),
    ]

    TOOL_SEQUENCES = {
        ("nmap", "hydra"): "Network discovery followed by credential brute force",
        ("nmap", "nikto"): "Network discovery followed by web vulnerability scan",
        ("nmap", "smbclient"): "Network discovery followed by SMB enumeration",
        ("enum4linux", "crackmapexec"): "SMB enumeration followed by credential testing",
        ("linpeas", "gtfobins"): "Linux privilege escalation chain",
        ("winpeas", "mimikatz"): "Windows privilege escalation chain",
        ("bloodhound", "crackmapexec"): "AD enumeration followed by credential testing",
        ("kerberoast", "hashcat"): "Kerberos ticket extraction and cracking",
    }

    def __init__(
        self,
        llm_planner=None,
        rag_retriever=None,
        lessons_db=None,
        storage_path: str = "data/distilled_knowledge",
    ):
        """
        Initialize the experience distiller.

        Args:
            llm_planner: LLM attack planner for intelligent analysis
            rag_retriever: RAG retriever for knowledge publishing
            lessons_db: Lessons learned database for cross-session learning
            storage_path: Path to store distilled knowledge
        """
        self.llm_planner = llm_planner
        self.rag_retriever = rag_retriever
        self.lessons_db = lessons_db
        self.storage_path = storage_path

        # In-memory storage for extracted patterns
        self.attack_patterns: Dict[str, AttackPattern] = {}
        self.tool_combinations: Dict[str, ToolCombination] = {}
        self.vuln_configs: Dict[str, VulnerabilityConfig] = {}

        # Statistics
        self.stats = {
            "sessions_processed": 0,
            "patterns_extracted": 0,
            "tool_combos_extracted": 0,
            "vuln_configs_extracted": 0,
            "published_to_rag": 0,
            "llm_analyses": 0,
            "rule_based_extractions": 0,
        }

    def distill_session(self, session_data: dict) -> dict:
        """
        Analyze a complete session and extract all knowledge.

        Args:
            session_data: Dict containing:
                - session_id: str
                - actions: List[dict] - actions taken
                - results: List[dict] - results of actions
                - findings: List[dict] - discovered vulnerabilities/configs
                - success: bool - whether session achieved objectives
                - reward: float - total reward
                - reflections: List[dict] - agent reflections (optional)

        Returns:
            Dict with extracted patterns, combos, and configs
        """
        session_id = session_data.get("session_id", f"session_{int(time.time())}")
        actions = session_data.get("actions", [])
        results = session_data.get("results", [])
        findings = session_data.get("findings", [])
        success = session_data.get("success", False)
        reward = session_data.get("reward", 0.0)

        logger.info(f"Distilling session {session_id}: {len(actions)} actions, success={success}")

        extracted = {
            "patterns": [],
            "combos": [],
            "configs": [],
            "session_id": session_id,
        }

        # Extract attack patterns
        if success or reward > 0.5:
            patterns = self.extract_attack_patterns(actions)
            for pattern in patterns:
                pattern.source_sessions.append(session_id)
                self._store_pattern(pattern)
            extracted["patterns"] = patterns

        # Extract tool combinations
        combos = self.extract_tool_combinations(actions)
        for combo in combos:
            self._store_combo(combo)
        extracted["combos"] = combos

        # Extract vulnerability configurations
        configs = self.extract_vuln_configs(findings)
        for config in configs:
            self._store_config(config)
        extracted["configs"] = configs

        # Update lessons database
        if self.lessons_db and success:
            self._update_lessons(session_id, actions, results, findings)

        # Update statistics
        self.stats["sessions_processed"] += 1
        self.stats["patterns_extracted"] += len(extracted["patterns"])
        self.stats["tool_combos_extracted"] += len(extracted["combos"])
        self.stats["vuln_configs_extracted"] += len(extracted["configs"])

        return extracted

    def extract_attack_patterns(self, actions: List[dict]) -> List[AttackPattern]:
        """
        Extract generalized attack patterns from action sequences.

        Uses LLM for intelligent pattern recognition when available,
        falls back to rule-based extraction.

        Args:
            actions: List of action dictionaries with type, target, params, result

        Returns:
            List of AttackPattern objects
        """
        if not actions:
            return []

        patterns = []

        # Try LLM-based extraction first
        if self.llm_planner:
            try:
                llm_patterns = self._extract_patterns_with_llm(actions)
                if llm_patterns:
                    patterns.extend(llm_patterns)
                    self.stats["llm_analyses"] += 1
            except Exception as e:
                logger.warning(f"LLM pattern extraction failed: {e}, using rule-based")

        # Fall back to rule-based extraction
        if not patterns:
            rule_patterns = self._extract_patterns_rule_based(actions)
            patterns.extend(rule_patterns)
            self.stats["rule_based_extractions"] += 1

        return patterns

    def extract_tool_combinations(self, action_sequence: List[dict]) -> List[ToolCombination]:
        """
        Extract effective tool combinations from action sequences.

        Identifies tool chains that work well together based on
        sequential usage patterns and success indicators.

        Args:
            action_sequence: List of action dictionaries

        Returns:
            List of ToolCombination objects
        """
        if not action_sequence:
            return []

        combos = []

        # Extract tools used
        tools_used = []
        for action in action_sequence:
            tool = action.get("tool") or action.get("parameters", {}).get("tool")
            if tool:
                tools_used.append(tool.lower())

        # Find known effective sequences
        for seq, purpose in self.TOOL_SEQUENCES.items():
            if self._is_subsequence(list(seq), tools_used):
                combo_id = self._generate_id(f"combo_{'_'.join(seq)}")
                combo = ToolCombination(
                    combo_id=combo_id,
                    tools=list(seq),
                    purpose=purpose,
                    success_rate=self._calculate_success_rate(seq),
                    context=f"Effective for {purpose.lower()}",
                )
                combos.append(combo)

        # Discover new tool combinations
        new_combos = self._discover_tool_combos(tools_used, action_sequence)
        combos.extend(new_combos)

        return combos

    def extract_vuln_configs(self, findings: List[dict]) -> List[VulnerabilityConfig]:
        """
        Extract product-specific vulnerability configurations.

        Analyzes findings to identify misconfigurations and their
        exploitation methods.

        Args:
            findings: List of finding dictionaries with product, version, vuln info

        Returns:
            List of VulnerabilityConfig objects
        """
        if not findings:
            return []

        configs = []

        for finding in findings:
            product = finding.get("product") or finding.get("service", "unknown")
            version = finding.get("version", "unknown")
            vuln = finding.get("vulnerability") or finding.get("cve_id", "")
            misconfig = finding.get("misconfiguration") or finding.get("finding", "")
            exploit_method = finding.get("exploitation_method") or finding.get("solution", "")

            if misconfig and product != "unknown":
                config_id = self._generate_id(f"vuln_{product}_{version}_{misconfig}")
                config = VulnerabilityConfig(
                    config_id=config_id,
                    product=product,
                    version=version,
                    misconfiguration=misconfig,
                    exploitation_method=exploit_method,
                    detection_difficulty=finding.get("detection_difficulty", 0.5),
                )
                configs.append(config)

        # Try LLM-based extraction for more detailed configs
        if self.llm_planner and findings:
            try:
                llm_configs = self._extract_vuln_configs_with_llm(findings)
                # Merge with rule-based, preferring LLM results
                existing_ids = {c.config_id for c in configs}
                for config in llm_configs:
                    if config.config_id not in existing_ids:
                        configs.append(config)
            except Exception as e:
                logger.warning(f"LLM vuln config extraction failed: {e}")

        return configs

    def generalize_pattern(self, pattern: AttackPattern) -> AttackPattern:
        """
        Make a pattern more general and applicable to more situations.

        Uses LLM for intelligent generalization when available.

        Args:
            pattern: The pattern to generalize

        Returns:
            A generalized AttackPattern
        """
        if not self.llm_planner:
            return self._rule_based_generalize(pattern)

        try:
            prompt = f"""Generalize this attack pattern to be applicable to more situations while preserving its core methodology:

Pattern: {pattern.name}
Description: {pattern.description}
Steps: {json.dumps(pattern.steps, ensure_ascii=False)}
Prerequisites: {pattern.prerequisites}

Create a generalized version that:
1. Removes specific IPs, hostnames, or target-specific values
2. Uses generic service names instead of specific ports
3. Abstracts tool parameters to their essential options
4. Broadens applicability conditions

Return JSON:
{{
    "name": "Generalized pattern name",
    "description": "Generalized description",
    "prerequisites": ["generic prerequisite 1", ...],
    "steps": [{{"action": "...", "description": "..."}}, ...],
    "applicability": ["when to use 1", ...]
}}"""
            # Use the LLM extractor's API call method
            messages = [
                {"role": "system", "content": "You are a penetration testing expert specializing in pattern generalization."},
                {"role": "user", "content": prompt},
            ]

            response = self.llm_planner.extractor._call_api(
                messages, use_json_mode=True, temperature=0.3
            )
            result = self.llm_planner.extractor._parse_json_response(response)

            generalized = AttackPattern(
                pattern_id=pattern.pattern_id + "_gen",
                name=result.get("name", pattern.name),
                description=result.get("description", pattern.description),
                prerequisites=result.get("prerequisites", pattern.prerequisites),
                steps=result.get("steps", pattern.steps),
                success_conditions=pattern.success_conditions,
                applicability=result.get("applicability", pattern.applicability),
                confidence=pattern.confidence * 0.9,  # Slightly lower for generalized
                source_sessions=pattern.source_sessions.copy(),
            )
            return generalized

        except Exception as e:
            logger.warning(f"LLM generalization failed: {e}")
            return self._rule_based_generalize(pattern)

    def publish_to_rag(
        self,
        patterns: List[AttackPattern] = None,
        combos: List[ToolCombination] = None,
        configs: List[VulnerabilityConfig] = None,
    ) -> int:
        """
        Publish extracted knowledge to RAG knowledge base.

        Args:
            patterns: Patterns to publish (default: all stored)
            combos: Tool combinations to publish (default: all stored)
            configs: Vulnerability configs to publish (default: all stored)

        Returns:
            Number of documents published
        """
        if not self.rag_retriever:
            logger.warning("No RAG retriever configured, cannot publish")
            return 0

        published_count = 0

        # Get items to publish
        patterns = patterns or list(self.attack_patterns.values())
        combos = combos or list(self.tool_combinations.values())
        configs = configs or list(self.vuln_configs.values())

        store = self.rag_retriever.store

        # Publish patterns
        for pattern in patterns:
            try:
                doc_data = pattern.to_rag_document()
                from models.vector_store import Document
                doc = Document(
                    id=doc_data["id"],
                    content=doc_data["content"],
                    metadata=doc_data["metadata"],
                    doc_type=doc_data["doc_type"],
                )
                store.add_documents([doc], collection="attack_patterns")
                published_count += 1
            except Exception as e:
                logger.warning(f"Failed to publish pattern {pattern.pattern_id}: {e}")

        # Publish tool combinations
        for combo in combos:
            try:
                doc_data = combo.to_rag_document()
                from models.vector_store import Document
                doc = Document(
                    id=doc_data["id"],
                    content=doc_data["content"],
                    metadata=doc_data["metadata"],
                    doc_type=doc_data["doc_type"],
                )
                store.add_documents([doc], collection="tool_combinations")
                published_count += 1
            except Exception as e:
                logger.warning(f"Failed to publish combo {combo.combo_id}: {e}")

        # Publish vulnerability configs
        for config in configs:
            try:
                doc_data = config.to_rag_document()
                from models.vector_store import Document
                doc = Document(
                    id=doc_data["id"],
                    content=doc_data["content"],
                    metadata=doc_data["metadata"],
                    doc_type=doc_data["doc_type"],
                )
                store.add_documents([doc], collection="vuln_configs")
                published_count += 1
            except Exception as e:
                logger.warning(f"Failed to publish config {config.config_id}: {e}")

        self.stats["published_to_rag"] += published_count
        logger.info(f"Published {published_count} documents to RAG")

        return published_count

    def get_distillation_stats(self) -> dict:
        """
        Get statistics about the distillation process.

        Returns:
            Dict with processing counts and storage status
        """
        return {
            **self.stats,
            "stored_patterns": len(self.attack_patterns),
            "stored_combos": len(self.tool_combinations),
            "stored_configs": len(self.vuln_configs),
            "llm_available": self.llm_planner is not None,
            "rag_available": self.rag_retriever is not None,
            "lessons_db_available": self.lessons_db is not None,
        }

    # Private methods

    def _extract_patterns_with_llm(self, actions: List[dict]) -> List[AttackPattern]:
        """Use LLM to extract attack patterns from actions."""
        if not self.llm_planner:
            return []

        # Format actions for LLM analysis
        action_descriptions = []
        for action in actions:
            desc = f"- {action.get('type', 'unknown')}: {action.get('target', '')}"
            params = action.get("parameters", {})
            if params:
                desc += f" params={json.dumps(params)}"
            result = action.get("result", "")
            if result:
                desc += f" -> {result}"
            action_descriptions.append(desc)

        prompt = f"""Analyze this penetration test action sequence and extract generalized attack patterns:

Actions:
{chr(10).join(action_descriptions)}

Identify:
1. The attack methodology used
2. Key steps in the attack chain
3. Prerequisites for success
4. Success indicators
5. When this pattern is applicable

Return JSON array of patterns:
[
  {{
    "name": "Pattern name",
    "description": "What this pattern achieves",
    "prerequisites": ["required condition 1", ...],
    "steps": [
      {{"action": "action_type", "target": "target pattern", "tool": "optional tool"}},
      ...
    ],
    "success_conditions": ["how to verify success", ...],
    "applicability": ["when to use this", ...],
    "confidence": 0.8
  }}
]"""

        try:
            messages = [
                {"role": "system", "content": "You are a penetration testing expert specializing in pattern extraction."},
                {"role": "user", "content": prompt},
            ]

            response = self.llm_planner.extractor._call_api(
                messages, use_json_mode=True, temperature=0.3
            )
            result = self.llm_planner.extractor._parse_json_response(response)

            patterns = []
            if isinstance(result, list):
                for p in result:
                    pattern_id = self._generate_id(p.get("name", "pattern"))
                    pattern = AttackPattern(
                        pattern_id=pattern_id,
                        name=p.get("name", "Unnamed Pattern"),
                        description=p.get("description", ""),
                        prerequisites=p.get("prerequisites", []),
                        steps=p.get("steps", []),
                        success_conditions=p.get("success_conditions", []),
                        applicability=p.get("applicability", []),
                        confidence=p.get("confidence", 0.7),
                        source_sessions=[],
                    )
                    patterns.append(pattern)

            return patterns

        except Exception as e:
            logger.error(f"LLM pattern extraction error: {e}")
            return []

    def _extract_patterns_rule_based(self, actions: List[dict]) -> List[AttackPattern]:
        """Extract patterns using rule-based matching."""
        patterns = []
        action_types = [a.get("type", "").lower() for a in actions]
        action_str = " ".join(action_types)

        # Match known patterns
        for pattern_regex, pattern_name in self.SUCCESS_PATTERNS:
            if re.search(pattern_regex, action_str):
                pattern_id = self._generate_id(pattern_name)

                # Extract steps from matching actions
                steps = []
                for action in actions:
                    if any(kw in action.get("type", "").lower() for kw in pattern_regex.split(".*")):
                        steps.append({
                            "action": action.get("type", ""),
                            "target": self._generalize_target(action.get("target", "")),
                            "tool": action.get("parameters", {}).get("tool", ""),
                        })

                pattern = AttackPattern(
                    pattern_id=pattern_id,
                    name=pattern_name,
                    description=f"Automatically extracted {pattern_name} pattern",
                    prerequisites=self._infer_prerequisites(pattern_name),
                    steps=steps,
                    success_conditions=[f"Successful {pattern_name}"],
                    applicability=self._infer_applicability(pattern_name),
                    confidence=0.6,
                    source_sessions=[],
                )
                patterns.append(pattern)

        # Detect sequential patterns
        sequential_patterns = self._detect_sequential_patterns(actions)
        patterns.extend(sequential_patterns)

        return patterns

    def _detect_sequential_patterns(self, actions: List[dict]) -> List[AttackPattern]:
        """Detect patterns from action sequences."""
        patterns = []

        # Look for reconnaissance -> exploitation patterns
        recon_actions = [a for a in actions if "scan" in a.get("type", "").lower() or "enum" in a.get("type", "").lower()]
        exploit_actions = [a for a in actions if "exploit" in a.get("type", "").lower() or "brute" in a.get("type", "").lower()]

        if recon_actions and exploit_actions:
            pattern_id = self._generate_id("recon_to_exploit")
            pattern = AttackPattern(
                pattern_id=pattern_id,
                name="Reconnaissance-to-Exploitation Chain",
                description="Standard penetration testing workflow: discover then exploit",
                prerequisites=["Network access to target", "Valid credentials or anonymous access"],
                steps=[
                    {"action": "network_scan", "target": "target_network", "description": "Identify live hosts"},
                    {"action": "port_scan", "target": "discovered_hosts", "description": "Identify open ports"},
                    {"action": "service_enumeration", "target": "open_ports", "description": "Enumerate services"},
                    {"action": "vulnerability_scan", "target": "services", "description": "Find vulnerabilities"},
                    {"action": "exploit", "target": "vulnerability", "description": "Exploit identified vulnerability"},
                ],
                success_conditions=["Shell obtained", "Credentials captured", "Data accessed"],
                applicability=["Initial access scenarios", "Unknown network assessment"],
                confidence=0.75,
                source_sessions=[],
            )
            patterns.append(pattern)

        # Look for privilege escalation patterns
        priv_actions = [a for a in actions if "priv" in a.get("type", "").lower() or "escalat" in a.get("type", "").lower()]
        cred_actions = [a for a in actions if "cred" in a.get("type", "").lower() or "dump" in a.get("type", "").lower()]

        if priv_actions and cred_actions:
            pattern_id = self._generate_id("priv_esc_to_cred_dump")
            pattern = AttackPattern(
                pattern_id=pattern_id,
                name="Privilege Escalation to Credential Dumping",
                description="Escalate privileges then dump credentials for lateral movement",
                prerequisites=["Initial shell access", "User-level privileges"],
                steps=[
                    {"action": "privilege_escalation", "target": "local_system", "description": "Escalate to admin/root"},
                    {"action": "credential_dumping", "target": "memory/registry", "description": "Extract credentials"},
                    {"action": "lateral_movement", "target": "other_hosts", "description": "Use credentials to move"},
                ],
                success_conditions=["Admin/root privileges", "Credentials extracted", "Access to additional hosts"],
                applicability=["Post-exploitation", "Domain environment"],
                confidence=0.8,
                source_sessions=[],
            )
            patterns.append(pattern)

        return patterns

    def _discover_tool_combos(self, tools_used: List[str], actions: List[dict]) -> List[ToolCombination]:
        """Discover new tool combinations from usage patterns."""
        combos = []

        # Find consecutive tool usage
        for i in range(len(tools_used) - 1):
            tool1, tool2 = tools_used[i], tools_used[i + 1]

            # Check if this is a new combination
            combo_key = (tool1, tool2)
            if combo_key not in self.TOOL_SEQUENCES:
                # Calculate success rate based on action results
                success_rate = self._calculate_success_rate(combo_key)

                if success_rate > 0.5:  # Only include if reasonably successful
                    combo_id = self._generate_id(f"combo_{tool1}_{tool2}")
                    combo = ToolCombination(
                        combo_id=combo_id,
                        tools=[tool1, tool2],
                        purpose=f"Discovered combination: {tool1} followed by {tool2}",
                        success_rate=success_rate,
                        context=f"Observed success rate: {success_rate:.1%}",
                    )
                    combos.append(combo)

        return combos

    def _extract_vuln_configs_with_llm(self, findings: List[dict]) -> List[VulnerabilityConfig]:
        """Use LLM to extract vulnerability configurations."""
        if not self.llm_planner or not findings:
            return []

        prompt = f"""Analyze these security findings and extract product-specific vulnerability configurations:

Findings:
{json.dumps(findings, ensure_ascii=False, indent=2)}

For each finding, identify:
1. Product and version
2. Specific misconfiguration
3. Exploitation method
4. Detection difficulty

Return JSON array:
[
  {{
    "product": "product name",
    "version": "version",
    "misconfiguration": "specific misconfiguration",
    "exploitation_method": "how to exploit",
    "detection_difficulty": 0.7
  }}
]"""

        try:
            messages = [
                {"role": "system", "content": "You are a security expert specializing in vulnerability analysis."},
                {"role": "user", "content": prompt},
            ]

            response = self.llm_planner.extractor._call_api(
                messages, use_json_mode=True, temperature=0.3
            )
            result = self.llm_planner.extractor._parse_json_response(response)

            configs = []
            if isinstance(result, list):
                for c in result:
                    config_id = self._generate_id(f"vuln_{c.get('product', 'unknown')}_{c.get('version', 'unknown')}")
                    config = VulnerabilityConfig(
                        config_id=config_id,
                        product=c.get("product", "unknown"),
                        version=c.get("version", "unknown"),
                        misconfiguration=c.get("misconfiguration", ""),
                        exploitation_method=c.get("exploitation_method", ""),
                        detection_difficulty=c.get("detection_difficulty", 0.5),
                    )
                    configs.append(config)

            return configs

        except Exception as e:
            logger.error(f"LLM vuln config extraction error: {e}")
            return []

    def _rule_based_generalize(self, pattern: AttackPattern) -> AttackPattern:
        """Apply rule-based generalization to a pattern."""
        # Remove specific IPs, hostnames
        generalized_steps = []
        for step in pattern.steps:
            gen_step = step.copy()
            target = gen_step.get("target", "")
            gen_step["target"] = self._generalize_target(target)
            generalized_steps.append(gen_step)

        # Generalize prerequisites
        gen_prereqs = []
        for prereq in pattern.prerequisites:
            gen_prereqs.append(self._generalize_text(prereq))

        # Generalize applicability
        gen_applicability = []
        for app in pattern.applicability:
            gen_applicability.append(self._generalize_text(app))

        return AttackPattern(
            pattern_id=pattern.pattern_id + "_gen",
            name=pattern.name,
            description=pattern.description,
            prerequisites=gen_prereqs,
            steps=generalized_steps,
            success_conditions=pattern.success_conditions,
            applicability=gen_applicability,
            confidence=pattern.confidence * 0.9,
            source_sessions=pattern.source_sessions.copy(),
        )

    def _generalize_target(self, target: str) -> str:
        """Generalize a specific target to a pattern."""
        if not target:
            return ""

        # Replace IPs
        target = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<ip>', target)

        # Replace ports
        target = re.sub(r':(\d+)', ':<port>', target)

        # Replace specific hostnames
        target = re.sub(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', '<hostname>', target)

        return target

    def _generalize_text(self, text: str) -> str:
        """Generalize text by removing specific values."""
        # Remove IPs
        text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<ip>', text)

        # Remove specific hostnames
        text = re.sub(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', '<hostname>', text)

        # Remove usernames
        text = re.sub(r'user:\s*\w+', 'user: <username>', text)

        return text

    def _infer_prerequisites(self, pattern_name: str) -> List[str]:
        """Infer prerequisites for a pattern based on its name."""
        prereqs_map = {
            "SSH Brute Force Attack": ["SSH service accessible", "Username list"],
            "SMB Enumeration": ["SMB service accessible", "Port 445 open"],
            "SQL Injection Attack": ["Web application with input fields", "Database backend"],
            "Privilege Escalation": ["Initial shell access", "User-level privileges"],
            "Lateral Movement": ["Valid credentials", "Access to internal network"],
            "Credential Dumping": ["Admin/root privileges", "Shell access"],
        }
        return prereqs_map.get(pattern_name, ["Appropriate access level"])

    def _infer_applicability(self, pattern_name: str) -> List[str]:
        """Infer applicability conditions for a pattern."""
        app_map = {
            "SSH Brute Force Attack": ["SSH service detected", "Password authentication enabled"],
            "SMB Enumeration": ["Windows environment", "SMB signing disabled"],
            "SQL Injection Attack": ["Web application testing", "Input validation testing"],
            "Privilege Escalation": ["Post-exploitation", "User shell obtained"],
            "Lateral Movement": ["Domain environment", "Multiple hosts accessible"],
            "Credential Dumping": ["Post-exploitation", "Privilege escalation achieved"],
        }
        return app_map.get(pattern_name, ["General penetration testing"])

    def _calculate_success_rate(self, tool_sequence) -> float:
        """Calculate success rate for a tool sequence."""
        # Check if we have historical data
        if isinstance(tool_sequence, tuple):
            key = tuple(tool_sequence) if isinstance(tool_sequence, list) else tool_sequence
            if key in self.TOOL_SEQUENCES:
                # Known sequence - assume moderate success
                return 0.7

        # Default for new combinations
        return 0.5

    def _is_subsequence(self, sub: List[str], main: List[str]) -> bool:
        """Check if sub is a subsequence of main."""
        it = iter(main)
        return all(any(c == ch for c in it) for ch in sub)

    def _store_pattern(self, pattern: AttackPattern) -> None:
        """Store a pattern in memory."""
        if pattern.pattern_id in self.attack_patterns:
            # Merge with existing
            existing = self.attack_patterns[pattern.pattern_id]
            existing.source_sessions.extend(pattern.source_sessions)
            existing.confidence = min(1.0, existing.confidence + 0.1)
        else:
            self.attack_patterns[pattern.pattern_id] = pattern

    def _store_combo(self, combo: ToolCombination) -> None:
        """Store a tool combination in memory."""
        if combo.combo_id in self.tool_combinations:
            existing = self.tool_combinations[combo.combo_id]
            # Update success rate with new observation
            existing.success_rate = (existing.success_rate + combo.success_rate) / 2
        else:
            self.tool_combinations[combo.combo_id] = combo

    def _store_config(self, config: VulnerabilityConfig) -> None:
        """Store a vulnerability configuration in memory."""
        if config.config_id not in self.vuln_configs:
            self.vuln_configs[config.config_id] = config

    def _update_lessons(
        self,
        session_id: str,
        actions: List[dict],
        results: List[dict],
        findings: List[dict],
    ) -> None:
        """Update lessons database with distilled knowledge."""
        if not self.lessons_db:
            return

        from rl_agent.lessons_db import Lesson

        # Create a lesson from successful patterns
        for finding in findings:
            if finding.get("severity") in ("high", "critical"):
                lesson_id = self._generate_id(f"lesson_{finding.get('finding', '')}")
                lesson = Lesson(
                    lesson_id=lesson_id,
                    category="success_pattern",
                    description=f"Successful exploitation: {finding.get('finding', 'Unknown')}",
                    context=f"Product: {finding.get('product', 'Unknown')} {finding.get('version', '')}",
                    action_suggestion=finding.get("exploitation_method", ""),
                    confidence=0.7,
                    occurrences=1,
                    success_correlation=1.0,
                    created_at=time.time(),
                    last_seen=time.time(),
                    source_session=session_id,
                )
                self.lessons_db.add_lesson(lesson)

    @staticmethod
    def _generate_id(text: str) -> str:
        """Generate a stable ID from text content."""
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def save(self) -> None:
        """Save all distilled knowledge to disk."""
        import os

        os.makedirs(self.storage_path, exist_ok=True)

        # Save patterns
        patterns_file = os.path.join(self.storage_path, "attack_patterns.json")
        with open(patterns_file, 'w') as f:
            json.dump(
                {pid: p.to_dict() for pid, p in self.attack_patterns.items()},
                f, indent=2, ensure_ascii=False
            )

        # Save combos
        combos_file = os.path.join(self.storage_path, "tool_combinations.json")
        with open(combos_file, 'w') as f:
            json.dump(
                {cid: c.to_dict() for cid, c in self.tool_combinations.items()},
                f, indent=2, ensure_ascii=False
            )

        # Save configs
        configs_file = os.path.join(self.storage_path, "vuln_configs.json")
        with open(configs_file, 'w') as f:
            json.dump(
                {cid: c.to_dict() for cid, c in self.vuln_configs.items()},
                f, indent=2, ensure_ascii=False
            )

        # Save stats
        stats_file = os.path.join(self.storage_path, "stats.json")
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

        logger.info(f"Saved distilled knowledge to {self.storage_path}")

    def load(self) -> bool:
        """Load distilled knowledge from disk."""
        import os

        patterns_file = os.path.join(self.storage_path, "attack_patterns.json")
        if os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                self.attack_patterns = {
                    pid: AttackPattern.from_dict(p) for pid, p in data.items()
                }
                logger.info(f"Loaded {len(self.attack_patterns)} attack patterns")
            except Exception as e:
                logger.warning(f"Failed to load patterns: {e}")

        combos_file = os.path.join(self.storage_path, "tool_combinations.json")
        if os.path.exists(combos_file):
            try:
                with open(combos_file, 'r') as f:
                    data = json.load(f)
                self.tool_combinations = {
                    cid: ToolCombination.from_dict(c) for cid, c in data.items()
                }
                logger.info(f"Loaded {len(self.tool_combinations)} tool combinations")
            except Exception as e:
                logger.warning(f"Failed to load combos: {e}")

        configs_file = os.path.join(self.storage_path, "vuln_configs.json")
        if os.path.exists(configs_file):
            try:
                with open(configs_file, 'r') as f:
                    data = json.load(f)
                self.vuln_configs = {
                    cid: VulnerabilityConfig.from_dict(c) for cid, c in data.items()
                }
                logger.info(f"Loaded {len(self.vuln_configs)} vulnerability configs")
            except Exception as e:
                logger.warning(f"Failed to load configs: {e}")

        stats_file = os.path.join(self.storage_path, "stats.json")
        if os.path.exists(stats_file):
            try:
                with open(stats_file, 'r') as f:
                    self.stats.update(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load stats: {e}")

        return True


# Global instance
_global_distiller: Optional[ExperienceDistiller] = None


def get_experience_distiller(
    llm_planner=None,
    rag_retriever=None,
    lessons_db=None,
) -> ExperienceDistiller:
    """Get or create global experience distiller instance."""
    global _global_distiller

    if _global_distiller is None:
        _global_distiller = ExperienceDistiller(
            llm_planner=llm_planner,
            rag_retriever=rag_retriever,
            lessons_db=lessons_db,
        )
        _global_distiller.load()

    return _global_distiller
