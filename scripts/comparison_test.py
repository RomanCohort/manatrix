"""
Manatrix Comparison Experiments
对比实验: LLM-only vs LLM+RAG vs Full System
"""
import json
import time
import asyncio
import sys
import yaml
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


class ComparisonExperiment:
    """对比实验框架"""

    def __init__(self):
        self.results = {}
        self.llm = None

    async def init_llm(self):
        """初始化LLM"""
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
            api_key = config.get("llm", {}).get("api_key", "")

        from models.llm_provider import create_provider
        self.llm = create_provider(api_key=api_key)
        print("[OK] LLM initialized")

    async def test_llm_only(self, target: str, goal: str):
        """
        测试纯LLM方法 (无RAG, 无MoE, 无专家)
        只依赖LLM的通用知识
        """
        print(f"\n[Test 1] LLM-only (no RAG, no experts)")

        prompt = f"""You are a penetration tester. Target: {target}, Goal: {goal}
Provide a detailed attack plan using your general knowledge only."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        # 分析响应质量
        plan_length = len(response.content)
        has_specifics = any(x in response.content.lower() for x in [
            "cve-", "nmap", "metasploit", "exploit", "vulnerability"
        ])

        result = {
            "time": elapsed,
            "plan_length": plan_length,
            "has_specifics": has_specifics,
            "response_preview": response.content[:200]
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Plan length: {plan_length} chars")
        print(f"  Has specifics: {has_specifics}")

        return result

    async def test_llm_with_rag(self, target: str, goal: str, query: str):
        """
        测试LLM + RAG (有知识库)
        """
        print(f"\n[Test 2] LLM + RAG (with knowledge base)")

        # 模拟RAG检索
        from models.vector_store import EmbeddingService, VectorStore
        embedding_service = EmbeddingService()
        vector_store = VectorStore()

        # 检索相关知识
        try:
            query_emb = embedding_service.embed([query])
            results = vector_store.search(query_emb, k=5)
            context = "\n".join([r.content for r in results]) if results else "No context found"
        except:
            context = "[RAG unavailable - using hash embeddings]"

        prompt = f"""You are a penetration tester. Target: {target}, Goal: {goal}

Relevant Knowledge:
{context}

Provide an attack plan based on the above knowledge."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        plan_length = len(response.content)
        has_cve = "cve-" in response.content.lower()

        result = {
            "time": elapsed,
            "plan_length": plan_length,
            "has_cve": has_cve,
            "has_context": context != "[RAG unavailable]"
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Plan length: {plan_length} chars")
        print(f"  Has CVE references: {has_cve}")

        return result

    async def test_llm_with_experts(self, target: str, goal: str):
        """
        测试LLM + 专家路由
        """
        print(f"\n[Test 3] LLM + Expert Routing")

        # 确定目标类型
        if "http://" in target or "https://" in target:
            target_type = "web"
            expert = "WebSecurityExpert"
        elif "192.168" in target or "10." in target:
            target_type = "network"
            expert = "NetworkReconExpert"
        else:
            target_type = "general"
            expert = "FullScopeExpert"

        prompt = f"""As a {expert}, analyze target: {target}
Goal: {goal}

Provide a detailed penetration test plan specific to {target_type} targets."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        plan_length = len(response.content)
        has_domain_knowledge = any(x in response.content.lower() for x in [
            "web", "sql", "xss", "network", "port", "smb", "ldap"
        ])

        result = {
            "time": elapsed,
            "plan_length": plan_length,
            "expert_used": expert,
            "has_domain_knowledge": has_domain_knowledge
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Expert: {expert}")
        print(f"  Has domain knowledge: {has_domain_knowledge}")

        return result

    async def test_full_system(self, target: str, goal: str):
        """
        测试完整系统 (LLM + RAG + MoE + Team)
        """
        print(f"\n[Test 4] Full System (LLM + RAG + MoE + Team)")

        # 组合所有组件
        from models.vector_store import EmbeddingService, VectorStore
        from models.expert_router import ExpertRouter

        # RAG
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        try:
            query_emb = embedding_service.embed([target])
            results = vector_store.search(query_emb, k=5)
            context = "\n".join([r.content for r in results])
        except:
            context = ""

        # Expert routing
        router = ExpertRouter()
        state = {"target": target, "goal": goal}
        try:
            decision = router.analyze_situation(state)
            expert = decision.primary_expert.name if decision else "Unknown"
        except:
            expert = "FullScope"

        # Full prompt
        prompt = f"""As {expert} expert with access to vulnerability database:

Target: {target}
Goal: {goal}

Vulnerability Context:
{context}

Provide a comprehensive attack plan including:
1. Reconnaissance
2. Vulnerability identification
3. Exploitation
4. Post-exploitation
5. Evidence collection"""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        plan_length = len(response.content)
        has_full_coverage = all(x in response.content.lower() for x in [
            "recon", "exploit", "post"
        ])

        result = {
            "time": elapsed,
            "plan_length": plan_length,
            "expert": expert,
            "full_coverage": has_full_coverage
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Expert: {expert}")
        print(f"  Full coverage: {has_full_coverage}")

        return result

    async def run_comparison(self):
        """运行对比实验"""
        print("=" * 60)
        print("Manatrix Comparison Experiments")
        print("=" * 60)

        await self.init_llm()

        # 测试场景
        test_cases = [
            {
                "name": "Web Application Test",
                "target": "http://test.example.com",
                "goal": "Find SQL injection vulnerabilities",
                "query": "SQL injection web vulnerability"
            },
            {
                "name": "Network Penetration",
                "target": "192.168.1.100",
                "goal": "Gain initial access and escalate privileges",
                "query": "Windows privilege escalation"
            }
        ]

        all_results = {"timestamp": datetime.now().isoformat(), "experiments": {}}

        for case in test_cases:
            print(f"\n{'='*50}")
            print(f"Scenario: {case['name']}")
            print(f"Target: {case['target']}")
            print(f"Goal: {case['goal']}")
            print("=" * 50)

            results = {}

            # Test 1: LLM-only
            try:
                results["llm_only"] = await self.test_llm_only(case["target"], case["goal"])
            except Exception as e:
                print(f"  [Error] {e}")
                results["llm_only"] = {"error": str(e)}

            # Test 2: LLM + RAG
            try:
                results["llm_rag"] = await self.test_llm_with_rag(
                    case["target"], case["goal"], case["query"]
                )
            except Exception as e:
                print(f"  [Error] {e}")
                results["llm_rag"] = {"error": str(e)}

            # Test 3: LLM + Experts
            try:
                results["llm_experts"] = await self.test_llm_with_experts(
                    case["target"], case["goal"]
                )
            except Exception as e:
                print(f"  [Error] {e}")
                results["llm_experts"] = {"error": str(e)}

            # Test 4: Full System
            try:
                results["full_system"] = await self.test_full_system(
                    case["target"], case["goal"]
                )
            except Exception as e:
                print(f"  [Error] {e}")
                results["full_system"] = {"error": str(e)}

            all_results["experiments"][case["name"]] = results

        # 保存结果
        with open("comparison_results.json", "w") as f:
            json.dump(all_results, f, indent=2)

        # 打印总结
        print("\n" + "=" * 60)
        print("COMPARISON SUMMARY")
        print("=" * 60)

        for case_name, results in all_results["experiments"].items():
            print(f"\n{case_name}:")

            for method, data in results.items():
                if "error" not in data:
                    print(f"  {method}:")
                    print(f"    Time: {data.get('time', 'N/A'):.1f}s")
                    print(f"    Plan length: {data.get('plan_length', 'N/A')} chars")

        return all_results


async def main():
    experiment = ComparisonExperiment()
    results = await experiment.run_comparison()
    return results


if __name__ == "__main__":
    asyncio.run(main())