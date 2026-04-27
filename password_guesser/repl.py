"""
Enhanced REPL (Read-Eval-Print Loop) for Password Guesser CLI.

Features:
- Tab completion using readline
- Command history persistence (~/.pg_history)
- Variable system ($target, $session, etc.)
- Object introspection (ls, vars, set, get)
- Pipeline support
- Shell integration
"""

import os
import sys
import json
import shlex
import atexit
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable


class EnhancedREPL:
    """
    Enhanced REPL with readline support, history persistence, and variables.
    """

    # History file location
    HISTORY_FILE = Path.home() / ".pg_history"
    WORKSPACE_DIR = Path.home() / ".password_guesser"

    # Maximum history size
    MAX_HISTORY = 1000

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the enhanced REPL."""
        self.config_path = config_path
        self.variables: Dict[str, Any] = {}
        self.objects: Dict[str, Any] = {}
        self.running = True
        self.llm = None
        self.orchestrator = None

        # Ensure workspace directory exists
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize readline
        self._init_readline()

        # Load previous history
        self._load_history()

        # Register exit handler
        atexit.register(self._save_history)

        # Initialize LLM if available
        self._init_llm()

        # Available commands for completion
        self.commands = self._get_commands()

        # Session start time
        self.session_start = datetime.now()

    def _init_readline(self):
        """Initialize readline for tab completion and history navigation."""
        try:
            import readline

            # Set up tab completion
            readline.parse_and_bind("tab: complete")
            readline.set_completer(self._completer)

            # Enable history navigation with up/down arrows
            readline.parse_and_bind("set show-all-if-ambiguous on")
            readline.parse_and_bind("set show-all-if-unmodified on")
            readline.parse_and_bind("set completion-ignore-case on")
            readline.parse_and_bind("set bell-style none")

            # Set history file
            if self.HISTORY_FILE.exists():
                readline.read_history_file(str(self.HISTORY_FILE))

            self.readline = readline

        except ImportError:
            # readline not available (Windows without pyreadline3)
            self.readline = None
            print("[!] readline not available. Install pyreadline3 for tab completion:")
            print("    pip install pyreadline3")

    def _completer(self, text: str, state: int) -> Optional[str]:
        """Tab completion function."""
        # Get current line and buffer
        try:
            import readline
            line = readline.get_line_buffer()
        except:
            line = text

        # Parse the line to get command and arguments
        parts = line.lstrip().split()

        if not parts or len(parts) == 1 and not line.endswith(' '):
            # Completing command name
            matches = [cmd for cmd in self.commands if cmd.startswith(text)]
        else:
            # Completing argument
            cmd = parts[0] if parts else ""
            matches = self._complete_argument(cmd, text, parts)

        if state < len(matches):
            return matches[state]
        return None

    def _complete_argument(self, cmd: str, text: str, parts: List[str]) -> List[str]:
        """Complete arguments based on command context."""
        completions = []

        # File path completion
        if cmd in ['load', 'save', 'import', 'export', 'eval', 'hash', 'encode', 'scan', 'attack', 'run']:
            completions = self._complete_path(text)

        # Variable completion
        elif text.startswith('$'):
            completions = ['$' + name for name in self.variables.keys() if name.startswith(text[1:])]

        # Command-specific completions
        elif cmd == 'set':
            if len(parts) == 2:
                completions = ['target', 'session', 'port', 'mode', 'goal', 'wordlist']

        elif cmd == 'use':
            completions = ['nmap', 'hydra', 'sqlmap', 'metasploit', 'hashcat', 'john']

        elif cmd == 'show':
            completions = ['options', 'sessions', 'targets', 'variables', 'history', 'status']

        # Filter by current text
        if completions:
            completions = [c for c in completions if c.startswith(text)]

        return completions

    def _complete_path(self, text: str) -> List[str]:
        """Complete file/directory paths."""
        try:
            path = Path(text) if text else Path('.')
            parent = path.parent if path.parent.exists() else Path('.')

            prefix = path.name if path.name else ''

            matches = []
            for item in parent.iterdir():
                if item.name.startswith(prefix):
                    if item.is_dir():
                        matches.append(str(item) + '/')
                    else:
                        matches.append(str(item))

            return matches
        except:
            return []

    def _get_commands(self) -> List[str]:
        """Get list of available commands."""
        return [
            # Core commands
            'help', 'exit', 'quit', 'clear', 'status', 'version',
            # Variable commands
            'set', 'get', 'unset', 'vars', 'ls', 'save', 'load',
            # Execution commands
            'run', 'exec', 'eval', 'hash', 'encode', 'decode', 'crypt',
            # Attack commands
            'scan', 'attack', 'exploit', 'payload', 'shell',
            # Recon commands
            'recon', 'crawl', 'fuzz', 'dns', 'osint', 'whois',
            # Password commands
            'generate', 'wordlist', 'rules', 'crack',
            # Knowledge commands
            'search', 'cve', 'technique', 'knowledge',
            # Session commands
            'session', 'sessions', 'connect', 'disconnect', 'listener',
            # LLM commands
            'llm', 'ask', 'analyze',
            # Utility commands
            'history', 'alias', 'unalias', 'source', 'edit', 'cat', 'cd', 'pwd',
            # Debug commands
            'debug', 'profile', 'time', 'trace',
        ]

    def _load_history(self):
        """Load command history from file."""
        if self.HISTORY_FILE.exists():
            try:
                # readline handles this in _init_readline
                pass
            except Exception as e:
                print(f"[!] Could not load history: {e}")

    def _save_history(self):
        """Save command history to file."""
        if self.readline:
            try:
                # Truncate history to max size
                self.readline.set_history_length(self.MAX_HISTORY)
                self.readline.write_history_file(str(self.HISTORY_FILE))
            except Exception:
                pass

    def _init_llm(self):
        """Initialize LLM provider if configured."""
        try:
            from models.llm_provider import get_provider, LLMConfig
            import yaml

            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    cfg = yaml.safe_load(f)
                llm_cfg = cfg.get('llm', {})
                if llm_cfg.get('api_key') and llm_cfg.get('api_key') != 'YOUR_DEEPSEEK_API_KEY':
                    config = LLMConfig(
                        provider=llm_cfg.get('provider', 'deepseek'),
                        model=llm_cfg.get('model', 'deepseek-chat'),
                        api_key=llm_cfg.get('api_key'),
                        api_base=llm_cfg.get('api_base', 'https://api.deepseek.com/v1'),
                    )
                    self.llm = get_provider(config)
        except Exception:
            pass

    def run(self):
        """Run the interactive REPL."""
        self._print_banner()

        while self.running:
            try:
                # Get input with prompt
                line = self._get_input()

                if not line or line.isspace():
                    continue

                # Add to history
                if self.readline:
                    self.readline.add_history(line)

                # Process the command
                self._process_command(line)

            except KeyboardInterrupt:
                print("\n[!] Use 'exit' to quit")
            except EOFError:
                print("\n[+] Goodbye!")
                break
            except Exception as e:
                print(f"[!] Error: {e}")

        # Save history on exit
        self._save_history()

    def _get_input(self) -> str:
        """Get input with appropriate prompt."""
        # Build prompt with context
        target = self.variables.get('target', '')
        if target:
            prompt = f"pg({target})> "
        else:
            prompt = "pg> "

        return input(prompt).strip()

    def _print_banner(self):
        """Print welcome banner."""
        print("\n" + "=" * 60)
        print("  Password Guesser Interactive Shell v2.0")
        print("  Type 'help' for commands, 'exit' to quit")
        print("  Tab completion enabled, history saved to ~/.pg_history")
        print("=" * 60)

        if self.llm:
            print("[+] LLM provider initialized")
        print()

    def _process_command(self, line: str):
        """Process a command line."""
        # Handle variable substitution
        line = self._substitute_variables(line)

        # Parse command
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"[!] Parse error: {e}")
            return

        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:]

        # Dispatch to command handler
        handler = getattr(self, f'_cmd_{cmd}', None)
        if handler:
            handler(args)
        else:
            # Try external command
            self._cmd_external(cmd, args)

    def _substitute_variables(self, line: str) -> str:
        """Substitute $var with variable values."""
        import re

        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.variables:
                return str(self.variables[var_name])
            return match.group(0)

        return re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', replace_var, line)

    # ==================== Command Handlers ====================

    def _cmd_help(self, args: List[str]):
        """Show help."""
        if args:
            self._show_command_help(args[0])
        else:
            self._show_general_help()

    def _show_general_help(self):
        """Show general help message."""
        print("""
Core Commands:
  help [cmd]       Show help for command
  exit, quit       Exit the shell
  clear            Clear screen
  version          Show version info
  status           Show system status

Variable Commands:
  set <name> <value>   Set a variable
  get <name>           Get variable value
  unset <name>         Delete a variable
  vars, ls             List all variables
  save <file>          Save variables to file
  load <file>          Load variables from file

Execution Commands:
  run <cmd> [args]     Run a CLI subcommand
  exec <file>          Execute commands from file
  eval <password>      Evaluate password strength
  time <cmd>           Time command execution

Attack Commands:
  scan <target>        Scan target
  attack <target>      Launch attack
  exploit <cve>        Search exploit
  payload <type>       Generate payload

Recon Commands:
  recon <target>       Full reconnaissance
  crawl <url>          Web crawler
  fuzz <url>           Fuzz target
  dns <domain>         DNS enumeration

Password Commands:
  generate [n]         Generate passwords
  wordlist <file>      Generate wordlist
  crack <hash>         Attempt to crack hash

Utility Commands:
  hash <text>          Calculate hash
  encode <text>        Encode text
  decode <text>        Decode text
  history [n]          Show command history
  alias <name> <cmd>   Create alias

Debug Commands:
  debug <cmd>          Debug mode
  profile <cmd>        Profile command
  trace <cmd>          Trace execution

LLM Commands:
  llm <prompt>         Ask LLM
  ask <question>       Alias for llm
  analyze <target>     AI-powered analysis
""")

    def _show_command_help(self, cmd: str):
        """Show help for specific command."""
        help_texts = {
            'set': "set <name> <value> - Set a variable. Variables can be used with $ prefix.",
            'get': "get <name> - Get the value of a variable.",
            'vars': "vars - List all defined variables.",
            'run': "run <command> [args...] - Run any CLI subcommand.",
            'scan': "scan <target> [--ports <range>] [--type <type>] - Scan a target.",
            'attack': "attack <target> [--mode <mode>] [--goal <goal>] - Launch attack.",
            'llm': "llm <prompt> - Send prompt to LLM provider.",
            'history': "history [n] - Show last n commands (default 20).",
        }
        print(help_texts.get(cmd, f"No help available for '{cmd}'"))

    def _cmd_exit(self, args: List[str]):
        """Exit the REPL."""
        self.running = False
        print("[+] Goodbye!")

    _cmd_quit = _cmd_exit

    def _cmd_clear(self, args: List[str]):
        """Clear the screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def _cmd_version(self, args: List[str]):
        """Show version."""
        print("Password Guesser CLI v2.0.0")
        print(f"Python {sys.version.split()[0]}")
        print(f"Session started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")

    def _cmd_status(self, args: List[str]):
        """Show system status."""
        print(f"\nSession Status:")
        print(f"  Started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Variables: {len(self.variables)}")
        print(f"  LLM: {'Enabled' if self.llm else 'Disabled'}")
        if self.variables:
            print(f"\nActive Variables:")
            for name, value in self.variables.items():
                print(f"  ${name} = {value}")

    def _cmd_set(self, args: List[str]):
        """Set a variable."""
        if len(args) < 2:
            print("Usage: set <name> <value>")
            return

        name = args[0]
        value = ' '.join(args[1:])
        self.variables[name] = value
        print(f"[+] ${name} = {value}")

    def _cmd_get(self, args: List[str]):
        """Get a variable value."""
        if not args:
            print("Usage: get <name>")
            return

        name = args[0]
        if name in self.variables:
            print(self.variables[name])
        else:
            print(f"[!] Variable '${name}' not found")

    def _cmd_unset(self, args: List[str]):
        """Delete a variable."""
        if not args:
            print("Usage: unset <name>")
            return

        name = args[0]
        if name in self.variables:
            del self.variables[name]
            print(f"[+] Variable '${name}' removed")
        else:
            print(f"[!] Variable '${name}' not found")

    def _cmd_vars(self, args: List[str]):
        """List all variables."""
        _cmd_ls = _cmd_vars  # Alias
        if not self.variables:
            print("No variables defined")
            return

        print("\nVariables:")
        for name, value in self.variables.items():
            print(f"  ${name:<15} = {value}")
        print()

    def _cmd_ls(self, args: List[str]):
        """Alias for vars."""
        self._cmd_vars(args)

    def _cmd_save(self, args: List[str]):
        """Save variables to file."""
        if not args:
            filepath = self.WORKSPACE_DIR / "variables.json"
        else:
            filepath = Path(args[0])

        with open(filepath, 'w') as f:
            json.dump(self.variables, f, indent=2)

        print(f"[+] Saved {len(self.variables)} variables to {filepath}")

    def _cmd_load(self, args: List[str]):
        """Load variables from file."""
        if not args:
            filepath = self.WORKSPACE_DIR / "variables.json"
        else:
            filepath = Path(args[0])

        if not filepath.exists():
            print(f"[!] File not found: {filepath}")
            return

        with open(filepath, 'r') as f:
            loaded = json.load(f)

        self.variables.update(loaded)
        print(f"[+] Loaded {len(loaded)} variables from {filepath}")

    def _cmd_run(self, args: List[str]):
        """Run a CLI subcommand."""
        if not args:
            print("Usage: run <command> [args...]")
            return

        # Import and call the CLI
        import subprocess
        cmd = [sys.executable, "password_guesser/cli.py"] + args

        result = subprocess.run(cmd, capture_output=False)
        return result.returncode

    def _cmd_exec(self, args: List[str]):
        """Execute commands from file."""
        if not args:
            print("Usage: exec <file>")
            return

        filepath = Path(args[0])
        if not filepath.exists():
            print(f"[!] File not found: {filepath}")
            return

        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    print(f"pg> {line}")
                    self._process_command(line)

    def _cmd_eval(self, args: List[str]):
        """Evaluate password strength."""
        if not args:
            pwd = input("Enter password: ").strip()
        else:
            pwd = args[0]

        # Import evaluation function
        from password_guesser.cli import _evaluate_password_cli
        _evaluate_password_cli(pwd, detailed=True)

    def _cmd_hash(self, args: List[str]):
        """Calculate hash values."""
        if not args:
            text = input("Enter text: ").strip()
        else:
            text = ' '.join(args)

        from password_guesser.cli import _print_hashes
        _print_hashes(text)

    def _cmd_encode(self, args: List[str]):
        """Encode text."""
        if len(args) < 2:
            print("Usage: encode <text> <method>")
            return

        from password_guesser.cli import _encode_text
        _encode_text(args[0], args[1])

    def _cmd_decode(self, args: List[str]):
        """Decode text."""
        if len(args) < 2:
            print("Usage: decode <text> <method>")
            return

        from password_guesser.cli import _decode_text
        _decode_text(args[0], args[1])

    def _cmd_history(self, args: List[str]):
        """Show command history."""
        if not self.readline:
            print("[!] History not available")
            return

        n = int(args[0]) if args else 20
        history_len = self.readline.get_current_history_length()

        start = max(0, history_len - n)
        print(f"\nCommand History (last {min(n, history_len)}):\n")

        for i in range(start, history_len):
            item = self.readline.get_history_item(i + 1)
            print(f"  {i - start + 1:4d}. {item}")
        print()

    def _cmd_llm(self, args: List[str]):
        """Send prompt to LLM."""
        if not self.llm:
            print("[!] LLM not configured. Set API key in config.yaml")
            return

        if not args:
            prompt = input("Prompt: ").strip()
        else:
            prompt = ' '.join(args)

        print("\n[LLM] Thinking...")
        try:
            response = self.llm.call([{"role": "user", "content": prompt}])
            print(f"\n{response.content if hasattr(response, 'content') else response}\n")
        except Exception as e:
            print(f"[!] LLM error: {e}")

    _cmd_ask = _cmd_llm

    def _cmd_time(self, args: List[str]):
        """Time command execution."""
        if not args:
            print("Usage: time <command> [args...]")
            return

        import time
        start = time.time()

        cmd = args[0]
        cmd_args = args[1:]

        handler = getattr(self, f'_cmd_{cmd}', None)
        if handler:
            handler(cmd_args)
        else:
            self._cmd_external(cmd, cmd_args)

        elapsed = time.time() - start
        print(f"\n[Time] {elapsed:.3f} seconds")

    def _cmd_debug(self, args: List[str]):
        """Debug command execution."""
        if not args:
            print("Usage: debug <command> [args...]")
            return

        import pdb
        pdb.set_trace()

        cmd = args[0]
        cmd_args = args[1:]

        handler = getattr(self, f'_cmd_{cmd}', None)
        if handler:
            handler(cmd_args)

    def _cmd_profile(self, args: List[str]):
        """Profile command execution."""
        if not args:
            print("Usage: profile <command> [args...]")
            return

        import cProfile
        import pstats
        from io import StringIO

        profiler = cProfile.Profile()
        profiler.enable()

        cmd = args[0]
        cmd_args = args[1:]

        handler = getattr(self, f'_cmd_{cmd}', None)
        if handler:
            handler(cmd_args)

        profiler.disable()

        s = StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats(20)

        print("\n--- Profile Results ---\n")
        print(s.getvalue())

    def _cmd_external(self, cmd: str, args: List[str]):
        """Handle unknown command - try to run as CLI subcommand."""
        import subprocess
        full_cmd = [sys.executable, "password_guesser/cli.py", cmd] + args

        try:
            result = subprocess.run(full_cmd, capture_output=False)
            if result.returncode != 0:
                print(f"[!] Command '{cmd}' failed with exit code {result.returncode}")
        except FileNotFoundError:
            print(f"[!] Unknown command: {cmd}. Type 'help' for available commands.")


def run_interactive(config_path: str = "config.yaml"):
    """Entry point for interactive mode."""
    repl = EnhancedREPL(config_path)
    repl.run()


if __name__ == "__main__":
    run_interactive()
