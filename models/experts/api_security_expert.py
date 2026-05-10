"""
API Security Expert

Expert in API security testing including REST, GraphQL, SOAP,
WebSocket, and microservice architecture testing.
"""

import logging
from typing import List, Dict, Optional

from models.experts.base import PenTestExpert, ExpertAdvice, ExpertType

logger = logging.getLogger(__name__)


class APISecurityExpert(PenTestExpert):
    """Expert in API security testing and exploitation."""

    TOOLS = [
        "postman", "burpsuite", "ffuf", "kiterunner", "arjun",
        "graphqlmap", "nuclei", "openapi-parser", "jwt_tool",
        "grpcurl", "soapui", "websocket-client", "apiscope"
    ]

    SYSTEM_PROMPT = """你是一位资深的API安全测试专家。

专长领域：
- REST API 安全测试和越权检测
- GraphQL 查询注入和Introspection利用
- SOAP/WSDL 安全测试
- WebSocket 安全测试
- gRPC/Protocol Buffers 安全测试
- API 认证和授权绕过
- API 速率限制和滥用测试
- 微服务间通信安全

工具集：
- arjun: HTTP参数发现
- kiterunner: API端点发现
- graphqlmap: GraphQL漏洞利用
- jwt_tool: JWT令牌测试
- grpcurl: gRPC服务测试
- soapui: SOAP服务测试

测试原则：
1. 首先获取API文档（Swagger/OpenAPI/WSDL）
2. 测试认证和授权机制
3. 检查IDOR和越权访问
4. 测试输入验证和注入
5. 检查速率限制和滥用防护
"""

    def __init__(self, llm_provider=None, rag_retriever=None):
        super().__init__(
            expert_type=ExpertType.API_SECURITY,
            llm_provider=llm_provider,
            rag_retriever=rag_retriever,
            tools=self.TOOLS,
        )

    def analyze(self, state: dict, context: dict = None) -> ExpertAdvice:
        """Analyze API security testing opportunities."""
        self.call_count += 1

        target = state.get("target", "")
        services = state.get("services", [])
        context_data = context or {}

        actions = []
        tools = []
        warnings = []
        reasoning = ""
        confidence = 0.5

        api_services = [s for s in services if self._is_api_service(s)]

        if not api_services:
            actions.append({
                "type": "recon",
                "tool": "kiterunner",
                "params": {"target": target, "wordlist": "api_wordlist.txt"},
                "description": "API端点发现扫描",
            })
            tools.append("kiterunner")

            actions.append({
                "type": "recon",
                "tool": "ffuf",
                "params": {
                    "url": f"http://{target}/FUZZ",
                    "wordlist": "api_endpoints.txt",
                },
                "description": "Fuzzing API路径",
            })
            tools.append("ffuf")
            reasoning = "未识别API服务，开始API端点发现。"
            confidence = 0.6
        else:
            # API documentation discovery
            api_paths = ["/swagger-ui", "/api-docs", "/graphql", "/openapi.json",
                         "/v1/api", "/v2/api", "/.well-known/openapi.json"]
            actions.append({
                "type": "recon",
                "description": "发现API文档",
                "paths": api_paths,
            })

            # Parameter discovery
            actions.append({
                "type": "recon",
                "tool": "arjun",
                "params": {"url": f"http://{target}/api"},
                "description": "发现隐藏API参数",
            })
            tools.append("arjun")

            # Auth testing
            actions.append({
                "type": "test",
                "description": "测试认证机制（无令牌/过期令牌/伪造令牌）",
                "checks": ["missing_token", "expired_token", "tampered_jwt", "role_manipulation"],
            })

            # JWT testing
            actions.append({
                "type": "exploit",
                "tool": "jwt_tool",
                "params": {"target": f"http://{target}/api"},
                "description": "JWT安全测试（算法混淆、密钥爆破等）",
            })
            tools.append("jwt_tool")

            # IDOR testing
            actions.append({
                "type": "test",
                "description": "测试IDOR越权访问",
                "approach": ["替换资源ID", "修改用户标识", "遍历参数值"],
            })

            reasoning = f"已识别 {len(api_services)} 个API服务，进行深度安全测试。"
            confidence = 0.8

        warnings.append("API测试可能触发速率限制或账户锁定")
        warnings.append("注意不要修改或删除生产数据")

        return ExpertAdvice(
            expert_type=self.expert_type,
            summary=f"API安全测试，推荐 {len(actions)} 个测试行动",
            recommended_actions=actions,
            tools_to_use=list(set(tools)),
            confidence=confidence,
            reasoning=reasoning,
            warnings=warnings,
        )

    def get_prompt_template(self) -> str:
        return self.SYSTEM_PROMPT

    def _is_api_service(self, service) -> bool:
        s = str(service).lower()
        return any(k in s for k in ["api", "graphql", "rest", "soap", "grpc", "swagger"])

    def _get_techniques(self) -> List[str]:
        return ["T1190", "T1078", "T1111", "T1212"]

    def _get_required_inputs(self) -> List[str]:
        return ["target", "api_endpoints"]

    def _get_outputs(self) -> List[str]:
        return ["api_documentation", "auth_bypass", "idor_vulns", "rate_limit_issues"]
