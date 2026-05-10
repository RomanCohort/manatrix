"""
Manatrix Studio - RStudio-like IDE

Provides a full-featured web-based IDE with RStudio-style panels:
- Source Editor (Monaco)
- Console/Terminal (Xterm.js + WebSocket bridge)
- File Browser
- Variables/Environment
- History
- Output/Plots

Usage:
    manatrix studio --port 8500
    # Then open http://localhost:8500/studio
"""

import os
import sys
import json
import asyncio
import subprocess
import threading
import uuid
import time
import re
import shlex
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Set
from collections import OrderedDict

# Add project root to path
# In Electron packaged mode, backend modules are in backend/ directory
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)

# Check if running from Electron packaged mode (backend/ subdir)
if os.path.basename(_parent_dir) == 'backend':
    _project_root = _parent_dir  # packaged: backend/ contains manatrix, models, etc.
    sys.path.insert(0, _project_root)
else:
    _project_root = _parent_dir  # dev: web/ is inside the project root
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.routing import Route, WebSocketRoute
from starlette.responses import RedirectResponse

app_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(app_dir, "static")

# SECURITY: Get workspace root from environment, default to app directory
WORKSPACE_ROOT = os.environ.get("STUDIO_WORKSPACE_ROOT", app_dir)

def _is_safe_path(path: str) -> bool:
    """Check if path is within allowed workspace root. Prevents path traversal attacks."""
    try:
        # Resolve the path and check it's within workspace
        abs_path = os.path.realpath(os.path.join(WORKSPACE_ROOT, path))
        workspace_real = os.path.realpath(WORKSPACE_ROOT)
        return abs_path.startswith(workspace_real + os.sep) or abs_path == workspace_real
    except (ValueError, OSError):
        return False

def _check_api_key(request: Request) -> bool:
    """Check if request has valid API key. Returns True if valid or auth disabled."""
    auth_disabled = os.environ.get("STUDIO_AUTH_DISABLED", "false").lower() == "true"
    if auth_disabled:
        return True
    expected_key = os.environ.get("STUDIO_API_KEY", "")
    if not expected_key:
        return True  # No key configured, allow all
    provided_key = request.headers.get("X-API-Key", "")
    return provided_key == expected_key

# Create FastAPI app for studio
studio_app = FastAPI(
    title="Manatrix Studio",
    description="RStudio-like IDE for Manatrix CLI",
    version="1.0.0",
)

# Mount static files
try:
    studio_app.mount("/static", StaticFiles(directory=static_dir), name="studio_static")
except Exception:
    pass

# Redirect /studio -> /
from fastapi.responses import RedirectResponse

@studio_app.get("/studio")
async def redirect_studio():
    return RedirectResponse(url="/")

@studio_app.get("/studio/")
async def redirect_studio_slash():
    return RedirectResponse(url="/")


# =============================================================================
# Session Management
# =============================================================================

class StudioSession:
    """Manages a single studio session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.variables = {}      # name -> value
        self.last_result = None   # .Last.value
        self.history = []         # command history
        self.cwd = os.getcwd()
        self.start_time = time.time()
        self.process: Optional[subprocess.Popen] = None
        self.output_lock = threading.Lock()
        self.output_buffer = ""

    def add_history(self, cmd: str):
        """Add command to history."""
        if cmd.strip() and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
            if len(self.history) > 1000:
                self.history = self.history[-1000:]

    def set_var(self, name: str, value: Any):
        """Set a variable."""
        self.variables[name] = {
            "value": str(value)[:100],
            "type": type(value).__name__,
            "updated": datetime.now().isoformat(),
        }

    def get_state(self) -> dict:
        """Get session state for environment panel."""
        return {
            "session_id": self.session_id,
            "variables": self.variables,
            "last_result": str(self.last_result)[:100] if self.last_result else None,
            "history": self.history[-50:],
            "cwd": self.cwd,
            "uptime": time.time() - self.start_time,
        }


# Global session storage
_sessions: Dict[str, StudioSession] = {}
_session_lock = threading.Lock()


def get_session(session_id: str) -> StudioSession:
    """Get or create a session."""
    with _session_lock:
        if session_id not in _sessions:
            _sessions[session_id] = StudioSession(session_id)
        return _sessions[session_id]


def cleanup_session(session_id: str):
    """Clean up a session."""
    with _session_lock:
        if session_id in _sessions:
            sess = _sessions[session_id]
            if sess.process:
                try:
                    sess.process.terminate()
                    sess.process.wait(timeout=2)
                except Exception:
                    pass
            del _sessions[session_id]


# =============================================================================
# WebSocket Connection Manager
# =============================================================================

class StudioConnectionManager:
    """Manages WebSocket connections for studio sessions."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                cleanup_session(session_id)

    async def send(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            dead = set()
            for ws in self.active_connections[session_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self.active_connections[session_id].discard(ws)


manager = StudioConnectionManager()


# =============================================================================
# Command Execution
# =============================================================================

# Store the event loop for thread-safe WebSocket sends
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def _ws_send(ws: WebSocket, data: dict):
    """Thread-safe WebSocket send — schedules send_json on the event loop."""
    if _main_loop is None:
        return
    try:
        future = asyncio.run_coroutine_threadsafe(ws.send_json(data), _main_loop)
        future.result(timeout=5)
    except Exception:
        pass


def run_command_sync(session: StudioSession, command: str, ws: WebSocket):
    """Run a command synchronously and stream output via WebSocket."""
    try:
        # Parse command
        parts = shlex.split(command)
        if not parts:
            return

        # Add to history
        session.add_history(command)

        # Detect special commands
        if parts[0] in ("cd", "setwd"):
            if len(parts) > 1:
                new_dir = os.path.expanduser(parts[1])
                if os.path.isdir(new_dir):
                    os.chdir(new_dir)
                    session.cwd = os.getcwd()
                    _ws_send(ws, {"type": "output", "data": f"Directory: {session.cwd}\n"})
                else:
                    _ws_send(ws, {"type": "error", "data": f"Directory not found: {new_dir}\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] == "getwd":
            _ws_send(ws, {"type": "output", "data": f"{session.cwd}\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] in ("ls", "dir"):
            items = os.listdir(session.cwd)
            output = "\n".join(sorted(items))
            _ws_send(ws, {"type": "output", "data": output + "\n"})
            session.last_result = items
            session.set_var("last_result", items)
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] in ("rm", "del"):
            if "--all" in parts:
                session.variables.clear()
                _ws_send(ws, {"type": "output", "data": "[+] All variables cleared\n"})
            elif len(parts) > 1:
                for name in parts[1:]:
                    if name in session.variables:
                        del session.variables[name]
                        _ws_send(ws, {"type": "output", "data": f"[+] Removed: {name}\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] == "save.image":
            image_file = Path.home() / ".pg_workspace" / f"session_{session.session_id}.json"
            image_file.parent.mkdir(exist_ok=True)
            with open(image_file, 'w') as f:
                json.dump({
                    "variables": session.variables,
                    "history": session.history,
                    "cwd": session.cwd,
                    "last_result": session.last_result,
                }, f, indent=2, default=str)
            _ws_send(ws, {"type": "output", "data": f"[+] Workspace saved: {image_file}\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] == "options":
            if len(parts) > 2 and parts[1] == "set":
                _ws_send(ws, {"type": "output", "data": f"[+] Option set: {parts[2]}\n"})
            else:
                _ws_send(ws, {"type": "output", "data": "Options: prompt, color, width\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] in ("?", "help") and len(parts) > 1:
            cmd_to_help = parts[1]
            help_text = get_help_text(cmd_to_help)
            _ws_send(ws, {"type": "output", "data": help_text + "\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] == "??":  # apropos search
            keyword = " ".join(parts[1:]) if len(parts) > 1 else ""
            results = search_commands(keyword)
            _ws_send(ws, {"type": "output", "data": results + "\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        if parts[0] == "demo":
            result = subprocess.run(
                [sys.executable, "-m", "manatrix.cli", "demo"] + parts[1:],
                capture_output=True, text=True, timeout=30, cwd=session.cwd
            )
            _ws_send(ws, {"type": "output", "data": result.stdout})
            if result.stderr:
                _ws_send(ws, {"type": "error", "data": result.stderr})
            _ws_send(ws, {"type": "done", "returncode": result.returncode, "command": command})
            return

        if parts[0] == ".Last" or (parts[0] == ".Last.value"):
            _ws_send(ws, {"type": "output", "data": f"{session.last_result}\n"})
            _ws_send(ws, {"type": "done", "returncode": 0, "command": command})
            return

        # Default: run via CLI
        # Prefix with manatrix if not already
        if parts[0] == "manatrix":
            cli_args = parts[1:]
        else:
            cli_args = parts

        _ws_send(ws, {"type": "status", "data": f"Running: {' '.join(cli_args)}\n"})

        result = subprocess.run(
            [sys.executable, "-m", "manatrix.cli"] + cli_args,
            capture_output=True, text=True, timeout=120, cwd=session.cwd
        )

        if result.stdout:
            _ws_send(ws, {"type": "output", "data": result.stdout})
        if result.stderr:
            _ws_send(ws, {"type": "error", "data": result.stderr})

        session.last_result = result.stdout
        session.set_var("last_result", result.stdout[:100])

        # Detect if chart was generated
        output_match = re.findall(r'(\S+\.(png|svg|jpg|jpeg|pdf))', result.stdout)
        for img_path, _ in output_match:
            if os.path.exists(img_path):
                _ws_send(ws, {"type": "chart", "data": img_path})

        _ws_send(ws, {"type": "done", "returncode": result.returncode, "command": command})

    except subprocess.TimeoutExpired:
        _ws_send(ws, {"type": "error", "data": "[!] Command timed out\n"})
    except Exception as e:
        _ws_send(ws, {"type": "error", "data": f"[!] Error: {e}\n"})


def run_command_async(session: StudioSession, command: str, ws: WebSocket):
    """Run command in a background thread."""
    thread = threading.Thread(target=run_command_sync, args=(session, command, ws), daemon=True)
    thread.start()


# =============================================================================
# Help & Search
# =============================================================================

KNOWN_COMMANDS = {
    "train": "Train the MAMBA password model",
    "generate": "Generate password candidates",
    "evaluate": "Evaluate password strength",
    "scan": "Network scanning/reconnaissance",
    "attack": "Launch attack mode",
    "pentest": "Run penetration test",
    "web": "Start web interface",
    "interactive": "Launch Kali-style interactive terminal",
    "chart": "Generate charts and visualizations",
    "export": "Export reports to various formats",
    "pipeline": "Execute command pipelines (R's %>% equivalent)",
    "demo": "Run built-in demonstrations",
    "history": "Command history management",
    "alias": "Manage command aliases",
    "theme": "UI theme and colors",
    "backup": "Backup and restore workspace",
    "watch": "Watch command output periodically",
    "cron": "Schedule commands to run",
    "macro": "Create and manage command macros",
    "snippet": "Code snippet manager",
    "quick": "Quick attack templates",
    "cve": "CVE database lookup",
    "attack-pattern": "MITRE ATT&CK pattern lookup",
    "triage": "Vulnerability triage and prioritization",
    "wordlist-stats": "Wordlist statistics",
    "session-replay": "Replay recorded sessions",
    "version": "Show version information",
    "status": "Show system status",
    "config": "Configuration management",
    "hash": "Calculate hash values",
    "encode": "Encode/decode text",
    "report": "Generate pentest report",
    "benchmark": "Run performance benchmarks",
    "knowledge": "Knowledge base operations",
    "llm": "Direct LLM interaction",
    "graph": "Attack graph visualization/export",
    "tools": "Penetration testing tools management",
    "payload": "Generate payloads",
    "reverse-shell": "Reverse shell generator",
    "listener": "Listener management",
    "session": "Session management",
    "dns": "DNS enumeration",
    "osint": "OSINT reconnaissance",
    "rules": "Password rules operations",
    "pcfg": "PCFG password generation",
    "sandbox": "Sandbox execution",
    "evasion": "Evasion techniques",
    "scope": "Scope management",
    "lessons": "Lessons learned management",
}


def get_help_text(command: str) -> str:
    """Get help text for a command."""
    if command in KNOWN_COMMANDS:
        return f"{command}: {KNOWN_COMMANDS[command]}\nRun 'manatrix {command} --help' for details."
    return f"Unknown command: {command}\nRun 'manatrix help' to see all commands."


def search_commands(keyword: str) -> str:
    """Search commands by keyword."""
    if not keyword:
        return "\n".join(f"  {cmd:20} {desc}" for cmd, desc in KNOWN_COMMANDS.items())
    results = [(cmd, desc) for cmd, desc in KNOWN_COMMANDS.items()
               if keyword.lower() in cmd.lower() or keyword.lower() in desc.lower()]
    if results:
        return "\n".join(f"  {cmd:20} {desc}" for cmd, desc in sorted(results))
    return f"No commands found matching '{keyword}'"


# =============================================================================
# WebSocket Endpoint
# =============================================================================

@studio_app.websocket("/terminal/{session_id}")
async def terminal_websocket(websocket: WebSocket, session_id: str):
    """WebSocket terminal - bidirectional CLI bridge."""
    global _main_loop
    _main_loop = asyncio.get_running_loop()

    await manager.connect(session_id, websocket)
    session = get_session(session_id)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "welcome",
            "data": r"""
  ____             ____ _                ____                          _
 |  _ \  ___ _   _ / ___| |__   ___  ___|  _ \ ___ _ __   ___  _ __ __| |
 | | | |/ _ \ | | | |   | '_ \ / _ \/ __| |_) / _ \ '_ \ / _ \| '__/ _` |
 | |_| |  __/ |_| | |___| | | |  __/ (__|  _ <  __/ |_) | (_) | | | (_| |
 |____/ \___|\__, |\____|_| |_|\___|\___|_| \_\___| .__/ \___/|_|  \__,_|
            |___/                                |_|

 Manatrix Studio - Type 'help' for commands, '?' <cmd> for help
 Use Ctrl+Enter to run commands, Ctrl+L to clear
"""
        })

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                msg = {"type": "command", "data": data}

            msg_type = msg.get("type", "command")

            if msg_type == "command":
                command = msg.get("data", "").strip()
                if command:
                    run_command_async(session, command, websocket)

            elif msg_type == "resize":
                # Terminal resize
                await websocket.send_json({"type": "resize_ack", "cols": msg.get("cols"), "rows": msg.get("rows")})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


# =============================================================================
# REST API Endpoints
# =============================================================================

@studio_app.get("/")
async def serve_studio():
    """Serve the main studio HTML page."""
    html_path = os.path.join(static_dir, "studio.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="Studio not found. Please build the studio first.")


@studio_app.get("/api/info")
async def get_info():
    """Get studio info."""
    return {
        "name": "Manatrix Studio",
        "version": "1.0.0",
        "description": "RStudio-like IDE for Manatrix CLI",
        "features": [
            "Console/Terminal with WebSocket bridge",
            "Source Editor with Monaco",
            "File Browser",
            "Variables/Environment panel",
            "Command History",
            "Chart/Plot viewer",
            "R-style commands (? / ?? / demo / ls / rm / save.image)",
            "Pipeline operator (%)%",
            "162+ CLI commands",
            "Jupyter kernel support",
        ],
        "theme": "dark",
        "panels": ["source", "console", "output", "environment", "history", "files"],
    }


@studio_app.get("/api/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get current session state for Environment panel."""
    session = get_session(session_id)
    return session.get_state()


@studio_app.post("/api/session/{session_id}/execute")
async def execute_command(session_id: str, request: Request):
    """Execute a command via REST API."""
    body = await request.json()
    command = body.get("command", "")
    session = get_session(session_id)

    try:
        # Use asyncio subprocess to avoid blocking the event loop
        cmd_args = [sys.executable, "-m", "manatrix.cli"] + shlex.split(command)
        process = await asyncio.create_subprocess_exec(
            *cmd_args,
            cwd=session.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {"stdout": "", "stderr": "Command timed out", "returncode": -1}

        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "returncode": process.returncode,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


@studio_app.get("/api/files")
async def list_files(path: str = ""):
    """List files in workspace."""
    if not path:
        path = os.getcwd()

    abs_path = os.path.abspath(os.path.expanduser(path))

    if not os.path.exists(abs_path):
        return {"error": "Path not found", "path": abs_path}

    items = []
    try:
        for item in sorted(os.listdir(abs_path)):
            item_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(item_path)
            stat = os.stat(item_path)
            items.append({
                "name": item,
                "path": item_path,
                "is_dir": is_dir,
                "size": stat.st_size if not is_dir else 0,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    except PermissionError:
        return {"error": "Permission denied", "path": abs_path, "items": []}

    return {
        "path": abs_path,
        "items": items,
    }


@studio_app.get("/api/files/read")
async def read_file(request: Request, path: str):
    """Read a file for the source editor."""
    # Security: Check path is within workspace
    if not _is_safe_path(path):
        return JSONResponse({"success": False, "error": "Path outside workspace"}, status_code=403)

    abs_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))

    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(abs_path, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot read file: {e}")

    return {
        "path": abs_path,
        "content": content,
        "language": detect_language(abs_path),
    }


@studio_app.post("/api/files/save")
async def save_file(request: Request):
    """Save a file from the source editor."""
    body = await request.json()
    path = body.get("path", "")
    content = body.get("content", "")

    # Security: Check path is within workspace
    if not _is_safe_path(path):
        return JSONResponse({"success": False, "error": "Path outside workspace"}, status_code=403)

    abs_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path))

    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/history")
async def get_history(session_id: str = "default", limit: int = 50):
    """Get command history."""
    session = get_session(session_id)
    return {
        "history": session.history[-limit:],
    }


@studio_app.get("/api/completions")
async def get_completions(prefix: str = ""):
    """Get command completions for tab completion."""
    if not prefix:
        return {"completions": list(KNOWN_COMMANDS.keys())}

    completions = [cmd for cmd in KNOWN_COMMANDS.keys() if cmd.startswith(prefix)]
    return {"completions": completions}


@studio_app.post("/api/search")
async def search_files(request: Request):
    """Search for text across files in the workspace."""
    body = await request.json()
    query = body.get("query", "")
    pattern = body.get("pattern", "")
    path = body.get("path", os.getcwd())
    case_sensitive = body.get("case_sensitive", False)
    use_regex = body.get("use_regex", False)
    max_results = body.get("max_results", 500)

    search_query = query or pattern
    if not search_query:
        return {"success": False, "error": "No search query provided"}

    abs_path = os.path.abspath(os.path.expanduser(path))
    results = []
    files_searched = 0
    files_ignored = {'.git', '__pycache__', '.pytest_cache', 'node_modules',
                     '.venv', 'venv', '.tox', '.eggs', 'build', 'dist', '*.pyc'}

    try:
        flags = 0 if use_regex else re.IGNORECASE
        if case_sensitive and not use_regex:
            flags = 0

        regex = re.compile(search_query, flags) if use_regex else re.compile(re.escape(search_query), flags)

        for root, dirs, files in os.walk(abs_path):
            # Filter ignored directories
            dirs[:] = [d for d in dirs if d not in files_ignored and not d.startswith('.')]

            for filename in files:
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                try:
                    stat = os.stat(filepath)
                    if stat.st_size > 5 * 1024 * 1024:  # Skip files > 5MB
                        continue

                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    except Exception:
                        continue

                    files_searched += 1
                    lines = content.split('\n')

                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            results.append({
                                "file": filepath,
                                "relative_path": os.path.relpath(filepath, abs_path),
                                "line": line_num,
                                "content": line.rstrip(),
                                "match": regex.search(line).group(0),
                            })
                            if len(results) >= max_results:
                                break
                except Exception:
                    continue

                if len(results) >= max_results:
                    break

            if len(results) >= max_results:
                break

        return {
            "success": True,
            "query": search_query,
            "path": abs_path,
            "results": results[:max_results],
            "total": len(results),
            "files_searched": files_searched,
        }
    except re.error as e:
        return {"success": False, "error": f"Invalid regex: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/search/replace")
async def replace_in_files(request: Request):
    """Replace text across files."""
    body = await request.json()
    query = body.get("query", "")
    replacement = body.get("replacement", "")
    path = body.get("path", os.getcwd())
    case_sensitive = body.get("case_sensitive", False)
    use_regex = body.get("use_regex", False)
    dry_run = body.get("dry_run", True)
    files_filter = body.get("files", [])  # Only replace in specific files

    if not query:
        return {"success": False, "error": "No search query provided"}

    abs_path = os.path.abspath(os.path.expanduser(path))
    files_modified = []
    errors = []

    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(query, flags)

        for root, dirs, files in os.walk(abs_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'.git', '__pycache__', 'node_modules'}]

            for filename in files:
                if filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)

                # Filter by files if specified
                if files_filter:
                    rel = os.path.relpath(filepath, abs_path)
                    if rel not in files_filter and filename not in files_filter:
                        continue

                if os.path.getsize(filepath) > 5 * 1024 * 1024:
                    continue

                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    if not regex.search(content):
                        continue

                    if dry_run:
                        files_modified.append({"file": filepath, "changes": len(regex.findall(content))})
                    else:
                        new_content = regex.sub(replacement, content)
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_modified.append(filepath)
                except Exception as e:
                    errors.append({"file": filepath, "error": str(e)})

        return {
            "success": True,
            "files_modified": files_modified,
            "errors": errors,
            "dry_run": dry_run,
        }
    except re.error as e:
        return {"success": False, "error": f"Invalid regex: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/chart")
async def generate_chart(request: Request):
    """Generate a chart and return the image URL."""
    body = await request.json()
    chart_type = body.get("type", "bar")
    data = body.get("data", {})
    output_path = body.get("output", f"/tmp/chart_{uuid.uuid4().hex[:8]}.png")

    # Generate chart using matplotlib
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(8, 5))

        if chart_type == "bar":
            labels = data.get("labels", ["A", "B", "C", "D", "E"])
            values = data.get("values", [10, 20, 30, 40, 50])
            bars = ax.bar(labels, values, color=["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6"])
            ax.set_ylabel("Value")
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       str(val), ha='center', va='bottom', color='white')

        elif chart_type == "line":
            x = data.get("x", list(range(10)))
            y = data.get("y", [i**2 for i in range(10)])
            ax.plot(x, y, marker='o', linewidth=2, markersize=6, color="#3498db")
            ax.fill_between(x, y, alpha=0.3, color="#3498db")

        elif chart_type == "pie":
            labels = data.get("labels", ["A", "B", "C"])
            values = data.get("values", [30, 40, 30])
            colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]
            ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors[:len(values)],
                   textprops={'color': 'white'})
            ax.set_title(chart_type.upper(), color='white', fontsize=16)

        elif chart_type == "scatter":
            x = data.get("x", np.random.rand(50) * 100)
            y = data.get("y", np.random.rand(50) * 100)
            sizes = data.get("sizes", [30] * len(x))
            ax.scatter(x, y, s=sizes, c=y, cmap='viridis', alpha=0.7, edgecolors='white')

        elif chart_type == "histogram":
            values = data.get("values", np.random.randn(1000) * 10 + 50)
            ax.hist(values, bins=30, color="#3498db", edgecolor="white", alpha=0.8)

        elif chart_type == "heatmap":
            import numpy as np
            values = data.get("values")
            if values is None:
                values = np.random.rand(10, 10)
            im = ax.imshow(values, cmap='viridis', aspect='auto')
            fig.colorbar(im, ax=ax)

        elif chart_type == "radar":
            from math import pi
            categories = data.get("categories", ["Speed", "Reliability", "Comfort", "Safety", "Efficiency"])
            values_data = data.get("values", [4, 3, 5, 2, 4])
            values_data += values_data[:1]
            angles = [n / float(len(categories)) * 2 * pi for n in range(len(categories))]
            angles += angles[:1]
            ax = fig.add_subplot(111, polar=True)
            ax.plot(angles, values_data, 'o-', linewidth=2, color="#3498db")
            ax.fill(angles, values_data, alpha=0.25, color="#3498db")
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, color='white')

        fig.patch.set_facecolor('#1e1e1e')
        ax.set_facecolor('#2d2d2d')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, facecolor='#1e1e1e', edgecolor='none')
        plt.close()

        return {
            "success": True,
            "image_url": output_path,
            "type": chart_type,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/chart/plotly")
async def generate_plotly_chart(request: Request):
    """Generate an interactive Plotly chart."""
    body = await request.json()
    chart_type = body.get("type", "bar")
    data = body.get("data", {})

    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import json as json_module

        fig = None

        if chart_type == "bar":
            labels = data.get("labels", ["A", "B", "C", "D", "E"])
            values = data.get("values", [10, 20, 30, 40, 50])
            fig = go.Figure(data=[go.Bar(x=labels, y=values,
                                        marker_color=['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6'])])

        elif chart_type == "line":
            x = data.get("x", list(range(20)))
            y = data.get("y", [i**1.5 for i in x])
            fig = go.Figure(data=[go.Scatter(x=x, y=y, mode='lines+markers',
                                            line=dict(color='#3498db', width=2),
                                            marker=dict(size=6))])
            fig.add_trace(go.Scatter(x=x, y=[v*0.9 for v in y], mode='lines',
                                    line=dict(color='#e74c3c', width=1, dash='dash')))

        elif chart_type == "pie":
            labels = data.get("labels", ["A", "B", "C"])
            values = data.get("values", [30, 40, 30])
            fig = go.Figure(data=[go.Pie(labels=labels, values=values,
                                        marker=dict(colors=['#3498db', '#e74c3c', '#2ecc71']))])

        elif chart_type == "scatter":
            x = data.get("x", list(range(50)))
            y = data.get("y", [i + (i%10) for i in x])
            sizes = data.get("sizes", [10]*len(x))
            fig = go.Figure(data=[go.Scatter(x=x, y=y, mode='markers',
                                            marker=dict(size=sizes, color=y,
                                                      colorscale='Viridis', opacity=0.7))])

        elif chart_type == "heatmap":
            import numpy as np
            z = data.get("values")
            if z is None:
                z = np.random.rand(10, 10).tolist()
            fig = go.Figure(data=go.Heatmap(z=z, colorscale='Viridis'))

        elif chart_type == "histogram":
            values = data.get("values", [1, 2, 3, 3, 3, 4, 4, 5, 5, 5, 5, 6, 7, 8, 9])
            fig = go.Figure(data=[go.Histogram(x=values, marker_color='#3498db')])

        elif chart_type == "radar":
            categories = data.get("categories", ["Speed", "Power", "Range", "Charging", "Cost"])
            values_data = data.get("values", [4, 3, 5, 2, 4])
            values_data += values_data[:1]
            from math import pi
            angles = [n / float(len(categories)) * 2 * pi for n in range(len(categories))]
            angles += angles[:1]
            fig = go.Figure(data=go.Scatterpolar(
                r=values_data, theta=categories,
                fill='toself', fillcolor='rgba(52, 152, 219, 0.3)',
                line=dict(color='#3498db')
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])))

        if fig:
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor='#1e1e1e',
                plot_bgcolor='#2d2d2d',
                font=dict(color='white'),
                margin=dict(l=40, r=40, t=40, b=40),
            )
            html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            return {"success": True, "html": html, "type": chart_type}

        return {"success": False, "error": "Unknown chart type"}

    except ImportError:
        # Fallback: return placeholder
        return {"success": False, "error": "plotly not installed. Install with: pip install plotly"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/themes")
async def get_themes():
    """Get available themes."""
    return {
        "themes": [
            {"id": "dark", "name": "Dark", "preview": {"bg": "#1e1e1e", "fg": "#cccccc", "accent": "#3498db"}},
            {"id": "light", "name": "Light", "preview": {"bg": "#ffffff", "fg": "#333333", "accent": "#0066cc"}},
            {"id": "matrix", "name": "Matrix", "preview": {"bg": "#0d0d0d", "fg": "#00ff00", "accent": "#00ff00"}},
            {"id": "nord", "name": "Nord", "preview": {"bg": "#2e3440", "fg": "#eceff4", "accent": "#88c0d0"}},
            {"id": "solarized", "name": "Solarized", "preview": {"bg": "#002b36", "fg": "#fdf6e3", "accent": "#268bd2"}},
        ],
        "current": "dark",
    }


@studio_app.post("/api/workspace/save")
async def save_workspace(request: Request):
    """Save full workspace state (tabs, variables, history, theme, layout)."""
    body = await request.json()
    session_id = body.get("session_id", "default")
    workspace = body.get("workspace", {})

    ws_dir = Path.home() / ".pg_workspace"
    ws_dir.mkdir(exist_ok=True)
    ws_file = ws_dir / f"studio_{session_id}.json"

    try:
        with open(ws_file, 'w', encoding='utf-8') as f:
            json.dump(workspace, f, indent=2, ensure_ascii=False, default=str)
        return {"success": True, "path": str(ws_file)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/workspace/load")
async def load_workspace(session_id: str = "default"):
    """Load saved workspace state."""
    ws_file = Path.home() / ".pg_workspace" / f"studio_{session_id}.json"

    if not ws_file.exists():
        # Try loading the last saved workspace
        ws_dir = Path.home() / ".pg_workspace"
        if ws_dir.exists():
            files = sorted(ws_dir.glob("studio_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                ws_file = files[0]

    if ws_file.exists():
        try:
            with open(ws_file, 'r', encoding='utf-8') as f:
                return {"success": True, "workspace": json.load(f)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "No saved workspace found"}


@studio_app.get("/api/workspace/list")
async def list_workspaces():
    """List all saved workspaces."""
    ws_dir = Path.home() / ".pg_workspace"
    workspaces = []
    if ws_dir.exists():
        for f in sorted(ws_dir.glob("studio_*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            stat = f.stat()
            workspaces.append({
                "id": f.stem.replace("studio_", ""),
                "path": str(f),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size,
            })
    return {"workspaces": workspaces[:20]}


@studio_app.post("/api/files/new")
async def create_file(request: Request):
    """Create a new file."""
    body = await request.json()
    path = body.get("path", "")
    content = body.get("content", "")

    abs_path = os.path.abspath(os.path.expanduser(path))
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/terminal/interrupt")
async def interrupt_terminal(session_id: str):
    """Interrupt the current running command."""
    session = get_session(session_id)
    if session.process:
        session.process.terminate()
        return {"success": True, "message": "Process interrupted"}
    return {"success": False, "message": "No running process"}


def detect_language(path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".sh": "shell",
        ".bash": "shell",
        ".sql": "sql",
        ".xml": "xml",
        ".csv": "plaintext",
        ".txt": "plaintext",
        ".r": "r",
        ".ipynb": "json",
    }
    ext = os.path.splitext(path)[1].lower()
    return ext_map.get(ext, "plaintext")


# =============================================================================
# Git Integration API
# =============================================================================

@studio_app.get("/api/git/status")
async def git_status():
    """Get git repository status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain=v1", "--branch"],
            capture_output=True, text=True, timeout=10, cwd=os.getcwd()
        )
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        branch = "main"
        ahead = behind = 0
        files = []

        for line in lines:
            if line.startswith("## "):
                # Branch line: ## main...origin/main [ahead 1, behind 2]
                branch_info = line[3:]
                if "..." in branch_info:
                    branch = branch_info.split("...")[0]
                    if "ahead" in branch_info:
                        ahead = int(branch_info.split("ahead ")[1].split(",")[0].split("]")[0])
                    if "behind" in branch_info:
                        behind = int(branch_info.split("behind ")[1].split("]")[0])
            elif line:
                # File status: XY filename
                status = line[:2]
                filename = line[3:]
                staged = status[0] != " " and status[0] != "?"
                modified = status[1] != " "
                untracked = status == "??"
                files.append({
                    "path": filename,
                    "status": status.strip(),
                    "staged": staged,
                    "modified": modified,
                    "untracked": untracked,
                })

        # Get current branch more reliably
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5, cwd=os.getcwd()
        )
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip() or branch

        return {
            "success": True,
            "branch": branch,
            "ahead": ahead,
            "behind": behind,
            "files": files,
            "clean": len(files) == 0,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Git command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/git/log")
async def git_log(limit: int = 20):
    """Get git commit history."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--pretty=format:%H|%h|%an|%ae|%at|%s", "--date=unix"],
            capture_output=True, text=True, timeout=10, cwd=os.getcwd()
        )
        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|", 5)
                if len(parts) == 6:
                    commits.append({
                        "hash": parts[0],
                        "short_hash": parts[1],
                        "author": parts[2],
                        "email": parts[3],
                        "timestamp": int(parts[4]),
                        "message": parts[5],
                    })
        return {"success": True, "commits": commits}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/git/branches")
async def git_branches():
    """List all branches."""
    try:
        result = subprocess.run(
            ["git", "branch", "-a", "--format=%(refname:short)|%(objectname:short)|%(upstream:short)"],
            capture_output=True, text=True, timeout=10, cwd=os.getcwd()
        )
        branches = []
        current = ""

        # Get current branch
        current_result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=5, cwd=os.getcwd()
        )
        if current_result.returncode == 0:
            current = current_result.stdout.strip()

        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                name = parts[0].replace("remotes/", "") if parts[0].startswith("remotes/") else parts[0]
                branches.append({
                    "name": name,
                    "hash": parts[1] if len(parts) > 1 else "",
                    "upstream": parts[2] if len(parts) > 2 else "",
                    "current": name == current,
                    "remote": parts[0].startswith("remotes/"),
                })
        return {"success": True, "branches": branches, "current": current}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/git/commit")
async def git_commit(request: Request):
    """Create a git commit."""
    body = await request.json()
    message = body.get("message", "")
    files = body.get("files", [])

    if not message:
        return {"success": False, "error": "Commit message required"}

    try:
        # Stage files if specified
        if files:
            for f in files:
                subprocess.run(["git", "add", f], check=True, cwd=os.getcwd())
        else:
            subprocess.run(["git", "add", "-A"], check=True, cwd=os.getcwd())

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", message],
            capture_output=True, text=True, timeout=30, cwd=os.getcwd()
        )

        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        else:
            return {"success": False, "error": result.stderr or result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/git/push")
async def git_push():
    """Push to remote."""
    try:
        result = subprocess.run(
            ["git", "push"],
            capture_output=True, text=True, timeout=60, cwd=os.getcwd()
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/git/pull")
async def git_pull():
    """Pull from remote."""
    try:
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True, text=True, timeout=60, cwd=os.getcwd()
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/git/checkout")
async def git_checkout(request: Request):
    """Checkout a branch."""
    body = await request.json()
    branch = body.get("branch", "")

    if not branch:
        return {"success": False, "error": "Branch name required"}

    try:
        result = subprocess.run(
            ["git", "checkout", branch],
            capture_output=True, text=True, timeout=30, cwd=os.getcwd()
        )
        if result.returncode == 0:
            return {"success": True, "output": result.stdout}
        return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/git/diff")
async def git_diff(file: str = "", staged: bool = False):
    """Get git diff."""
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if file:
            cmd.append(file)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, cwd=os.getcwd()
        )
        return {"success": True, "diff": result.stdout}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Snippet API
# =============================================================================

SNIPPETS_FILE = Path.home() / ".pg_workspace" / "snippets.json"

DEFAULT_SNIPPETS = {
    "python": [
        {"id": "py-print", "name": "Print Debug", "code": 'print(f"{variable=}")', "desc": "Debug print with variable name"},
        {"id": "py-main", "name": "Main Block", "code": 'if __name__ == "__main__":\n    pass', "desc": "Python main guard"},
        {"id": "py-try", "name": "Try Except", "code": "try:\n    pass\nexcept Exception as e:\n    print(f'Error: {e}')", "desc": "Exception handling"},
        {"id": "py-class", "name": "Class Template", "code": "class MyClass:\n    def __init__(self):\n        pass\n\n    def __repr__(self):\n        return f'MyClass()'", "desc": "Basic class structure"},
    ],
    "shell": [
        {"id": "sh-for", "name": "For Loop", "code": "for item in $(ls); do\n    echo $item\ndone", "desc": "Shell for loop"},
        {"id": "sh-if", "name": "If Statement", "code": "if [ -f \"$file\" ]; then\n    echo \"File exists\"\nfi", "desc": "Shell if statement"},
    ],
    "attack": [
        {"id": "nmap-scan", "name": "Nmap Quick Scan", "code": "nmap -sV -sC -p- --min-rate=1000 -T4 $TARGET", "desc": "Full port scan with scripts"},
        {"id": "gobuster-dir", "name": "Gobuster Directory", "code": "gobuster dir -u $URL -w /usr/share/wordlists/dirb/common.txt -x php,html,txt", "desc": "Directory enumeration"},
        {"id": "hydra-ssh", "name": "Hydra SSH", "code": "hydra -l $USER -P /usr/share/wordlists/rockyou.txt ssh://$TARGET", "desc": "SSH brute force"},
    ],
    "recon": [
        {"id": "whois", "name": "Whois Lookup", "code": "whois $DOMAIN", "desc": "Domain whois info"},
        {"id": "dig-all", "name": "DNS Enum", "code": "dig $DOMAIN ANY +noall +answer", "desc": "DNS enumeration"},
    ],
}


def load_snippets() -> dict:
    """Load snippets from file."""
    if SNIPPETS_FILE.exists():
        try:
            with open(SNIPPETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SNIPPETS.copy()


def save_snippets(snippets: dict):
    """Save snippets to file."""
    SNIPPETS_FILE.parent.mkdir(exist_ok=True)
    with open(SNIPPETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(snippets, f, indent=2, ensure_ascii=False)


@studio_app.get("/api/snippets")
async def get_snippets():
    """Get all snippets."""
    return {"success": True, "snippets": load_snippets()}


@studio_app.post("/api/snippets")
async def add_snippet(request: Request):
    """Add or update a snippet."""
    body = await request.json()
    category = body.get("category", "python")
    snippet = body.get("snippet", {})

    snippets = load_snippets()
    if category not in snippets:
        snippets[category] = []

    # Generate ID if not provided
    if not snippet.get("id"):
        snippet["id"] = f"{category[:2]}-{int(time.time())}"

    # Update existing or add new
    for i, s in enumerate(snippets[category]):
        if s.get("id") == snippet["id"]:
            snippets[category][i] = snippet
            break
    else:
        snippets[category].append(snippet)

    save_snippets(snippets)
    return {"success": True, "id": snippet["id"]}


@studio_app.delete("/api/snippets")
async def delete_snippet(category: str, snippet_id: str):
    """Delete a snippet."""
    snippets = load_snippets()
    if category in snippets:
        snippets[category] = [s for s in snippets[category] if s.get("id") != snippet_id]
        save_snippets(snippets)
    return {"success": True}


# =============================================================================
# REPL API
# =============================================================================

@studio_app.post("/api/repl/python")
async def repl_python(request: Request):
    """Execute Python code in REPL mode."""
    # Security: Require API key for code execution
    if not _check_api_key(request):
        return JSONResponse({"success": False, "error": "Authentication required"}, status_code=401)

    body = await request.json()
    code = body.get("code", "")
    session_id = body.get("session_id", "default")

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=30, cwd=os.getcwd()
        )
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/repl/shell")
async def repl_shell(request: Request):
    """Execute shell command."""
    # Security: Require API key for shell execution
    if not _check_api_key(request):
        return JSONResponse({"success": False, "error": "Authentication required"}, status_code=401)

    body = await request.json()
    command = body.get("command", "")

    if not command:
        return {"success": False, "error": "No command provided"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()
        )
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Report Generator API
# =============================================================================

REPORT_TEMPLATES = {
    "executive": {
        "name": "Executive Summary",
        "sections": ["overview", "risk_summary", "recommendations"],
    },
    "technical": {
        "name": "Technical Report",
        "sections": ["scope", "methodology", "findings", "vulnerabilities", "remediation"],
    },
    "vulnerability": {
        "name": "Vulnerability Assessment",
        "sections": ["summary", "critical", "high", "medium", "low", "remediation"],
    },
}

@studio_app.get("/api/report/templates")
async def get_report_templates():
    """Get available report templates."""
    return {"templates": REPORT_TEMPLATES}


@studio_app.post("/api/report/generate")
async def generate_report(request: Request):
    """Generate a pentest report."""
    body = await request.json()
    template = body.get("template", "technical")
    title = body.get("title", "Penetration Test Report")
    scope = body.get("scope", [])
    findings = body.get("findings", [])
    format_type = body.get("format", "html")

    if template not in REPORT_TEMPLATES:
        return {"success": False, "error": f"Unknown template: {template}"}

    sections = REPORT_TEMPLATES[template]["sections"]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Generate report content
    if format_type == "html":
        report = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .meta {{ color: #7f8c8d; font-size: 14px; }}
        .finding {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-left: 4px solid #e74c3c; }}
        .severity-critical {{ border-left-color: #e74c3c; }}
        .severity-high {{ border-left-color: #e67e22; }}
        .severity-medium {{ border-left-color: #f1c40f; }}
        .severity-low {{ border-left-color: #2ecc71; }}
        .risk-high {{ color: #e74c3c; font-weight: bold; }}
        .risk-medium {{ color: #e67e22; }}
        .risk-low {{ color: #2ecc71; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #3498db; color: white; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="meta">Generated: {timestamp} | Template: {REPORT_TEMPLATES[template]['name']}</p>

    <h2>Scope</h2>
    <ul>
        {''.join(f'<li>{s}</li>' for s in (scope or ['Not specified']))}
    </ul>

    <h2>Executive Summary</h2>
    <p>This report documents the findings from the penetration testing assessment.</p>

    <h2>Findings Summary</h2>
    <table>
        <tr><th>#</th><th>Finding</th><th>Severity</th><th>Status</th></tr>
        {''.join(f'<tr><td>{i+1}</td><td>{f.get("title", "Unknown")}</td><td class="severity-{f.get("severity", "medium").lower()}">{f.get("severity", "Medium")}</td><td>{f.get("status", "Open")}</td></tr>' for i, f in enumerate(findings)) if findings else '<tr><td colspan="4">No findings recorded</td></tr>'}
    </table>

    {''.join(f'<div class="finding severity-{f.get("severity", "medium").lower()}"><h3>{f.get("title", "Finding")}</h3><p>{f.get("description", "")}</p><p><strong>Severity:</strong> {f.get("severity", "Medium")}</p><p><strong>Remediation:</strong> {f.get("remediation", "TBD")}</p></div>' for f in findings) if findings else ''}

    <h2>Recommendations</h2>
    <ol>
        <li>Address all critical and high severity findings immediately</li>
        <li>Implement security monitoring and logging</li>
        <li>Conduct regular security assessments</li>
        <li>Establish a vulnerability management program</li>
    </ol>

    <p style="margin-top: 40px; color: #7f8c8d; font-size: 12px;">
    Generated by Manatrix Studio | {timestamp}
    </p>
</body>
</html>"""
    else:  # Markdown
        report = f"""# {title}

**Generated:** {timestamp}
**Template:** {REPORT_TEMPLATES[template]['name']}

## Scope

{''.join(f'- {s}\n' for s in (scope or ['Not specified']))}

## Executive Summary

This report documents the findings from the penetration testing assessment.

## Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
{''.join(f'| {i+1} | {f.get("title", "Unknown")} | {f.get("severity", "Medium")} | {f.get("status", "Open")} |\n' for i, f in enumerate(findings)) if findings else '| - | No findings | - | - |'}

{''.join(f'\n### {f.get("title", "Finding")}\n\n**Severity:** {f.get("severity", "Medium")}\n\n{f.get("description", "")}\n\n**Remediation:** {f.get("remediation", "TBD")}\n' for f in findings) if findings else ''}

## Recommendations

1. Address all critical and high severity findings immediately
2. Implement security monitoring and logging
3. Conduct regular security assessments
4. Establish a vulnerability management program

---
*Generated by Manatrix Studio*
"""

    # Save report
    report_dir = Path.home() / ".pg_workspace" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    ext = "html" if format_type == "html" else "md"
    report_path = report_dir / f"report_{int(time.time())}.{ext}"

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    return {
        "success": True,
        "path": str(report_path),
        "format": format_type,
        "size": len(report),
    }


# =============================================================================
# Wordlist Analyzer API
# =============================================================================

@studio_app.post("/api/wordlist/analyze")
async def analyze_wordlist(request: Request):
    """Analyze a wordlist file."""
    body = await request.json()
    filepath = body.get("path", "")

    if not filepath:
        return {"success": False, "error": "No file path provided"}

    abs_path = os.path.abspath(os.path.expanduser(filepath))
    if not os.path.exists(abs_path):
        return {"success": False, "error": "File not found"}

    try:
        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        total = len(lines)
        lengths = []
        charsets = {"upper": 0, "lower": 0, "digit": 0, "special": 0}
        patterns = {"numeric": 0, "alpha": 0, "alphanumeric": 0, "mixed": 0}
        min_len = float('inf')
        max_len = 0
        total_chars = 0
        entropy_sum = 0

        for line in lines:
            word = line.rstrip('\n\r')
            length = len(word)
            lengths.append(length)
            total_chars += length
            min_len = min(min_len, length) if length > 0 else min_len
            max_len = max(max_len, length)

            # Character analysis
            has_upper = has_lower = has_digit = has_special = False
            for c in word:
                if c.isupper(): has_upper = True; charsets["upper"] += 1
                elif c.islower(): has_lower = True; charsets["lower"] += 1
                elif c.isdigit(): has_digit = True; charsets["digit"] += 1
                else: has_special = True; charsets["special"] += 1

            # Pattern classification
            if word.isdigit(): patterns["numeric"] += 1
            elif word.isalpha(): patterns["alpha"] += 1
            elif word.isalnum(): patterns["alphanumeric"] += 1
            else: patterns["mixed"] += 1

            # Entropy approximation
            if length > 0:
                unique_chars = len(set(word))
                entropy_sum += unique_chars / length

        # Calculate distribution
        length_dist = {}
        for l in lengths:
            length_dist[l] = length_dist.get(l, 0) + 1

        avg_len = total_chars / total if total > 0 else 0
        avg_entropy = entropy_sum / total if total > 0 else 0

        # Top lengths
        top_lengths = sorted(length_dist.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "success": True,
            "file": abs_path,
            "total_entries": total,
            "file_size": os.path.getsize(abs_path),
            "length_stats": {
                "min": min_len if min_len != float('inf') else 0,
                "max": max_len,
                "average": round(avg_len, 2),
                "distribution": dict(top_lengths),
            },
            "charset_coverage": {
                "uppercase": charsets["upper"],
                "lowercase": charsets["lower"],
                "digits": charsets["digit"],
                "special": charsets["special"],
                "percentages": {
                    "upper": round(charsets["upper"] / max(total_chars, 1) * 100, 2),
                    "lower": round(charsets["lower"] / max(total_chars, 1) * 100, 2),
                    "digit": round(charsets["digit"] / max(total_chars, 1) * 100, 2),
                    "special": round(charsets["special"] / max(total_chars, 1) * 100, 2),
                },
            },
            "patterns": patterns,
            "entropy_score": round(avg_entropy * 100, 2),
            "quality_rating": "High" if avg_entropy > 0.7 else "Medium" if avg_entropy > 0.4 else "Low",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Session Recording API
# =============================================================================

RECORDINGS_DIR = Path.home() / ".pg_workspace" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)


@studio_app.get("/api/recording/list")
async def list_recordings():
    """List all session recordings."""
    recordings = []
    for f in sorted(RECORDINGS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
            recordings.append({
                "id": f.stem,
                "path": str(f),
                "name": data.get("name", f.stem),
                "duration": data.get("duration", 0),
                "commands": len(data.get("commands", [])),
                "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
        except Exception:
            pass
    return {"recordings": recordings[:50]}


@studio_app.post("/api/recording/save")
async def save_recording(request: Request):
    """Save a session recording."""
    body = await request.json()
    name = body.get("name", f"recording_{int(time.time())}")
    commands = body.get("commands", [])

    recording_id = f"rec_{int(time.time())}"
    filepath = RECORDINGS_DIR / f"{recording_id}.json"

    with open(filepath, 'w') as f:
        json.dump({
            "id": recording_id,
            "name": name,
            "commands": commands,
            "duration": commands[-1]["timestamp"] - commands[0]["timestamp"] if commands else 0,
            "created": datetime.now().isoformat(),
        }, f, indent=2)

    return {"success": True, "id": recording_id, "path": str(filepath)}


@studio_app.get("/api/recording/load/{recording_id}")
async def load_recording(recording_id: str):
    """Load a session recording."""
    filepath = RECORDINGS_DIR / f"{recording_id}.json"
    if not filepath.exists():
        return {"success": False, "error": "Recording not found"}

    with open(filepath, 'r') as f:
        data = json.load(f)

    return {"success": True, "recording": data}


@studio_app.delete("/api/recording/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete a session recording."""
    filepath = RECORDINGS_DIR / f"{recording_id}.json"
    if filepath.exists():
        filepath.unlink()
    return {"success": True}


# =============================================================================
# Jupyter Notebook Integration
# =============================================================================

@studio_app.get("/api/notebook/read")
async def read_notebook(path: str = ""):
    """Read and parse a Jupyter notebook."""
    if not path:
        return {"success": False, "error": "No notebook path provided"}

    abs_path = os.path.abspath(os.path.expanduser(path))
    if not os.path.exists(abs_path) or not abs_path.endswith('.ipynb'):
        return {"success": False, "error": "Not a valid notebook file"}

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)

        cells = []
        for i, cell in enumerate(nb.get("cells", [])):
            cells.append({
                "index": i,
                "type": cell.get("cell_type", "code"),
                "source": "".join(cell.get("source", [])),
                "outputs": cell.get("outputs", []),
                "metadata": cell.get("metadata", {}),
                "execution_count": cell.get("execution_count"),
            })

        return {
            "success": True,
            "path": abs_path,
            "name": nb.get("metadata", {}).get("kernelspec", {}).get("display_name", "Python"),
            "kernel": nb.get("metadata", {}).get("kernelspec", {}).get("name", "python3"),
            "nbformat": nb.get("nbformat", 4),
            "cells": cells,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/notebook/execute")
async def execute_notebook_cell(request: Request):
    """Execute a single notebook cell."""
    body = await request.json()
    code = body.get("code", "")
    session_id = body.get("session_id", "default")

    if not code:
        return {"success": False, "error": "No code provided"}

    # Execute via subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=60, cwd=os.getcwd()
        )

        outputs = []
        if result.stdout:
            outputs.append({
                "output_type": "stream",
                "name": "stdout",
                "text": result.stdout,
            })
        if result.stderr:
            outputs.append({
                "output_type": "error",
                "ename": "Error",
                "evalue": result.stderr,
                "traceback": [result.stderr],
            })

        return {
            "success": True,
            "outputs": outputs,
            "execution_count": 1,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out", "outputs": [{
            "output_type": "error", "ename": "Timeout", "evalue": "Execution exceeded 60 seconds", "traceback": []
        }]}
    except Exception as e:
        return {"success": False, "error": str(e), "outputs": [{
            "output_type": "error", "ename": "Error", "evalue": str(e), "traceback": []
        }]}


@studio_app.post("/api/notebook/save")
async def save_notebook(request: Request):
    """Save a notebook with updated cells."""
    body = await request.json()
    path = body.get("path", "")
    cells = body.get("cells", [])

    if not path:
        return {"success": False, "error": "No path provided"}

    abs_path = os.path.abspath(os.path.expanduser(path))

    # Read existing notebook to preserve metadata
    try:
        with open(abs_path, 'r') as f:
            nb = json.load(f)
    except Exception as e:
        return {"success": False, "error": str(e)}

    # Update cells
    nb["cells"] = [
        {
            "cell_type": cell.get("type", "code"),
            "execution_count": cell.get("execution_count"),
            "metadata": cell.get("metadata", {}),
            "outputs": cell.get("outputs", []),
            "source": cell.get("source", ""),
        }
        for cell in cells
    ]
    nb["nbformat"] = nb.get("nbformat", 4)

    try:
        with open(abs_path, 'w') as f:
            json.dump(nb, f, indent=1)
        return {"success": True, "path": abs_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Attack Graph Visualization
# =============================================================================

@studio_app.get("/api/attack-graph")
async def get_attack_graph(path: str = ""):
    """Read attack graph from JSON and return D3.js-compatible data."""
    # Default path - try the attack_graph directory
    default_paths = [
        os.path.join(os.getcwd(), "attack_graph", "attack_graph.json"),
        os.path.join(os.getcwd(), "attack_result.json"),
        os.path.join(os.path.dirname(os.getcwd()), "attack_graph", "attack_graph.json"),
    ]

    if path:
        default_paths.insert(0, path)

    graph_data = None
    used_path = None

    for p in default_paths:
        abs_path = os.path.abspath(os.path.expanduser(p))
        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                used_path = abs_path
                break
            except Exception:
                pass

    if not graph_data:
        # Generate a sample graph
        graph_data = {
            "nodes": [
                {"id": "attacker", "label": "Attacker", "type": "attacker", "x": 0, "y": 0.5},
                {"id": "gateway", "label": "Gateway", "type": "entry", "x": 0.2, "y": 0.5},
                {"id": "web_server", "label": "Web Server", "type": "target", "x": 0.4, "y": 0.3},
                {"id": "database", "label": "Database", "type": "target", "x": 0.6, "y": 0.5},
                {"id": "internal", "label": "Internal Net", "type": "target", "x": 0.8, "y": 0.5},
            ],
            "edges": [
                {"source": "attacker", "target": "gateway", "label": "port_scan"},
                {"source": "gateway", "target": "web_server", "label": "web_exploit"},
                {"source": "web_server", "target": "database", "label": "sql_injection"},
                {"source": "database", "target": "internal", "label": "lateral_movement"},
            ],
        }

    # Convert to D3 format
    nodes = []
    node_map = {}
    risk_colors = {"critical": "#e74c3c", "high": "#e67e22", "medium": "#f1c40f", "low": "#2ecc71", "info": "#3498db"}

    for i, node in enumerate(graph_data.get("nodes", [])):
        n = {
            "id": node.get("id", f"node_{i}"),
            "label": node.get("label", node.get("id", f"Node {i}")),
            "type": node.get("type", "unknown"),
            "risk": node.get("risk", "info"),
            "color": risk_colors.get(node.get("risk", "info"), "#3498db"),
            "x": node.get("x", i * 0.2),
            "y": node.get("y", 0.5),
        }
        nodes.append(n)
        node_map[n["id"]] = n

    edges = []
    for edge in graph_data.get("edges", []):
        src = edge.get("source") if isinstance(edge.get("source"), str) else edge.get("source", {}).get("id", "unknown")
        tgt = edge.get("target") if isinstance(edge.get("target"), str) else edge.get("target", {}).get("id", "unknown")
        if src in node_map and tgt in node_map:
            edges.append({
                "source": src,
                "target": tgt,
                "label": edge.get("label", ""),
                "weight": edge.get("weight", 1),
            })

    return {
        "success": True,
        "path": used_path,
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


# =============================================================================
# Manatrix Direct Module Integration (No subprocess overhead)
# =============================================================================

@studio_app.post("/api/manatrix/train")
async def manatrix_train(request: Request):
    """Train password model directly via Python API."""
    body = await request.json()
    config_path = body.get("config", "config.yaml")
    data_path = body.get("data", "data/passwords.txt")
    epochs = body.get("epochs", 10)
    output = body.get("output", "checkpoints")

    try:
        # Import directly to avoid subprocess
        import yaml
        from training import DistributedTrainer

        # Load config
        config_file = os.path.join(_project_root, config_path)
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
        else:
            config = {}

        return {
            "success": True,
            "message": "Training endpoint ready",
            "config": config_file,
            "data": data_path,
            "epochs": epochs,
            "note": "Use CLI: manatrix train --config config.yaml --data passwords.txt"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/generate")
async def manatrix_generate(request: Request):
    """Generate passwords using trained model."""
    body = await request.json()
    checkpoint = body.get("checkpoint", "checkpoints/best_model.pt")
    target_info = body.get("target_info", "")
    count = body.get("count", 100)
    output_file = body.get("output", None)

    try:
        from models import MambaPasswordModel, MambaConfig, MLPEncoder
        from utils import PasswordTokenizer
        from utils.feature_utils import TargetFeatures
        import torch

        checkpoint_path = os.path.join(_project_root, checkpoint)
        if not os.path.exists(checkpoint_path):
            return {"success": False, "error": f"Checkpoint not found: {checkpoint_path}"}

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_config = MambaConfig()
        model = MambaPasswordModel(model_config)
        mlp_encoder = MLPEncoder(input_dim=64, hidden_dims=[128, 128], output_dim=128)

        ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
        model.load_state_dict(ckpt['model_state_dict'])
        mlp_encoder.load_state_dict(ckpt['mlp_state_dict'])
        model = model.to(device).eval()
        mlp_encoder = mlp_encoder.to(device).eval()

        tokenizer = PasswordTokenizer()
        target_features = TargetFeatures.from_text(target_info) if target_info else TargetFeatures()

        # Generate passwords
        passwords = []
        with torch.no_grad():
            for _ in range(min(count, 1000)):
                input_ids = torch.randint(0, len(tokenizer), (1, 32), device=device)
                cond = torch.randn(1, 128, device=device)
                if target_info:
                    cond = mlp_encoder(target_features.to_tensor(device).unsqueeze(0))
                logits = model(input_ids, cond=cond)
                tokens = torch.argmax(logits, dim=-1)[0]
                password = tokenizer.decode(tokens.cpu().numpy())
                if password not in passwords:
                    passwords.append(password)

        if output_file:
            output_path = os.path.join(_project_root, output_file)
            with open(output_path, 'w') as f:
                f.write('\n'.join(passwords))
            return {"success": True, "count": len(passwords), "output": output_path}
        return {"success": True, "passwords": passwords[:count], "count": len(passwords)}

    except FileNotFoundError:
        return {"success": False, "error": "Checkpoint file not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/evaluate")
async def manatrix_evaluate(request: Request):
    """Evaluate password strength."""
    body = await request.json()
    password = body.get("password", "")
    password_hash = body.get("hash", None)

    try:
        from evaluation import PasswordStrengthEvaluator

        evaluator = PasswordStrengthEvaluator()

        if password:
            result = evaluator.evaluate(password)
            return {
                "success": True,
                "password": password,
                "strength": result.strength.value if hasattr(result, 'strength') else result.get('strength', 'unknown'),
                "score": result.score if hasattr(result, 'score') else result.get('score', 0),
                "crack_time": result.crack_time if hasattr(result, 'crack_time') else result.get('crack_time', 'unknown'),
                "feedback": result.feedback if hasattr(result, 'feedback') else result.get('feedback', []),
            }
        elif password_hash:
            # Estimate hash type and crack time
            return {
                "success": True,
                "hash": password_hash[:20] + "...",
                "estimated_type": "unknown",
                "crack_time_estimate": "depends on hash type",
            }
        else:
            return {"success": False, "error": "Provide password or hash"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/pcfg")
async def manatrix_pcfg_generate(request: Request):
    """Generate passwords using PCFG."""
    body = await request.json()
    grammar_file = body.get("grammar", None)
    count = body.get("count", 100)
    target = body.get("target", None)

    try:
        from pcfg import PCFGGenerator

        generator = PCFGGenerator()

        if grammar_file:
            grammar_path = os.path.join(_project_root, grammar_file)
            if os.path.exists(grammar_path):
                generator.load_grammar(grammar_path)

        passwords = generator.generate(count)

        if target:
            # Filter/prioritize passwords based on target info
            filtered = [p for p in passwords if any(t.lower() in p.lower() for t in target.split())]
            if filtered:
                passwords = filtered + [p for p in passwords if p not in filtered]

        return {
            "success": True,
            "count": len(passwords),
            "passwords": passwords[:count],
            "grammar": grammar_file,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/rules")
async def manatrix_rules(request: Request):
    """Apply password rules."""
    body = await request.json()
    action = body.get("action", "list")  # list, apply, generate
    base_wordlist = body.get("wordlist", [])
    rule_file = body.get("rule", "rules/default.rule")

    try:
        from rules import PasswordRuleEngine, HashcatRuleParser

        if action == "list":
            # List available rules
            rules_dir = os.path.join(_project_root, "rules")
            available = []
            if os.path.exists(rules_dir):
                for f in os.listdir(rules_dir):
                    if f.endswith('.rule'):
                        available.append(f)
            return {"success": True, "rules": available}

        elif action == "apply":
            if not base_wordlist:
                return {"success": False, "error": "No wordlist provided"}
            if isinstance(base_wordlist, str):
                # Treat as file path
                wl_path = os.path.join(_project_root, base_wordlist)
                if os.path.exists(wl_path):
                    with open(wl_path, 'r') as f:
                        base_wordlist = [line.strip() for line in f if line.strip()]

            rule_path = os.path.join(_project_root, rule_file)
            parser = HashcatRuleParser()
            engine = PasswordRuleEngine()

            if os.path.exists(rule_path):
                rules = parser.parse_file(rule_path)
                engine.load_rules(rules)
            else:
                # Use default rules
                engine.load_rules(["l", "u", "c", "$1", "$2", "$3"])

            results = []
            for word in base_wordlist[:1000]:  # Limit for API
                variations = engine.apply_rules(word)
                results.extend(variations)

            return {
                "success": True,
                "input_count": len(base_wordlist),
                "output_count": len(results),
                "passwords": list(set(results))[:1000],
            }

        return {"success": False, "error": "Unknown action"}

    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/crawl")
async def manatrix_crawl(request: Request):
    """Crawl website for password-related info."""
    body = await request.json()
    url = body.get("url", "")
    depth = body.get("depth", 2)
    vuln_scan = body.get("vuln_scan", False)

    if not url:
        return {"success": False, "error": "URL required"}

    try:
        # Check if crawler module exists
        from crawler import WebCrawler

        crawler = WebCrawler(max_depth=depth)
        results = crawler.crawl(url)

        return {
            "success": True,
            "url": url,
            "pages_crawled": len(results.get('pages', [])),
            "findings": results.get('findings', []),
            "vulnerabilities": results.get('vulnerabilities', []) if vuln_scan else [],
        }
    except ImportError:
        return {
            "success": False,
            "error": "Crawler module not available",
            "note": "Crawler requires additional dependencies"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/pentest")
async def manatrix_pentest(request: Request):
    """Run penetration test."""
    body = await request.json()
    target = body.get("target", "")
    mode = body.get("mode", "scan")  # scan, exploit, report

    if not target:
        return {"success": False, "error": "Target required"}

    try:
        from pentest import PenTestOrchestrator

        # Basic pentest simulation
        return {
            "success": True,
            "target": target,
            "mode": mode,
            "status": "ready",
            "note": "Use manatrix attack --target <target> for full functionality"
        }
    except ImportError:
        return {
            "success": False,
            "error": "Pentest module not available",
            "note": "Pentest requires additional dependencies"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.get("/api/manatrix/info")
async def manatrix_info():
    """Get manatrix system information."""
    try:
        import torch

        info = {
            "project_root": _project_root,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "python_version": sys.version,
            "modules": {
                "models": os.path.exists(os.path.join(_project_root, "models")),
                "optimization": os.path.exists(os.path.join(_project_root, "optimization")),
                "evaluation": os.path.exists(os.path.join(_project_root, "evaluation")),
                "training": os.path.exists(os.path.join(_project_root, "training")),
                "rules": os.path.exists(os.path.join(_project_root, "rules")),
                "pcfg": os.path.exists(os.path.join(_project_root, "pcfg")),
                "crawler": os.path.exists(os.path.join(_project_root, "crawler")),
                "pentest": os.path.exists(os.path.join(_project_root, "pentest")),
                "rl_agent": os.path.exists(os.path.join(_project_root, "rl_agent")),
            },
            "checkpoints": [],
        }

        # List checkpoints
        ckpt_dir = os.path.join(_project_root, "checkpoints")
        if os.path.exists(ckpt_dir):
            for f in os.listdir(ckpt_dir):
                if f.endswith('.pt') or f.endswith('.pth'):
                    info["checkpoints"].append(f)

        return info

    except Exception as e:
        return {"error": str(e)}


@studio_app.get("/api/manatrix/config")
async def manatrix_config():
    """Get manatrix configuration."""
    try:
        config_path = os.path.join(_project_root, "config.yaml")
        if os.path.exists(config_path):
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return {"success": True, "config": config}
        return {"success": False, "error": "config.yaml not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@studio_app.post("/api/manatrix/config")
async def manatrix_update_config(request: Request):
    """Update manatrix configuration."""
    body = await request.json()
    try:
        import yaml
        config_path = os.path.join(_project_root, "config.yaml")

        # Load existing or create new
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Update with new values
        config.update(body)

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        return {"success": True, "config": config}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Autonomous Attack (ManatrixAgent - Claude Code Style)
# =============================================================================

# Track active attack sessions
_attack_sessions: Dict[str, Any] = {}

@studio_app.websocket("/ws/attack/{session_id}")
async def attack_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time autonomous attack streaming."""
    await websocket.accept()
    _attack_sessions[session_id] = {"ws": websocket, "running": False, "agent": None}

    try:
        while True:
            # Receive messages from client
            msg = await websocket.receive_text()
            data = json.loads(msg)

            msg_type = data.get("type", "")

            if msg_type == "start":
                # Start autonomous attack
                brief = data.get("brief", "")
                dry_run = data.get("dry_run", False)
                llm_config = data.get("llm_config", {})

                _attack_sessions[session_id]["running"] = True

                # Send starting status
                await websocket.send_json({
                    "type": "status",
                    "data": {
                        "session_id": session_id,
                        "phase": "initializing",
                        "message": "Initializing autonomous attack..."
                    }
                })

                # Get LLM config - prefer the one sent from client, fallback to session/config
                if not llm_config or not llm_config.get("api_key"):
                    llm_config = _get_llm_config_from_session(session_id)

                if not llm_config or not llm_config.get("api_key"):
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "No LLM configuration found. Please configure API key in Settings (\u2699 button)."}
                    })
                    _attack_sessions[session_id]["running"] = False
                    continue

                try:
                    from models.manatrix_agent import ManatrixAgent
                    from models.llm_provider import LLMConfig, get_provider

                    config = LLMConfig(provider=llm_config.get("provider", "deepseek"),
                                        api_key=llm_config.get("api_key", ""),
                                        model=llm_config.get("model"),
                                        base_url=llm_config.get("base_url"))

                    agent = ManatrixAgent(
                        llm_config=config,
                        workspace_dir=os.path.join(_project_root, "workspace", session_id)
                    )
                    _attack_sessions[session_id]["agent"] = agent

                    # Callback to stream updates via WebSocket
                    async def on_update(event_type: str, data: dict):
                        try:
                            await websocket.send_json({
                                "type": event_type,
                                "data": data
                            })
                        except Exception:
                            pass

                    async def on_action(action, result):
                        try:
                            await websocket.send_json({
                                "type": "action_complete",
                                "data": {
                                    "action_id": action.action_id,
                                    "type": action.type,
                                    "target": action.target,
                                    "success": result.success,
                                    "duration": result.duration,
                                }
                            })
                        except Exception:
                            pass

                    # Run the attack
                    result = agent.run(
                        brief=brief,
                        on_update=on_update,
                        on_action=on_action,
                        dry_run=dry_run,
                    )

                    # Send final result
                    await websocket.send_json({
                        "type": "complete",
                        "data": result.to_dict()
                    })

                except ImportError as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Agent module not available: {e}"}
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": str(e)}
                    })

                _attack_sessions[session_id]["running"] = False

            elif msg_type == "pause":
                # Pause the attack
                if session_id in _attack_sessions and _attack_sessions[session_id]["agent"]:
                    agent = _attack_sessions[session_id]["agent"]
                    # Signal pause - agent will check this flag
                    _attack_sessions[session_id]["running"] = False
                    await websocket.send_json({
                        "type": "paused",
                        "data": {"message": "Attack paused"}
                    })

            elif msg_type == "resume":
                # Resume paused attack
                if session_id in _attack_sessions:
                    _attack_sessions[session_id]["running"] = True
                    await websocket.send_json({
                        "type": "resumed",
                        "data": {"message": "Attack resumed"}
                    })

            elif msg_type == "stop":
                # Stop the attack
                if session_id in _attack_sessions:
                    _attack_sessions[session_id]["running"] = False
                    if _attack_sessions[session_id]["agent"]:
                        # Mark agent state as interrupted
                        agent = _attack_sessions[session_id]["agent"]
                        if agent.state:
                            from models.agent.state import Phase
                            agent.state.phase = Phase.FAILED
                    await websocket.send_json({
                        "type": "stopped",
                        "data": {"message": "Attack stopped"}
                    })

            elif msg_type == "status":
                # Get current attack status
                if session_id in _attack_sessions:
                    agent = _attack_sessions[session_id]["agent"]
                    if agent:
                        await websocket.send_json({
                            "type": "status",
                            "data": agent.get_status()
                        })
                    else:
                        await websocket.send_json({
                            "type": "status",
                            "data": {"status": "idle"}
                        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except Exception:
            pass
    finally:
        if session_id in _attack_sessions:
            del _attack_sessions[session_id]


@studio_app.get("/api/attack/{session_id}/status")
async def get_attack_status(session_id: str):
    """Get status of an attack session."""
    if session_id in _attack_sessions:
        agent = _attack_sessions[session_id].get("agent")
        if agent:
            return {"success": True, "status": agent.get_status()}
    return {"success": True, "status": {"status": "idle"}}


@studio_app.get("/api/attack/sessions")
async def list_attack_sessions():
    """List all active attack sessions."""
    sessions = []
    for sid, info in _attack_sessions.items():
        sessions.append({
            "session_id": sid,
            "running": info.get("running", False),
        })
    return {"success": True, "sessions": sessions}


def _get_llm_config_from_session(session_id: str) -> Optional[dict]:
    """Get LLM config from session storage or config.yaml."""
    # Try session storage first
    if session_id in _sessions:
        session = _sessions[session_id]
        if hasattr(session, 'variables') and "llm_config" in session.variables:
            return session.variables["llm_config"]["value"] if isinstance(session.variables["llm_config"], dict) else session.variables.get("llm_config")

    # Fall back to global config
    try:
        config_path = os.path.join(_project_root, "config.yaml")
        if os.path.exists(config_path):
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            llm = config.get("llm", {})
            # Normalize field names: api_base -> base_url
            if "api_base" in llm and "base_url" not in llm:
                llm["base_url"] = llm["api_base"]
            if llm.get("api_key") and llm["api_key"] != "YOUR_API_KEY":
                return llm
    except Exception:
        pass

    return None


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    port = int(os.environ.get("STUDIO_PORT", 8500))
    # In Electron mode, always bind to 127.0.0.1 for security
    host = os.environ.get("STUDIO_HOST", "localhost")
    if host == "127.0.0.1":
        open_browser_enabled = False
    else:
        open_browser_enabled = True

    def open_browser():
        time.sleep(1.5)
        # Skip browser auto-open in Electron mode (when HOST=127.0.0.1)
        if open_browser_enabled:
            webbrowser.open(f"http://{host}:{port}/studio/")

    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(
        "web.studio:studio_app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
