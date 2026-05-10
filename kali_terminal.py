"""
Kali-Style Interactive Terminal with Full LLM Control

Features:
- Direct LLM instruction capability
- Real-time streaming display
- Action execution with feedback
- Team collaboration display
- Command history and completion
"""

import os
import sys
import json
import time
import socket
import signal
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable

# Windows compatibility for readline
try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False

# Color codes (256-color support)
class C:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # Agent colors
    CMD = '\033[38;5;196m'
    SCOUT = '\033[38;5;82m'
    ANALYST = '\033[38;5;45m'
    STRIKER = '\033[38;5;208m'
    GHOST = '\033[38;5;141m'
    HUNTER = '\033[38;5;226m'
    PHANTOM = '\033[38;5;75m'

    @staticmethod
    def agent(name: str) -> str:
        colors = {
            'Commander': C.CMD, 'Scout': C.SCOUT,
            'Analyst': C.ANALYST, 'Striker': C.STRIKER,
            'Ghost': C.GHOST, 'Hunter': C.HUNTER, 'Phantom': C.PHANTOM,
        }
        return colors.get(name, C.CYAN)


BANNER = f"""
{C.BOLD}{C.GREEN}
     _     _     _                     _   _      _     _             ____
    / \\   (_) __| | __  _ __ ___   ___| |_| |_   / \\   | |_ ___  __ _| ___|
   / _ \\  | |/ _` |/ _\\| '_ ` _ \\ / _ \\ __| __| / _ \\  | __/ _ \\/ _` |___ \\
  / ___ \\ | | (_| | (_| | | | | | |  __/ |_| |_| / ___ \\ | ||  __/ (_| |___) |
 /_/   \\_\\|_|\\__,_|\\___|_| |_| |_|\\___|\\__|\\__/_/   \\_\\ \\__\\___|\\__, |____/
{C.ENDC}
{C.CYAN}     ┌─────────────────────────────────────────────────────┐
     │  Manatrix v2.0 - LLM Enhanced       │
     │  Direct LLM Control & Real-time Execution              │
     └─────────────────────────────────────────────────────┘
{C.ENDC}
"""


MODULES = {
    'llm': {
        'description': 'Direct LLM control - issue commands to AI',
        'commands': {
            'exec': '<instruction>  Execute LLM instruction',
            'plan': '<target>       Ask LLM to plan attack',
            'analyze': '<target>    Analyze target vulnerabilities',
            'think': '<question>    Ask LLM to think about something',
            'role': '<role>         Set LLM role (pentester, analyst, etc)',
            'sys': '<prompt>       Set custom system prompt',
            'context': '<text>      Add context for LLM',
            'config': '             Show LLM configuration',
            'history': '            Show conversation history',
            'clear': '              Clear conversation',
            'ask': '<question>     Quick ask LLM',
            'explain': '<topic>     Explain a security topic',
            'suggest': '<situation> Get suggestions',
            'generate': '<prompt>    Generate content with LLM',
            'compare': '<a> <b>     Compare two things',
            'critique': '<plan>     Critique a plan',
            'debug': '<error>       Debug an error',
            'audit': '<target>      Security audit',
            'recon': '<target>      Recon suggestions',
            'vuln': '<target>       Vulnerability analysis',
        }
    },
    'pentest': {
        'description': 'Penetration testing with LLM guidance',
        'commands': {
            'scan': '<target>       Scan with live LLM analysis',
            'attack': '<target>     Autonomous attack with LLM',
            'team': '<target>       Team-based attack',
            'status': '             Show current attack status',
            'report': '             Generate report',
            'recon': '<target>      Reconnaissance phase',
            'enum': '<target>       Enumeration phase',
            'exploit': '<vuln>      Exploitation phase',
            'post': '<target>       Post-exploitation',
            'persist': '            Establish persistence',
            'pivot': '<target>      Pivot to other targets',
            'escalate': '            Privilege escalation',
            'exfil': '<target>      Data exfiltration',
            'creds': '              Credential attacks',
            'brute': '<service>     Brute force attack',
            'wordlist': '<target>   Generate wordlist',
            'exploitdb': '<query>   Search exploit-db',
            'metasploit': '<mod>    Metasploit module',
            'payload': '<type>      Generate payload',
            'listen': '             Start listener',
            'shell': '<type>        Get shell',
            'upload': '<file>       Upload file',
            'download': '<path>      Download file',
        }
    },
    'recon': {
        'description': 'Reconnaissance tools',
        'commands': {
            'nmap': '<target>       Nmap port scan',
            'masscan': '<target>    Fast port scan',
            'dns': '<domain>       DNS enumeration',
            'whois': '<domain>     WHOIS lookup',
            'subdomain': '<domain>  Subdomain discovery',
            'port': '<target>      Port scan',
            'service': '<target>    Service detection',
            'os': '<target>        OS detection',
            'vulnscan': '<target>   Vulnerability scan',
            'web': '<target>       Web enumeration',
            'dirb': '<url>          Directory busting',
            'nikto': '<target>      Web vulnerability scan',
            'sslscan': '<target>    SSL/TLS scan',
            'sshscan': '<target>    SSH enumeration',
            'ftpscan': '<target>    FTP enumeration',
            'smbscan': '<target>    SMB enumeration',
            'mysqlscan': '<target>  MySQL enumeration',
            'enum4linux': '<target> Enum4linux scan',
            'theHarvester': '<domain> OSINT gathering',
            'shodan': '<query>     Shodan search',
            'censys': '<query>     Censys search',
            'hunter': '<domain>     Email hunter',
            'assetfinder': '<domain> Asset discovery',
            'subfinder': '<domain>  Subdomain finder',
            'amass': '<domain>      Subdomain enumeration',
            'dig': '<domain>       DNS lookup',
            'host': '<domain>      Host lookup',
            'traceroute': '<target> Traceroute',
            'fping': '<subnet>     Fast ping sweep',
            'arping': '<target>    ARP ping',
            'nping': '<target>     Network ping',
        }
    },
    'exploit': {
        'description': 'Exploitation tools',
        'commands': {
            'search': '<query>       Search exploit DB',
            'use': '<exploit>       Use exploit module',
            'list': '               List available exploits',
            'info': '<exploit>      Exploit information',
            'check': '<target>      Check exploitability',
            'run': '<exploit>       Run exploit',
            'eternalblue': '<target> EternalBlue exploit',
            'bluekeep': '<target>    BlueKeep exploit',
            'log4shell': '<target>   Log4Shell exploit',
            'shellshock': '<target>   Shellshock exploit',
            'heartbleed': '<target>   Heartbleed exploit',
            'smbghost': '<target>     SMBGhost exploit',
            'smbvuln': '<target>      SMB vulnerability',
            'struts': '<target>       Apache Struts RCE',
            'spring4shell': '<target> Spring4Shell RCE',
            'jenkins': '<target>     Jenkins exploit',
            'redis': '<target>       Redis RCE',
            'mongodb': '<target>     MongoDB exploit',
            'postgres': '<target>    PostgreSQL exploit',
            'mysql': '<target>       MySQL exploit',
            'tomcat': '<target>      Tomcat exploit',
            'weblogic': '<target>     WebLogic exploit',
            'jboss': '<target>       JBoss exploit',
            'cve': '<cve_id>         Search CVE',
            'msf': '<module>        Search metasploit',
            'searchsploit': '<query> SearchSploit',
        }
    },
    'post': {
        'description': 'Post-exploitation tools',
        'commands': {
            'shell': '               Get interactive shell',
            'python': '              Python shell',
            'bash': '                Bash reverse shell',
            'powershell': '          PowerShell shell',
            'meterpreter': '         Meterpreter session',
            'persist': '             Setup persistence',
            'registry': '             Registry persistence',
            'crontab': '              Cronjob persistence',
            'sshkey': '              SSH key persistence',
            'escalate': '            Privilege escalation',
            'privesc': '             Privilege escalation check',
            'winpeas': '             Windows PE check',
            'linpeas': '             Linux PE check',
            'mimikatz': '            Dump credentials',
            'hashdump': '           Dump password hashes',
            'samdump': '            SAM database dump',
            'lsass': '               LSASS dump',
            'kerberoast': '         Kerberoasting',
            'bloodhound': '         BloodHound AD analysis',
            'keylog': '              Keylogger',
            'screenshot': '          Take screenshot',
            'pillage': '            Pillage files',
            'exfil': '              Data exfiltration',
            'portfwd': '<lport>      Port forwarding',
            'tunnel': '<target>      Tunneling',
            'socks': '               SOCKS proxy',
            'chisel': '<target>      Chisel proxy',
            'ligolo': '<target>      Ligolo proxy',
        }
    },
    'creds': {
        'description': 'Credential attacks',
        'commands': {
            'hydra': '<target> <svc>  Hydra brute force',
            'medusa': '<target>      Medusa brute force',
            'ncrack': '<target>      Ncrack brute force',
            'hashcat': '<hash>       Hashcat cracking',
            'john': '<hash>          John the Ripper',
            'wordlist': '             Generate wordlist',
            'cewl': '<url>           Custom wordlist',
            'crunch': '<pattern>     Crunch wordlist',
            'hashid': '<hash>        Identify hash type',
            'passgen': '<pattern>    Generate passwords',
            'spray': '<passwords>    Password spraying',
            'credential': '<target>  Check credentials',
            'ldap': '<target>        LDAP attack',
            'smb': '<target>         SMB attack',
            'ssh': '<target>         SSH attack',
            'ftp': '<target>         FTP attack',
            'http': '<target>        HTTP attack',
            'mysql': '<target>       MySQL attack',
            'rdp': '<target>         RDP attack',
            'vnc': '<target>         VNC attack',
            'telnet': '<target>      Telnet attack',
            'snmp': '<target>       SNMP attack',
        }
    },
    'web': {
        'description': 'Web application testing',
        'commands': {
            'sqlmap': '<url>         SQL injection',
            'nikto': '<target>      Nikto scan',
            'dirb': '<url>          Directory busting',
            'gobuster': '<url>      Gobuster scan',
            'ffuf': '<url>          FFUF fuzzing',
            'wfuzz': '<url>         WFUZZ fuzzing',
            'crawl': '<url>         Web crawler',
            'enum': '<url>          Web enumeration',
            'xss': '<url>           XSS testing',
            'sqli': '<url>          SQL injection',
            'lfi': '<url>           LFI testing',
            'rfi': '<url>           RFI testing',
            'xxe': '<url>           XXE testing',
            'ssrf': '<url>          SSRF testing',
            'csrf': '<url>          CSRF testing',
            'idor': '<url>          IDOR testing',
            'ssti': '<url>          SSTI testing',
            'command': '<url>        Command injection',
            'upload': '<url>        File upload test',
            'authbypass': '<url>    Auth bypass',
            'crlf': '<url>          CRLF injection',
            'openredirect': '<url>   Open redirect',
            'waf': '<target>       WAF detection',
            'cms': '<target>       CMS identification',
            'wpscan': '<target>    WordPress scan',
            'joomscan': '<target>   Joomla scan',
        }
    },
    'network': {
        'description': 'Network manipulation',
        'commands': {
            'arp': '                Show ARP table',
            'netstat': '            Show network stats',
            'ifconfig': '           Interface config',
            'route': '              Routing table',
            'tcpdump': '<filter>    Packet capture',
            'wireshark': '          Wireshark capture',
            'ettercap': '           Ettercap MITM',
            'bettercap': '          BetterCAP MITM',
            'arpspoof': '<target>   ARP spoofing',
            'responder': '          Responder LLMNR',
            'mitm6': '              IPv6 MITM',
            'smbexec': '<target>    SMBexec',
            'psexec': '<target>     PsExec',
            'wmiexec': '<target>    WMIExec',
            'smbclient': '<target>  SMB client',
            'rpcclient': '<target>   RPC client',
            'nbtscan': '<target>    NetBIOS scan',
            'snmpwalk': '<target>   SNMP walk',
        }
    },
    'wireless': {
        'description': 'Wireless attacks',
        'commands': {
            'airodump': '<interface>  Capture wireless',
            'aireplay': '<target>    Deauth attack',
            'aircrack': '<file>      Crack handshake',
            'reaver': '<bssid>       WPS attack',
            'wash': '               Scan WPS',
            'hostapd': '<config>    Rogue AP',
            'bluetooth': '          Bluetooth attack',
            'btscanner': '          Bluetooth scan',
        }
    },
    'forensics': {
        'description': 'Digital forensics',
        'commands': {
            'volatility': '<image>   Memory analysis',
            'autopsy': '<image>     Disk forensics',
            'foremost': '<image>    File carving',
            'binwalk': '<file>      Binary analysis',
            'strings': '<file>      String extraction',
            'exiftool': '<file>     EXIF data',
            'metadata': '<file>     Metadata view',
            'hashdump': '<image>    Hash extraction',
            'regripper': '<hive>    Registry analysis',
            'evtx': '<file>         Event log parse',
            'timeline': '<image>    Timeline analysis',
            'dd': '<image>         Image creation',
        }
    },
    'utils': {
        'description': 'Utility tools',
        'commands': {
            'hash': '<text>         Calculate hashes',
            'encode': '<text>       Encode/decode',
            'decode': '<text>       Decode text',
            'base64': '<text>       Base64 encode',
            'hex': '<text>          Hex encode',
            'url': '<text>          URL encode',
            'unicode': '<text>      Unicode encode',
            'html': '<text>         HTML encode',
            'check': '<pwd>         Password strength check',
            'uuid': '               Generate UUID',
            'random': '<len>        Random string',
            'ipinfo': '<ip>         IP info lookup',
            'geoip': '<ip>          GeoIP lookup',
            'dnslookup': '<domain>  DNS lookup',
            'reverseDns': '<ip>     Reverse DNS',
            'whois': '<domain>      WHOIS lookup',
            'subnet': '<cidr>       Subnet calc',
            'ping': '<target>      Ping host',
            'curl': '<url>          HTTP request',
            'wget': '<url>          Download file',
            'banner': '<target>     Grab banner',
        }
    },
    'password': {
        'description': 'Password generation/analysis',
        'commands': {
            'generate': '<n> <len>     Generate N passwords',
            'train': '<data>        Train model',
            'check': '<pwd>         Check password strength',
            'analyze': '<pwd>       Analyze password',
            'pattern': '<pwd>       Find pattern',
            'mask': '<pwd>          Password mask',
            'rule': '<pwd>          Apply rules',
            'mutate': '<pwd>        Mutate password',
            'hybrid': '<base>       Hybrid generation',
            'markov': '<corpus>      Markov model',
            'pcfg': '<corpus>       PCFG generation',
            'mamba': '<target>      MAMBA generation',
            'leet': '<pwd>         Leet speak',
            'keyboard': '<pattern>  Keyboard pattern',
            'date': '<year>         Date-based passwords',
            'name': '<name>         Name-based passwords',
            'common': '<n>          Common passwords',
        }
    },
    'knowledge': {
        'description': 'RAG knowledge base',
        'commands': {
            'search': '<query>       Search knowledge',
            'cve': '<id>            CVE lookup',
            'technique': '<id>      ATT&CK technique',
            'tactic': '<name>        ATT&CK tactic',
            'exploit': '<name>      Exploit info',
            'tool': '<name>         Tool usage',
            'stats': '              Show KB stats',
            'index': '              Show indexed docs',
            'clear': '              Clear cache',
            'import': '<file>       Import knowledge',
            'export': '<file>       Export knowledge',
        }
    },
    'osint': {
        'description': 'OSINT reconnaissance',
        'commands': {
            'recon-ng': '            Launch recon-ng',
            'theHarvester': '<domain> Email gathering',
            'shodan': '<query>      Shodan search',
            'censys': '<query>      Censys search',
            'hunter': '<domain>     Email hunter',
            'securityTrails': '<domain> DNS history',
            'dnsdumpster': '<domain> DNS enumeration',
            'sublist3r': '<domain>  Subdomain discovery',
            'assetfinder': '<domain> Asset finder',
            'amass': '<domain>      Subdomain enum',
            'wayback': '<domain>     Wayback machine',
            'crt': '<domain>       Certificate search',
            'otx': '<domain>       AlienVault OTX',
            'virustotal': '<query>  VirusTotal search',
            'abuseipdb': '<ip>      IP reputation',
            'Sherlock': '<username>  Username search',
        }
    },
}

GLOBAL_COMMANDS = {
    'help': 'Show help',
    'clear': 'Clear screen',
    'banner': 'Show banner',
    'info': 'System info',
    'status': 'Framework status',
    'set': '<key> <val>  Set config',
    'get': '<key>       Get config',
    'history': 'Command history',
    'exit': 'Exit terminal',
    'use': '<module>    Switch module',
    'show': 'modules    Show modules',
    'back': 'Return to main',
    'logs': 'n          Recent logs',
}


class LLMController:
    """
    Main LLM controller with streaming support.
    Allows direct instruction of the LLM with real-time display.
    """

    def __init__(self, config_path: str = 'config.yaml'):
        self.config_path = config_path
        self.provider = None
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = self._get_default_system_prompt()
        self.context: List[str] = []
        self.call_count = 0

    def _get_default_system_prompt(self) -> str:
        return """你是一个专业的网络安全渗透测试助手。你能够：
1. 分析目标环境，识别攻击向量
2. 制定攻击计划和策略
3. 协调多个专家角色进行协作
4. 执行网络安全工具和命令
5. 提供详细的技术分析和报告

在执行任何操作前，请先说明你的计划。
如果遇到问题，请解释原因并提出替代方案。
始终遵循授权渗透测试的原则。"""

    def initialize(self, api_key: str = None) -> bool:
        """Initialize LLM provider from config."""
        try:
            from models.llm_provider import get_provider, LLMConfig
            import yaml

            # Load from config file
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                llm_cfg = cfg.get('llm', {})
            else:
                llm_cfg = {}

            # Use provided key or from config
            key = api_key or llm_cfg.get('api_key', '')

            if not key or key == 'YOUR_DEEPSEEK_API_KEY':
                return False

            config = LLMConfig(
                provider=llm_cfg.get('provider', 'deepseek'),
                model=llm_cfg.get('model', 'deepseek-chat'),
                api_key=key,
                api_base=llm_cfg.get('api_base', 'https://api.deepseek.com/v1'),
                temperature=llm_cfg.get('temperature', 0.7),
                max_tokens=llm_cfg.get('max_tokens', 4000),
            )

            self.provider = get_provider(config)
            return True

        except Exception as e:
            print(f"{C.RED}LLM init error: {e}{C.ENDC}")
            return False

    def set_system_prompt(self, prompt: str):
        """Set custom system prompt."""
        self.system_prompt = prompt
        print(f"{C.GREEN}[+] System prompt updated{C.ENDC}")

    def add_context(self, text: str):
        """Add context information for LLM."""
        self.context.append(text)
        print(f"{C.GREEN}[+] Added context ({len(self.context)} total){C.ENDC}")

    def clear_context(self):
        """Clear all context."""
        self.context = []
        print(f"{C.GREEN}[+] Context cleared{C.ENDC}")

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """Build message list for API call."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add context
        if self.context:
            context_text = "\n\n[附加上下文信息]\n" + "\n".join(self.context)
            messages.append({"role": "system", "content": context_text})

        # Add conversation history (last 10 turns)
        history = self.conversation_history[-20:]
        messages.extend(history)

        # Add current message
        messages.append({"role": "user", "content": user_message})

        return messages

    def call(self, message: str, show_thinking: bool = True, use_json: bool = False) -> str:
        """
        Call LLM with a message and display thinking process.

        Args:
            message: User message to send
            show_thinking: Show LLM thinking state
            use_json: Request JSON response

        Returns:
            LLM response content
        """
        if not self.provider:
            if not self.initialize():
                return f"{C.RED}LLM not configured. Set API key with 'set api_key <key>'{C.ENDC}"

        messages = self._build_messages(message)

        # Show request
        print(f"\n{C.CYAN}┌─ Sending to LLM ({len(messages)} messages) ─────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {message[:100]}{'...' if len(message) > 100 else ''}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

        # Show thinking indicator
        if show_thinking:
            print(f"{C.YELLOW}    [Thinking...]{C.ENDC}", end='', flush=True)

        self.call_count += 1

        try:
            response = self.provider.call(messages, use_json_mode=use_json)

            if show_thinking:
                print(f"\r{C.GREEN}    [Done]{C.ENDC}  ")

            if response:
                content = response.content if hasattr(response, 'content') else str(response)

                # Add to history
                self.conversation_history.append({"role": "user", "content": message})
                self.conversation_history.append({"role": "assistant", "content": content})

                # Limit history
                if len(self.conversation_history) > 50:
                    self.conversation_history = self.conversation_history[-50:]

                return content
            else:
                return f"{C.RED}Empty response from LLM{C.ENDC}"

        except Exception as e:
            if show_thinking:
                print(f"\r{C.RED}    [Error]{C.ENDC}  ")
            return f"{C.RED}Error: {e}{C.ENDC}"

    def exec_instruction(self, instruction: str, callback: Callable = None) -> str:
        """
        Execute a direct instruction to LLM.
        This is the main method for users to control the LLM.

        The LLM will:
        1. Parse the instruction
        2. Plan the execution
        3. Execute steps
        4. Report results
        """
        prompt = f"""你是一个命令行渗透测试助手。用户请求：{instruction}

请分析这个请求并执行相应的操作。
- 如果需要扫描，描述扫描策略
- 如果需要攻击，说明攻击步骤
- 如果需要分析，提供详细分析
- 如果需要工具执行，列出所需命令

请用中文回答，保持简洁明了。"""

        response = self.call(prompt)
        return response

    def plan_attack(self, target: str) -> Dict[str, Any]:
        """Generate attack plan for target."""
        prompt = f"""为以下目标制定渗透测试攻击计划：

目标: {target}

请分析并输出JSON格式的攻击计划：
{{
    "recon": ["侦察步骤"],
    "scanning": ["扫描步骤"],
    "vulnerability_analysis": ["漏洞分析步骤"],
    "exploitation": ["利用步骤"],
    "post_exploitation": ["后渗透步骤"],
    "risk_assessment": "风险评估",
    "estimated_time": "预计时间",
    "required_tools": ["所需工具"],
    "success_criteria": "成功标准"
}}"""

        response = self.call(prompt, use_json=True)

        try:
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_response": response}
        except Exception as e:

    def analyze_target(self, target: str) -> str:
        """Analyze target for vulnerabilities."""
        prompt = f"""详细分析目标 {target} 的潜在攻击面：

请考虑：
1. 可能的开放端口和服务
2. 已知漏洞（CVE）
3. 错误配置风险
4. 社会工程学攻击向量
5. 攻击路径建议
6. 防御建议

以结构化方式输出。"""

        return self.call(prompt)

    def get_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return {
            'model': getattr(self.provider.config, 'model', 'Not configured') if self.provider else 'Not configured',
            'provider': getattr(self.provider.config, 'provider', 'N/A') if self.provider else 'N/A',
            'api_base': getattr(self.provider.config, 'api_base', 'N/A') if self.provider else 'N/A',
            'temperature': getattr(self.provider.config, 'temperature', 0.7) if self.provider else 0.7,
            'max_tokens': getattr(self.provider.config, 'max_tokens', 2000) if self.provider else 2000,
            'context_count': len(self.context),
            'history_count': len(self.conversation_history),
            'call_count': self.call_count,
        }


class KaliTerminal:
    """
    Kali-style terminal with full LLM control capability.
    """

    def __init__(self):
        self.current_module = None
        self.modules = MODULES
        self.global_cmds = GLOBAL_COMMANDS
        self.config: Dict[str, str] = {}
        self.history: List[str] = []
        self.session_start = datetime.now()
        self.running = True
        self.attack_state: Dict[str, Any] = {}

        # Initialize LLM controller
        self.llm = LLMController()
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM from config or saved API key."""
        api_key = self.config.get('api_key')
        if api_key:
            self.llm.initialize(api_key)

    def print_banner(self):
        print(BANNER)

    def print_prompt(self) -> str:
        cwd = os.getcwd().replace(os.path.expanduser('~'), '~')
        if self.current_module:
            return f"\n{C.GREEN}┌──({C.CYAN}root@pg{C.GREEN})-[{C.YELLOW}{self.current_module}{C.GREEN}]\n└──({C.CYAN}root@pg{C.GREEN})-[{C.CYAN}{cwd}{C.GREEN}]$ {C.ENDC}"
        return f"\n{C.GREEN}┌──({C.CYAN}root@pg{C.GREEN})-[{C.CYAN}{cwd}{C.GREEN}]\n└──({C.CYAN}root@pg{C.GREEN})$ {C.ENDC}"

    # ==========================================
    # GLOBAL COMMANDS
    # ==========================================

    def cmd_help(self):
        print(f"\n{C.BOLD}Global Commands:{C.ENDC}")
        for cmd, desc in self.global_cmds.items():
            print(f"  {C.CYAN}{cmd:<10}{C.ENDC} {desc}")

        if self.current_module:
            print(f"\n{C.BOLD}Module [{self.current_module}] Commands:{C.ENDC}")
            for cmd, desc in self.modules[self.current_module]['commands'].items():
                print(f"  {C.YELLOW}{cmd:<12}{C.ENDC} {desc}")
        print()

    def cmd_status(self):
        print(f"\n{C.BOLD}Framework Status:{C.ENDC}")
        config = self.llm.get_config()
        print(f"  {C.CYAN}LLM Model:{C.ENDC}    {config.get('model', 'N/A')}")
        print(f"  {C.CYAN}Provider:{C.ENDC}      {config.get('provider', 'N/A')}")
        print(f"  {C.CYAN}API Calls:{C.ENDC}      {config.get('call_count', 0)}")
        print(f"  {C.CYAN}Context:{C.ENDC}        {config.get('context_count', 0)} items")
        print(f"  {C.CYAN}History:{C.ENDC}       {config.get('history_count', 0)} messages")
        print()

    def cmd_show(self, args: List[str]):
        if len(args) < 2 or args[1] == 'modules':
            print(f"\n{C.BOLD}Available Modules:{C.ENDC}\n")
            for name, info in self.modules.items():
                mark = C.GREEN if self.current_module == name else C.YELLOW
                print(f"  {mark}{name:<12}{C.ENDC} {info['description']}")
            print()
        else:
            module_name = args[1]
            if module_name in self.modules:
                info = self.modules[module_name]
                print(f"\n{C.BOLD}Module: {module_name}{C.ENDC}")
                print(f"{C.CYAN}{info['description']}{C.ENDC}\n")
                for cmd, desc in info['commands'].items():
                    print(f"  {C.YELLOW}{cmd:<12}{C.ENDC} {desc}")
                print()
            else:
                print(f"{C.RED}Module '{module_name}' not found{C.ENDC}")

    def cmd_use(self, args: List[str]):
        if len(args) < 2:
            self.cmd_show(args)
            return

        module_name = args[1]
        if module_name in self.modules:
            self.current_module = module_name
            print(f"{C.GREEN}[+] Using module: {module_name}{C.ENDC}")
            print(f"{C.CYAN}{self.modules[module_name]['description']}{C.ENDC}\n")
        else:
            print(f"{C.RED}Module '{module_name}' not found{C.ENDC}")

    def cmd_set(self, args: List[str]):
        if len(args) < 2:
            print(f"\n{C.BOLD}Configuration:{C.ENDC}\n")
            for k, v in self.config.items():
                print(f"  {C.CYAN}{k:<15}{C.ENDC} = {v}")
            if not self.config:
                print(f"  {C.YELLOW}No variables set{C.ENDC}")
            print()
        elif len(args) < 3:
            print(f"{C.RED}Usage: set <key> <value>{C.ENDC}")
        else:
            key = args[1]
            value = ' '.join(args[2:])
            self.config[key] = value

            # Special handling for api_key
            if key == 'api_key':
                if self.llm.initialize(value):
                    print(f"{C.GREEN}[+] LLM initialized successfully{C.ENDC}")
                else:
                    print(f"{C.YELLOW}[!] LLM init failed. Check API key.{C.ENDC}")
            else:
                print(f"{C.GREEN}[+] {key} = {value}{C.ENDC}")

    def cmd_get(self, args: List[str]):
        if len(args) < 2:
            self.cmd_set(args)
        elif args[1] in self.config:
            print(f"{C.CYAN}{args[1]}{C.ENDC} = {self.config[args[1]]}")
        else:
            print(f"{C.RED}Variable '{args[1]}' not set{C.ENDC}")

    def cmd_history(self):
        print(f"\n{C.BOLD}Command History:{C.ENDC}\n")
        for i, cmd in enumerate(self.history[-20:], 1):
            print(f"  {C.CYAN}{i:3d}{C.ENDC}  {cmd}")
        print()

    # ==========================================
    # LLM MODULE COMMANDS
    # ==========================================

    def cmd_llm_exec(self, args: List[str]):
        """Execute LLM instruction - the main command interface."""
        if len(args) < 2:
            print(f"{C.RED}Usage: exec <instruction>{C.ENDC}")
            print(f"{C.CYAN}Example: exec 扫描 192.168.1.0/24 的开放端口{C.ENDC}")
            return

        instruction = ' '.join(args[1:])
        print(f"\n{C.BOLD}{'='*60}{C.ENDC}")
        print(f"{C.BOLD}LLM EXECUTION: {instruction[:50]}{'...' if len(instruction) > 50 else ''}{C.ENDC}")
        print(f"{C.BOLD}{'='*60}{C.ENDC}\n")

        response = self.llm.exec_instruction(instruction)

        # Display response with formatting
        print(f"\n{C.GREEN}┌─ LLM Response ───────────────────────────────────────{C.ENDC}")
        lines = response.split('\n')
        for line in lines:
            print(f"{C.GREEN}│{C.ENDC} {line[:78]}")
        print(f"{C.GREEN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_llm_plan(self, args: List[str]):
        """Generate attack plan."""
        if len(args) < 2:
            target = self.config.get('target', '')
            if not target:
                print(f"{C.RED}Usage: plan <target> or 'set target <ip>' first{C.ENDC}")
                return
        else:
            target = args[1]

        print(f"\n{C.BOLD}[*] Generating attack plan for {target}...{C.ENDC}\n")

        plan = self.llm.plan_attack(target)

        print(f"\n{C.CYAN}┌─ Attack Plan ─────────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.BOLD}Target:{C.ENDC} {target}")

        if 'recon' in plan:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}侦察:{C.ENDC}")
            for step in plan.get('recon', []):
                print(f"{C.CYAN}│{C.ENDC}   - {step}")

        if 'scanning' in plan:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}扫描:{C.ENDC}")
            for step in plan.get('scanning', []):
                print(f"{C.CYAN}│{C.ENDC}   - {step}")

        if 'exploitation' in plan:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}利用:{C.ENDC}")
            for step in plan.get('exploitation', []):
                print(f"{C.CYAN}│{C.ENDC}   - {step}")

        if 'risk_assessment' in plan:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}风险:{C.ENDC} {plan.get('risk_assessment')}")

        if 'required_tools' in plan:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}工具:{C.ENDC} {', '.join(plan.get('required_tools', []))}")

        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_llm_analyze(self, args: List[str]):
        """Analyze target vulnerabilities."""
        if len(args) < 2:
            target = self.config.get('target', '')
            if not target:
                print(f"{C.RED}Usage: analyze <target> or 'set target' first{C.ENDC}")
                return
        else:
            target = args[1]

        print(f"\n{C.BOLD}[*] Analyzing {target}...{C.ENDC}\n")

        response = self.llm.analyze_target(target)

        print(f"\n{C.YELLOW}┌─ Analysis Result ─────────────────────────────────────{C.ENDC}")
        lines = response.split('\n')
        for line in lines[:30]:
            print(f"{C.YELLOW}│{C.ENDC} {line[:78]}")
        print(f"{C.YELLOW}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_llm_think(self, args: List[str]):
        """Ask LLM to think about something."""
        if len(args) < 2:
            print(f"{C.RED}Usage: think <question>{C.ENDC}")
            return

        question = ' '.join(args[1:])
        response = self.llm.call(f"请详细分析以下问题：{question}")

        print(f"\n{C.CYAN}┌─ LLM Analysis ───────────────────────────────────────{C.ENDC}")
        lines = response.split('\n')
        for line in lines:
            print(f"{C.CYAN}│{C.ENDC} {line[:78]}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_llm_role(self, args: List[str]):
        """Set LLM role."""
        if len(args) < 2:
            print(f"{C.RED}Usage: role <role_name>{C.ENDC}")
            print(f"{C.CYAN}Available: pentester, analyst, hacker, defender, consultant{C.ENDC}")
            return

        role = args[1].lower()
        prompts = {
            'pentester': "你是一个专业的渗透测试工程师，擅长发现和利用系统漏洞。",
            'analyst': "你是一个网络安全分析师，擅长分析威胁和风险评估。",
            'hacker': "你是一个红队成员，专注于绕过安全防御。",
            'defender': "你是一个蓝队安全专家，专注于防御和保护系统。",
            'consultant': "你是一个安全顾问，提供全面的安全建议和最佳实践。",
        }

        if role in prompts:
            self.llm.set_system_prompt(prompts[role])
        else:
            print(f"{C.RED}Unknown role: {role}{C.ENDC}")
            print(f"{C.CYAN}Available: {', '.join(prompts.keys())}{C.ENDC}")

    def cmd_llm_sys(self, args: List[str]):
        """Set custom system prompt."""
        if len(args) < 2:
            print(f"{C.RED}Usage: sys <prompt_text>{C.ENDC}")
            return

        prompt = ' '.join(args[1:])
        self.llm.set_system_prompt(prompt)

    def cmd_llm_context(self, args: List[str]):
        """Add context for LLM."""
        if len(args) < 2:
            print(f"\n{C.BOLD}Current Context ({len(self.llm.context)} items):{C.ENDC}\n")
            for i, ctx in enumerate(self.llm.context, 1):
                print(f"  {C.CYAN}{i}.{C.ENDC} {ctx[:80]}...")
            if not self.llm.context:
                print(f"  {C.YELLOW}No context added{C.ENDC}")
            print()
        else:
            context = ' '.join(args[1:])
            self.llm.add_context(context)

    def cmd_llm_config(self, args=None):
        """Show LLM configuration."""
        print(f"\n{C.BOLD}LLM Configuration:{C.ENDC}\n")

        if self.llm.provider:
            config = self.llm.provider.config
            print(f"  {C.CYAN}Provider:{C.ENDC}     {config.provider}")
            print(f"  {C.CYAN}Model:{C.ENDC}        {config.model}")
            print(f"  {C.CYAN}API Base:{C.ENDC}     {config.api_base}")
            print(f"  {C.CYAN}Temperature:{C.ENDC}  {config.temperature}")
            print(f"  {C.CYAN}Max Tokens:{C.ENDC}   {config.max_tokens}")
            print(f"  {C.CYAN}API Key:{C.ENDC}      {'*' * 20}{str(config.api_key)[-4:] if config.api_key else 'Not set'}")
        else:
            print(f"  {C.YELLOW}LLM not initialized{C.ENDC}")
            print(f"  {C.CYAN}Set API key: set api_key <your_key>{C.ENDC}")

        print()
        print(f"  {C.CYAN}Session Stats:{C.ENDC}")
        print(f"    Calls: {self.llm.call_count}")
        print(f"    Context: {len(self.llm.context)} items")
        print(f"    History: {len(self.llm.conversation_history)} messages")
        print()

    def cmd_llm_history(self, args=None):
        """Show conversation history."""
        print(f"\n{C.BOLD}Conversation History:{C.ENDC}\n")

        history = self.llm.conversation_history[-20:]
        for i, msg in enumerate(history, 1):
            role_color = C.CYAN if msg['role'] == 'user' else C.GREEN
            role_name = "User" if msg['role'] == 'user' else "LLM"
            content = msg['content'][:100]
            print(f"  {C.DIM}{i}.{C.ENDC} {role_color}[{role_name}]{C.ENDC} {content}...")

        if not history:
            print(f"  {C.YELLOW}No conversation history{C.ENDC}")
        print()

    def cmd_llm_clear(self, args=None):
        """Clear conversation history."""
        self.llm.conversation_history = []
        print(f"{C.GREEN}[+] Conversation cleared{C.ENDC}")

    # ==========================================
    # PENTEST MODULE COMMANDS
    # ==========================================

    def cmd_pentest_scan(self, args: List[str]):
        """Scan target with LLM analysis."""
        if len(args) < 2:
            target = self.config.get('target', '')
            if not target:
                print(f"{C.RED}Usage: scan <target>{C.ENDC}")
                return
        else:
            target = args[1]

        print(f"\n{C.BOLD}[*] Scanning {target} with LLM guidance...{C.ENDC}\n")

        # Ask LLM for scan strategy
        strategy = self.llm.call(
            f"为以下目标制定扫描策略：{target}\n\n"
            f"请说明：1. 推荐的端口范围 2. 扫描类型 3. 所需工具 4. 预期结果\n"
            f"用JSON格式输出：{{\"ports\": \"...\", \"type\": \"...\", \"tools\": [], \"notes\": \"...\"}}",
            use_json=True
        )

        # Simulate scan
        print(f"{C.CYAN}┌─ Scan Results ─────────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Target: {target}")
        print(f"{C.CYAN}│{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.GREEN}PORT      STATE    SERVICE         VERSION{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {'─'*55}")

        ports = [
            ("22/tcp", "open", "ssh", "OpenSSH 8.2p1"),
            ("80/tcp", "open", "http", "nginx 1.18"),
            ("443/tcp", "open", "https", "nginx 1.18"),
            ("3306/tcp", "open", "mysql", "MySQL 5.7.33"),
        ]

        for p in ports:
            print(f"{C.CYAN}│{C.ENDC} {p[0]:<10} {C.GREEN}{p[1]:<8}{C.ENDC} {p[2]:<14} {p[3]}")

        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

        # Update state
        self.attack_state['target'] = target
        self.attack_state['services'] = [p[2] for p in ports]

        # Ask LLM for analysis
        print(f"{C.YELLOW}[*] Analyzing results with LLM...{C.ENDC}\n")
        analysis = self.llm.call(
            f"分析以下扫描结果，识别潜在攻击向量：\n{ports}\n\n"
            f"对于每个开放端口，指出可能的漏洞和攻击方法。",
        )

        print(f"{C.CYAN}┌─ LLM Analysis ───────────────────────────────────────{C.ENDC}")
        for line in analysis.split('\n')[:15]:
            print(f"{C.CYAN}│{C.ENDC} {line[:78]}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_pentest_attack(self, args: List[str]):
        """Launch autonomous attack with LLM."""
        if len(args) < 2:
            target = self.config.get('target', '')
            if not target:
                print(f"{C.RED}Usage: attack <target> or 'set target' first{C.ENDC}")
                return
        else:
            target = args[1]

        print(f"\n{C.BOLD}{'='*60}{C.ENDC}")
        print(f"{C.BOLD}  AUTONOMOUS ATTACK MODE{C.ENDC}")
        print(f"{C.BOLD}{'='*60}{C.ENDC}\n")
        print(f"  {C.CYAN}Target:{C.ENDC} {target}")
        print(f"  {C.CYAN}Mode:{C.ENDC}   LLM-guided autonomous attack\n")

        phases = [
            ('recon', 'Information gathering'),
            ('scan', 'Port and service scanning'),
            ('enum', 'Service enumeration'),
            ('vuln', 'Vulnerability assessment'),
            ('exploit', 'Exploitation attempt'),
            ('post', 'Post-exploitation'),
        ]

        for i, (phase, desc) in enumerate(phases, 1):
            print(f"{C.BOLD}[Step {i}/{len(phases)}] {phase.upper()}: {desc}{C.ENDC}")

            # Get LLM instruction for this phase
            instruction = self.llm.call(
                f"作为渗透测试的第{i}步，当前阶段是 {phase}。\n"
                f"目标：{target}\n"
                f"请给出具体的执行指令（1-2句话），说明要做什么以及为什么。",
            )

            print(f"  {C.CYAN}LLM指导：{instruction[:100]}...{C.ENDC}\n")
            time.sleep(0.5)

            # Update state
            self.attack_state['phase'] = phase
            self.attack_state['step'] = i

        print(f"\n{C.GREEN}[+] Autonomous attack phase complete{C.ENDC}")
        print(f"{C.CYAN}    Use 'team' for detailed team-based attack{C.ENDC}\n")

    def cmd_pentest_team(self, args: List[str]):
        """Run team-based attack with live agent display."""
        if len(args) < 2:
            target = self.config.get('target', '')
            if not target:
                print(f"{C.RED}Usage: team <target> or 'set target' first{C.ENDC}")
                return
        else:
            target = args[1]

        print(f"\n{C.BOLD}{'='*60}{C.ENDC}")
        print(f"{C.BOLD}  TEAM-BASED ATTACK MODE{C.ENDC}")
        print(f"{C.BOLD}{'='*60}{C.ENDC}\n")
        print(f"  {C.CYAN}Target:{C.ENDC} {target}\n")

        team = [
            ('Commander', 'Coordinating attack'),
            ('Scout', 'Reconnaissance'),
            ('Analyst', 'Vulnerability analysis'),
            ('Striker', 'Exploitation'),
            ('Ghost', 'Post-exploitation'),
            ('Hunter', 'Credential gathering'),
            ('Phantom', 'Lateral movement'),
        ]

        # Briefing
        print(f"{C.CYAN}┌─ Team Briefing ───────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.BOLD}Mission:{C.ENDC} Full compromise of {target}")
        print(f"{C.CYAN}│{C.ENDC} {C.BOLD}Team:{C.ENDC} {len(team)} specialists deployed")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

        # Each agent provides input
        for agent, role in team:
            print(f"{C.BOLD}{'─'*60}{C.ENDC}")
            color = C.agent(agent)
            print(f"{color}[{agent}] {C.ENDC} {C.DIM}({role}){C.ENDC}")

            # Get agent's recommendation from LLM
            prompt = f"你是渗透测试团队的{agent}，负责{role}。\n目标：{target}\n\n给出你的专业建议（30字以内）："
            response = self.llm.call(prompt)

            print(f"  {C.CYAN}{response[:100]}{'...' if len(response) > 100 else ''}{C.ENDC}\n")
            time.sleep(0.3)

        # Commander's decision
        print(f"{C.BOLD}{'─'*60}{C.ENDC}")
        print(f"{C.CMD}[Commander] Final Strategy:{C.ENDC}")

        decision = self.llm.call(
            f"作为团队指挥官，基于以上团队意见，为目标{target}制定最终攻击策略。\n"
            f"请给出：1. 攻击路径 2. 优先目标 3. 预期结果\n"
            f"用JSON格式输出。",
            use_json=True
        )

        print(f"  {C.CYAN}{decision[:200]}...{C.ENDC}\n")
        print(f"{C.GREEN}[+] Team planning complete{C.ENDC}\n")

    def cmd_pentest_status(self):
        """Show attack status."""
        if not self.attack_state:
            print(f"{C.YELLOW}[*] No active attack session{C.ENDC}\n")
            return

        print(f"\n{C.BOLD}Attack Status:{C.ENDC}\n")
        print(f"  {C.CYAN}Target:{C.ENDC}    {self.attack_state.get('target', 'N/A')}")
        print(f"  {C.CYAN}Phase:{C.ENDC}     {self.attack_state.get('phase', 'N/A')}")
        print(f"  {C.CYAN}Step:{C.ENDC}      {self.attack_state.get('step', 0)}")
        print(f"  {C.CYAN}Services:{C.ENDC}  {', '.join(self.attack_state.get('services', []))}")
        print()

    # ==========================================
    # UTILITY COMMANDS
    # ==========================================

    def cmd_utils_hash(self, args: List[str]):
        """Calculate hashes."""
        if len(args) < 2:
            print(f"{C.RED}Usage: hash <text>{C.ENDC}")
            return

        import hashlib
        text = ' '.join(args[1:])

        print(f"\n{C.BOLD}Hash Values:{C.ENDC}\n")
        print(f"  {C.CYAN}MD5:{C.ENDC}    {hashlib.md5(text.encode()).hexdigest()}")
        print(f"  {C.CYAN}SHA1:{C.ENDC}   {hashlib.sha1(text.encode()).hexdigest()}")
        print(f"  {C.CYAN}SHA256:{C.ENDC} {hashlib.sha256(text.encode()).hexdigest()}")
        print(f"  {C.CYAN}SHA512:{C.ENDC} {hashlib.sha512(text.encode()).hexdigest()}")
        print()

    def cmd_utils_encode(self, args: List[str]):
        """Encode/decode."""
        import base64
        import urllib.parse

        if len(args) < 3:
            print(f"{C.RED}Usage: encode <text> [--base64|--url|--hex]{C.ENDC}")
            return

        text = args[1]
        method = args[2]

        print(f"\n{C.BOLD}Encoding Results:{C.ENDC}\n")

        if method == '--base64':
            print(f"  {C.CYAN}Base64:{C.ENDC}  {base64.b64encode(text.encode()).decode()}")
        elif method == '--url':
            print(f"  {C.CYAN}URL:{C.ENDC}     {urllib.parse.quote(text)}")
        elif method == '--hex':
            print(f"  {C.CYAN}Hex:{C.ENDC}     {text.encode().hex()}")
        else:
            print(f"{C.RED}Unknown method: {method}{C.ENDC}")
        print()

    def cmd_password_check(self, args: List[str]):
        """Check password strength."""
        if len(args) < 2:
            pwd = input(f"  {C.CYAN}Enter password: {C.ENDC}")
        else:
            pwd = args[1]

        import re
        score = 0
        criteria = []

        if len(pwd) >= 8:
            score += 1
            criteria.append(("Length >= 8", True))
        else:
            criteria.append(("Length >= 8", False))

        if len(pwd) >= 12:
            score += 1

        if re.search(r'[A-Z]', pwd):
            score += 1
            criteria.append(("Uppercase", True))
        else:
            criteria.append(("Uppercase", False))

        if re.search(r'[a-z]', pwd):
            score += 1
            criteria.append(("Lowercase", True))
        else:
            criteria.append(("Lowercase", False))

        if re.search(r'[0-9]', pwd):
            score += 1
            criteria.append(("Numbers", True))
        else:
            criteria.append(("Numbers", False))

        if re.search(r'[^A-Za-z0-9]', pwd):
            score += 1
            criteria.append(("Special chars", True))
        else:
            criteria.append(("Special chars", False))

        rating = ['WEAK', 'WEAK', 'FAIR', 'FAIR', 'GOOD', 'STRONG', 'STRONG'][min(score, 6)]
        color = C.RED if score <= 2 else C.YELLOW if score <= 4 else C.GREEN

        print(f"\n  {C.BOLD}Password Analysis:{C.ENDC}")
        print(f"  {C.CYAN}Password:{C.ENDC} {'*' * len(pwd)}")
        print(f"  {C.CYAN}Length:{C.ENDC}   {len(pwd)}")
        print(f"  {C.CYAN}Score:{C.ENDC}    {score}/6")
        print(f"  {C.CYAN}Rating:{C.ENDC}   {color}{rating}{C.ENDC}\n")

        for name, passed in criteria:
            mark = f"{C.GREEN}[+]" if passed else f"{C.RED}[-]"
            print(f"  {mark} {name}{C.ENDC}")

        print()

    def cmd_exploit_search(self, args: List[str]):
        """Search exploits."""
        if len(args) < 2:
            print(f"{C.RED}Usage: search <query>{C.ENDC}")
            return

        query = ' '.join(args[1:])

        print(f"\n{C.YELLOW}[*] Searching exploits for '{query}'...{C.ENDC}\n")

        # Mock results
        exploits = [
            ("EternalBlue", "CVE-2017-0144", "SMB RCE", 9.8),
            ("Log4Shell", "CVE-2021-44228", "Log4j RCE", 10.0),
            ("Heartbleed", "CVE-2014-0160", "OpenSSL Info Leak", 5.0),
            ("Shellshock", "CVE-2014-6271", "Bash RCE", 9.8),
        ]

        for name, cve, desc, cvss in exploits:
            if query.lower() in f"{name} {cve} {desc}".lower():
                cvss_color = C.RED if cvss >= 9 else C.YELLOW
                print(f"  {C.CYAN}{name:<15}{C.ENDC} {cve:<15} {desc:<20} CVSS: {cvss_color}{cvss}{C.ENDC}")

        print()

    # ==========================================
    # RECON MODULE COMMANDS
    # ==========================================

    def cmd_recon_nmap(self, args: List[str]):
        """Nmap port scan with LLM guidance."""
        if len(args) < 2:
            target = self.config.get('target', '')
            if not target:
                print(f"{C.RED}Usage: nmap <target> [ports]{C.ENDC}")
                return
        else:
            target = args[1]
            ports = ' '.join(args[2:]) if len(args) > 2 else '1-1000'

        print(f"\n{C.BOLD}[*] Nmap scan for {target}...{C.ENDC}\n")

        # Get LLM guidance on scan strategy
        guidance = self.llm.call(
            f"为 {target} 推荐nmap扫描参数。需要考虑：\n"
            f"1. 推荐的端口范围 2. 扫描类型(-sS/-sT/-sV) 3. 是否需要操作系统检测 4. 脚本扫描建议\n"
            f"简洁回复（50字以内）",
        )

        print(f"{C.CYAN}[LLM Guidance] {guidance[:100]}{C.ENDC}\n")
        print(f"{C.YELLOW}[*] Starting nmap scan: nmap -sV -O {target} -p {ports}{C.ENDC}\n")

        # Simulated results
        results = [
            ("22/tcp", "open", "ssh", "OpenSSH 8.2p1 Ubuntu"),
            ("80/tcp", "open", "http", "Apache 2.4.41"),
            ("443/tcp", "open", "https", "Apache 2.4.41"),
            ("3306/tcp", "open", "mysql", "MySQL 8.0.32"),
        ]

        print(f"{C.CYAN}┌─ Nmap Results ─────────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Target: {target}    Ports: {ports}")
        print(f"{C.CYAN}│{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.GREEN}PORT      STATE    SERVICE         VERSION{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {'─'*50}")
        for p in results:
            print(f"{C.CYAN}│{C.ENDC} {p[0]:<10} {C.GREEN}{p[1]:<8}{C.ENDC} {p[2]:<14} {p[3]}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

        # LLM vulnerability assessment
        vuln_info = self.llm.call(
            f"根据扫描结果分析 {target} 的潜在漏洞：\n{results}\n"
            f"列出每个服务的已知漏洞和攻击方法",
        )
        print(f"{C.YELLOW}[*] Vulnerability Assessment:{C.ENDC}")
        for line in vuln_info.split('\n')[:10]:
            print(f"  {line[:78]}")
        print()

    def cmd_recon_whois(self, args: List[str]):
        """WHOIS lookup."""
        if len(args) < 2:
            print(f"{C.RED}Usage: whois <domain>{C.ENDC}")
            return

        domain = args[1]
        print(f"\n{C.BOLD}[*] WHOIS lookup for {domain}...{C.ENDC}\n")

        # Mock WHOIS data
        print(f"{C.CYAN}┌─ WHOIS Information ───────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Domain: {domain}")
        print(f"{C.CYAN}│{C.ENDC} Registrar: GoDaddy.com, LLC")
        print(f"{C.CYAN}│{C.ENDC} Created: 2020-01-15")
        print(f"{C.CYAN}│{C.ENDC} Expires: 2025-01-15")
        print(f"{C.CYAN}│{C.ENDC} Nameservers: ns1.example.com, ns2.example.com")
        print(f"{C.CYAN}│{C.ENDC} Status: clientUpdateProhibited")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_recon_dns(self, args: List[str]):
        """DNS enumeration."""
        if len(args) < 2:
            print(f"{C.RED}Usage: dns <domain>{C.ENDC}")
            return

        domain = args[1]
        print(f"\n{C.BOLD}[*] DNS enumeration for {domain}...{C.ENDC}\n")

        records = [
            ("A", "192.168.1.100"),
            ("AAAA", "2001:db8::1"),
            ("MX", "mail.example.com"),
            ("NS", "ns1.example.com"),
            ("TXT", "v=spf1 include:_spf.example.com ~all"),
        ]

        print(f"{C.CYAN}┌─ DNS Records ─────────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Domain: {domain}")
        print(f"{C.CYAN}│{C.ENDC}")
        for rec_type, value in records:
            print(f"{C.CYAN}│{C.ENDC} {rec_type:<6} {value}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_recon_subdomain(self, args: List[str]):
        """Subdomain discovery."""
        if len(args) < 2:
            print(f"{C.RED}Usage: subdomain <domain>{C.ENDC}")
            return

        domain = args[1]
        print(f"\n{C.BOLD}[*] Subdomain enumeration for {domain}...{C.ENDC}\n")

        subdomains = [
            "www", "mail", "ftp", "admin", "blog", "shop",
            "dev", "test", "staging", "api", "cdn", "static",
        ]

        print(f"{C.CYAN}┌─ Discovered Subdomains ────────────────────────────────{C.ENDC}")
        for sub in subdomains:
            print(f"{C.CYAN}│{C.ENDC} {sub}.{domain}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}")
        print(f"{C.GREEN}[+] Found {len(subdomains)} subdomains{C.ENDC}\n")

    def cmd_recon_shodan(self, args: List[str]):
        """Shodan search with LLM."""
        if len(args) < 2:
            print(f"{C.RED}Usage: shodan <query>{C.ENDC}")
            return

        query = ' '.join(args[1:])
        print(f"\n{C.BOLD}[*] Searching Shodan for: {query}{C.ENDC}\n")

        # LLM search strategy
        strategy = self.llm.call(
            f"分析Shodan搜索 '{query}' 的策略。给出：\n"
            f"1. 推荐的过滤器 2. 预期结果类型 3. 安全评估要点\n"
            f"简洁回复",
        )
        print(f"{C.YELLOW}[LLM] {strategy[:150]}{C.ENDC}\n")

        print(f"{C.CYAN}┌─ Shodan Results ──────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Query: {query}")
        print(f"{C.CYAN}│{C.ENDC} Results: ~50 hosts found")
        print(f"{C.CYAN}│{C.ENDC} Top ports: 22, 80, 443, 3306, 5432")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    # ==========================================
    # POST MODULE COMMANDS
    # ==========================================

    def cmd_post_shell(self, args: List[str]):
        """Get interactive shell."""
        print(f"\n{C.BOLD}[*] Spawning interactive shell...{C.ENDC}\n")

        guidance = self.llm.call(
            "根据当前攻击状态，推荐最合适的shell类型和获取方法。\n"
            "考虑：1. 目标系统 2. 已获取的权限 3. 网络环境\n"
            "简洁回复",
        )
        print(f"{C.CYAN}[LLM] {guidance[:200]}{C.ENDC}\n")

        print(f"{C.GREEN}[+] Shell spawned (simulated){C.ENDC}")
        print(f"{C.CYAN}    Use 'python', 'bash', 'powershell' for specific types{C.ENDC}\n")

    def cmd_post_persist(self, args: List[str]):
        """Setup persistence."""
        print(f"\n{C.BOLD}[*] Establishing persistence...{C.ENDC}\n")

        guidance = self.llm.call(
            "推荐持久化方法：\n"
            "1. Windows: registry, scheduled task, service\n"
            "2. Linux: cron, systemd, ssh key\n"
            "考虑目标系统和权限级别，简洁回复",
        )

        methods = [
            ("Windows", "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"),
            ("Linux", "/etc/crontab"),
            ("Both", "SSH key injection"),
        ]

        print(f"{C.CYAN}┌─ Persistence Methods ─────────────────────────────────{C.ENDC}")
        for os_type, method in methods:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}{os_type}:{C.ENDC} {method}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM Guidance] {guidance[:150]}{C.ENDC}\n")

    def cmd_post_escalate(self, args: List[str]):
        """Privilege escalation."""
        print(f"\n{C.BOLD}[*] Privilege escalation check...{C.ENDC}\n")

        check = self.llm.call(
            "基于典型环境，推荐权限提升检查项：\n"
            "1. SUID/SGID文件 2. sudo配置 3. 内核漏洞 4. 服务配置\n"
            "提供检查命令和利用思路",
        )

        vectors = [
            ("SUID Binaries", "find / -perm -4000 2>/dev/null"),
            ("Sudo Misconfig", "sudo -l"),
            ("Kernel Exploits", "uname -r; searchsploit"),
            ("Service Exploits", "ps aux; grep -v root"),
        ]

        print(f"{C.CYAN}┌─ Privilege Escalation Vectors ────────────────────────{C.ENDC}")
        for name, cmd in vectors:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}{name}:{C.ENDC}")
            print(f"{C.CYAN}│{C.ENDC}   {C.DIM}{cmd}{C.ENDC}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

        print(f"{C.YELLOW}[LLM] {check[:200]}{C.ENDC}\n")

    def cmd_post_mimikatz(self, args: List[str]):
        """Dump credentials with mimikatz."""
        print(f"\n{C.BOLD}[*] Credential dumping...{C.ENDC}\n")

        guidance = self.llm.call(
            "Mimikatz使用指南：\n"
            "1. 基础：sekurlsa::logonpasswords\n"
            "2. SAM数据库：lsadump::sam\n"
            "3. 票据：kerberos::list\n"
            "警告：仅用于授权测试",
        )

        creds = [
            ("Administrator", "LAB\\Administrator", "pwd123", "NTLM"),
            ("User", "LAB\\User", "Pass@word1", "NTLM"),
            ("Service", "LAB\\ServiceAccount", "S3rv1ce!", "NTLM"),
        ]

        print(f"{C.CYAN}┌─ Dumped Credentials (Demo) ───────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.RED}WARNING: Demo data only{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC}")
        for user, domain, pwd, hash_type in creds:
            print(f"{C.CYAN}│{C.ENDC} {C.BOLD}{domain}\\{user}{C.ENDC}")
            print(f"{C.CYAN}│{C.ENDC}   Password: {pwd}")
            print(f"{C.CYAN}│{C.ENDC}   Hash: {hash_type}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    # ==========================================
    # CREDS MODULE COMMANDS
    # ==========================================

    def cmd_creds_hydra(self, args: List[str]):
        """Hydra brute force."""
        if len(args) < 3:
            print(f"{C.RED}Usage: hydra <target> <service>{C.ENDC}")
            print(f"{C.CYAN}Example: hydra 192.168.1.100 ssh{C.ENDC}")
            return

        target = args[1]
        service = args[2]

        print(f"\n{C.BOLD}[*] Hydra brute force attack on {target}/{service}{C.ENDC}\n")

        # LLM strategy
        strategy = self.llm.call(
            f"为{target}的{service}服务制定密码爆破策略：\n"
            f"1. 推荐用户名字典 2. 密码字典选择 3. 并发线程数 4. 超时设置\n"
            f"给出hydra命令示例",
        )

        print(f"{C.YELLOW}[LLM Strategy]{C.ENDC}")
        print(f"{C.CYAN}{strategy[:300]}{C.ENDC}\n")

        print(f"{C.GREEN}[*] hydra -L users.txt -P passwords.txt {target} {service}{C.ENDC}\n")

    def cmd_creds_hashcat(self, args: List[str]):
        """Hashcat cracking."""
        if len(args) < 2:
            print(f"{C.RED}Usage: hashcat <hash> [--mode N]{C.ENDC}")
            return

        hash_val = args[1]
        mode = args[3] if len(args) > 3 and args[2] == '--mode' else '0'

        print(f"\n{C.BOLD}[*] Hashcat analysis for {hash_val[:20]}...{C.ENDC}\n")

        analysis = self.llm.call(
            f"分析哈希类型并推荐hashcat攻击模式：\n"
            f"哈希: {hash_val}\n"
            f"给出：1. 可能的哈希类型 2. -m 参数 3. 攻击策略 4. 推荐字典",
        )

        print(f"{C.CYAN}[LLM Analysis]{C.ENDC}")
        print(f"{C.CYAN}{analysis[:300]}{C.ENDC}\n")

        print(f"{C.YELLOW}[*] Recommended command: hashcat -m {mode} hash.txt wordlist.txt{C.ENDC}\n")

    def cmd_creds_wordlist(self, args: List[str]):
        """Generate wordlist."""
        print(f"\n{C.BOLD}[*] Wordlist generation...{C.ENDC}\n")

        guidance = self.llm.call(
            "密码字典生成策略：\n"
            "1. 基于目标信息（姓名、生日、公司名）\n"
            "2. 常见模式（leetspeak, word01）\n"
            "3. 规则转换\n"
            "给出生成命令和工具推荐",
        )

        sources = [
            "cewl -w dict.txt https://target.com",
            "crunch 8 12 -t @%%hat2020 -o wordlist.txt",
            "hashcat --stdout -a 3 ?d?d?d?d?d?d -o years.txt",
        ]

        print(f"{C.CYAN}┌─ Wordlist Sources ────────────────────────────────────{C.ENDC}")
        for src in sources:
            print(f"{C.CYAN}│{C.ENDC} {C.DIM}{src}{C.ENDC}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM] {guidance[:200]}{C.ENDC}\n")

    # ==========================================
    # WEB MODULE COMMANDS
    # ==========================================

    def cmd_web_sqlmap(self, args: List[str]):
        """SQL injection with sqlmap."""
        if len(args) < 2:
            print(f"{C.RED}Usage: sqlmap <url>{C.ENDC}")
            return

        url = args[1]
        print(f"\n{C.BOLD}[*] SQLMap scan for {url}{C.ENDC}\n")

        # LLM guidance
        guidance = self.llm.call(
            f"为URL {url} 制定SQL注入测试策略：\n"
            f"1. 推荐的sqlmap参数 2. 测试用例 3. 风险评估 4. 防御绕过\n"
            f"给出命令示例",
        )

        print(f"{C.YELLOW}[LLM Guidance]{C.ENDC}")
        print(f"{C.CYAN}{guidance[:300]}{C.ENDC}\n")

        print(f"{C.GREEN}[*] Recommended: sqlmap -u \"{url}\" --batch --level=2{C.ENDC}\n")

        # Simulated findings
        print(f"{C.CYAN}┌─ Potential Injections ────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Parameter: id (GET)")
        print(f"{C.CYAN}│{C.ENDC} Type: Boolean-based blind")
        print(f"{C.CYAN}│{C.ENDC} Confidence: Medium")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_web_gobuster(self, args: List[str]):
        """Directory busting with gobuster."""
        if len(args) < 2:
            print(f"{C.RED}Usage: gobuster <url>{C.ENDC}")
            return

        url = args[1]
        print(f"\n{C.BOLD}[*] Directory enumeration for {url}{C.ENDC}\n")

        guidance = self.llm.call(
            f"为{url}制定目录枚举策略：\n"
            f"1. 推荐字典 2. 扫描深度 3. 线程数 4. 常见敏感路径\n"
            f"简洁回复",
        )

        findings = ["admin", "api", "backup", "config", "dashboard", "login"]

        print(f"{C.CYAN}┌─ Discovered Paths ────────────────────────────────────{C.ENDC}")
        for path in findings:
            print(f"{C.CYAN}│{C.ENDC} /{path}/")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}")
        print(f"{C.GREEN}[+] Found {len(findings)} paths{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM] {guidance[:150]}{C.ENDC}\n")

    def cmd_web_xss(self, args: List[str]):
        """XSS testing."""
        if len(args) < 2:
            print(f"{C.RED}Usage: xss <url>{C.ENDC}")
            return

        url = args[1]
        print(f"\n{C.BOLD}[*] XSS testing for {url}{C.ENDC}\n")

        payloads = [
            "<script>alert(1)</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "\"><script>alert(1)</script>",
        ]

        guidance = self.llm.call(
            f"为{url}制定XSS测试策略：\n"
            f"1. 测试向量 2. WAF bypass 3. 上下文识别 4. 存储型vs反射型\n"
            f"给出payload建议",
        )

        print(f"{C.CYAN}┌─ Test Payloads ───────────────────────────────────────{C.ENDC}")
        for i, payload in enumerate(payloads, 1):
            print(f"{C.CYAN}│{C.ENDC} {i}. {C.DIM}{payload}{C.ENDC}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM] {guidance[:200]}{C.ENDC}\n")

    # ==========================================
    # NETWORK MODULE COMMANDS
    # ==========================================

    def cmd_network_arp(self, args: List[str]):
        """Show ARP table."""
        print(f"\n{C.BOLD}[*] ARP Table{C.ENDC}\n")

        entries = [
            ("192.168.1.1", "00:11:22:33:44:55", "gateway"),
            ("192.168.1.100", "aa:bb:cc:dd:ee:ff", "workstation"),
            ("192.168.1.200", "11:22:33:44:55:66", "server"),
        ]

        print(f"{C.CYAN}┌─ ARP Table ───────────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.BOLD}IP Address      MAC Address         Host{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {'─'*50}")
        for ip, mac, host in entries:
            print(f"{C.CYAN}│{C.ENDC} {ip:<15} {mac:<20} {host}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_network_netstat(self, args: List[str]):
        """Show network statistics."""
        print(f"\n{C.BOLD}[*] Network Connections{C.ENDC}\n")

        connections = [
            ("TCP", "0.0.0.0", "22", "LISTEN"),
            ("TCP", "0.0.0.0", "80", "LISTEN"),
            ("TCP", "192.168.1.100", "443", "ESTABLISHED"),
            ("UDP", "0.0.0.0", "53", "LISTEN"),
        ]

        print(f"{C.CYAN}┌─ Active Connections ─────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.BOLD}Proto  Local Address      Port  State{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {'─'*50}")
        for proto, local, port, state in connections:
            print(f"{C.CYAN}│{C.ENDC} {proto:<6} {local:<20} {port:<5} {state}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_network_tcpdump(self, args: List[str]):
        """Packet capture."""
        if len(args) < 2:
            filter_expr = ""
        else:
            filter_expr = ' '.join(args[1:])

        print(f"\n{C.BOLD}[*] Packet capture{C.ENDC}\n")
        print(f"{C.YELLOW}Filter: {filter_expr if filter_expr else '(none)'}{C.ENDC}")
        print(f"{C.GREEN}[*] tcpdump -i any {filter_expr}{C.ENDC}\n")

        guidance = self.llm.call(
            f"tcpdump抓包分析建议：\n"
            f"过滤器: {filter_expr}\n"
            f"1. 推荐捕获选项 2. 分析要点 3. 常见恶意流量特征\n"
            f"简洁回复",
        )
        print(f"{C.YELLOW}[LLM] {guidance[:200]}{C.ENDC}\n")

    # ==========================================
    # WIRELESS MODULE COMMANDS
    # ==========================================

    def cmd_wireless_airodump(self, args: List[str]):
        """Wireless capture."""
        if len(args) < 2:
            interface = "wlan0"
        else:
            interface = args[1]

        print(f"\n{C.BOLD}[*] Wireless AP detection on {interface}{C.ENDC}\n")

        guidance = self.llm.call(
            f"无线网络检测策略：\n"
            f"1. 推荐airodump参数 2. 信道选择 3. 握手捕获技巧 4. 安全评估\n"
            f"简洁回复",
        )

        aps = [
            ("00:11:22:33:44:55", "MyNetwork_5G", "WPA2", -45, "6"),
            ("AA:BB:CC:DD:EE:FF", "Guest_WiFi", "WPA2", -60, "11"),
            ("11:22:33:44:55:66", "FreeWiFi", "OPEN", -70, "1"),
        ]

        print(f"{C.CYAN}┌─ Detected APs ───────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {C.BOLD}BSSID          SSID          ENC    RSSI  CH{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} {'─'*50}")
        for bssid, ssid, enc, rssi, ch in aps:
            enc_color = C.GREEN if enc != "OPEN" else C.RED
            print(f"{C.CYAN}│{C.ENDC} {bssid}  {ssid:<12} {enc_color}{enc:<6}{C.ENDC} {rssi}  {ch}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM] {guidance[:200]}{C.ENDC}\n")

    # ==========================================
    # FORENSICS MODULE COMMANDS
    # ==========================================

    def cmd_forensics_volatility(self, args: List[str]):
        """Memory forensics."""
        if len(args) < 2:
            print(f"{C.RED}Usage: volatility <image>{C.ENDC}")
            return

        image = args[1]
        print(f"\n{C.BOLD}[*] Memory analysis: {image}{C.ENDC}\n")

        guidance = self.llm.call(
            f"内存取证分析建议：\n"
            f"1. 推荐volatility命令 2. 分析目标（进程、网络连接、凭证）3. 取证要点\n"
            f"简洁回复",
        )

        print(f"{C.CYAN}┌─ Analysis Commands ──────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} volatility -f {image} windows.pslist")
        print(f"{C.CYAN}│{C.ENDC} volatility -f {image} windows.netscan")
        print(f"{C.CYAN}│{C.ENDC} volatility -f {image} windows.hashdump")
        print(f"{C.CYAN}│{C.ENDC} volatility -f {image} windows.malfind")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM] {guidance[:200]}{C.ENDC}\n")

    def cmd_forensics_strings(self, args: List[str]):
        """Extract strings from file."""
        if len(args) < 2:
            print(f"{C.RED}Usage: strings <file>{C.ENDC}")
            return

        file_path = args[1]
        print(f"\n{C.BOLD}[*] String extraction: {file_path}{C.ENDC}\n")

        guidance = self.llm.call(
            f"字符串分析建议：\n"
            f"1. 推荐长度阈值 2. 编码选择 3. 重点关注的模式（URL、IP、密钥）\n"
            f"简洁回复",
        )

        findings = [
            "https://malware-c2.example.com",
            "admin:password123",
            "API_KEY=sk-xxxxx",
            "192.168.1.100:4444",
        ]

        print(f"{C.CYAN}┌─ Interesting Strings ─────────────────────────────────{C.ENDC}")
        for s in findings:
            print(f"{C.CYAN}│{C.ENDC} {C.DIM}{s}{C.ENDC}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[LLM] {guidance[:150]}{C.ENDC}\n")

    # ==========================================
    # OSINT MODULE COMMANDS
    # ==========================================

    def cmd_osint_shodan(self, args: List[str]):
        """Shodan OSINT search."""
        if len(args) < 2:
            print(f"{C.RED}Usage: shodan <query>{C.ENDC}")
            return

        query = ' '.join(args[1:])
        print(f"\n{C.BOLD}[*] Shodan search: {query}{C.ENDC}\n")

        results = self.llm.call(
            f"分析Shodan搜索 '{query}' 的结果解读：\n"
            f"1. 端口和服务信息 2. 漏洞暴露 3. 地理位置 4. 历史数据\n"
            f"给出安全评估要点",
        )

        print(f"{C.CYAN}┌─ Shodan Results ──────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} Query: {query}")
        print(f"{C.CYAN}│{C.ENDC} Total hosts: ~100")
        print(f"{C.CYAN}│{C.ENDC} Top ports: 22, 80, 443, 8080, 3306")
        print(f"{C.CYAN}│{C.ENDC} Top vulnerabilities: CVE-2021-26855, CVE-2021-27065")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.YELLOW}[Analysis]{C.ENDC}")
        print(f"{C.CYAN}{results[:300]}{C.ENDC}\n")

    def cmd_osint_hunter(self, args: List[str]):
        """Email hunter."""
        if len(args) < 2:
            print(f"{C.RED}Usage: hunter <domain>{C.ENDC}")
            return

        domain = args[1]
        print(f"\n{C.BOLD}[*] Email enumeration: {domain}{C.ENDC}\n")

        emails = [
            f"admin@{domain}",
            f"contact@{domain}",
            f"info@{domain}",
            f"support@{domain}",
        ]

        print(f"{C.CYAN}┌─ Discovered Emails ───────────────────────────────────{C.ENDC}")
        for email in emails:
            print(f"{C.CYAN}│{C.ENDC} {email}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}")
        print(f"{C.GREEN}[+] Found {len(emails)} emails{C.ENDC}\n")

    def cmd_osint_wayback(self, args: List[str]):
        """Wayback machine."""
        if len(args) < 2:
            print(f"{C.RED}Usage: wayback <domain>{C.ENDC}")
            return

        domain = args[1]
        print(f"\n{C.BOLD}[*] Wayback archive search: {domain}{C.ENDC}\n")

        archives = [
            ("2024-01-15", "/admin/", "Login page"),
            ("2024-03-20", "/backup/", "Directory listing"),
            ("2024-06-10", "/api/v1/", "API documentation"),
        ]

        print(f"{C.CYAN}┌─ Historical Snapshots ──────────────────────────────{C.ENDC}")
        for date, path, desc in archives:
            print(f"{C.CYAN}│{C.ENDC} {date}  {path:<20} {desc}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    # ==========================================
    # KNOWLEDGE MODULE COMMANDS
    # ==========================================

    def cmd_knowledge_search(self, args: List[str]):
        """Search knowledge base."""
        if len(args) < 2:
            print(f"{C.RED}Usage: search <query>{C.ENDC}")
            return

        query = ' '.join(args[1:])
        print(f"\n{C.BOLD}[*] Knowledge search: {query}{C.ENDC}\n")

        results = self.llm.call(
            f"在知识库中搜索 '{query}' 并提供相关安全知识：\n"
            f"包括：1. 相关漏洞 2. 攻击技术 3. 防御建议 4. 参考资料\n"
            f"结构化回复",
        )

        print(f"{C.CYAN}┌─ Search Results ──────────────────────────────────────{C.ENDC}")
        for line in results.split('\n')[:15]:
            print(f"{C.CYAN}│{C.ENDC} {line[:78]}")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    def cmd_knowledge_cve(self, args: List[str]):
        """CVE lookup."""
        if len(args) < 2:
            print(f"{C.RED}Usage: cve <cve_id>{C.ENDC}")
            return

        cve_id = args[1].upper()
        print(f"\n{C.BOLD}[*] CVE lookup: {cve_id}{C.ENDC}\n")

        info = self.llm.call(
            f"查询 {cve_id} 的详细信息：\n"
            f"1. 漏洞描述 2. CVSS评分 3. 影响版本 4. 利用可行性 5. 修复建议\n"
            f"结构化回复",
        )

        print(f"{C.CYAN}┌─ CVE Information ─────────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} ID: {cve_id}")
        print(f"{C.CYAN}│{C.ENDC} CVSS: 9.8 (Critical)")
        print(f"{C.CYAN}│{C.ENDC} Affected: Multiple versions")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")
        print(f"{C.CYAN}{info[:400]}{C.ENDC}\n")

    def cmd_knowledge_technique(self, args: List[str]):
        """ATT&CK technique lookup."""
        if len(args) < 2:
            print(f"{C.RED}Usage: technique <technique_id>{C.ENDC}")
            return

        tech_id = args[1].upper()
        print(f"\n{C.BOLD}[*] ATT&CK technique: {tech_id}{C.ENDC}\n")

        print(f"{C.CYAN}┌─ Technique Details ──────────────────────────────────{C.ENDC}")
        print(f"{C.CYAN}│{C.ENDC} ID: {tech_id}")
        print(f"{C.CYAN}│{C.ENDC} Tactic: Initial Access")
        print(f"{C.CYAN}│{C.ENDC} Description: Attack technique description")
        print(f"{C.CYAN}│{C.ENDC} Detection: Detection guidance")
        print(f"{C.CYAN}└─────────────────────────────────────────────────────────────{C.ENDC}\n")

    # ==========================================
    # COMMAND EXECUTION
    # ==========================================

    def _execute_module_command(self, cmd: str, args: List[str]):
        """Route command to handler."""
        if not self.current_module:
            return False

        handlers = {
            'llm': {
                'exec': self.cmd_llm_exec,
                'plan': self.cmd_llm_plan,
                'analyze': self.cmd_llm_analyze,
                'think': self.cmd_llm_think,
                'role': self.cmd_llm_role,
                'sys': self.cmd_llm_sys,
                'context': self.cmd_llm_context,
                'config': self.cmd_llm_config,
                'history': self.cmd_llm_history,
                'clear': self.cmd_llm_clear,
            },
            'pentest': {
                'scan': self.cmd_pentest_scan,
                'attack': self.cmd_pentest_attack,
                'team': self.cmd_pentest_team,
                'status': self.cmd_pentest_status,
            },
            'utils': {
                'hash': self.cmd_utils_hash,
                'encode': self.cmd_utils_encode,
            },
            'password': {
                'check': self.cmd_password_check,
            },
            'exploit': {
                'search': self.cmd_exploit_search,
            },
            'recon': {
                'nmap': self.cmd_recon_nmap,
                'whois': self.cmd_recon_whois,
                'dns': self.cmd_recon_dns,
                'subdomain': self.cmd_recon_subdomain,
                'shodan': self.cmd_recon_shodan,
            },
            'post': {
                'shell': self.cmd_post_shell,
                'persist': self.cmd_post_persist,
                'escalate': self.cmd_post_escalate,
                'mimikatz': self.cmd_post_mimikatz,
            },
            'creds': {
                'hydra': self.cmd_creds_hydra,
                'hashcat': self.cmd_creds_hashcat,
                'wordlist': self.cmd_creds_wordlist,
            },
            'web': {
                'sqlmap': self.cmd_web_sqlmap,
                'gobuster': self.cmd_web_gobuster,
                'xss': self.cmd_web_xss,
            },
            'network': {
                'arp': self.cmd_network_arp,
                'netstat': self.cmd_network_netstat,
                'tcpdump': self.cmd_network_tcpdump,
            },
            'wireless': {
                'airodump': self.cmd_wireless_airodump,
            },
            'forensics': {
                'volatility': self.cmd_forensics_volatility,
                'strings': self.cmd_forensics_strings,
            },
            'osint': {
                'shodan': self.cmd_osint_shodan,
                'hunter': self.cmd_osint_hunter,
                'wayback': self.cmd_osint_wayback,
            },
            'knowledge': {
                'search': self.cmd_knowledge_search,
                'cve': self.cmd_knowledge_cve,
                'technique': self.cmd_knowledge_technique,
            },
        }

        if self.current_module in handlers:
            if cmd in handlers[self.current_module]:
                handlers[self.current_module][cmd](args)
                return True

        return False

    def parse_and_execute(self, line: str):
        """Parse and execute command line."""
        line = line.strip()
        if not line:
            return

        self.history.append(line)
        parts = line.split()
        cmd = parts[0]

        # Exit handling
        if cmd in ['exit', 'quit']:
            print(f"\n{C.CYAN}[*] Goodbye!{C.ENDC}\n")
            self.running = False
            return

        # Global commands
        if cmd == 'help':
            self.cmd_help()
        elif cmd == 'clear':
            os.system('cls' if os.name == 'nt' else 'clear')
            self.print_banner()
        elif cmd == 'banner':
            self.print_banner()
        elif cmd == 'info':
            import platform
            print(f"\n{C.BOLD}System Info:{C.ENDC}")
            print(f"  {C.CYAN}Hostname:{C.ENDC}  {socket.gethostname()}")
            print(f"  {C.CYAN}Platform:{C.ENDC}  {platform.system()} {platform.release()}")
            print(f"  {C.CYAN}Python:{C.ENDC}    {platform.python_version()}")
            print()
        elif cmd == 'status':
            self.cmd_status()
        elif cmd == 'show':
            self.cmd_show(parts)
        elif cmd == 'use':
            self.cmd_use(parts)
        elif cmd == 'back':
            self.current_module = None
            print(f"{C.GREEN}[+] Returned to main context{C.ENDC}")
        elif cmd == 'set':
            self.cmd_set(parts)
        elif cmd == 'get':
            self.cmd_get(parts)
        elif cmd == 'history':
            self.cmd_history()
        elif cmd == 'cd':
            if len(parts) > 1:
                try:
                    os.chdir(os.path.expanduser(parts[1]))
                except Exception as e:
                    print(f"{C.RED}cd: {e}{C.ENDC}")
        elif cmd == 'pwd':
            print(os.getcwd())

        # Module commands
        elif self.current_module:
            if not self._execute_module_command(cmd, parts):
                print(f"{C.RED}[!] Unknown command: {cmd}{C.ENDC}")
                print(f"{C.CYAN}Available: {', '.join(self.modules[self.current_module]['commands'].keys())}{C.ENDC}\n")

        else:
            print(f"{C.RED}[!] Unknown command: {cmd}{C.ENDC}")
            print(f"{C.CYAN}Type 'help' or 'show modules'{C.ENDC}\n")

    def run(self):
        """Run the terminal."""
        self.print_banner()

        print(f"{C.CYAN}Type 'help' for commands{C.ENDC}")
        print(f"{C.CYAN}Type 'use llm' to control LLM directly{C.ENDC}")
        print(f"{C.CYAN}Type 'set api_key <key>' to configure LLM{C.ENDC}\n")

        while self.running:
            try:
                line = input(self.print_prompt())
                self.parse_and_execute(line)
            except KeyboardInterrupt:
                print(f"\n{C.YELLOW}[!] Use 'exit' to quit{C.ENDC}")
            except EOFError:
                print(f"\n{C.CYAN}[*] Goodbye!{C.ENDC}\n")
                break


def main():
    terminal = KaliTerminal()
    terminal.run()


if __name__ == "__main__":
    main()