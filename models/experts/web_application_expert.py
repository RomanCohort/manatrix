"""
Web Application Security Expert

Expert in web application penetration testing, including OWASP Top 10,
business logic vulnerabilities, and web framework-specific issues.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class WebApplicationExpert(PenTestExpert):
    """Expert in web application security testing."""

    TOOLS = [
        "burpsuite", "sqlmap", "nikto", "dirb", "gobuster", "ffuf",
        "nuclei", "xsstrike", "ssrfmap", "jwt_tool", "commix",
        "wfuzz", "feroxbuster", "paramspider", "arjun"
    ]

    SYSTEM_PROMPT = """你是一位资深的Web应用安全测试专家。

专长领域：
- OWASP Top 10 漏洞测试（SQL注入、XSS、CSRF、SSRF等）
- Web服务发现和目录枚举
- API安全测试（REST、GraphQL）
- Web框架特定漏洞利用
- 业务逻辑漏洞挖掘
- WebShell上传和利用
- JWT/Token安全测试

工具集：
- burpsuite: Web代理和综合测试
- sqlmap: SQL注入自动化
- xsstrike: XSS检测
- ssrfmap: SSRF漏洞利用
- jwt_tool: JWT安全测试
- commix: 命令注入测试
- dirb/gobuster/feroxbuster: 目录枚举
- nuclei: 漏洞扫描
- wfuzz/ffuf: Fuzzing测试

测试原则：
1. 从信息收集开始，了解目标技术栈
2. 测试标准漏洞（OWASP Top 10）
3. 挖掘业务逻辑漏洞
4. 注意测试用例的边界条件
5. 验证漏洞的实际影响
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.WEB_APPLICATION,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze web application security testing opportunities."""
        self.call_count += 1

        services = state.get("services", [])
        vulnerabilities = state.get("vulnerabilities", [])
        target = state.get("target", "")

        # Find web services
        web_services = [s for s in services if self._is_web_service(s)]
        web_vulns = [v for v in vulnerabilities if self._is_web_vuln(v)]

        actions = []
        tools = []
        warnings = []
        relevant_cves = []
        reasoning = ""
        confidence = 0.5

        if not web_services and not web_vulns:
            # No web services identified
            actions.append({
                "type": "scan",
                "tool": "nuclei",
                "params": {"target": target, "tags": ["web"]},
                "description": "扫描Web服务",
            })
            actions.append({
                "type": "recon",
                "tool": "whatweb",
                "params": {"target": target},
                "description": "识别Web技术栈",
            })
            tools.extend(["nuclei", "whatweb"])
            reasoning = "未发现Web服务，先进行Web指纹识别。"
            confidence = 0.7

        else:
            # Directory enumeration
            for service in web_services[:2]:
                url = self._get_url(service, target)
                actions.append({
                    "type": "recon",
                    "tool": "gobuster",
                    "params": {
                        "url": url,
                        "wordlist": "dirb/common.txt",
                        "extensions": "php,html,asp,aspx,jsp",
                    },
                    "description": f"目录枚举: {url}",
                })
                tools.append("gobuster")

            # Check for SQL injection
            if web_vulns:
                sql_vulns = [v for v in web_vulns if self._is_sql_vuln(v)]
                if sql_vulns or not web_vulns:
                    actions.append({
                        "type": "exploit",
                        "tool": "sqlmap",
                        "params": {"target": url, "risk": 1, "level": 1},
                        "description": "SQL注入测试",
                    })
                    tools.append("sqlmap")

            # Check for XSS
            actions.append({
                "type": "scan",
                "tool": "xsstrike",
                "params": {"target": url, "crawl": True},
                "description": "XSS漏洞扫描",
                "optional": True,
            })
            tools.append("xsstrike")

            # Nikto scan
            actions.append({
                "type": "scan",
                "tool": "nikto",
                "params": {"target": url},
                "description": "Web服务器安全扫描",
            })
            tools.append("nikto")

            # Check for API
            if any("api" in str(s).lower() for s in web_services):
                actions.append({
                    "type": "recon",
                    "tool": "ffuf",
                    "params": {
                        "url": url + "/FUZZ",
                        "wordlist": "api_endpoints.txt",
                    },
                    "description": "API端点枚举",
                })
                tools.append("ffuf")

            reasoning = f"已识别 {len(web_services)} 个Web服务，进行综合测试。"
            confidence = 0.8

        # Add warnings
        warnings.append("Web测试可能产生大量请求，注意日志记录")
        warnings.append("SQL注入等测试可能修改数据库内容")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"Web应用安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
            relevant_cves=relevant_cves,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _is_web_service(self, service) -> bool:
        """Check if service is a web service."""
        s = str(service).lower()
        web_indicators = ["http", "https", "web", "apache", "nginx", "iis",
                          "tomcat", "jboss", "glassfish", "80", "443", "8080", "8443"]
        return any(ind in s for ind in web_indicators)

    def _is_web_vuln(self, vuln) -> bool:
        """Check if vulnerability is web-related."""
        v = str(vuln).lower()
        return any(ind in v for ind in ["xss", "sql", "injection", "csrf", "ssrf",
                                          "rce", "upload", "idor", "lfi", "rfi", "xxe"])

    def _is_sql_vuln(self, vuln) -> bool:
        """Check if vulnerability is SQL injection."""
        v = str(vuln).lower()
        return any(ind in v for ind in ["sql", "injection", "sqli"])

    def _get_url(self, service, target) -> str:
        """Convert service info to URL."""
        s = str(service).lower()
        if "https" in s:
            return f"https://{target}"
        return f"http://{target}"

    def _get_techniques(self) -> List[str]:
        return ["T1190", "T1059.007", "T1211", "T1051", "T1552.001"]

    def _get_required_inputs(self) -> List[str]:
        return ["target", "services"]

    def _get_outputs(self) -> List[str]:
        return ["web_vulnerabilities", "endpoints", "database_dump", "webshell"]
