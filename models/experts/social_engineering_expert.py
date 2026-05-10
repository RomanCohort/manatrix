"""
Social Engineering Expert

Expert in social engineering attacks including phishing,
spear phishing, pretexting, and human manipulation techniques.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class SocialEngineeringExpert(PenTestExpert):
    """Expert in social engineering attack planning and execution."""

    TOOLS = [
        "gophish", "social-engineer-toolkit", "SET", "king-phisher",
        " credential", "harvester", "maltego", "maskphish", "smsgen",
        "evilginx2", "blackeye", "fishing"
    ]

    SYSTEM_PROMPT = """你是一位资深的社会工程学专家。

专长领域：
- 钓鱼攻击（邮件、短信、语音）
- 鱼叉式钓鱼（Spear Phishing）
- 凭证收割攻击
- 水坑攻击（Watering Hole）
- 身份伪装和冒充
- USB攻击（BadUSB、恶意USB）
- 物理渗透和尾随
- Pretexting（编造情境）

钓鱼技术：
1. 克隆正规网站收割凭据
2. 伪造登录页面
3. 恶意附件投递
4. 短信钓鱼（Smishing）
5. 语音钓鱼（Vishing）
6. 克隆无线接入点

工具集：
- gophish: 开源钓鱼框架
- SET (Social-Engineer Toolkit): 社会工程工具
- evilginx2: 高级钓鱼代理
- king-phisher: 钓鱼活动管理
- theHarvester: 邮箱收集

攻击原则：
1. 信息收集是成功的基础
2. 攻击要有针对性和个性化
3. 利用信任和紧迫感
4. 测试员工的警惕性
5. 记录所有攻击用于报告
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.SOCIAL_ENGINEERING,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze social engineering opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        domain = state.get("domain", "")
        employees = state.get("employees", [])
        current_phase = state.get("phase", "")

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if not employees:
            # Reconnaissance for social engineering
            actions.append({
                "type": "recon",
                "tool": "theHarvester",
                "params": {"domain": domain or target, "source": "all"},
                "description": "收集邮箱和员工信息",
            })
            tools.append("theHarvester")

            actions.append({
                "type": "recon",
                "tool": "maltego",
                "params": {"entity": "Company", "transforms": "all"},
                "description": "使用Maltego进行OSINT分析",
            })
            tools.append("maltego")

            actions.append({
                "type": "recon",
                "description": "收集社交媒体信息",
                "platforms": ["LinkedIn", "Twitter", "Facebook", "GitHub"],
            })
            reasoning = "需要先收集目标组织和人员信息。"
            confidence = 0.6
        else:
            # Build phishing campaign
            actions.append({
                "type": "prepare",
                "tool": "gophish",
                "params": {"campaign_name": "security_test"},
                "description": "搭建钓鱼活动框架",
            })
            tools.append("gophish")

            # Landing page
            actions.append({
                "type": "create",
                "tool": "evilginx2",
                "params": {"phishing_url": f"https://login.{domain}"},
                "description": "创建凭证收割钓鱼页面",
            })
            tools.append("evilginx2")

            # Email template
            actions.append({
                "type": "create",
                "description": "制作钓鱼邮件模板",
                "templates": [
                    "密码过期提醒",
                    "IT支持请求",
                    "文档共享邀请",
                    "安全警告",
                ],
            })

            # Clone legitimate site
            actions.append({
                "type": "clone",
                "tool": "SET",
                "params": {"site": "o365", "method": "web"},
                "description": "克隆Office 365登录页面",
            })
            tools.append("SET")

            # SMS phishing (optional)
            if state.get("phone_numbers"):
                actions.append({
                    "type": "sms_phishing",
                    "tool": "smsgen",
                    "params": {"targets": state.get("phone_numbers")[:5]},
                    "description": "SMS钓鱼攻击",
                    "optional": True,
                })
                tools.append("smsgen")

            reasoning = f"已收集 {len(employees)} 名员工信息，准备钓鱼攻击。"
            confidence = 0.8

        # Physical attack vectors
        if current_phase in ["post_exploitation", "lateral_movement"]:
            actions.append({
                "type": "physical",
                "description": "物理社工攻击",
                "vectors": [
                    "恶意USB投放",
                    "伪装成IT人员",
                    "尾随进入",
                    "肩窥",
                ],
                "optional": True,
            })

        warnings.append("社会工程测试需确保授权范围明确")
        warnings.append("钓鱼测试前应通知邮件管理员")
        warnings.append("避免收集敏感个人信息")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"社会工程测试，推荐 {len(actions)} 个攻击行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1566", "T1566.001", "T1566.002", "T1566.003", "T1184", "T1456"]

    def _get_required_inputs(self) -> List[str]:
        return ["domain", "employees"]

    def _get_outputs(self) -> List[str]:
        return ["captured_credentials", "phishing_results", "employee_awareness"]