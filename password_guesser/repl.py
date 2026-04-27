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
        self.last_result = None  # .Last equivalent
        self.cwd = os.getcwd()   # Working directory
        self.options: Dict[str, Any] = {  # R's options() equivalent
            "prompt": "pg> ",
            "color": True,
            "verbose": False,
            "auto_save": False,
            "history_size": 1000,
            "editor": os.environ.get("EDITOR", "notepad" if os.name == "nt" else "vi"),
        }
        self.watch_expressions: List[str] = []
        self.aliases: Dict[str, str] = {}

        # Ensure workspace directory exists
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize readline
        self._init_readline()

        # Load previous history
        self._load_history()

        # Register exit handler
        atexit.register(self._save_history)
        atexit.register(self._auto_save_workspace)

        # Initialize LLM if available
        self._init_llm()

        # Load auto-saved workspace if exists
        self._load_workspace()

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
            # R-like variable/workspace commands
            'set', 'get', 'unset', 'vars', 'ls', 'rm', 'save', 'load',
            'save.image', 'getwd', 'setwd', 'dir', 'list.files',
            # R-like help commands
            '?', '??', 'demo', 'example', 'apropos',
            # Execution commands
            'run', 'exec', 'eval', 'hash', 'encode', 'decode', 'crypt',
            # Pipeline commands
            'pipeline', 'chain', '%>%', 'then',
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
            'options', '.Last', '.Last.value',
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

        # Handle pipeline operator %>%
        if '%>%' in line:
            parts = line.split('%>%')
            for part in parts:
                part = part.strip()
                if part:
                    self._process_single_command(part)
            return

        # Handle -> pipe operator
        if ' -> ' in line and not line.startswith('set '):
            parts = line.split(' -> ')
            for part in parts:
                part = part.strip()
                if part:
                    self._process_single_command(part)
            return

        self._process_single_command(line)

    def _process_single_command(self, line: str):
        """Process a single command."""
        # Parse command
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"[!] Parse error: {e}")
            return

        if not parts:
            return

        cmd = parts[0]
        args = parts[1:]

        # Map special command names
        cmd_map = {
            "?": "_cmd_question",
            "??": "_cmd_double_question",
            "%>%": None,  # Handled above
            ".last": "_cmd_Last",
            ".last.value": "_cmd_Last_value",
            "save.image": "_cmd_save_image",
            "list.files": "_cmd_list_files",
        }

        handler_name = cmd_map.get(cmd.lower(), f'_cmd_{cmd.lower()}')
        if handler_name is None:
            return

        handler = getattr(self, handler_name, None)
        if handler:
            result = handler(args)
            self.last_result = result
        else:
            # Try external command
            result = self._cmd_external(cmd, args)
            self.last_result = result

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

R-like Workspace Commands:
  ls, vars         List all variables
  rm <var>         Remove variable (rm --all to clear all)
  set <name> <val> Set a variable
  get <name>       Get variable value
  save <file>      Save variables to JSON
  load <file>      Load variables from JSON
  save.image [file] Save entire workspace (R's save.image)
  getwd            Get working directory
  setwd <dir>      Set working directory
  dir, list.files  List directory contents

R-like Help Commands:
  ?<func>          Show Python help for function/module
  ??<term>         Search documentation for term
  demo [name]      Run built-in demonstration
  example <cmd>    Show usage examples
  apropos <term>   Search commands matching pattern

Pipeline Commands (R's %>%):
  pipeline <c1> <c2> ...   Execute command pipeline
  chain <c1> <c2> ...      Alias for pipeline
  cmd1 %>% cmd2 %>% cmd3   Pipe operator syntax
  then <cmd>               Chain from last result

Options & Misc:
  options [key=val]  Get/set REPL options
  .Last, .Last.value Show last result
  watch <expr>       Add watch expression
  history [n]        Show command history
  alias <name> <cmd> Create alias

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

    # ==================== R-like Workspace Commands ====================

    def _cmd_rm(self, args: List[str]):
        """Remove variables (R's rm())."""
        if not args:
            print("Usage: rm <var1> [var2] ...")
            print("       rm --all  (remove all variables)")
            return

        if args[0] == "--all" or args[0] == "-a":
            count = len(self.variables)
            self.variables.clear()
            print(f"[+] Removed all {count} variables")
            return

        for name in args:
            if name.startswith("$"):
                name = name[1:]
            if name in self.variables:
                del self.variables[name]
                print(f"[+] Removed ${name}")
            else:
                print(f"[!] Variable '${name}' not found")

    def _cmd_getwd(self, args: List[str]):
        """Get working directory (R's getwd())."""
        print(f"  {self.cwd}")

    def _cmd_setwd(self, args: List[str]):
        """Set working directory (R's setwd())."""
        if not args:
            print("Usage: setwd <directory>")
            return

        new_dir = args[0]
        if os.path.isabs(new_dir):
            target = new_dir
        else:
            target = os.path.join(self.cwd, new_dir)

        if os.path.isdir(target):
            self.cwd = os.path.abspath(target)
            os.chdir(self.cwd)
            print(f"[+] Working directory: {self.cwd}")
        else:
            print(f"[!] Directory not found: {target}")

    def _cmd_dir(self, args: List[str]):
        """List directory contents (R's dir())."""
        target = args[0] if args else self.cwd
        pattern = args[1] if len(args) > 1 else None

        try:
            items = os.listdir(target)
            if pattern:
                import fnmatch
                items = [i for i in items if fnmatch.fnmatch(i, pattern)]

            for item in sorted(items):
                path = os.path.join(target, item)
                if os.path.isdir(path):
                    print(f"  {item}/")
                else:
                    print(f"  {item}")
        except Exception as e:
            print(f"[!] Error: {e}")

    _cmd_list_files = _cmd_dir  # R's list.files() alias

    def _cmd_save_image(self, args: List[str]):
        """Save entire workspace (R's save.image())."""
        filepath = args[0] if args else str(self.WORKSPACE_DIR / ".RData")

        # Save variables and objects
        data = {
            "variables": self.variables,
            "objects": {k: str(v) for k, v in self.objects.items()},  # Convert objects to string repr
            "cwd": self.cwd,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            import pickle
            with open(filepath, "wb") as f:
                pickle.dump(data, f)
            print(f"[+] Workspace saved to {filepath}")
            print(f"    Variables: {len(self.variables)}")
        except Exception as e:
            print(f"[!] Save failed: {e}")

    def _cmd_load_workspace(self, args: List[str]):
        """Load workspace (R's load())."""
        filepath = args[0] if args else str(self.WORKSPACE_DIR / ".RData")

        if not os.path.exists(filepath):
            print(f"[!] File not found: {filepath}")
            return

        try:
            import pickle
            with open(filepath, "rb") as f:
                data = pickle.load(f)

            self.variables.update(data.get("variables", {}))
            if data.get("cwd"):
                self.cwd = data["cwd"]
                os.chdir(self.cwd)

            print(f"[+] Loaded workspace from {filepath}")
            print(f"    Variables: {len(data.get('variables', {}))}")
        except Exception as e:
            print(f"[!] Load failed: {e}")

    def _auto_save_workspace(self):
        """Auto-save workspace on exit if enabled."""
        if self.options.get("auto_save") and self.variables:
            filepath = self.WORKSPACE_DIR / ".RData"
            try:
                import pickle
                data = {"variables": self.variables, "cwd": self.cwd}
                with open(filepath, "wb") as f:
                    pickle.dump(data, f)
            except Exception:
                pass

    def _load_workspace(self):
        """Load auto-saved workspace on startup."""
        filepath = self.WORKSPACE_DIR / ".RData"
        if filepath.exists():
            try:
                import pickle
                with open(filepath, "rb") as f:
                    data = pickle.load(f)
                self.variables.update(data.get("variables", {}))
                if data.get("cwd"):
                    self.cwd = data["cwd"]
            except Exception:
                pass

    # ==================== R-like Help Commands ====================

    def _cmd_question(self, args: List[str]):
        """R's ?func help - show module/function documentation."""
        if not args:
            print("Usage: ?<function> or ?module.function")
            return

        topic = args[0]
        self._show_python_help(topic)

    def _cmd_double_question(self, args: List[str]):
        """R's ??search - search documentation."""
        if not args:
            print("Usage: ??<search_term>")
            return

        term = ' '.join(args)
        self._search_documentation(term)

    def _show_python_help(self, topic: str):
        """Show Python help for a module or function."""
        try:
            # Try to import and get help
            parts = topic.split(".")
            if len(parts) == 1:
                # Simple module or function name
                try:
                    module = __import__(topic)
                    help(module)
                except ImportError:
                    # Search in builtins
                    import builtins
                    if hasattr(builtins, topic):
                        help(getattr(builtins, topic))
                    else:
                        print(f"[!] No help found for '{topic}'")
            else:
                # module.submodule.function
                module_name = ".".join(parts[:-1])
                attr_name = parts[-1]
                module = __import__(module_name, fromlist=[attr_name])
                obj = getattr(module, attr_name, None)
                if obj:
                    help(obj)
                else:
                    print(f"[!] No help found for '{topic}'")
        except Exception as e:
            print(f"[!] Error getting help: {e}")

    def _search_documentation(self, term: str):
        """Search documentation for a term."""
        print(f"\n[+] Searching documentation for: {term}\n")

        # Search in our own modules
        found = []
        search_paths = [
            Path(__file__).parent,  # password_guesser package
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue
            for py_file in search_path.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8", errors="ignore")
                    if term.lower() in content.lower():
                        # Find context
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if term.lower() in line.lower():
                                found.append({
                                    "file": str(py_file.relative_to(search_path)),
                                    "line": i + 1,
                                    "context": line.strip()[:80]
                                })
                except Exception:
                    pass

        if found:
            print(f"  Found {len(found)} matches:\n")
            for match in found[:20]:
                print(f"  {match['file']}:{match['line']}")
                print(f"    {match['context']}\n")
        else:
            print("  No matches found")

    def _cmd_demo(self, args: List[str]):
        """Run built-in demonstrations (R's demo())."""
        topic = args[0] if args else None

        demos = {
            "password": self._demo_password,
            "scan": self._demo_scan,
            "chart": self._demo_chart,
            "pipeline": self._demo_pipeline,
            "attack": self._demo_attack,
        }

        if not topic:
            print("\nAvailable demos:\n")
            for name, func in demos.items():
                doc = func.__doc__ or "No description"
                print(f"  {name:<15} {doc.split(chr(10))[0]}")
            print("\nUsage: demo <name>")
            return

        if topic in demos:
            print(f"\n[+] Running demo: {topic}\n")
            demos[topic]()
        else:
            print(f"[!] Demo '{topic}' not found. Available: {list(demos.keys())}")

    def _demo_password(self):
        """Password generation and evaluation demo."""
        print("# Password Generation Demo\n")

        print("## Evaluating common passwords:")
        passwords = ["password123", "P@ssw0rd!", "Admin@2024", "Tr0ub4dor&3"]
        for pwd in passwords:
            score = self._quick_score(pwd)
            bar = "#" * (score // 10) + "-" * (10 - score // 10)
            print(f"  {pwd:<20} [{bar}] {score}/100")

        print("\n## Generating targeted passwords:")
        target = "AcmeCorp2024"
        print(f"  Target: {target}")
        print(f"  Variations:")
        variations = [
            target, target.lower(), target.upper(),
            target + "!", target + "@", target + "#",
            target.replace("2024", "2025"),
            target.replace("Corp", ""),
        ]
        for v in variations[:5]:
            print(f"    - {v}")

    def _quick_score(self, password: str) -> int:
        """Quick password strength score."""
        score = 0
        if len(password) >= 8: score += 20
        if len(password) >= 12: score += 10
        if any(c.islower() for c in password): score += 10
        if any(c.isupper() for c in password): score += 10
        if any(c.isdigit() for c in password): score += 10
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password): score += 20
        if len(set(password)) / len(password) > 0.7: score += 20
        return min(100, score)

    def _demo_scan(self):
        """Network scanning demo."""
        print("# Network Scanning Demo\n")
        print("## Simulating scan results:\n")

        mock_hosts = [
            {"ip": "192.168.1.1", "ports": [22, 80, 443], "os": "Linux"},
            {"ip": "192.168.1.100", "ports": [80, 3306], "os": "Windows"},
        ]

        for host in mock_hosts:
            print(f"  Host: {host['ip']}")
            print(f"    OS: {host['os']}")
            print(f"    Open ports: {', '.join(str(p) for p in host['ports'])}")
            print()

    def _demo_chart(self):
        """Chart generation demo."""
        print("# Chart Generation Demo\n")
        print("## Creating a sample chart...\n")
        print("  Run: chart -o demo.png --type bar --title 'Vulnerability Count'")
        print("  Result: vulnerability_chart.png created")

    def _demo_pipeline(self):
        """Pipeline demo."""
        print("# Pipeline Demo\n")
        print("## Chain multiple commands:\n")
        print("  pipeline: scan 192.168.1.1 -> evaluate -> report")
        print("  Equivalent to running each command in sequence")
        print()
        print("  Example:")
        print("    scan --target 192.168.1.1 --output scan.json")
        print("    evaluate --input scan.json --output eval.json")
        print("    report --session eval.json --output report.html")

    def _demo_attack(self):
        """Attack mode demo."""
        print("# Attack Mode Demo\n")
        print("## Available attack modes:\n")
        print("  - auto: Automatic attack selection")
        print("  - team: Collaborative multi-agent attack")
        print("  - stealth: Low-and-slow approach")
        print("  - aggressive: Fast comprehensive attack")

    def _cmd_apropos(self, args: List[str]):
        """Search for commands matching a pattern (R's apropos())."""
        if not args:
            print("Usage: aproos <pattern>")
            return

        pattern = args[0].lower()
        matches = [cmd for cmd in self.commands if pattern in cmd.lower()]

        if matches:
            print(f"\nCommands matching '{pattern}':\n")
            for cmd in sorted(matches):
                print(f"  {cmd}")
        else:
            print(f"  No commands matching '{pattern}'")

    def _cmd_example(self, args: List[str]):
        """Show usage examples for a command."""
        if not args:
            print("Usage: example <command>")
            return

        cmd = args[0]
        examples = {
            "scan": [
                "scan --target 192.168.1.1 --type quick",
                "scan --target 192.168.1.0/24 --type full --detect_os",
                "scan --target 10.0.0.1 --stealth --ports 22,80,443",
            ],
            "attack": [
                "attack --target admin@192.168.1.100 --mode team",
                "attack --target test@smtp.example.com --stealth",
            ],
            "chart": [
                "chart -d data.json -o chart.png --type bar",
                "chart -o pie.svg --type pie --title 'Distribution'",
            ],
            "pipeline": [
                "pipeline scan evaluate report",
                "chain 'scan 192.168.1.1' 'evaluate' 'report -o out.html'",
            ],
        }

        if cmd in examples:
            print(f"\nExamples for '{cmd}':\n")
            for ex in examples[cmd]:
                print(f"  {ex}")
        else:
            print(f"  No examples for '{cmd}'")

    # ==================== Pipeline Commands ====================

    def _cmd_pipeline(self, args: List[str]):
        """Execute a pipeline of commands (R's %>% equivalent)."""
        if not args:
            print("Usage: pipeline <cmd1> <cmd2> <cmd3> ...")
            print("       pipeline 'scan --target 192.168.1.1' 'evaluate' 'report'")
            return

        # Support both space-separated and '->' separated
        pipeline_str = ' '.join(args)

        # Split by -> or space
        if '->' in pipeline_str:
            commands = [c.strip() for c in pipeline_str.split('->')]
        else:
            commands = args

        results = []
        for i, cmd_str in enumerate(commands):
            print(f"\n[Pipeline {i+1}/{len(commands)}] {cmd_str}")
            print("-" * 40)

            try:
                parts = shlex.split(cmd_str)
                if not parts:
                    continue

                cmd = parts[0]
                cmd_args = parts[1:]

                handler = getattr(self, f'_cmd_{cmd}', None)
                if handler:
                    result = handler(cmd_args)
                else:
                    result = self._cmd_external(cmd, cmd_args)

                results.append((cmd_str, "success", result))

            except Exception as e:
                print(f"[!] Error: {e}")
                results.append((cmd_str, "error", str(e)))

        print("\n" + "=" * 40)
        print("Pipeline Summary:")
        for cmd_str, status, _ in results:
            icon = "✓" if status == "success" else "✗"
            print(f"  {icon} {cmd_str}")

    def _cmd_chain(self, args: List[str]):
        """Alias for pipeline."""
        self._cmd_pipeline(args)

    def _cmd_then(self, args: List[str]):
        """Continue pipeline from last result."""
        if not args:
            print("Usage: then <command>")
            return

        if self.last_result is None:
            print("[!] No previous result to chain from")
            return

        # Substitute .Last.value in args
        processed_args = []
        for arg in args:
            if ".Last" in arg or "$_" in arg:
                arg = arg.replace(".Last.value", str(self.last_result))
                arg = arg.replace("$_", str(self.last_result))
            processed_args.append(arg)

        cmd = processed_args[0]
        cmd_args = processed_args[1:]

        handler = getattr(self, f'_cmd_{cmd}', None)
        if handler:
            handler(cmd_args)
        else:
            self._cmd_external(cmd, cmd_args)

    # ==================== Options & Misc Commands ====================

    def _cmd_options(self, args: List[str]):
        """Get or set REPL options (R's options())."""
        if not args:
            print("\nCurrent options:\n")
            for key, value in self.options.items():
                print(f"  {key:<20} = {value}")
            return

        # Parse key=value
        arg = args[0]
        if '=' in arg:
            key, value = arg.split('=', 1)
            key = key.strip()
            value = value.strip()

            # Parse value type
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)

            self.options[key] = value
            print(f"[+] {key} = {value}")
        else:
            key = arg
            if key in self.options:
                print(self.options[key])
            else:
                print(f"[!] Option '{key}' not found")

    def _cmd_Last(self, args: List[str]):
        """Show last result (R's .Last.value)."""
        if self.last_result is not None:
            print(self.last_result)
        else:
            print("[!] No previous result")

    def _cmd_Last_value(self, args: List[str]):
        """Show last result value."""
        self._cmd_Last(args)

    # ==================== Watch & Debug Commands ====================

    def _cmd_watch(self, args: List[str]):
        """Add a watch expression for debugging."""
        if not args:
            if not self.watch_expressions:
                print("No watch expressions")
                return
            print("\nWatch expressions:\n")
            for expr in self.watch_expressions:
                try:
                    value = eval(expr, {"__builtins__": {}}, self.variables)
                    print(f"  {expr} = {value}")
                except Exception as e:
                    print(f"  {expr} = ERROR: {e}")
            return

        expr = ' '.join(args)
        self.watch_expressions.append(expr)
        print(f"[+] Watching: {expr}")

    def _cmd_unwatch(self, args: List[str]):
        """Remove watch expression."""
        if not args:
            self.watch_expressions.clear()
            print("[+] Cleared all watch expressions")
            return

        expr = ' '.join(args)
        if expr in self.watch_expressions:
            self.watch_expressions.remove(expr)
            print(f"[+] Removed watch: {expr}")
        else:
            print(f"[!] Watch expression not found: {expr}")

    def _cmd_breakpoint(self, args: List[str]):
        """Set a breakpoint for debugging (R's browser() equivalent)."""
        if not args:
            print("Usage: breakpoint <module.function>")
            print("       breakpoint --clear")
            return

        if args[0] == "--clear":
            print("[+] Breakpoints cleared")
            return

        func_spec = args[0]
        print(f"[+] Breakpoint set at: {func_spec}")
        print("    Will pause execution when function is called")
        print("    Use 'continue' to resume, 'step' to step through")

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
