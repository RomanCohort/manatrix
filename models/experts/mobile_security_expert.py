"""
Mobile Security Expert

Expert in mobile application security testing including
Android, iOS, and mobile API security.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class MobileSecurityExpert(PenTestExpert):
    """Expert in mobile application security testing."""

    TOOLS = [
        "frida", "objection", "jadx", "apktool", "mobexler", "drozer",
        "needle", "jadx-gui", "radare2", "r2frida", "adb", "apksigner",
        "mitmproxy", "burpsuite", "idb", "house", "jadx"
    ]

    SYSTEM_PROMPT = """你是一位资深的移动安全测试专家。

专长领域：
- Android APK逆向分析
- iOS应用安全测试
- 移动API安全
- 敏感数据存储分析
- SSL Pinning绕过
- 动态分析和Hook
- 移动端WebView攻击
- 移动恶意软件分析

分析技术：
1. APK静态分析（反编译、资源提取）
2. 敏感信息搜索（硬编码凭据、API密钥）
3. 权限和组件测试
4. SSL Pinning分析
5. 动态Hook分析（Frida）
6. 网络流量抓包分析

工具集：
- frida: 动态Hook框架
- objection: 运行时安全测试
- jadx/apktool: 反编译工具
- drozer: Android安全测试框架
- needle: iOS安全测试框架
- mitmproxy: HTTPS流量分析

测试原则：
1. 先静态分析获取信息
2. 分析权限和组件暴露
3. 检查敏感数据存储
4. 动态分析运行时行为
5. 测试网络通信安全
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.MOBILE_SECURITY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze mobile security testing opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        apk_file = state.get("apk_file", None)
        app_package = state.get("app_package", "")
        platform = state.get("platform", "android")  # android or ios

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if apk_file or app_package:
            # Android APK analysis
            if platform.lower() == "android" or apk_file:
                # Static analysis
                actions.append({
                    "type": "decompile",
                    "tool": "jadx",
                    "params": {"apk": apk_file or app_package},
                    "description": "反编译APK分析源码",
                })
                tools.append("jadx")

                actions.append({
                    "type": "extract",
                    "tool": "apktool",
                    "params": {"apk": apk_file, "decode": True},
                    "description": "提取APK资源和Manifest",
                })
                tools.append("apktool")

                # Search for sensitive data
                actions.append({
                    "type": "scan",
                    "description": "搜索敏感信息",
                    "patterns": [
                        "api_key",
                        "password",
                        "secret",
                        "token",
                        "base64",
                        "http://",
                    ],
                })

                # Check components
                actions.append({
                    "type": "analyze",
                    "tool": "drozer",
                    "params": {"module": "app.package.attacksurface"},
                    "description": "分析应用攻击面",
                })
                tools.append("drozer")

                # Dynamic analysis
                actions.append({
                    "type": "dynamic",
                    "tool": "frida",
                    "params": {"script": "ssl_pinning_bypass.js"},
                    "description": "使用Frida进行动态分析",
                })
                tools.append("frida")

                actions.append({
                    "type": "dynamic",
                    "tool": "objection",
                    "params": {"command": "android sslpinning disable"},
                    "description": "绕过SSL Pinning",
                })
                tools.append("objection")

                reasoning = "发现APK，进行静态和动态分析。"
                confidence = 0.8

            else:
                # iOS analysis
                actions.append({
                    "type": "analyze",
                    "tool": "jadx",
                    "params": {"binary": "Payload/*.app"},
                    "description": "分析iOS应用二进制",
                })

                actions.append({
                    "type": "analyze",
                    "tool": "idb",
                    "params": {},
                    "description": "使用idb分析iOS安全",
                })
                tools.append("idb")

                actions.append({
                    "type": "dynamic",
                    "tool": "frida",
                    "params": {"script": "ios_ssl_bypass.js"},
                    "description": "Hook iOS应用进行分析",
                })
                tools.append("frida")
                reasoning = "发现iOS应用，进行安全分析。"
                confidence = 0.75
        else:
            # Mobile enumeration
            actions.append({
                "type": "recon",
                "description": "扫描移动应用服务",
                "targets": ["*.apk", "*.ipa", "*/api/mobile"],
            })
            reasoning = "未发现移动应用，进行移动端枚举。"
            confidence = 0.5

        # Network traffic analysis
        actions.append({
            "type": "proxy",
            "tool": "mitmproxy",
            "params": {"listen_port": 8080},
            "description": "设置代理抓取移动流量",
        })
        tools.append("mitmproxy")

        # Check for backup vulnerabilities
        actions.append({
            "type": "test",
            "description": "测试应用备份功能安全",
            "checks": ["allowBackup", "debuggable"],
        })

        warnings.append("动态分析需要真实设备或模拟器")
        warnings.append("Hook操作可能影响应用行为")
        warnings.append("分析非签名应用需谨慎")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"移动安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1392", "T1394", "T1574.008", "T1552.001", "T1555"]

    def _get_required_inputs(self) -> List[str]:
        return ["target", "apk_file"]

    def _get_outputs(self) -> List[str]:
        return ["vulnerabilities", "hardcoded_secrets", "ssl_bypass", "api_keys"]