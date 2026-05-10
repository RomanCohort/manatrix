"""
Manatrix Ablation Experiments
Test each component's contribution
"""
import json
import time
import asyncio
import sys
import yaml
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


class AblationExperiment:
    """Ablation study"""

    def __init__(self):
        self.llm = None

    async def init_llm(self):
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
            api_key = config.get("llm", {}).get("api_key", "")

        from models.llm_provider import create_provider
        self.llm = create_provider(api_key=api_key)
        print("[OK] LLM initialized")

    async def test_baseline(self, target: str, goal: str):
        """Full system"""
        print(f"\n[Baseline] Full System")

        prompt = f"""As penetration testing team lead with KB access:

Target: {target}
Goal: {goal}

KB: SMB enumeration: enum4linux, CVE-2021-XXXX. SQLi: sqlmap available.

Provide comprehensive plan with recon, vuln find, exploit, post-exploit sections."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        content = response.content.lower()
        score = sum([
            "recon" in content,
            "exploit" in content,
            "post" in content or "persistence" in content,
            len(response.content) > 3000
        ])

        return {"time": elapsed, "score": score, "length": len(response.content)}

    async def test_no_kb(self, target: str, goal: str):
        """No knowledge base"""
        print(f"\n[Ablation] No Knowledge Base")

        prompt = f"""As penetration tester:

Target: {target}
Goal: {goal}

Provide plan with sections: recon, vuln find, exploit, post-exploit."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        content = response.content.lower()
        score = sum([
            "recon" in content,
            "exploit" in content,
            "post" in content or "persistence" in content,
            len(response.content) > 2000
        ])

        return {"time": elapsed, "score": score, "length": len(response.content)}

    async def test_no_expert(self, target: str, goal: str):
        """No expert routing - just general"""
        print(f"\n[Ablation] No Expert Routing")

        prompt = f"""You are a penetration tester. Target: {target}, Goal: {goal}

Provide a plan."""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        content = response.content.lower()
        score = sum([
            "1." in response.content,
            "2." in response.content,
            len(response.content) > 1000
        ])

        return {"time": elapsed, "score": score, "length": len(response.content)}

    async def test_no_struct(self, target: str, goal: str):
        """No structure - minimal"""
        print(f"\n[Ablation] No Structure")

        prompt = f"""How would you penetration test {target}?"""

        start = time.time()
        response = await self.llm.async_call([{"role": "user", "content": prompt}])
        elapsed = time.time() - start

        return {"time": elapsed, "score": 1 if len(response.content) > 500 else 0, "length": len(response.content)}

    async def run(self):
        print("=" * 60)
        print("Manatrix Ablation Experiments")
        print("=" * 60)

        await self.init_llm()

        cases = [
            {"name": "Web Test", "target": "https://test.example.com", "goal": "Find vuln"},
            {"name": "Network Test", "target": "192.168.1.50", "goal": "Get access"},
        ]

        results = {"timestamp": datetime.now().isoformat(), "ablations": {}}

        for case in cases:
            print(f"\n{'='*50}")
            print(f"Case: {case['name']}")
            print("=" * 50)

            r = {}
            try:
                r["baseline"] = await self.test_baseline(case["target"], case["goal"])
            except Exception as e:
                r["baseline"] = {"error": str(e)}

            try:
                r["no_kb"] = await self.test_no_kb(case["target"], case["goal"])
            except Exception as e:
                r["no_kb"] = {"error": str(e)}

            try:
                r["no_expert"] = await self.test_no_expert(case["target"], case["goal"])
            except Exception as e:
                r["no_expert"] = {"error": str(e)}

            try:
                r["no_struct"] = await self.test_no_struct(case["target"], case["goal"])
            except Exception as e:
                r["no_struct"] = {"error": str(e)}

            results["ablations"][case["name"]] = r

        with open("ablation_results.json", "w") as f:
            json.dump(results, f, indent=2)

        print("\n" + "=" * 60)
        print("ABLATION SUMMARY")
        print("=" * 60)

        for name, data in results["ablations"].items():
            print(f"\n{name}:")
            base_score = data.get("baseline", {}).get("score", 0)
            for config, res in data.items():
                if "error" not in res:
                    score = res.get("score", 0)
                    diff = score - base_score
                    print(f"  {config}: score={score}, time={res.get('time', 0):.1f}s, diff={diff:+d}")

        return results


async def main():
    exp = AblationExperiment()
    return await exp.run()


if __name__ == "__main__":
    asyncio.run(main())