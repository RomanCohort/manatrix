"""
Cloud Security Expert

Expert in cloud platform penetration testing including AWS, Azure, GCP,
container security, and serverless architecture testing.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class CloudSecurityExpert(PenTestExpert):
    """Expert in cloud security testing and exploitation."""

    TOOLS = [
        "awscli", "azure-cli", "gcloud", "microburst", "S3Scanner",
        "pacu", "cloud_enum", " ScoutSuite", "prowler", "cloudsploit",
        "nimbus", "cloud容器", "nuclei", "trufflehog"
    ]

    SYSTEM_PROMPT = """你是一位资深的云安全测试专家。

专长领域：
- AWS/GCP/Azure 云服务渗透测试
- S3存储桶发现和访问测试
- IAM权限滥用和提权
- 容器逃逸和K8s攻击
- 无服务器函数攻击
- 云服务配置错误利用
- 元数据服务攻击
- 持久化和后门植入

AWS测试工具：
- awscli: AWS命令行工具
- pacu: AWS渗透测试框架
- microburst: S3枚举和访问
- trufflehog: 密钥扫描

Azure测试工具：
- azure-cli: Azure命令行工具
- stormspotter: Azure红队工具

测试原则：
1. 枚举所有可访问的云资源
2. 检查公开的S3桶/RDS/ELB
3. 分析IAM策略寻找提权路径
4. 检查元数据服务访问
5. 寻找暴露的密钥和凭证
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.CLOUD_SECURITY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze cloud security testing opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        services = state.get("services", [])
        cloud_provider = state.get("cloud_provider", "")
        cloud_creds = state.get("cloud_credentials", {})

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if not cloud_creds and not cloud_provider:
            # Detect cloud provider
            actions.append({
                "type": "recon",
                "description": "识别云服务提供商",
                "indicators": ["aws", "azure", "gcp", "cloud", "elasticbeanstalk"],
            })
            actions.append({
                "type": "scan",
                "tool": "cloud_enum",
                "params": {"target": target},
                "description": "枚举公开云资源",
            })
            tools.append("cloud_enum")
            reasoning = "未识别云环境，进行云服务发现。"
            confidence = 0.6
        else:
            # Check for exposed storage
            actions.append({
                "type": "recon",
                "tool": "S3Scanner",
                "params": {"mode": "enum"},
                "description": "枚举S3存储桶",
            })
            tools.append("S3Scanner")

            # Check credentials
            if cloud_creds:
                # IAM enumeration
                actions.append({
                    "type": "recon",
                    "tool": "awscli",
                    "params": {"command": "iam list-users"},
                    "description": "枚举IAM用户",
                })
                tools.append("awscli")

                actions.append({
                    "type": "recon",
                    "tool": "awscli",
                    "params": {"command": "iam list-roles"},
                    "description": "枚举IAM角色",
                })
                tools.append("awscli")

                # Check for secrets
                actions.append({
                    "type": "scan",
                    "tool": "trufflehog",
                    "params": {"source": "s3://"},
                    "description": "扫描存储桶中的密钥",
                })
                tools.append("trufflehog")

                # Privilege escalation check
                actions.append({
                    "type": "test",
                    "tool": "pacu",
                    "params": {"module": "enum_iam_permissions"},
                    "description": "枚举IAM权限寻找提权路径",
                })
                tools.append("pacu")

                reasoning = "发现云凭据，进行IAM枚举和权限分析。"
            else:
                actions.append({
                    "type": "recon",
                    "tool": "microburst",
                    "params": {"mode": "enum"},
                    "description": "AWS资源枚举",
                })
                tools.append("microburst")

            # Metadata service
            actions.append({
                "type": "test",
                "description": "测试元数据服务访问（169.254.169.254）",
                "endpoints": ["/latest/meta-data/", "/latest/api/token"],
            })

            reasoning = f"已识别{cloud_provider or '云'}环境，进行云资源安全测试。"
            confidence = 0.8

        warnings.append("云API调用可能产生费用")
        warnings.append("S3枚举可能触发CloudTrail告警")
        warnings.append("元数据服务攻击是敏感操作")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"云安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1078.004", "T1552.001", "T1552.005", "T1526", "T1613"]

    def _get_required_inputs(self) -> List[str]:
        return ["cloud_provider", "cloud_credentials"]

    def _get_outputs(self) -> List[str]:
        return ["cloud_resources", "stored_secrets", "iam_privesc", "data_access"]