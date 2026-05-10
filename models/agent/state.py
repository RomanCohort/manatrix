"""
Attack State Management

Tracks the current state of an autonomous attack including
discovered hosts, vulnerabilities, credentials, and progress.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
from enum import Enum
from datetime import datetime


class Phase(Enum):
    """Attack phases."""
    PLANNING = "planning"
    RECONNAISSANCE = "reconnaissance"
    VULNERABILITY_SCAN = "vulnerability_scan"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFILTRATION = "data_exfiltration"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Host:
    """Represents a discovered host."""
    ip: str
    hostname: Optional[str] = None
    os: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    services: Dict[int, str] = field(default_factory=dict)
    vulns: List[str] = field(default_factory=list)  # CVE IDs
    compromised: bool = False
    credentials: List[str] = field(default_factory=list)
    last_scanned: Optional[float] = None
    notes: str = ""

    def get_open_services(self) -> List[str]:
        return [f"{port}/{svc}" for port, svc in self.services.items()]


@dataclass
class Vulnerability:
    """Represents a discovered vulnerability."""
    cve_id: str
    host: str
    port: Optional[int] = None
    service: Optional[str] = None
    severity: str = "medium"  # critical, high, medium, low, info
    cvss: Optional[float] = None
    description: str = ""
    exploit_available: bool = False
    exploited: bool = False
    discovered_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "cve_id": self.cve_id,
            "host": self.host,
            "port": self.port,
            "service": self.service,
            "severity": self.severity,
            "cvss": self.cvss,
            "exploit_available": self.exploit_available,
            "exploited": self.exploited,
        }


@dataclass
class Credential:
    """Represents obtained credentials."""
    username: str
    password: Optional[str] = None
    hash: Optional[str] = None
    source: str = ""  # host or service
    privilege: str = "user"  # user, admin, root
    obtained_at: float = field(default_factory=time.time)
    used: bool = False

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "password": "***" if self.password else None,
            "hash": self.hash[:20] + "..." if self.hash else None,
            "source": self.source,
            "privilege": self.privilege,
        }


@dataclass
class AttackAction:
    """A single action in the attack."""
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""  # scan, exploit, brute, move, dump, exfil
    target: str = ""
    tool: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    phase: Phase = Phase.PLANNING
    status: str = "pending"  # pending, running, success, failure, skipped
    result: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    reward: float = 0.0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "type": self.type,
            "target": self.target,
            "tool": self.tool,
            "params": self.params,
            "phase": self.phase.value,
            "status": self.status,
            "result": self.result,
            "reward": self.reward,
        }


@dataclass
class AttackState:
    """
    Current state of an autonomous attack.

    This is the central state object that gets passed through
    the entire attack pipeline.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    phase: Phase = Phase.PLANNING
    started_at: float = field(default_factory=time.time)

    # Discovery
    hosts: Dict[str, Host] = field(default_factory=dict)  # ip -> Host
    vulns: List[Vulnerability] = field(default_factory=list)
    creds: List[Credential] = field(default_factory=list)

    # Progress
    actions: List[AttackAction] = field(default_factory=list)
    current_objective: str = ""
    completed_objectives: List[str] = field(default_factory=list)

    # Context
    targets: List[str] = field(default_factory=list)  # initial targets
    scope: str = "network"  # network, web, mobile, cloud, ad
    objectives: List[str] = field(default_factory=list)  # what we're trying to achieve

    # Metrics
    total_reward: float = 0.0
    success_rate: float = 0.0
    elapsed_time: float = 0.0

    # Findings
    shells: List[Dict] = field(default_factory=list)  # {host, user, type}
    extracted_data: List[str] = field(default_factory=list)  # file paths
    domain_info: Optional[Dict] = None

    # Notes for LLM context
    notes: List[str] = field(default_factory=list)

    def add_host(self, host: Host) -> None:
        """Add or update a discovered host."""
        self.hosts[host.ip] = host

    def add_vuln(self, vuln: Vulnerability) -> None:
        """Add a discovered vulnerability."""
        if vuln.host in self.hosts:
            self.hosts[vuln.host].vulns.append(vuln.cve_id)
        self.vulns.append(vuln)

    def add_cred(self, cred: Credential) -> None:
        """Add obtained credentials."""
        self.creds.append(cred)

    def add_action(self, action: AttackAction) -> None:
        """Record an executed action."""
        self.actions.append(action)

    def update_action(self, action_id: str, **kwargs) -> None:
        """Update an action's properties."""
        for action in self.actions:
            if action.action_id == action_id:
                for key, value in kwargs.items():
                    if hasattr(action, key):
                        setattr(action, key, value)
                break

    def get_compromised_hosts(self) -> List[str]:
        """Get list of compromised host IPs."""
        return [ip for ip, host in self.hosts.items() if host.compromised]

    def get_high_value_targets(self) -> List[Host]:
        """Get hosts with high-value vulns or credentials."""
        results = []
        for host in self.hosts.values():
            if host.vulns or host.credentials or host.compromised:
                results.append(host)
        return results

    def get_summary(self) -> str:
        """Generate a human-readable state summary."""
        lines = [
            f"Phase: {self.phase.value}",
            f"Hosts discovered: {len(self.hosts)}",
            f"Vulnerabilities found: {len(self.vulns)}",
            f"Credentials obtained: {len(self.creds)}",
            f"Compromised hosts: {len(self.get_compromised_hosts())}",
            f"Shells obtained: {len(self.shells)}",
            f"Total reward: {self.total_reward:.1f}",
            f"Elapsed: {self.elapsed_time:.0f}s",
        ]

        if self.notes:
            lines.append(f"Notes: {len(self.notes)}")

        return "\n".join(lines)

    def to_dict(self, include_output: bool = False) -> dict:
        """Serialize state for API/storage."""
        return {
            "session_id": self.session_id,
            "phase": self.phase.value,
            "started_at": self.started_at,
            "elapsed_time": self.elapsed_time,
            "hosts": {
                ip: {
                    "ip": h.ip,
                    "hostname": h.hostname,
                    "os": h.os,
                    "ports": h.ports,
                    "services": h.services,
                    "vulns": h.vulns,
                    "compromised": h.compromised,
                }
                for ip, h in self.hosts.items()
            },
            "vulns": [v.to_dict() for v in self.vulns],
            "creds": [c.to_dict() for c in self.creds],
            "actions": [a.to_dict() for a in self.actions[-50:]],  # last 50
            "shells": self.shells,
            "total_reward": self.total_reward,
            "objectives": self.objectives,
            "completed_objectives": self.completed_objectives,
        }

    def get_state_for_llm(self) -> str:
        """Format state for LLM context."""
        lines = [
            f"=== 当前攻击状态 ===",
            f"阶段: {self.phase.value}",
            f"用时: {self.elapsed_time:.0f}秒",
            "",
        ]

        # Hosts
        if self.hosts:
            lines.append(f"已发现 {len(self.hosts)} 台主机:")
            for ip, h in list(self.hosts.items())[:10]:
                services = ", ".join([f"{p}/{s}" for p, s in list(h.services.items())[:5]])
                status = "已攻陷" if h.compromised else "未攻陷"
                lines.append(f"  - {ip} ({status}): {services or '无服务'}")
        else:
            lines.append("尚未发现主机")

        # Vulns
        critical = [v for v in self.vulns if v.severity in ("critical", "high")]
        if critical:
            lines.append(f"\n严重漏洞 ({len(critical)} 个):")
            for v in critical[:5]:
                lines.append(f"  - {v.cve_id} @ {v.host}:{v.port} ({v.severity})")

        # Creds
        if self.creds:
            lines.append(f"\n已获取凭据 ({len(self.creds)} 个):")
            for c in self.creds[:5]:
                lines.append(f"  - {c.username} @ {c.source} ({c.privilege})")

        # Shells
        if self.shells:
            lines.append(f"\n已获得 {len(self.shells)} 个shell")
            for s in self.shells[:3]:
                lines.append(f"  - {s.get('user', '?')}@{s.get('host', '?')}")

        return "\n".join(lines)