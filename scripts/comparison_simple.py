"""
Manatrix Comparison Experiments - Simplified (No RAG downloads)
Tests: LLM-only vs LLM+Experts vs Full System
"""
import json
import time
import asyncio
import sys
import yaml
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


class SimpleComparison:
    """Simplified comparison - no RAG downloads"""

    def __init__(self):
        self.llm = None

    async def init_llm(self):
        """Initialize LLM"""
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
            api_key = config.get("llm", {}).get("api_key", "")

        from models.llm_provider import create_provider
        self.llm = create_provider(api_key=api_key)
        print("[OK] LLM initialized")

    async def test_llm_only(self, target: str, goal: str):
        """
        Test 1: Pure LLM - no RAG, no domain experts
        Just uses LLM general knowledge
        """
        print(f"\n[Test 1] LLM-only (general knowledge only)")

        prompt = f"""You are a penetration tester. Target: {target}, Goal: {goal}
Provide a detailed attack plan using your general security knowledge."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        content = response.content.lower()
        has_cve = "cve-" in content
        has_tool = any(x in content for x in ["nmap", "metasploit", "sqlmap"])
        has_specific = any(x in content for x in ["injection", "xss", "sqli", "exploit"])

        result = {
            "time": elapsed,
            "has_cve": has_cve,
            "has_tool": has_tool,
            "has_specific": has_specific,
            "length": len(response.content)
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Has CVE: {has_cve}, Has tools: {has_tool}, Specific: {has_specific}")

        return result

    async def test_llm_with_expert(self, target: str, goal: str):
        """
        Test 2: LLM + domain expert routing
        Adds expert context to prompt
        """
        print(f"\n[Test 2] LLM + Expert Routing")

        # Determine target type
        if "http://" in target or "https://" in target:
            expert = "WebSecurityExpert"
            expertise = "web application security, SQL injection, XSS, CSRF"
        elif "192.168" in target or "10." in target:
            expert = "NetworkSecurityExpert"
            expertise = "network penetration, lateral movement, privilege escalation"
        else:
            expert = "FullScopeExpert"
            expertise = "comprehensive penetration testing"

        prompt = f"""As a {expert} specialized in {expertise}:

Target: {target}
Goal: {goal}

Provide a detailed penetration test plan leveraging {expert} domain knowledge."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        content = response.content.lower()
        has_cve = "cve-" in content
        has_technique = any(x in content for x in ["recon", "scan", "exploit", "payload"])
        has_steps = "1." in response.content or "step" in content

        result = {
            "time": elapsed,
            "expert": expert,
            "has_cve": has_cve,
            "has_technique": has_technique,
            "has_steps": has_steps,
            "length": len(response.content)
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Expert: {expert}")
        print(f"  Has CVE: {has_cve}, Techniques: {has_technique}, Steps: {has_steps}")

        return result

    async def test_full_system(self, target: str, goal: str):
        """
        Test 3: Full system prompt with knowledge base simulation
        """
        print(f"\n[Test 3] Full System")

        # Simulated KB context (no download needed)
        kb_context = {
            "web": "SQL injection: Test with ' OR '1'='1, use sqlmap. CVE-2023-XXXX. XSS: <script>alert(1)</script>",
            "network": "SMB enumeration: enum4linux, port 445. CVE-2021-XXXX. Use impacket.",
            "default": "Information gathering first, then targeted exploitation."
        }

        # Select KB
        if "http://" in target or "https://" in target:
            context = kb_context["web"]
        elif "192.168" in target or "10." in target:
            context = kb_context["network"]
        else:
            context = kb_context["default"]

        prompt = f"""You are a penetration testing team lead with access to vulnerability knowledge base:

Target: {target}
Goal: {goal}

Relevant KB:
{context}

Provide a comprehensive plan:
1. Reconnaissance
2. Vulnerability discovery
3. Exploitation
4. Post-exploitation
5. Report"""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        content = response.content.lower()
        has_cve = "cve-" in content
        full_coverage = all(x in content for x in ["recon", "exploit", "post"])

        result = {
            "time": elapsed,
            "has_cve": has_cve,
            "full_coverage": full_coverage,
            "length": len(response.content)
        }

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Has CVE: {has_cve}, Full coverage: {full_coverage}")

        return result

    async def run(self):
        """Run comparison"""
        print("=" * 60)
        print("Manatrix Comparison Experiments")
        print("=" * 60)

        await self.init_llm()

        test_scenarios = [
            {"name": "Web App SQLi", "target": "https://test.example.com", "goal": "Find SQL injection"},
            {"name": "Network Access", "target": "192.168.1.100", "goal": "Gain access"},
        ]

        all_results = {"timestamp": datetime.now().isoformat(), "scenarios": {}}

        for case in test_scenarios:
            print(f"\n{'='*50}")
            print(f"Scenario: {case['name']}")
            print(f"Target: {case['target']}")
            print("=" * 50)

            r = {}

            try:
                r["llm_only"] = await self.test_llm_only(case["target"], case["goal"])
            except Exception as e:
                print(f"  [Error] {e}")
                r["llm_only"] = {"error": str(e)}

            try:
                r["llm_expert"] = await self.test_llm_with_expert(case["target"], case["goal"])
            except Exception as e:
                print(f"  [Error] {e}")
                r["llm_expert"] = {"error": str(e)}

            try:
                r["full_system"] = await self.test_full_system(case["target"], case["goal"])
            except Exception as e:
                print(f"  [Error] {e}")
                r["full_system"] = {"error": str(e)}

            all_results["scenarios"][case["name"]] = r

        # Save results
        with open("comparison_results.json", "w") as f:
            json.dump(all_results, f, indent=2)

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        for name, data in all_results["scenarios"].items():
            print(f"\n{name}:")
            for method, res in data.items():
                if "error" not in res:
                    print(f"  {method}: {res.get('time', 0):.1f}s, CVE={res.get('has_cve', False)}, len={res.get('length', 0)}")

        return all_results


async def main():
    comp = SimpleComparison()
    results = await comp.run()
    return results


if __name__ == "__main__":
    asyncio.run(main())