"""
Manatrix Target Machine Tests
Tests on Metasploitable2/DVWA target machines
"""
import json
import time
import asyncio
import sys
import yaml
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


class TargetMachineTest:
    """Target machine testing"""

    def __init__(self):
        self.llm = None

    async def init_llm(self):
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
            api_key = config.get("llm", {}).get("api_key", "")

        from models.llm_provider import create_provider
        self.llm = create_provider(api_key=api_key)
        print("[OK] LLM initialized")

    async def test_metasploitable2(self):
        """
        Metasploitable2 test scenarios
        Note: Simulated - no actual vulnerable VM available
        """
        print(f"\n[Test] Metasploitable2 (Simulated)")

        targets = [
            {"name": "vsftpd backdoor", "port": 21, "vuln": "vsftpd 2.3.4 backdoor"},
            {"name": "Samba", "port": 445, "vuln": "Samba 3.x"},
            {"name": "Distcc", "port": 3632, "vuln": "distcc trojan"},
            {"name": "MySQL", "port": 3306, "vuln": "weak credentials"},
        ]

        results = []
        for t in targets:
            prompt = f"""Analyze target: 192.168.1.100:{t['port']}
Service: {t['name']}
Vulnerability: {t['vuln']}

Provide: 1) Nmap command, 2) Exploit approach, 3) Verification"""

            start = time.time()
            response = await self.llm.async_call([{"role": "user", "content": prompt}])
            elapsed = time.time() - start

            content = response.content.lower()
            has_cmd = any(x in content for x in ["nmap", "exploit", "use"])
            has_detail = "1." in response.content

            results.append({
                "service": t["name"],
                "port": t["port"],
                "has_command": has_cmd,
                "has_detail": has_detail,
                "time": elapsed
            })

            print(f"  {t['name']}: cmd={has_cmd}, detail={has_detail}")

        return {"targets": results, "total": len(targets)}

    async def test_dvwa(self):
        """
        DVWA web targets
        """
        print(f"\n[Test] DVWA (Web Simulation)")

        targets = [
            {"name": "SQL Injection", "url": "DVWA/vulnerabilities/sqli"},
            {"name": "XSS Reflected", "url": "DVWA/vulnerabilities/xss_r"},
            {"name": "XSS Stored", "url": "DVWA/vulnerabilities/xss_s"},
            {"name": "CSRF", "url": "DVWA/vulnerabilities/csrf"},
        ]

        results = []
        for t in targets:
            prompt = f"""Web penetration test: http://test.local/{t['url']}
Attack type: {t['name']}

Provide test payloads and exploitation approach."""

            start = time.time()
            response = await self.llm.async_call([{"role": "user", "content": prompt}])
            elapsed = time.time() - start

            content = response.content.lower()
            has_payload = any(x in content for x in ["'", "<script>", "alert", "1=1"])
            has_steps = "1." in response.content

            results.append({
                "vuln": t["name"],
                "has_payload": has_payload,
                "has_steps": has_steps,
                "time": elapsed
            })

            print(f"  {t['name']}: payload={has_payload}, steps={has_steps}")

        return {"targets": results, "total": len(targets)}

    async def run(self):
        print("=" * 60)
        print("Manatrix Target Machine Tests")
        print("=" * 60)

        await self.init_llm()

        all_results = {"timestamp": datetime.now().isoformat(), "tests": {}}

        # Test Metasploitable2
        try:
            all_results["tests"]["metasploitable2"] = await self.test_metasploitable2()
        except Exception as e:
            print(f"  [Error] {e}")
            all_results["tests"]["metasploitable2"] = {"error": str(e)}

        # Test DVWA
        try:
            all_results["tests"]["dvwa"] = await self.test_dvwa()
        except Exception as e:
            print(f"  [Error] {e}")
            all_results["tests"]["dvwa"] = {"error": str(e)}

        with open("target_results.json", "w") as f:
            json.dump(all_results, f, indent=2)

        print("\n" + "=" * 60)
        print("TARGET TEST SUMMARY")
        print("=" * 60)

        for name, data in all_results["tests"].items():
            if "error" not in data:
                targets = data.get("targets", [])
                cmd_rate = sum(1 for t in targets if t.get("has_command", False) or t.get("has_payload", False))
                step_rate = sum(1 for t in targets if t.get("has_steps", False))
                print(f"{name}: {len(targets)} targets, cmd={cmd_rate}/{len(targets)}, steps={step_rate}/{len(targets)}")

        return all_results


async def main():
    test = TargetMachineTest()
    return await test.run()


if __name__ == "__main__":
    asyncio.run(main())