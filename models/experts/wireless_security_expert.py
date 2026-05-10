"""
Wireless Security Expert

Expert in wireless network penetration testing including WiFi,
Bluetooth, RFID, and other wireless protocol attacks.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class WirelessSecurityExpert(PenTestExpert):
    """Expert in wireless security testing."""

    TOOLS = [
        "aircrack-ng", "wireshark", "hcxdumptool", "hashcat", "cowpatty",
        "reaver", "bully", "fluxion", "wifite", "kismet", "bettercap",
        "proxmark3", "rfidiot", "pn532", "ubertooth", "hackrf", "bluelog"
    ]

    SYSTEM_PROMPT = """你是一位资深的无线安全测试专家。

专长领域：
- WiFi WPA/WPA2/WPA3 破解
- WPS 攻击
- 无线网络嗅探和中间人
- 恶意接入点搭建
- RFID 克隆和攻击
- 蓝牙安全测试
- ZigBee/LoRa 安全
- 无线键盘/鼠标攻击

WiFi攻击技术：
1. WPA/WPA2握手包捕获
2. 字典攻击破解PSK
3. PMKID攻击
4. WPS PIN暴力破解
5. 恶意Twin攻击
6. Karma攻击

工具集：
- aircrack-ng: WiFi审计套件
- wifite: 自动化WiFi攻击
- reaver: WPS攻击
- bettercap: 无线MITM
- proxmark3: RFID分析
- ubertooth: 蓝牙分析

测试原则：
1. 被动监听发现网络
2. 捕获握手包离线破解
3. 优先测试WPS
4. 注意避开授权范围外的网络
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.WIRELESS_SECURITY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze wireless security testing opportunities."""
        self.call_count += 1

        wifi_networks = state.get("wifi_networks", [])
        wifi_handshake = state.get("wifi_handshake", None)
        wps_enabled = state.get("wps_enabled", False)
        target_bssid = state.get("target_bssid", "")
        target_essid = state.get("target_essid", "")

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if not wifi_networks and not wifi_handshake:
            # Start wireless reconnaissance
            actions.append({
                "type": "recon",
                "tool": "airodump-ng",
                "params": {"interface": "wlan0", "channel": "all"},
                "description": "开始无线网络监听",
                "duration": "持续扫描直到发现目标",
            })
            tools.append("airodump-ng")

            actions.append({
                "type": "recon",
                "tool": "kismet",
                "params": {"interface": "wlan0"},
                "description": "使用Kismet进行被动扫描",
                "optional": True,
            })
            tools.append("kismet")
            reasoning = "未发现WiFi网络，开始无线监听。"
            confidence = 0.6
        else:
            # WiFi network found
            if wifi_handshake:
                # Handshake captured - crack it
                actions.append({
                    "type": "crack",
                    "tool": "aircrack-ng",
                    "params": {
                        "handshake": wifi_handshake,
                        "wordlist": "rockyou.txt",
                    },
                    "description": "使用Aircrack离线破解握手包",
                })
                tools.append("aircrack-ng")

                actions.append({
                    "type": "crack",
                    "tool": "hashcat",
                    "params": {
                        "mode": "2500",  # WPA-PMKID-PBKDF2
                        "handshake": wifi_handshake,
                    },
                    "description": "使用Hashcat GPU加速破解",
                })
                tools.append("hashcat")
                reasoning = "已捕获握手包，开始离线破解。"
            else:
                # Capture handshake
                actions.append({
                    "type": "capture",
                    "tool": "airodump-ng",
                    "params": {
                        "bssid": target_bssid,
                        "essid": target_essid,
                        "channel": "auto",
                        "write": "handshake",
                    },
                    "description": f"捕获 {target_essid} 的握手包",
                })
                tools.append("airodump-ng")

                # Deauth attack to force reconnection
                if target_bssid:
                    actions.append({
                        "type": "attack",
                        "tool": "aireplay-ng",
                        "params": {
                            "mode": "deauth",
                            "bssid": target_bssid,
                            "count": 10,
                        },
                        "description": "发送Deauth包强制设备重连",
                    })
                    tools.append("aireplay-ng")

                # WPS attack
                if wps_enabled:
                    actions.append({
                        "type": "attack",
                        "tool": "reaver",
                        "params": {
                            "bssid": target_bssid,
                            "interface": "wlan0",
                        },
                        "description": "WPS PIN暴力破解",
                    })
                    tools.append("reaver")
                    reasoning = "目标网络WPS已启用，尝试WPS攻击。"
                else:
                    reasoning = "已发现WiFi网络，开始捕获握手包。"

            # Evil Twin attack as backup
            actions.append({
                "type": "setup",
                "tool": "fluxion",
                "params": {"target_essid": target_essid},
                "description": "准备Evil Twin攻击作为备用方案",
                "optional": True,
            })
            tools.append("fluxion")

            confidence = 0.75 if wifi_handshake else 0.65

        # Bluetooth testing
        actions.append({
            "type": "recon",
            "tool": "bluelog",
            "params": {"interface": "hci0"},
            "description": "扫描蓝牙设备",
            "optional": True,
        })
        tools.append("bluelog")

        warnings.append("无线攻击可能干扰正常网络")
        warnings.append("未授权的网络攻击是违法行为")
        warnings.append("握手包捕获需要客户端连接")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"无线安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1550.001", "T1552.003", "T1563.001", "T1534", "T0852"]

    def _get_required_inputs(self) -> List[str]:
        return ["wifi_networks"]

    def _get_outputs(self) -> List[str]:
        return ["wifi_password", "wps_pin", "captured_traffic", "bluetooth_devices"]