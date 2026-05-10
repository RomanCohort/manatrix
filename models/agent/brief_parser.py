"""
Brief Parser

Parses user attack briefings into structured attack objectives.
Uses LLM to extract targets, scope, and goals from natural language.
"""

import logging
import json
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ScopeType(Enum):
    FULL = "full"              # Full penetration test
    LIMITED = "limited"        # Limited scope
    READ_ONLY = "read_only"    # Reconnaissance only
    WEB_ONLY = "web_only"      # Web application testing only
    NETWORK_ONLY = "network"   # Network testing only

    @classmethod
    def from_string(cls, s: str) -> "ScopeType":
        mapping = {
            "full": cls.FULL,
            "limited": cls.LIMITED,
            "read": cls.READ_ONLY,
            "recon": cls.READ_ONLY,
            "web": cls.WEB_ONLY,
            "network": cls.NETWORK_ONLY,
        }
        return mapping.get(s.lower(), cls.FULL)


class AttackType(Enum):
    NETWORK = "network"
    WEB = "web"
    MOBILE = "mobile"
    CLOUD = "cloud"
    AD = "active_directory"
    IOT = "iot"
    WIRELESS = "wireless"
    SOCIAL = "social_engineering"
    SUPPLY_CHAIN = "supply_chain"
    MIXED = "mixed"
    REVERSE_ENGINEERING = "reverse_engineering"
    HARDWARE = "hardware"

    @classmethod
    def from_string(cls, s: str) -> "AttackType":
        mapping = {
            "network": cls.NETWORK,
            "web": cls.WEB,
            "mobile": cls.MOBILE,
            "cloud": cls.CLOUD,
            "ad": cls.AD,
            "active_directory": cls.AD,
            "iot": cls.IOT,
            "wireless": cls.WIRELESS,
            "social": cls.SOCIAL,
            "supply_chain": cls.SUPPLY_CHAIN,
            "mixed": cls.MIXED,
            "reverse": cls.REVERSE_ENGINEERING,
            "reverse_engineering": cls.REVERSE_ENGINEERING,
            "decompile": cls.REVERSE_ENGINEERING,
            "decompilation": cls.REVERSE_ENGINEERING,
            "hardware": cls.HARDWARE,
            "hw": cls.HARDWARE,
            "chip": cls.HARDWARE,
            "pcb": cls.HARDWARE,
            "side_channel": cls.HARDWARE,
            "fault_injection": cls.HARDWARE,
        }
        return mapping.get(s.lower(), cls.MIXED)


@dataclass
class AttackObjectives:
    """Structured objectives parsed from user brief."""
    targets: List[str] = field(default_factory=list)  # IPs, domains, URLs
    scope: ScopeType = ScopeType.FULL
    objectives: List[str] = field(default_factory=list)  # "get_shell", "dump_creds"
    constraints: List[str] = field(default_factory=list)  # limitations
    attack_type: AttackType = AttackType.MIXED
    time_limit: Optional[int] = None  # minutes
    priority: str = "normal"  # normal, stealth, aggressive
    brief_raw: str = ""  # original brief text

    def to_dict(self) -> dict:
        return {
            "targets": self.targets,
            "scope": self.scope.value,
            "objectives": self.objectives,
            "constraints": self.constraints,
            "attack_type": self.attack_type.value,
            "priority": self.priority,
        }


BRIEF_PARSE_PROMPT = """你是一位专业的渗透测试分析助手。

请分析以下攻击任务简报，提取结构化信息。

简报内容:
{brief}

请返回JSON格式（不要包含其他内容）:
{{
    "targets": ["目标IP/域名/URL列表"],
    "scope": "full/limited/read_only/web/network",
    "objectives": ["具体目标列表，如：获取shell、获取凭据、提权、横向移动、数据窃取"],
    "constraints": ["限制条件列表"],
    "attack_type": "network/web/mobile/cloud/ad/iot/wireless/social/mixed",
    "priority": "normal/stealth/aggressive",
    "time_limit": null或分钟数
}}

分析原则：
1. 从简报中提取所有IP地址、域名、URL作为目标
2. 根据简报内容判断攻击类型
3. 明确所有约束和限制条件
4. 推断隐含的攻击目标
"""


class BriefParser:
    """Parses attack briefs into structured objectives."""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def parse(self, brief: str) -> AttackObjectives:
        """Parse a user brief into structured attack objectives."""
        if not brief or not brief.strip():
            return AttackObjectives(brief_raw=brief)

        # Try LLM-based parsing first
        if self.llm:
            try:
                return self._parse_with_llm(brief)
            except Exception as e:
                logger.warning(f"LLM brief parsing failed, falling back to rule-based: {e}")

        # Fallback to rule-based parsing
        return self._parse_rule_based(brief)

    def _parse_with_llm(self, brief: str) -> AttackObjectives:
        """Use LLM to parse the brief."""
        from models.llm_provider import LLMResponse

        messages = [
            {"role": "user", "content": BRIEF_PARSE_PROMPT.format(brief=brief)}
        ]

        response = self.llm.call(messages, use_json_mode=False)

        # Extract JSON from response
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        data = json.loads(content.strip())
        return self._dict_to_objectives(data, brief)

    def _parse_rule_based(self, brief: str) -> AttackObjectives:
        """Rule-based brief parsing fallback."""
        import re

        objectives = AttackObjectives(brief_raw=brief)

        # Extract IPs
        ip_pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?:/\d{1,2})?)\b'
        objectives.targets = re.findall(ip_pattern, brief)

        # Extract domains
        domain_pattern = r'\b([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)\b'
        domains = re.findall(domain_pattern, brief)
        for d in domains:
            if d not in objectives.targets:
                objectives.targets.append(d)

        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, brief)
        for u in urls:
            if u not in objectives.targets:
                objectives.targets.append(u)

        # Detect scope
        brief_lower = brief.lower()
        if any(w in brief_lower for w in ["仅侦察", "仅扫描", "recon only", "read only"]):
            objectives.scope = ScopeType.READ_ONLY
        elif any(w in brief_lower for w in ["web", "网站", "网页"]):
            objectives.scope = ScopeType.WEB_ONLY
            objectives.attack_type = AttackType.WEB
        elif any(w in brief_lower for w in ["网络", "network", "内网"]):
            objectives.scope = ScopeType.NETWORK_ONLY
            objectives.attack_type = AttackType.NETWORK

        # Detect objectives
        obj_keywords = {
            "get_shell": ["shell", "反弹", "反弹shell", "get shell"],
            "dump_creds": ["凭据", "密码", "credential", "hash", "mimikatz"],
            "privilege_escalation": ["提权", "privilege", "escalation", "root"],
            "lateral_movement": ["横向", "lateral", "pivot"],
            "data_exfiltration": ["数据", "窃取", "exfiltration"],
            "full_compromise": ["完全控制", "full compromise", "全面"],
            "reverse_engineering": ["逆向", "reverse", "反编译", "decompile", "二进制分析", "binary analysis"],
            "exploit_dev": ["漏洞利用开发", "exploit dev", "rop", "shellcode", "堆利用", "heap exploit"],
            "firmware_analysis": ["固件分析", "firmware analysis", "固件提取", "firmware extraction"],
            "side_channel_attack": ["侧信道", "side channel", "功耗分析", "power analysis", "em攻击", "cpa", "dpa"],
            "fault_injection": ["故障注入", "fault injection", "glitch", "电压故障", "时钟故障"],
            "chip_extraction": ["芯片提取", "chip extraction", "固件提取", "mcu提取"],
            "hardware_debug": ["硬件调试", "jtag", "uart", "调试接口"],
            "rfid_nfc_attack": ["rfid", "nfc", "mifare", "门禁", "智能卡"],
            "automotive_attack": ["汽车安全", "can总线", "obd", "车载"],
        }
        for obj, keywords in obj_keywords.items():
            if any(k in brief_lower for k in keywords):
                objectives.objectives.append(obj)

        if not objectives.objectives:
            objectives.objectives = ["reconnaissance", "vulnerability_scan", "exploitation"]

        # Detect attack type
        type_keywords = {
            AttackType.WEB: ["web", "网站", "sql注入", "xss", "http"],
            AttackType.AD: ["ad", "active directory", "域", "kerberos"],
            AttackType.CLOUD: ["aws", "azure", "gcp", "云", "cloud"],
            AttackType.IOT: ["iot", "摄像头", "路由器", "嵌入式"],
            AttackType.WIRELESS: ["wifi", "wireless", "蓝牙", "wpa"],
            AttackType.REVERSE_ENGINEERING: ["逆向", "reverse", "反编译", "decompile", "二进制", "binary", "固件分析", "firmware", "apk", "ghidra", "ida", "反汇编", "disassemble"],
            AttackType.HARDWARE: [
                "硬件", "hardware", "芯片", "chip", "mcu", "cpu", "soc", "fpga",
                "jtag", "uart", "spi", "i2c", "调试口", "debug port",
                "侧信道", "side channel", "故障注入", "fault injection", "glitch",
                "pcb", "电路板", "rfid", "nfc", "mifare", "proxmark",
                "can总线", "obd", "汽车", "automotive", "车载",
                "功耗分析", "电磁分析", "冷启动", "cold boot",
                "chipwhisperer", "去封装", "decap",
            ],
        }
        for atype, keywords in type_keywords.items():
            if any(k in brief_lower for k in keywords):
                objectives.attack_type = atype
                break

        return objectives

    def _dict_to_objectives(self, data: dict, brief: str) -> AttackObjectives:
        """Convert parsed dict to AttackObjectives."""
        return AttackObjectives(
            targets=data.get("targets", []),
            scope=ScopeType.from_string(data.get("scope", "full")),
            objectives=data.get("objectives", ["reconnaissance", "exploitation"]),
            constraints=data.get("constraints", []),
            attack_type=AttackType.from_string(data.get("attack_type", "mixed")),
            priority=data.get("priority", "normal"),
            time_limit=data.get("time_limit"),
            brief_raw=brief,
        )
