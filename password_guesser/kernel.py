"""
Password Guesser Jupyter Kernel

Provides a Jupyter kernel for interactive password guessing sessions.
"""

from ipykernel.kernelbase import Kernel
from ipykernel.kernelapp import IPKernelApp
import json
import sys
import subprocess
from typing import Any

__version__ = "1.0.0"


class PasswordGuesserKernel(Kernel):
    """Jupyter kernel for Password Guesser CLI."""

    banner = """
Password Guesser Kernel
========================
Interactive kernel for password generation, evaluation, and attack simulation.

Commands:
  !pg <command>  - Run password-guesser CLI command
  ?func          - Show help for function
  demo(name)     - Run demonstration

Example:
  !pg help scan
  !pg chart -o mychart.png --type bar
  demo("password")
"""

    implementation = "PasswordGuesser"
    implementation_version = __version__

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history = []

    def do_execute(self, code: str, silent: bool, store_history: bool = True,
                   user_expressions: dict = None, allow_stdin: bool = False) -> dict:

        if code.strip().startswith("!"):
            # Run as CLI command
            cmd = code.strip()[1:].strip()
            parts = cmd.split()
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "password_guesser.cli"] + parts,
                    capture_output=True, text=True, timeout=30
                )
                output = result.stdout + result.stderr
                return_code = result.returncode
            except subprocess.TimeoutExpired:
                output = "Command timed out"
                return_code = -1
            except Exception as e:
                output = f"Error: {e}"
                return_code = -1

            if not silent:
                stream_content = {"name": "stdout", "text": output}
                self.send_response(self.iopub_socket, "stream", stream_content)

            return {
                "status": "ok" if return_code == 0 else "error",
                "execution_count": self.execution_count,
                "payload": [],
                "user_expressions": {},
            }

        elif code.strip().startswith("?"):
            # Show help
            topic = code.strip()[1:].strip()
            if topic:
                output = f"Showing help for: {topic}\n"
                output += f"Run '!pg help {topic}' for details\n"
            else:
                output = self.banner

            if not silent:
                stream_content = {"name": "stdout", "text": output}
                self.send_response(self.iopub_socket, "stream", stream_content)

            return {"status": "ok", "execution_count": self.execution_count,
                    "payload": [], "user_expressions": {}}

        elif code.strip().startswith("demo"):
            # Run demo
            import re
            match = re.search(r'demo\(["\']([^"\']+)["\']\)', code)
            if match:
                topic = match.group(1)
                output = f"Running demo: {topic}\n\n"
                result = subprocess.run(
                    [sys.executable, "-m", "password_guesser.cli", "demo", topic],
                    capture_output=True, text=True, timeout=30
                )
                output += result.stdout
            else:
                output = "Usage: demo('name') where name is password, scan, attack, chart, pipeline"

            if not silent:
                stream_content = {"name": "stdout", "text": output}
                self.send_response(self.iopub_socket, "stream", stream_content)

            return {"status": "ok", "execution_count": self.execution_count,
                    "payload": [], "user_expressions": {}}

        else:
            # Python code - try to execute
            try:
                exec(code, {"__builtins__": {}})
                output = ""
            except Exception as e:
                output = f"Error: {type(e).__name__}: {e}"

            if not silent and output:
                stream_content = {"name": "stdout", "text": output}
                self.send_response(self.iopub_socket, "stream", stream_content)

            return {"status": "ok", "execution_count": self.execution_count,
                    "payload": [], "user_expressions": {}}

    def do_complete(self, code: str, cursor_pos: int) -> dict:
        """Provide tab completion."""
        # Simple completion - just return what we have
        completions = [
            "!pg", "!help", "!chart", "!scan", "!attack",
            "?", "demo(",
        ]
        return {
            "status": "ok",
            "cursor_start": 0,
            "cursor_end": cursor_pos,
            "matches": completions
        }

    def do_inspect(self, code: str, cursor_pos: int, detail_level: int = 0) -> dict:
        """Provide object introspection."""
        return {
            "status": "ok",
            "found": False,
            "data": {},
            "metadata": {}
        }


if __name__ == "__main__":
    IPKernelApp.launch_instance(kernel_class=PasswordGuesserKernel)