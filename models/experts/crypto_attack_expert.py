"""
Cryptography Attack Expert

Expert in cryptographic vulnerabilities and attacks including
password cracking, hash attacks, and cryptographic implementation flaws.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class CryptoAttackExpert(PenTestExpert):
    """Expert in cryptographic security testing."""

    TOOLS = [
        "hashcat", "john", "johntheripper", "openssl", "ghash", "ophcrack",
        "cryplock", "vulnerability", "padding oracle", "rsatool", "princeprocessor",
        "mimikatz", "keepass", "pyrit", "hash-identifier", "hashdb"
    ]

    SYSTEM_PROMPT = """你是一位资深的密码学攻击专家。

专长领域：
- 密码哈希破解（NTLM、Kerberos、SHA系列）
- Padding Oracle攻击
- RSA弱密钥分析
- 暴力破解和字典攻击
- Kerberos票据解密
- JWT攻击
- SSL/TLS漏洞测试
- 加密实现缺陷利用

哈希攻击技术：
- 字典攻击 + 规则变异
- 彩虹表攻击
- 彩虹表：ophcrack, rainbowcrack
- GPU加速破解：hashcat
- 分布式破解

常见哈希类型：
- NTLMv1/v2 (Windows认证)
- Kerberos TGS/AP
- SHA系列 (密码存储)
- bcrypt/Argon2 (慢哈希)
- JWT令牌

测试原则：
1. 首先识别哈希类型
2. 评估破解复杂度
3. 选择最优攻击方法
4. 利用规则优化字典
5. 并行化提高效率
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.CRYPTO_ATTACK,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze cryptographic attack opportunities."""
        self.call_count += 1

        hashes = state.get("hashes", [])
        credentials = state.get("credentials", [])
        jwt_tokens = state.get("jwt_tokens", [])
        ssl_cert = state.get("ssl_certificate", None)
        domain = state.get("domain", "")

        actions = []
        tools = []
        warnings = []
        relevant_cves = []
        reasoning = ""
        confidence = 0.5

        if hashes:
            # Analyze hash types
            actions.append({
                "type": "analyze",
                "tool": "hash-identifier",
                "params": {"hashes": hashes[:3]},
                "description": "识别哈希类型",
            })
            tools.append("hash-identifier")

            # Setup crack attack
            actions.append({
                "type": "crack",
                "tool": "hashcat",
                "params": {
                    "hashfile": "hashes.txt",
                    "wordlist": "rockyou.txt",
                    "rules": "best64.rule",
                    "attack_mode": 0,
                },
                "description": "使用Hashcat字典攻击",
            })
            tools.append("hashcat")

            # Check for Kerberoast hashes
            kerb_hashes = [h for h in hashes if "$krb" in str(h).lower()]
            if kerb_hashes:
                actions.append({
                    "type": "crack",
                    "tool": "hashcat",
                    "params": {
                        "mode": "13100",  # Kerberoast TGS
                        "rules": "OneRuleToRuleThemAll",
                    },
                    "description": "Kerberoast哈希破解",
                })
                tools.append("hashcat")

            reasoning = f"发现 {len(hashes)} 个哈希，准备破解攻击。"
            confidence = 0.75
        elif jwt_tokens:
            # JWT attacks
            for token in jwt_tokens[:2]:
                actions.append({
                    "type": "analyze",
                    "tool": "jwt_tool",
                    "params": {"token": token},
                    "description": "分析JWT令牌安全",
                })
                tools.append("jwt_tool")

                # Common JWT attacks
                actions.append({
                    "type": "exploit",
                    "description": "尝试JWT攻击",
                    "attacks": [
                        "alg:none",
                        "HS256->RS256",
                        "kid injection",
                        "弱密钥爆破"
                    ],
                })
            reasoning = "发现JWT令牌，进行安全测试。"
            confidence = 0.7
        else:
            # Enumerate hash sources
            actions.append({
                "type": "recon",
                "description": "枚举潜在哈希来源",
                "sources": [
                    "/etc/shadow",
                    "NTDS.dit",
                    "SAM数据库",
                    "配置文件",
                    "Kerberos票据",
                ],
            })
            reasoning = "未发现哈希，先枚举潜在来源。"
            confidence = 0.5

        # SSL/TLS testing
        if ssl_cert:
            actions.append({
                "type": "analyze",
                "tool": "openssl",
                "params": {"mode": "s_client"},
                "description": "分析SSL证书安全",
            })
            tools.append("openssl")

            actions.append({
                "type": "test",
                "description": "测试SSL/TLS漏洞",
                "checks": ["弱加密套件", "心脏滴血", "POODLE", "Downgrade攻击"],
            })

        warnings.append("哈希破解需要大量计算资源")
        warnings.append("破解时间取决于密码复杂度")
        warnings.append("Kerberoast会产生Kerberos日志")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"密码学攻击测试，推荐 {len(actions)} 个攻击行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1110", "T1110.001", "T1110.002", "T1110.003", "T1110.004", "T1558"]

    def _get_required_inputs(self) -> List[str]:
        return ["hashes", "hash_type"]

    def _get_outputs(self) -> List[str]:
        return ["cracked_passwords", "weak_keys", "decrypted_data"]