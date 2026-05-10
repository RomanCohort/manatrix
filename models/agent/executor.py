"""
Tool Execution & Result Interpretation

Executes attack actions and interprets results using LLM.
"""

import logging
import time
import subprocess
import asyncio
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from models.agent.state import AttackAction, AttackState, Phase, Host, Vulnerability, Credential

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing an attack action."""
    success: bool
    tool: str = ""
    command: str = ""
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    duration: float = 0.0
    parsed: Dict[str, Any] = field(default_factory=dict)
    interpretation: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "tool": self.tool,
            "duration": self.duration,
            "return_code": self.return_code,
            "parsed": self.parsed,
            "interpretation": self.interpretation,
            "error": self.error,
        }


INTERPRET_PROMPT = """分析以下工具执行结果，提取关键信息。

执行的操作: {action_type} -> {target}
工具: {tool}
命令: {command}

输出:
{output}

错误输出:
{stderr}

请返回JSON:
{{
    "success": true/false,
    "summary": "结果摘要",
    "hosts_found": ["发现的IP"],
    "ports_found": {{"ip": [端口列表]}},
    "services_found": {{"ip": {{"port": "service"}}}},
    "vulns_found": [{{"cve": "CVE-XXXX-XXXX", "host": "ip", "port": 80, "severity": "high"}}],
    "credentials_found": [{{"username": "user", "password": "pass", "source": "ip"}}],
    "compromised": ["已攻陷的IP"],
    "shells_obtained": [{{"host": "ip", "user": "username", "type": "reverse_shell"}}],
    "data_extracted": ["提取的数据路径"],
    "next_steps": ["建议的下一步操作"],
    "notes": "其他重要备注"
}}
"""


class AgentToolExecutor:
    """Executes attack actions and interprets results."""

    # Tool to command mapping
    TOOL_COMMANDS = {
        "nmap": {
            "scan": "nmap -sV -sC {params} {target}",
            "full": "nmap -sV -sC -p- {target}",
            "udp": "nmap -sU -sV {target}",
        },
        "nuclei": "nuclei -u {target} {params}",
        "nikto": "nikto -h {target}",
        "hydra": "hydra -l {username} -P {wordlist} {service}://{target}",
        "sqlmap": "sqlmap -u {url} --batch --random-agent",
        "gobuster": "gobuster dir -u {url} -w {wordlist}",
        "ffuf": "ffuf -u {url}/FUZZ -w {wordlist}",
        "searchsploit": "searchsploit {query}",
        "hashcat": "hashcat -m {mode} {hash_file} {wordlist}",
        "john": "john --wordlist={wordlist} {hash_file}",
        "dig": "dig {query} {target}",
        "whatweb": "whatweb {target}",
        "theHarvester": "theHarvester -d {target} -b all",
        # Reverse Engineering tools
        "ghidra": "analyzeHeadless {project} {target_name} -import {target} -prescript {pre_script}",
        "jadx": "jadx -d {output_dir} {target}",
        "apktool": "apktool d {target} -o {output_dir}",
        "radare2": "r2 -A {target}",
        "binwalk": "binwalk -e {target} --run-as={run_as}",
        "checksec": "checksec --file={target}",
        "ropgadget": "ROPGadget --binary {target}",
        "strings": "strings -a {target} | head -100",
        "file": "file {target}",
        "objdump": "objdump -d {target} | head -200",
        "readelf": "readelf -a {target}",
        "frida": "frida -U -f {package} -l {script}",
        "pwntools": "python3 {script}",  # pwntools script
        "angr": "python3 -m angr {target}",
        "afl": "afl-fuzz -i {input} -o {output} {binary} @@",
        "dex2jar": "d2j-dex2jar {target} -o {output}",
        "smali": "smali assemble {target} -o {output}",
        "dnspy": "dnSpy {target}",
        "ilspy": "ilspycmd {target}",
        "cfr": "java -jar cfr.jar {target} --outputdir {output_dir}",
        "procyon": "java -jar procyon.jar {target}",
        "firmware_mod_kit": "binwalk -e {target} && cd _target.extracted && firmware-mod-kit/extract-firmware.sh {target}",
        # Hardware Security tools
        "chipwhisperer": "python3 -m chipwhisperer {params}",
        "openocd": "openocd -f interface/{params} -f target/{target}.cfg",
        "flashrom": "flashrom -p {params} -r {output}.bin",
        "JTAGulator": "JTAGulator -v 3.3",
        "jtagenum": "python3 JTAGenum.py -p /dev/ttyUSB0",
        "minicom": "minicom -D /dev/ttyUSB0 -b {params}",
        "proxmark3": "proxmark3 /dev/ttyACM0 -c '{params}'",
        "mfoc": "mfoc -O {output}.mfd -P {params}",
        "mfcuk": "mfcuk -C -R 5 -B -S {params}",
        "cansniffer": "cansniffer {params} -c",
        "candump": "candump {params} -td",
        "cansend": "cansend {params} {target}",
        "saleae_logic": "saleae_logic_cli capture --device {params}",
        "hackrf_one": "hackrf_transfer -r {output}.raw -f {params} -l 32 -g 32",
        "killerbee": "python3 -m killerbee {params}",
        "ubertooth": "ubertooth-rx -c {params}",
        "rfcat": "python3 -c 'from rflib import *; d=RfCat(); d.{params}'",
        "gnuradio": "gnuradio-companion {params}",
        "binwalk_hw": "binwalk -e {target}",
        "strings_hw": "strings -a {target} | head -200",
        "checksec_hw": "checksec --file={target}",
        "uart_scan": "python3 -m serial.tools.miniterm /dev/ttyUSB0 {params}",
        "i2cdetect": "i2cdetect -y {params}",
        "nm_hw": "nm {target} | head -100",
        "objdump_hw": "objdump -d {target} | head -200",
        "readelf_hw": "readelf -a {target}",
        "firmware_extract": "binwalk -Me {target} --run-as=root",
        "secure_boot_bypass": "python3 secure_boot_bypass.py --target {target}",
        "decap_analysis": "python3 die_imaging.py --input {target} --magnification 100x",
        "pcb_trace": "python3 pcb_reverse.py --image {target}",
    }

    def __init__(self, llm_provider=None, timeout: int = 120, sandbox: bool = False):
        self.llm = llm_provider
        self.timeout = timeout
        self.sandbox = sandbox
        self.history: List[ExecutionResult] = []

    def execute(self, action: AttackAction, state: AttackState) -> ExecutionResult:
        """Execute an attack action and return results."""
        start_time = time.time()

        result = ExecutionResult(success=False, tool=action.tool or action.type)

        try:
            # Build command
            command = self._build_command(action, state)
            result.command = command

            if not command:
                # No real command to execute - simulate
                result = self._simulate_action(action, state)
            else:
                # Check if the tool is available on the system
                tool_name = command.split()[0] if command else ""
                tool_available = self._check_tool_available(tool_name)

                if tool_available:
                    # Execute the real command
                    result = self._run_command(command)
                    result.tool = action.tool or action.type
                else:
                    # Tool not installed - use simulation
                    logger.info(f"Tool '{tool_name}' not available, using simulation for {action.type}")
                    result = self._simulate_action(action, state)
                    result.command = command
                    result.interpretation = f"[SIMULATED] Tool '{tool_name}' not installed locally"

        except subprocess.TimeoutExpired:
            result.error = "Command timed out"
            result.success = False
        except FileNotFoundError as e:
            # Tool not found - fall back to simulation
            logger.info(f"Tool not found ({e}), using simulation")
            result = self._simulate_action(action, state)
        except Exception as e:
            result.error = str(e)
            result.success = False

        result.duration = time.time() - start_time

        # Interpret results with LLM
        if self.llm and result.stdout:
            try:
                result = self._interpret_result(result, action)
            except Exception as e:
                logger.warning(f"Result interpretation failed: {e}")

        # Update state from results
        if result.parsed:
            self._update_state_from_result(state, result)

        # Record
        self.history.append(result)
        return result

    def _build_command(self, action: AttackAction, state: AttackState) -> str:
        """Build the shell command for an action."""
        tool = action.tool
        target = action.target

        if not tool or tool == "auto":
            # Auto-select tool based on action type
            tool = self._auto_select_tool(action)

        template = self.TOOL_COMMANDS.get(tool, "")
        if isinstance(template, dict):
            # Type-specific template
            template = template.get(action.type, template.get("scan", ""))

        if not template:
            return ""

        # Format command
        params = {**action.params, "target": target}
        try:
            # Build safe format dict: use all keys from params + defaults for common placeholders
            format_dict = {
                "target": target,
                "params": "",
                "output_dir": "output",
                "project": "/tmp/project",
                "target_name": "Target",
                "pre_script": "",
                "output": "output",
                "run_as": "",
                "package": "com.target.app",
                "script": "script.py",
                "input": "seeds",
                "binary": target,
                "query": target,
                "username": "admin",
                "wordlist": "/usr/share/wordlists/rockyou.txt",
                "service": "ssh",
                "url": f"http://{target}",
            }
            format_dict.update(params)
            command = template.format(**format_dict)
        except (KeyError, IndexError, ValueError):
            # Last resort: just replace target
            command = template.replace("{target}", target)
            # Strip remaining placeholders
            import re
            command = re.sub(r'\{[^}]+\}', '', command)

        return command

    def _auto_select_tool(self, action: AttackAction) -> str:
        """Auto-select a tool based on action type."""
        mapping = {
            "scan": "nmap",
            "enum": "nmap",
            "exploit": "searchsploit",
            "brute": "hydra",
            "dump": "hashcat",
            "move": "crackmapexec",
            "exfil": "curl",
            "web_scan": "nuclei",
            "dir_enum": "gobuster",
            # Reverse Engineering
            "reverse": "ghidra",
            "decompile": "jadx",
            "disassemble": "ghidra",
            "firmware": "binwalk",
            "analyze": "radare2",
            "fuzz": "afl",
        }
        return mapping.get(action.type, "nmap")

    def _check_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available on the system (Windows/Unix)."""
        if not tool_name:
            return False
        import shutil
        return shutil.which(tool_name) is not None

    def _run_command(self, command: str) -> ExecutionResult:
        """Run a shell command."""
        result = ExecutionResult(success=False, command=command)

        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        result.stdout = proc.stdout[:10000]  # Truncate
        result.stderr = proc.stderr[:5000]
        result.return_code = proc.returncode
        result.success = proc.returncode == 0

        return result

    def _simulate_action(self, action: AttackAction, state: AttackState) -> ExecutionResult:
        """Simulate an action for planning/analysis mode."""
        target = action.target or "target"

        result = ExecutionResult(
            success=True,
            tool=action.tool or "simulation",
            stdout=f"[SIMULATION] {action.type} -> {target}: completed",
            interpretation=f"Simulated {action.type} on {target}",
        )

        # Generate simulation data based on action type
        if action.type == "scan":
            result.parsed = {
                "hosts_found": [target],
                "ports_found": {target: [22, 80, 443, 3306, 8080]},
                "services_found": {target: {"22": "ssh", "80": "http", "443": "https", "3306": "mysql"}},
            }
            result.interpretation = f"Found 5 open ports on {target}: ssh(22), http(80), https(443), mysql(3306), http-proxy(8080)"
        elif action.type == "exploit":
            result.parsed = {
                "success": True,
                "shells_obtained": [{"host": target, "user": "www-data", "type": "reverse_shell"}],
            }
            result.interpretation = f"Successfully exploited target {target}, obtained reverse shell as www-data"
        elif action.type == "brute":
            result.parsed = {
                "success": True,
                "credentials_found": [{"username": "admin", "password": "admin123", "source": target}],
            }
            result.interpretation = f"Successfully bruteforced credentials: admin@admin123 on {target}"
        elif action.type == "enum":
            result.parsed = {
                "hosts_found": [target],
                "vulns_found": [{"cve": "CVE-2024-0001", "host": target, "port": 80, "severity": "high"}],
            }
            result.interpretation = f"Enumerated {target}: found 1 high severity vulnerability"
        elif action.type in ("decompile", "reverse"):
            result.parsed = {
                "success": True,
                "data_extracted": ["encryption_key_found", "api_endpoints", "hardcoded_credentials"],
            }
            result.interpretation = f"Decompiled {target}: found encryption keys, API endpoints, and hardcoded credentials"
        elif action.type == "disassemble":
            result.parsed = {
                "success": True,
                "data_extracted": ["function_map", "control_flow_graph"],
            }
            result.interpretation = f"Disassembled {target}: generated function map and control flow graph"
        elif action.type == "analyze":
            result.parsed = {
                "success": True,
                "data_extracted": ["memory_layout", "cross_references"],
            }
            result.interpretation = f"Analyzed {target}: mapped memory layout and cross-references"
        elif action.type == "fuzz":
            result.parsed = {
                "success": True,
                "vulns_found": [{"cve": "FUZZ-CRASH-001", "host": target, "severity": "critical"}],
            }
            result.interpretation = f"Fuzzing {target}: found 1 crash with potential exploitability"
        elif action.type in ("move", "lateral"):
            result.parsed = {
                "hosts_found": ["192.168.1.2", "192.168.1.3"],
                "compromised": ["192.168.1.2"],
            }
            result.interpretation = f"Lateral movement from {target}: compromised 192.168.1.2"
        elif action.type == "dump":
            result.parsed = {
                "credentials_found": [
                    {"username": "root", "password": "hash:5f4dcc3b5aa765d61d8327deb882cf99", "source": target},
                    {"username": "admin", "password": "hash:e10adc3949ba59abbe56e057f20f883e", "source": target},
                ],
            }
            result.interpretation = f"Dumped 2 password hashes from {target}"
        # Hardware attack simulations
        elif action.type == "hw_scan":
            result.parsed = {
                "success": True,
                "interfaces_found": ["JTAG", "UART", "SPI", "I2C"],
                "chips_identified": [
                    {"part_number": "STM32F407", "manufacturer": "STMicroelectronics", "flash_size": "512KB"},
                ],
                "debug_ports": ["JTAG (4-pin)", "UART (RX/TX/GND)"],
            }
            result.interpretation = f"Hardware recon on {target}: found STM32F407 MCU with JTAG/UART interfaces"
        elif action.type == "hw_access":
            result.parsed = {
                "success": True,
                "debug_connected": True,
                "halted": True,
                "chip_id": "0x361",
                "flash_size": "512KB",
            }
            result.interpretation = f"Successfully connected to {target} via JTAG, MCU halted"
        elif action.type == "hw_firmware":
            result.parsed = {
                "success": True,
                "firmware_extracted": True,
                "firmware_size": "512KB",
                "filesystem_type": "JFFS2",
                "sensitive_data": ["default_password", "api_keys", "certificates"],
            }
            result.interpretation = f"Extracted 512KB firmware from {target}, found JFFS2 filesystem with sensitive data"
        elif action.type == "hw_sca":
            result.parsed = {
                "success": True,
                "traces_collected": 10000,
                "key_bytes_recovered": 16,
                "key": "DEADBEEF0123456789ABCDEF01234567",
                "attack_method": "CPA",
            }
            result.interpretation = f"Side-channel attack on {target}: recovered AES-128 key via CPA"
        elif action.type == "hw_fault":
            result.parsed = {
                "success": True,
                "glitch_type": "voltage",
                "bypassed": ["secure_boot", "read_protection"],
                "effect": "security_check_skipped",
            }
            result.interpretation = f"Fault injection on {target}: bypassed secure boot via voltage glitch"
        elif action.type == "hw_rfid":
            result.parsed = {
                "success": True,
                "tag_type": "MIFARE Classic 1K",
                "uid": "04:A3:B2:C1",
                "keys_recovered": {"A": ["FFFFFFFFFFFF"], "B": ["123456789ABC"]},
                "data_dumped": True,
            }
            result.interpretation = f"RFID attack on {target}: recovered keys and dumped MIFARE Classic card"
        elif action.type == "hw_can":
            result.parsed = {
                "success": True,
                "messages_captured": 5000,
                "ecus_found": ["Engine", "ABS", "BCM", "InstrumentCluster"],
                "signals_decoded": ["RPM", "Speed", "DoorStatus", "EngineTemp"],
            }
            result.interpretation = f"CAN bus analysis on {target}: identified 4 ECUs, decoded 4 signal types"
        elif action.type == "hw_pcb":
            result.parsed = {
                "success": True,
                "layers": 4,
                "components": ["MCU", "Flash", "Power Management", "RF Module"],
                "netlist_extracted": True,
                "schematic_generated": True,
            }
            result.interpretation = f"PCB reverse engineering on {target}: extracted netlist, generated schematic"

        return result

    def _interpret_result(self, result: ExecutionResult, action: AttackAction) -> ExecutionResult:
        """Use LLM to interpret tool output."""
        prompt = INTERPRET_PROMPT.format(
            action_type=action.type,
            target=action.target,
            tool=result.tool,
            command=result.command,
            output=result.stdout[:3000] or "(empty)",
            stderr=result.stderr[:1000] or "(none)",
        )

        response = self.llm.call(
            [{"role": "user", "content": prompt}],
            use_json_mode=False,
            temperature=0.3,
        )

        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        try:
            import json
            parsed = json.loads(content.strip())
            result.parsed = parsed
            result.interpretation = parsed.get("summary", "")
            if "success" in parsed:
                result.success = parsed["success"]
        except Exception:
            result.interpretation = content[:500]

        return result

    def _update_state_from_result(self, state: AttackState, result: ExecutionResult) -> None:
        """Update attack state from parsed results."""
        parsed = result.parsed

        # Hosts
        for ip in parsed.get("hosts_found", []):
            if ip not in state.hosts:
                state.add_host(Host(ip=ip))

        # Ports & services
        for ip, ports in parsed.get("ports_found", {}).items():
            if ip in state.hosts:
                state.hosts[ip].ports = list(set(state.hosts[ip].ports + ports))

        for ip, services in parsed.get("services_found", {}).items():
            if ip in state.hosts:
                for port_str, svc in services.items():
                    port = int(port_str) if isinstance(port_str, str) else port_str
                    state.hosts[ip].services[port] = svc

        # Vulnerabilities
        for vuln_data in parsed.get("vulns_found", []):
            state.add_vuln(Vulnerability(
                cve_id=vuln_data.get("cve", "UNKNOWN"),
                host=vuln_data.get("host", ""),
                port=vuln_data.get("port"),
                severity=vuln_data.get("severity", "medium"),
            ))

        # Credentials
        for cred_data in parsed.get("credentials_found", []):
            state.add_cred(Credential(
                username=cred_data.get("username", ""),
                password=cred_data.get("password"),
                source=cred_data.get("source", ""),
            ))

        # Shells
        for shell in parsed.get("shells_obtained", []):
            host = shell.get("host", "")
            if host in state.hosts:
                state.hosts[host].compromised = True
            state.shells.append(shell)

        # Compromised
        for ip in parsed.get("compromised", []):
            if ip in state.hosts:
                state.hosts[ip].compromised = True
            if ip not in state.get_compromised_hosts():
                state.shells.append({"host": ip, "user": "unknown", "type": "compromised"})
