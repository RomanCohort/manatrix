"""
Active Directory Security Expert

Expert in Active Directory penetration testing, including
kerberos attacks, bloodhound analysis, and domain privilege escalation.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class ActiveDirectoryExpert(PenTestExpert):
    """Expert in Active Directory security testing."""

    TOOLS = [
        "bloodhound", "powerview", "bloodhound-python", "kerbrute",
        "mimikatz", "rubeus", "certify", "silkroad", "crackmapexec",
        "impacket", "enum4linux", "ldapsearch", "ntdsutil"
    ]

    SYSTEM_PROMPT = """你是一位资深的Active Directory安全测试专家。

专长领域：
- Kerberos认证攻击（Kerberoast、AS-REP Roasting）
- Active Directory枚举和信息收集
- BloodHound攻击路径分析
- 域权限维持和提权
- LDAP协议攻击
- NTDS.dit凭据提取
- 组策略利用（GPP、CLMVP）
- 证书服务攻击
- 基于DNS的域渗透

工具集：
- bloodhound/bloodhound-python: AD攻击路径分析
- powerview: AD环境侦察
- rubeus: Kerberos攻击工具
- certify: AD CS攻击
- mimikatz: 凭据窃取
- crackmapexec: 多协议攻击工具
- impacket: 网络协议利用库

Kerberos攻击原则：
1. 枚举域用户和服务账户
2. 寻找SPN并请求TGS
3. 提取服务账户NT哈希
4. 离线破解或使用哈希传递

攻击路径分析：
1. 收集AD数据（LDAP、Kerberos、SMB等）
2. 导入BloodHound分析攻击路径
3. 识别到达域管理员的最短路径
4. 按路径执行攻击
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.ACTIVE_DIRECTORY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze AD security testing opportunities."""
        self.call_count += 1

        has_shell = state.get("has_shell", False)
        is_admin = state.get("is_admin", False)
        domain = state.get("domain", "")
        credentials = state.get("credentials", [])
        hashes = state.get("hashes", [])

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if not domain:
            # Find domain info
            actions.append({
                "type": "recon",
                "tool": "powerview",
                "params": {"command": "Get-NetDomain"},
                "description": "获取域信息",
            })
            tools.append("powerview")
            reasoning = "未发现域环境信息，先进行域发现。"
            confidence = 0.6
        else:
            # Check if we have credentials
            if not credentials and not hashes:
                # User enumeration
                actions.append({
                    "type": "recon",
                    "tool": "kerbrute",
                    "params": {"mode": "userenum", "wordlist": "users.txt"},
                    "description": "枚举域用户",
                })
                tools.append("kerbrute")

                actions.append({
                    "type": "recon",
                    "tool": "enum4linux",
                    "params": {},
                    "description": "枚举SMB共享和用户",
                })
                tools.append("enum4linux")
                reasoning = "发现域环境，需要进行用户枚举和初始侦察。"
            else:
                # Kerberoasting
                if is_admin:
                    actions.append({
                        "type": "attack",
                        "tool": "rubeus",
                        "params": {"command": "kerberoast"},
                        "description": "Kerberoasting攻击",
                    })
                    tools.append("rubeus")

                    actions.append({
                        "type": "attack",
                        "tool": "mimikatz",
                        "params": {"command": "privilege::debug;sekurlsa::tickets /export"},
                        "description": "导出所有Kerberos票据",
                    })
                    tools.append("mimikatz")

                    # AD CS attacks
                    actions.append({
                        "type": "attack",
                        "tool": "certify",
                        "params": {"command": "find /vulnerable"},
                        "description": "查找AD CS漏洞配置",
                    })
                    tools.append("certify")

                    # BloodHound collection
                    actions.append({
                        "type": "recon",
                        "tool": "bloodhound-python",
                        "params": {"collection": "All"},
                        "description": "收集AD数据用于BloodHound分析",
                    })
                    tools.append("bloodhound-python")

                    reasoning = "已获得域凭据，进行Kerberos攻击和攻击路径分析。"
                else:
                    # User enum for SPN
                    actions.append({
                        "type": "recon",
                        "tool": "powerview",
                        "params": {"command": "Get-DomainUser -SPN"},
                        "description": "查找SPN用户（Kerberoast目标）",
                    })
                    tools.append("powerview")

                    actions.append({
                        "type": "recon",
                        "tool": "bloodhound-python",
                        "params": {"collection": "Default"},
                        "description": "收集基本AD数据",
                    })
                    tools.append("bloodhound-python")

                    reasoning = "已获得域访问，进行SPN枚举和权限评估。"

                confidence = 0.8

        warnings.append("AD攻击可能触发蓝色团队检测")
        warnings.append("Kerberoasting会产生大量日志")
        warnings.append("BloodHound收集会产生LDAP查询")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"Active Directory安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1558", "T1550.003", "T1098", "T1553.002", "T1003.003", "T1087.002"]

    def _get_required_inputs(self) -> List[str]:
        return ["domain", "credentials"]

    def _get_outputs(self) -> List[str]:
        return ["domain_admin", "tickets", "hashes", "attack_path"]