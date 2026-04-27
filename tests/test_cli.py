"""
CLI Tests for Password Guesser Framework.

Run with: pytest tests/test_cli.py -v
"""

import pytest
import subprocess
import sys
import os
import tempfile
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCLIHelp:
    """Tests for CLI help and basic functionality."""

    def test_main_help(self):
        """Test main help output."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "password-guesser" in result.stdout
        assert "train" in result.stdout
        assert "generate" in result.stdout
        assert "scan" in result.stdout

    def test_version_command(self):
        """Test version command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "version"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Version" in result.stdout
        assert "Python" in result.stdout

    def test_all_subcommands_have_help(self):
        """Test that all subcommands have help documentation."""
        subcommands = [
            "train", "generate", "web", "pentest", "status", "interactive",
            "evaluate", "scan", "attack", "wordlist", "knowledge", "benchmark",
            "config", "hash", "encode", "report", "version", "crawl", "rl",
            "augment", "rules", "sandbox", "adversarial", "pcfg", "tools",
            "exploit", "payload", "session", "dns", "osint", "analyze", "llm",
            "graph", "evasion", "scope", "lessons", "reverse-shell", "listener",
            "network", "crypt", "api", "hashcat", "stego", "fuzz", "wifi", "db", "log"
        ]

        for cmd in subcommands:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", cmd, "--help"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0, f"Command {cmd} help failed"
            assert "usage:" in result.stdout.lower() or "usage" in result.stderr.lower()


class TestEvaluateCommand:
    """Tests for evaluate command."""

    def test_evaluate_weak_password(self):
        """Test evaluating a weak password."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "evaluate", "-p", "password"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "PASSWORD" in result.stdout
        assert "WEAK" in result.stdout.upper() or "VERY WEAK" in result.stdout.upper()

    def test_evaluate_strong_password(self):
        """Test evaluating a strong password."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "evaluate", "-p", "Xk9#mP2$vLqR7Wz!"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "STRONG" in result.stdout.upper() or "VERY STRONG" in result.stdout.upper()

    def test_evaluate_detailed(self):
        """Test detailed password evaluation."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "evaluate", "-p", "Test123!", "-d"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Criteria" in result.stdout


class TestHashCommand:
    """Tests for hash command."""

    def test_hash_text(self):
        """Test hashing text."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hash", "-t", "hello"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "MD5" in result.stdout
        assert "SHA256" in result.stdout
        # MD5 of "hello" is known
        assert "5d41402abc4b2a76b9719d911017c592" in result.stdout

    def test_hash_empty_text(self):
        """Test hashing with no arguments shows usage."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hash"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # Should show error or help
        assert "text" in result.stdout.lower() or "file" in result.stdout.lower()

    def test_hash_specific_algorithm(self):
        """Test hashing with specific algorithm."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hash", "-t", "hello", "-a", "sha256"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "SHA256" in result.stdout
        assert "MD5" not in result.stdout  # Should only show SHA256

    def test_hash_compare_match(self):
        """Test hash comparison with matching hash."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hash",
             "-t", "hello", "-c", "5d41402abc4b2a76b9719d911017c592"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "MATCH" in result.stdout

    def test_hash_file(self):
        """Test hashing a file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "hash", "-f", temp_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert "MD5" in result.stdout
        finally:
            os.unlink(temp_path)


class TestEncodeCommand:
    """Tests for encode command."""

    def test_encode_base64(self):
        """Test base64 encoding."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "encode", "-t", "hello", "-m", "base64"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        # Base64 of "hello" is "aGVsbG8="
        assert "aGVsbG8=" in result.stdout

    def test_decode_base64(self):
        """Test base64 decoding."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "encode", "-t", "aGVsbG8=", "-m", "base64", "-d"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_encode_all(self):
        """Test encoding with all methods."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "encode", "-t", "test", "-m", "all"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Base64" in result.stdout
        assert "Hex" in result.stdout


class TestWordlistCommand:
    """Tests for wordlist command."""

    def test_wordlist_generation(self):
        """Test wordlist generation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "wordlist",
                 "-o", output_path, "--pattern", "@@@2024", "--count", "10"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert os.path.exists(output_path)

            with open(output_path) as f:
                lines = f.readlines()
            assert len(lines) > 0
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_wordlist_rules_method(self):
        """Test wordlist with rules method."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "wordlist",
                 "-o", output_path, "--method", "rules", "--count", "20"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert "Generated" in result.stdout
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestReverseShellCommand:
    """Tests for reverse-shell command."""

    def test_reverse_shell_bash(self):
        """Test bash reverse shell generation."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "reverse-shell",
             "--lhost", "127.0.0.1", "--lport", "4444", "-t", "bash"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "bash" in result.stdout.lower()
        assert "127.0.0.1" in result.stdout
        assert "4444" in result.stdout

    def test_reverse_shell_all(self):
        """Test all reverse shell types."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "reverse-shell",
             "--lhost", "10.0.0.1", "--lport", "9999", "-t", "all"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "BASH" in result.stdout
        assert "PYTHON" in result.stdout
        assert "POWERSHELL" in result.stdout


class TestNetworkCommand:
    """Tests for network command."""

    def test_network_resolve(self):
        """Test DNS resolution."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "network",
             "--action", "resolve", "--target", "localhost"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "127.0.0.1" in result.stdout

    def test_network_ifconfig(self):
        """Test ifconfig action."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "network", "--action", "ifconfig"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Hostname" in result.stdout


class TestCryptCommand:
    """Tests for crypt command."""

    def test_crypt_rot13(self):
        """Test ROT13 encryption."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "crypt",
             "--action", "encrypt", "--text", "hello", "--algorithm", "rot13"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        # ROT13 of "hello" is "uryyb"
        assert "uryyb" in result.stdout

    def test_crypt_base64(self):
        """Test base64 encryption."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "crypt",
             "--action", "encrypt", "--text", "test", "--algorithm", "base64"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        # Base64 of "test" is "dGVzdA=="
        assert "dGVzdA==" in result.stdout

    def test_crypt_caesar(self):
        """Test Caesar cipher."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "crypt",
             "--action", "encrypt", "--text", "abc", "--algorithm", "caesar", "--shift", "1"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        # Caesar shift 1 of "abc" is "bcd"
        assert "bcd" in result.stdout

    def test_crypt_xor(self):
        """Test XOR encryption."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "crypt",
             "--action", "encrypt", "--text", "hello", "--algorithm", "xor", "--key", "key123"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Encrypted" in result.stdout

    def test_crypt_decrypt_rot13(self):
        """Test ROT13 decryption (same as encrypt)."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "crypt",
             "--action", "decrypt", "--text", "uryyb", "--algorithm", "rot13"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "hello" in result.stdout


class TestHashcatCommand:
    """Tests for hashcat command."""

    def test_hashcat_detect_md5(self):
        """Test MD5 hash detection."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hashcat",
             "--action", "detect", "--hash", "e10adc3949ba59abbe56e057f20f883e"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "MD5" in result.stdout

    def test_hashcat_example(self):
        """Test hashcat examples."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hashcat", "--action", "example"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Dictionary attack" in result.stdout

    def test_hashcat_benchmark(self):
        """Test hashcat benchmark."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "hashcat", "--action", "benchmark"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "MD5" in result.stdout


class TestAPICommand:
    """Tests for API command."""

    def test_api_get_httpbin(self):
        """Test API GET request to httpbin."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "api",
             "--action", "get", "--url", "http://httpbin.org/get"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "200" in result.stdout or "OK" in result.stdout

    def test_api_swagger_check(self):
        """Test API swagger detection."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "api",
             "--action", "swagger", "--url", "http://httpbin.org"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        # Either finds swagger or reports not found
        assert "Swagger" in result.stdout or "No Swagger" in result.stdout


class TestStegoCommand:
    """Tests for stego command."""

    def test_stego_list_formats(self):
        """Test stego list formats."""
        # Create a dummy file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.png', delete=False) as f:
            f.write("dummy")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "stego",
                 "--action", "list_formats", "--input", temp_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert "lsb" in result.stdout.lower()
        finally:
            os.unlink(temp_path)


class TestFuzzCommand:
    """Tests for fuzz command."""

    def test_fuzz_web(self):
        """Test web fuzzing."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "fuzz",
             "--action", "web", "--url", "http://example.com/FUZZ"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Fuzzing" in result.stdout


class TestWifiCommand:
    """Tests for wifi command."""

    def test_wifi_scan(self):
        """Test wifi scan."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "wifi", "--action", "scan"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Networks" in result.stdout or "network" in result.stdout.lower()

    def test_wifi_crack_info(self):
        """Test wifi crack info."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "wifi", "--action", "crack"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "handshake" in result.stdout.lower() or "hashcat" in result.stdout.lower()


class TestDBCommand:
    """Tests for db command."""

    def test_db_injection(self):
        """Test database injection info."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "db",
             "--action", "injection", "--target", "localhost"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "SQL Injection" in result.stdout or "payload" in result.stdout.lower()

    def test_db_schema(self):
        """Test database schema info."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "db",
             "--action", "schema", "--target", "localhost", "--type", "mysql"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "information_schema" in result.stdout.lower() or "schema" in result.stdout.lower()


class TestLogCommand:
    """Tests for log command."""

    def test_log_analyze(self):
        """Test log analysis."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("2024-01-01 ERROR: Test error message\n")
            f.write("2024-01-01 INFO: Test info message\n")
            f.write("2024-01-01 WARNING: Test warning message\n")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "log",
                 "--action", "analyze", "--file", temp_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert "ERROR" in result.stdout
            assert "WARNING" in result.stdout
        finally:
            os.unlink(temp_path)

    def test_log_search(self):
        """Test log search."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("ERROR: Database connection failed\n")
            f.write("INFO: Application started\n")
            f.write("ERROR: File not found\n")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "log",
                 "--action", "search", "--file", temp_path, "--pattern", "ERROR"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert "ERROR" in result.stdout
        finally:
            os.unlink(temp_path)

    def test_log_suspicious(self):
        """Test suspicious log detection."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("192.168.1.1 - GET /admin?user=admin' OR '1'='1\n")
            f.write("192.168.1.2 - GET /../../etc/passwd\n")
            f.write("192.168.1.3 - POST /login?user=<script>alert(1)</script>\n")
            temp_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "log",
                 "--action", "suspicious", "--file", temp_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            # Should detect suspicious patterns
            assert "suspicious" in result.stdout.lower() or "SQL" in result.stdout
        finally:
            os.unlink(temp_path)


class TestConfigCommand:
    """Tests for config command."""

    def test_config_init(self):
        """Test config initialization."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_path = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "config",
                 "--action", "init"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            # Config init may create file in cwd, check both
            # Just verify command runs successfully
            assert result.returncode == 0 or "Created" in result.stdout or "config" in result.stdout
        finally:
            if os.path.exists(config_path):
                os.unlink(config_path)


class TestPayloadCommand:
    """Tests for payload command."""

    def test_payload_reverse_shell_bash(self):
        """Test reverse shell payload generation."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "payload",
             "--type", "reverse_shell_bash", "--lhost", "127.0.0.1", "--lport", "4444"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "bash" in result.stdout.lower()
        assert "127.0.0.1" in result.stdout

    def test_payload_python_shell(self):
        """Test Python reverse shell payload."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "payload",
             "--type", "reverse_shell_python", "--lhost", "10.0.0.1", "--lport", "9999"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "python" in result.stdout.lower()
        assert "socket" in result.stdout.lower()


class TestListenerCommand:
    """Tests for listener command."""

    def test_listener_list(self):
        """Test listener list."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "listener", "--action", "list"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "Listeners" in result.stdout or "Type" in result.stdout


class TestKnowledgeCommand:
    """Tests for knowledge command."""

    def test_knowledge_stats(self):
        """Test knowledge stats."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "knowledge", "--action", "stats"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "CVE" in result.stdout or "Technique" in result.stdout


class TestReportCommand:
    """Tests for report command."""

    def test_report_generation(self):
        """Test report generation from session data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "goal": "test",
                "total_steps": 5,
                "total_reward": 10.0,
                "duration": 30,
                "steps": [{"action": "scan"}]
            }, f)
            session_path = f.name

        output_path = session_path.replace('.json', '_report.md')

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "report",
                 "--session", session_path, "--output", output_path, "--format", "markdown"],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            assert result.returncode == 0
            assert os.path.exists(output_path)
        finally:
            os.unlink(session_path)
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestCommandCount:
    """Test to verify all expected commands exist."""

    def test_command_count(self):
        """Verify we have the expected number of commands."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "--help"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0

        # Count subcommands in help output
        expected_commands = [
            "train", "generate", "web", "pentest", "status", "interactive",
            "evaluate", "scan", "attack", "wordlist", "knowledge", "benchmark",
            "config", "hash", "encode", "report", "version", "crawl", "rl",
            "augment", "rules", "sandbox", "adversarial", "pcfg", "tools",
            "exploit", "payload", "session", "dns", "osint", "analyze", "llm",
            "graph", "evasion", "scope", "lessons", "reverse-shell", "listener",
            "network", "crypt", "api", "hashcat", "stego", "fuzz", "wifi", "db", "log",
            "debug", "profile", "env", "pkg", "script", "data", "output", "doc", "help"
        ]

        for cmd in expected_commands:
            assert cmd in result.stdout, f"Command '{cmd}' not found in help"

    def test_debug_info(self):
        """Test debug info command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "debug", "--action", "info"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "Python" in result.stdout

    def test_debug_check(self):
        """Test debug check command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "debug", "--action", "check"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_debug_deps(self):
        """Test debug deps command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "debug", "--action", "deps"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_debug_config(self):
        """Test debug config command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "debug", "--action", "config"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_debug_memory(self):
        """Test debug memory command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "debug", "--action", "memory"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_profile_benchmark(self):
        """Test profile benchmark command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "profile", "--action", "benchmark"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_profile_compare(self):
        """Test profile compare command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "profile", "--action", "compare"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_env_show(self):
        """Test env show command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "env", "--action", "show"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "ENVIRONMENT" in result.stdout

    def test_env_init(self):
        """Test env init command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "env", "--action", "init"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "OK" in result.stdout

    def test_pkg_list(self):
        """Test pkg list command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "pkg", "--action", "list", "--type", "python"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_pkg_check(self):
        """Test pkg check command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "pkg", "--action", "check"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0

    def test_script_help(self):
        """Test script help command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "script", "--help"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "validate" in result.stdout

    def test_script_validate(self):
        """Test script validate with non-existent file."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "script", "nonexistent.pg", "--validate"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "not found" in result.stdout

    def test_output_formats(self):
        """Test output format command."""
        for fmt in ["table", "json", "csv", "markdown"]:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "output", "--format", fmt],
                capture_output=True, text=True,
                cwd="D:/password_guesser"
            )
            assert result.returncode == 0

    def test_doc_list(self):
        """Test doc list command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "doc", "--list"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "train" in result.stdout

    def test_doc_topic(self):
        """Test doc topic command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "doc", "train"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "Training" in result.stdout

    def test_data_validate_json(self):
        """Test data validate with JSON file."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump({"test": "data"}, f)
            tmpfile = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "data",
                 "--action", "validate", "--input", tmpfile],
                capture_output=True, text=True,
                cwd="D:/password_guesser"
            )
            assert result.returncode == 0
            assert "Valid JSON" in result.stdout
        finally:
            os.unlink(tmpfile)

    def test_data_stats_json(self):
        """Test data stats with JSON file."""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False, encoding="utf-8") as f:
            json.dump([{"a": 1}, {"a": 2}], f)
            tmpfile = f.name

        try:
            result = subprocess.run(
                [sys.executable, "password_guesser/cli.py", "data",
                 "--action", "stats", "--input", tmpfile],
                capture_output=True, text=True,
                cwd="D:/password_guesser"
            )
            assert result.returncode == 0
        finally:
            os.unlink(tmpfile)


class TestHelpCommand:
    """Test help command functionality."""

    def test_help_no_args(self):
        """Test help command without arguments."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "help"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "Command Reference" in result.stdout
        assert "Core Commands" in result.stdout

    def test_help_specific_command(self):
        """Test help for a specific command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "help", "scan"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "SCAN" in result.stdout
        assert "scanning" in result.stdout.lower()

    def test_help_with_examples(self):
        """Test help with examples flag."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "help", "train", "--examples"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "Examples" in result.stdout
        assert "password-guesser train" in result.stdout

    def test_help_with_verbose(self):
        """Test help with verbose flag."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "help", "interactive", "-v"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "INTERACTIVE" in result.stdout

    def test_help_unknown_command(self):
        """Test help for unknown command."""
        result = subprocess.run(
            [sys.executable, "password_guesser/cli.py", "help", "nonexistent123"],
            capture_output=True, text=True,
            cwd="D:/password_guesser"
        )
        assert result.returncode == 0
        assert "No detailed help" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
