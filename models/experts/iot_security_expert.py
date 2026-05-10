"""
IoT & Embedded Security Expert

Expert in IoT device security testing including firmware analysis,
embedded systems, and hardware hacking.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class IoTIoTSecurityExpert(PenTestExpert):
    """Expert in IoT and embedded system security testing."""

    TOOLS = [
        "firmwalker", "binwalk", "firmware-mod-kit", "qemu", "ghidra",
        "radare2", "gdb", "stlink", "openocd", "flashrom", "johntheripper",
        "jtagulator", "buspirate", "saleae", "ubertooth", "hackrf"
    ]

    SYSTEM_PROMPT = """你是一位资深的IoT和嵌入式安全测试专家。

专长领域：
- 固件分析和逆向工程
- 嵌入式操作系统安全
- 无线通信安全（ZigBee、BLE、LoRa）
- 硬件调试接口攻击（JTAG、UART、SWD）
- 传感器欺骗和数据注入
- PLC和SCADA安全
- 摄像头和路由器渗透
- 智能家居设备攻击

工具集：
- binwalk: 固件提取和分析
- firmwalker: 固件敏感信息扫描
- ghidra/radare2: 逆向工程
- qemu: 固件模拟
- ubertooth: 蓝牙分析
- hackrf: 无线信号分析

测试原则：
1. 先进行被动信息收集
2. 分析固件获取默认凭据
3. 测试物理接口（串口、JTAG）
4. 分析通信协议安全性
5. 检查更新机制完整性
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.IOT_SECURITY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze IoT security testing opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        device_type = state.get("device_type", "")
        firmware = state.get("firmware", None)
        services = state.get("services", [])

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        # Detect IoT device
        iot_indicators = ["camera", "router", "nas", "printer", "smart", "hub", "gateway", "plc", "rtu", "iot"]
        is_iot = device_type or any(ind in str(services).lower() for ind in iot_indicators)

        if is_iot or device_type:
            if firmware:
                # Firmware analysis
                actions.append({
                    "type": "analyze",
                    "tool": "binwalk",
                    "params": {"firmware": firmware, "extract": True},
                    "description": "提取和分析固件",
                })
                tools.append("binwalk")

                actions.append({
                    "type": "scan",
                    "tool": "firmwalker",
                    "params": {"directory": "extracted_firmware/"},
                    "description": "扫描固件中的敏感信息",
                })
                tools.append("firmwalker")

                actions.append({
                    "type": "analyze",
                    "description": "分析固件中的二进制文件",
                    "tools": ["ghidra", "radare2"],
                })
                reasoning = "发现固件，进行深度分析。"
                confidence = 0.8
            else:
                # Service enumeration
                actions.append({
                    "type": "recon",
                    "description": "识别IoT设备类型和服务",
                    "checks": ["UPnP", "mDNS", "SSDP", "CoAP"],
                })

                # Default credentials check
                actions.append({
                    "type": "auth",
                    "description": "测试默认凭据",
                    "common_creds": [
                        ("admin", "admin"),
                        ("admin", "password"),
                        ("root", "root"),
                        ("user", "user"),
                    ],
                })

                # UPnP enumeration
                actions.append({
                    "type": "recon",
                    "tool": "upnp-info",
                    "description": "枚举UPnP服务",
                })

                # Check for known vulnerabilities
                if device_type:
                    actions.append({
                        "type": "search",
                        "tool": "searchsploit",
                        "params": {"query": device_type},
                        "description": f"搜索 {device_type} 的已知漏洞",
                    })
                    tools.append("searchsploit")

                reasoning = f"已识别IoT设备，进行服务枚举和安全测试。"
                confidence = 0.7
        else:
            # IoT discovery
            actions.append({
                "type": "recon",
                "description": "扫描IoT设备特征",
                "ports": [80, 443, 8080, 8443, 554, 37777, 5000, 9000],
            })
            reasoning = "未发现明确IoT设备，进行IoT特征扫描。"
            confidence = 0.5

        # Physical interface testing
        actions.append({
            "type": "hardware",
            "description": "检查物理调试接口",
            "interfaces": ["UART", "JTAG", "SWD", "GPIO"],
            "optional": True,
        })

        # Wireless testing
        actions.append({
            "type": "wireless",
            "description": "测试无线通信安全",
            "protocols": ["WiFi", "BLE", "ZigBee", "LoRa"],
            "optional": True,
        })

        warnings.append("IoT设备测试可能影响设备正常运行")
        warnings.append("固件分析需要足够存储空间")
        warnings.append("物理接口测试需要硬件访问权限")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"IoT安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1190", "T1552.003", "T1525", "T0819", "T0886"]

    def _get_required_inputs(self) -> List[str]:
        return ["target", "device_type"]

    def _get_outputs(self) -> List[str]:
        return ["firmware_analysis", "default_creds", "vulnerabilities", "physical_access"]