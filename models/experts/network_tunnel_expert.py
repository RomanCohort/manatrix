"""
Network Tunnel & Pivoting Expert

Expert in network tunneling, pivoting, and establishing covert
communication channels through compromised networks.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class NetworkTunnelExpert(PenTestExpert):
    """Expert in network tunneling and pivoting operations."""

    TOOLS = [
        "ssh", "plink", "chisel", "ligolo-ng", "ncat", "proxychains",
        "darkstar", "gost", "ngrok", "frp", "meterpreter", "koadic",
        "pivotnacci", " sharpened"
    ]

    SYSTEM_PROMPT = """你是一位资深的网络隧道和跳转专家。

专长领域：
- SSH隧道和端口转发
- HTTP/HTTPS隧道建立
- VPN over ICMP/DNS
- 代理链构建和负载均衡
- Meterpreter/Socat隧道
- DNS隧道数据传输
- 端口敲门和认证跳转
- 多重跳转链建立

隧道工具：
- chisel: 快速HTTP隧道
- ligolo-ng: 高性能TUN隧道
- gost: Go代理隧道
- ncat/proxychains: SOCKS代理
- meterpreter: 内置路由和代理

隧道原则：
1. 优先使用ICMP/DNS隧道绕过防火墙
2. 建立多重冗余隧道
3. 使用加密隧道保护流量
4. 最小化网络足迹
5. 及时清理痕迹
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.NETWORK_TUNNEL,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze tunneling and pivoting opportunities."""
        self.call_count += 1

        has_shell = state.get("has_shell", False)
        compromised_hosts = state.get("compromised_hosts", [])
        internal_networks = state.get("internal_networks", [])
        external_ip = state.get("attacker_ip", "")

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if not has_shell:
            actions.append({
                "type": "wait",
                "description": "需要先获取目标访问权限才能建立隧道",
            })
            reasoning = "尚未获得访问权限，无法建立隧道。"
            confidence = 0.6
        elif not compromised_hosts:
            actions.append({
                "type": "recon",
                "description": "枚举内部网络和路由表",
                "commands": ["route", "ip route", "netstat -r"],
            })
            reasoning = "需要先发现内部网络结构。"
            confidence = 0.5
        else:
            # Determine tunnel approach
            if len(compromised_hosts) == 1:
                # Single hop - basic pivot
                host = compromised_hosts[0]
                actions.append({
                    "type": "setup",
                    "tool": "chisel",
                    "params": {
                        "mode": "reverse",
                        "listen_port": 8080,
                        "target": host,
                    },
                    "description": "建立Chisel反向隧道",
                })
                tools.append("chisel")

                actions.append({
                    "type": "setup",
                    "description": "配置Proxychains使用SOCKS代理",
                })

                reasoning = "已获得单台主机，配置基本跳转。"
                confidence = 0.7
            else:
                # Multiple hosts - chained tunnel
                for i, host in enumerate(compromised_hosts[:3]):
                    actions.append({
                        "type": "setup",
                        "tool": "chisel",
                        "params": {
                            "server": f"host_{i}",
                            "mode": "reverse",
                        },
                        "description": f"在主机 {host} 建立第{i+1}跳隧道",
                    })
                    tools.append("chisel")

                # Ligolo-ng for high performance
                actions.append({
                    "type": "setup",
                    "tool": "ligolo-ng",
                    "params": {"interface": "tun0"},
                    "description": "建立Ligolo-ng高性能隧道",
                })
                tools.append("ligolo-ng")

                reasoning = f"已获得{len(compromised_hosts)}台主机，建立多层跳转链。"
                confidence = 0.85

            # Check for internal networks
            if internal_networks:
                actions.append({
                    "type": "scan",
                    "description": "通过隧道扫描内部网络",
                    "targets": internal_networks,
                })

        # DNS/ICMP tunnel option
        if has_shell:
            actions.append({
                "type": "setup",
                "description": "建立DNS隧道作为备用通道",
                "tool": "dnscat2" if not has_shell else "iodine",
                "optional": True,
            })
            tools.append("iodine")

        warnings.append("隧道操作可能被发现或阻断")
        warnings.append("大量端口转发可能触发告警")
        warnings.append("DNS隧道速度较慢")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"网络隧道建立，推荐 {len(actions)} 个配置行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1572", "T1090.003", "T1095", "T1573", "T1568"]

    def _get_required_inputs(self) -> List[str]:
        return ["compromised_hosts", "has_shell"]

    def _get_outputs(self) -> List[str]:
        return ["tunnels", "proxy_chain", "pivot_points", "internal_access"]