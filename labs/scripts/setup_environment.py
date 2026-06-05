"""
Environment Setup Script
========================

Automated setup for penetration testing lab environments.

Usage:
    python labs/scripts/setup_environment.py --install dvwa
    python labs/scripts/setup_environment.py --check-all
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class EnvironmentSetup:
    """Setup penetration testing environments."""

    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def check_docker(self) -> bool:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print(f"[+] Docker installed: {result.stdout.strip()}")
                return True
            else:
                print("[-] Docker not installed")
                return False
        except Exception as e:
            print(f"[-] Docker check failed: {e}")
            return False

    def install_dvwa(self) -> bool:
        """Install DVWA using Docker."""
        print("\n[*] Installing DVWA...")

        if not self.check_docker():
            print("[-] Docker not available, cannot install DVWA")
            return False

        try:
            # Pull DVWA image
            print("[*] Pulling DVWA Docker image...")
            result = subprocess.run(
                ["docker", "pull", "vulnerables/web-dvwa"],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                print(f"[-] Failed to pull image: {result.stderr}")
                return False

            # Run DVWA container
            print("[*] Starting DVWA container...")
            result = subprocess.run(
                ["docker", "run", "-d", "-p", "80:80", "--name", "dvwa", "vulnerables/web-dvwa"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                print(f"[+] DVWA started on http://localhost:80")
                print("[+] Login: admin/password")
                return True
            elif "already in use" in result.stderr or "Conflict" in result.stderr:
                print("[+] DVWA container already running")
                return True
            else:
                print(f"[-] Failed to start DVWA: {result.stderr}")
                return False

        except Exception as e:
            print(f"[-] DVWA installation failed: {e}")
            return False

    def check_metasploitable(self) -> bool:
        """Check Metasploitable2 availability."""
        print("\n[*] Checking Metasploitable2...")

        # Check for VM file
        vm_path = Path("D:/password_guesser/labs/metasploitable/Metasploitable2.vmx")

        if vm_path.exists():
            print(f"[+] Metasploitable2 VM found at {vm_path}")
            return True
        else:
            print("[-] Metasploitable2 not found")
            print("[*] Download from: https://sourceforge.net/projects/metasploitable/")
            return False

    def check_htb_vpn(self) -> bool:
        """Check HackTheBox VPN configuration."""
        print("\n[*] Checking HackTheBox VPN...")

        vpn_config = Path.home() / ".config" / "htb.ovpn"

        if vpn_config.exists():
            print(f"[+] HTB VPN config found: {vpn_config}")
            return True
        else:
            print("[-] HTB VPN not configured")
            print("[*] Download VPN config from: https://app.hackthebox.com")
            return False

    def check_tools(self) -> Dict:
        """Check required penetration testing tools."""
        print("\n[*] Checking penetration testing tools...")

        tools = {
            "nmap": ["nmap", "--version"],
            "metasploit": ["msfconsole", "--version"],
            "hydra": ["hydra", "-h"],
            "sqlmap": ["sqlmap", "--version"],
            "curl": ["curl", "--version"],
        }

        results = {}

        for tool, cmd in tools.items():
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    print(f"[+] {tool}: installed")
                    results[tool] = True
                else:
                    print(f"[-] {tool}: not installed")
                    results[tool] = False
            except Exception as e:
                print(f"[-] {tool}: error - {e}")
                results[tool] = False

        return results

    def check_all(self) -> Dict:
        """Check all environments."""
        print("\n" + "="*60)
        print("  Penetration Testing Environment Check")
        print("="*60)

        results = {
            "docker": self.check_docker(),
            "dvwa": self.install_dvwa() if self.check_docker() else False,
            "metasploitable": self.check_metasploitable(),
            "htb_vpn": self.check_htb_vpn(),
            "tools": self.check_tools()
        }

        # Save status
        self._save_status(results)

        return results

    def _save_status(self, results: Dict):
        """Save environment status."""
        output_dir = Path("D:/password_guesser/results")
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / f"env_status_{self.timestamp}.json"

        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n[+] Status saved: {output_file}")

        # Summary
        print("\n" + "="*60)
        print("  Environment Status Summary")
        print("="*60)

        print(f"\nDocker: {'✓' if results['docker'] else '✗'}")
        print(f"DVWA: {'✓' if results['dvwa'] else '✗'}")
        print(f"Metasploitable2: {'✓' if results['metasploitable'] else '✗'}")
        print(f"HTB VPN: {'✓' if results['htb_vpn'] else '✗'}")

        tools = results.get('tools', {})
        tools_ok = sum(1 for v in tools.values() if v)
        print(f"Tools: {tools_ok}/{len(tools)} installed")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Environment Setup")
    parser.add_argument("--install", choices=["dvwa"], help="Install environment")
    parser.add_argument("--check-all", action="store_true", help="Check all environments")
    args = parser.parse_args()

    setup = EnvironmentSetup()

    if args.install == "dvwa":
        setup.install_dvwa()
    elif args.check_all:
        setup.check_all()
    else:
        # Default: check all
        setup.check_all()


if __name__ == "__main__":
    main()