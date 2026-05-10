"""
Supply Chain Security Expert

Expert in supply chain attacks including dependency confusion,
typosquatting, malicious packages, and third-party component vulnerabilities.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class SupplyChainExpert(PenTestExpert):
    """Expert in supply chain security testing."""

    TOOLS = [
        "checkmarx", "snyk", "trufflehog", "package-lists", "typosquat",
        "dependency-check", "retire-js", "npm-audit", "pip-audit",
        "cargo-audit", "grype", "trivy", "syft", "cyclonedx"
    ]

    SYSTEM_PROMPT = """你是一位资深的供应链安全测试专家。

专长领域：
- 依赖混淆攻击
- Typosquatting攻击
- 恶意包检测
- 第三方组件漏洞
- 源码泄露检测
- CI/CD安全测试
- 容器镜像安全
- NPM/PyPI/Java攻击

供应链攻击技术：
1. 依赖混淆：发布同名高版本包
2. Typosquatting：注册近似名称的包
3. 恶意提交：向开源项目植入后门
4. 供应链污染：攻击构建工具

测试工具：
- snyk: 依赖漏洞扫描
- grype/trivy: 容器镜像扫描
- trufflehog: 密钥扫描
- retire-js: JavaScript漏洞扫描
- npm-audit: NPM包安全检查

测试原则：
1. 枚举所有第三方依赖
2. 检查版本和已知漏洞
3. 搜索相似的恶意包
4. 分析CI/CD管道安全
5. 测试构建过程完整性
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.SUPPLY_CHAIN,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze supply chain security opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        package_manager = state.get("package_manager", "")  # npm, pip, maven, etc
        dependencies = state.get("dependencies", [])
        ci_cd = state.get("ci_cd", False)

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        if dependencies or package_manager:
            # Dependency vulnerability scanning
            if "npm" in package_manager.lower() or "node" in package_manager.lower():
                actions.append({
                    "type": "scan",
                    "tool": "npm-audit",
                    "params": {"package.json": "package.json"},
                    "description": "扫描NPM依赖漏洞",
                })
                tools.append("npm-audit")

                actions.append({
                    "type": "scan",
                    "tool": "retire-js",
                    "params": {"path": "node_modules"},
                    "description": "扫描JavaScript漏洞",
                })
                tools.append("retire-js")

            elif "pip" in package_manager.lower() or "python" in package_manager.lower():
                actions.append({
                    "type": "scan",
                    "tool": "pip-audit",
                    "params": {"requirements": "requirements.txt"},
                    "description": "扫描Python依赖漏洞",
                })
                tools.append("pip-audit")

            elif "maven" in package_manager.lower() or "java" in package_manager.lower():
                actions.append({
                    "type": "scan",
                    "tool": "dependency-check",
                    "params": {"project": "pom.xml"},
                    "description": "扫描Maven依赖漏洞",
                })
                tools.append("dependency-check")

            elif "cargo" in package_manager.lower() or "rust" in package_manager.lower():
                actions.append({
                    "type": "scan",
                    "tool": "cargo-audit",
                    "params": {},
                    "description": "扫描Cargo依赖漏洞",
                })
                tools.append("cargo-audit")

            # General supply chain scan
            actions.append({
                "type": "scan",
                "tool": "snyk",
                "params": {"test": "all"},
                "description": "综合供应链漏洞扫描",
            })
            tools.append("snyk")

            # Typosquatting check
            actions.append({
                "type": "search",
                "tool": "typosquat",
                "params": {"packages": dependencies[:10]},
                "description": "检查恶意包名称",
            })

            reasoning = f"发现 {package_manager or '未知'} 依赖，进行供应链扫描。"
            confidence = 0.75

        else:
            # Find dependencies
            actions.append({
                "type": "recon",
                "description": "枚举项目依赖",
                "files": [
                    "package.json",
                    "requirements.txt",
                    "pom.xml",
                    "go.mod",
                    "Cargo.toml",
                    "Gemfile",
                    "composer.json",
                ],
            })
            reasoning = "未发现依赖配置，先枚举依赖文件。"
            confidence = 0.5

        # CI/CD security
        if ci_cd:
            actions.append({
                "type": "audit",
                "description": "审计CI/CD管道安全",
                "checks": [
                    " secrets",
                    " weak permissions",
                    " untrusted input",
                    " artifact verification",
                ],
            })

        # Container scanning
        if state.get("dockerfile") or state.get("container_images"):
            actions.append({
                "type": "scan",
                "tool": "trivy",
                "params": {"images": state.get("container_images", [])},
                "description": "扫描容器镜像漏洞",
            })
            tools.append("trivy")

            actions.append({
                "type": "scan",
                "tool": "syft",
                "params": {"output": "cyclonedx"},
                "description": "生成SBOM清单",
            })
            tools.append("syft")

        warnings.append("供应链测试可能影响CI/CD流程")
        warnings.append("恶意包检测需要注意命名相似性")
        warnings.append("扫描结果需要人工验证")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"供应链安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _get_techniques(self) -> List[str]:
        return ["T1195.001", "T1195.002", "T1195.003", "T1195.004", "T1574.006"]

    def _get_required_inputs(self) -> List[str]:
        return ["dependencies", "package_manager"]

    def _get_outputs(self) -> List[str]:
        return ["vulnerable_dependencies", "malicious_packages", "secrets_leaked"]