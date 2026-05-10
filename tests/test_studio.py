"""
Unit Tests for Manatrix Studio API

Run with: pytest tests/test_studio.py -v
"""

import pytest
import sys
import os
import json
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


class TestStudioAPI:
    """Test all studio.py API endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client."""
        from web.studio import studio_app
        self.client = TestClient(studio_app)

    # =============================================================================
    # Info & Themes
    # =============================================================================

    def test_api_info(self):
        """Test /api/info endpoint."""
        response = self.client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Manatrix Studio"
        assert "version" in data
        assert "panels" in data

    def test_api_themes(self):
        """Test /api/themes endpoint returns all themes."""
        response = self.client.get("/api/themes")
        assert response.status_code == 200
        data = response.json()
        assert "themes" in data
        themes = data["themes"]
        assert len(themes) == 5
        theme_ids = [t["id"] for t in themes]
        assert "dark" in theme_ids
        assert "light" in theme_ids
        assert "matrix" in theme_ids
        assert "nord" in theme_ids
        assert "solarized" in theme_ids

    # =============================================================================
    # File Browser
    # =============================================================================

    def test_api_files_list(self):
        """Test /api/files listing."""
        response = self.client.get("/api/files?path=.")
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "items" in data

    def test_api_files_list_root(self):
        """Test /api/files with non-existent path."""
        response = self.client.get("/api/files?path=/nonexistent")
        assert response.status_code == 200
        data = response.json()
        # Should return error or empty list
        assert "path" in data

    # =============================================================================
    # Git API
    # =============================================================================

    def test_api_git_status(self):
        """Test /api/git/status endpoint."""
        response = self.client.get("/api/git/status")
        assert response.status_code == 200
        data = response.json()
        # May fail if not in git repo, that's ok
        if data["success"]:
            assert "branch" in data
            assert "files" in data
            assert "clean" in data

    def test_api_git_log(self):
        """Test /api/git/log endpoint."""
        response = self.client.get("/api/git/log?limit=5")
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert "commits" in data
            for commit in data["commits"]:
                assert "hash" in commit
                assert "message" in commit

    def test_api_git_branches(self):
        """Test /api/git/branches endpoint."""
        response = self.client.get("/api/git/branches")
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert "branches" in data
            assert "current" in data

    def test_api_git_diff(self):
        """Test /api/git/diff endpoint."""
        response = self.client.get("/api/git/diff")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "diff" in data

    # =============================================================================
    # Snippets API
    # =============================================================================

    def test_api_snippets_list(self):
        """Test /api/snippets GET."""
        response = self.client.get("/api/snippets")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "snippets" in data
        assert "python" in data["snippets"]
        assert "shell" in data["snippets"]

    def test_api_snippets_add(self):
        """Test /api/snippets POST (add snippet)."""
        response = self.client.post("/api/snippets", json={
            "category": "python",
            "snippet": {
                "name": "Test Snippet",
                "code": "print('test')",
                "desc": "Test description"
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_api_snippets_delete(self):
        """Test /api/snippets DELETE."""
        # First add
        add_resp = self.client.post("/api/snippets", json={
            "category": "test_cat",
            "snippet": {"name": "Temp", "code": "x=1"}
        })
        snippet_id = add_resp.json().get("id")

        # Then delete
        if snippet_id:
            del_resp = self.client.delete(f"/api/snippets?category=test_cat&snippet_id={snippet_id}")
            assert del_resp.status_code == 200

    # =============================================================================
    # REPL API
    # =============================================================================

    def test_api_repl_python(self):
        """Test /api/repl/python execution."""
        response = self.client.post("/api/repl/python", json={
            "code": "print(2 + 2)"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stdout" in data
        assert "4" in data["stdout"]

    def test_api_repl_python_error(self):
        """Test /api/repl/python error handling."""
        response = self.client.post("/api/repl/python", json={
            "code": "print(undefined_var)"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True  # Python itself returns success
        assert "stderr" in data

    def test_api_repl_shell(self):
        """Test /api/repl/shell execution."""
        response = self.client.post("/api/repl/shell", json={
            "command": "echo test_output"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "test_output" in data["stdout"]

    def test_api_repl_shell_empty(self):
        """Test /api/repl/shell with empty command."""
        response = self.client.post("/api/repl/shell", json={
            "command": ""
        })
        data = response.json()
        assert data["success"] is False

    # =============================================================================
    # Workspace API
    # =============================================================================

    def test_api_workspace_save(self):
        """Test /api/workspace/save."""
        response = self.client.post("/api/workspace/save", json={
            "session_id": "test_session",
            "workspace": {"theme": "dark", "tabs": []}
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "path" in data

    def test_api_workspace_load(self):
        """Test /api/workspace/load."""
        # Save first
        self.client.post("/api/workspace/save", json={
            "session_id": "test_load_session",
            "workspace": {"theme": "light"}
        })
        # Then load
        response = self.client.get("/api/workspace/load?session_id=test_load_session")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["workspace"]["theme"] == "light"

    def test_api_workspace_load_not_found(self):
        """Test /api/workspace/load when no workspace exists."""
        response = self.client.get("/api/workspace/load?session_id=nonexistent_session_xyz")
        data = response.json()
        # May succeed if there's any other workspace, or return error
        assert "success" in data

    # =============================================================================
    # Search API
    # =============================================================================

    def test_api_search(self):
        """Test /api/search endpoint."""
        response = self.client.post("/api/search", json={
            "query": "def main",
            "path": "manatrix"
        })
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "results" in data
        assert "total" in data
        assert "files_searched" in data

    def test_api_search_regex(self):
        """Test /api/search with regex."""
        response = self.client.post("/api/search", json={
            "pattern": r"import\s+\w+",
            "path": "manatrix",
            "use_regex": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_api_search_empty(self):
        """Test /api/search with empty query."""
        response = self.client.post("/api/search", json={
            "query": "",
            "path": "."
        })
        data = response.json()
        assert data["success"] is False

    def test_api_search_replace_dry_run(self):
        """Test /api/search/replace with dry_run."""
        response = self.client.post("/api/search/replace", json={
            "query": "test_search_term",
            "replacement": "replaced",
            "dry_run": True
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["dry_run"] is True

    # =============================================================================
    # Chart API
    # =============================================================================

    def test_api_chart_bar(self):
        """Test /api/chart for bar chart."""
        response = self.client.post("/api/chart", json={
            "type": "bar",
            "data": {
                "labels": ["A", "B", "C"],
                "values": [10, 20, 30]
            }
        })
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert "image_url" in data

    def test_api_chart_pie(self):
        """Test /api/chart for pie chart."""
        response = self.client.post("/api/chart", json={
            "type": "pie",
            "data": {
                "labels": ["X", "Y"],
                "values": [30, 70]
            }
        })
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert "image_url" in data

    # =============================================================================
    # Notebook API
    # =============================================================================

    def test_api_notebook_read_not_found(self):
        """Test /api/notebook/read with non-existent notebook."""
        response = self.client.get("/api/notebook/read?path=/nonexistent.ipynb")
        data = response.json()
        assert data["success"] is False

    def test_api_notebook_read_no_path(self):
        """Test /api/notebook/read without path."""
        response = self.client.get("/api/notebook/read")
        data = response.json()
        assert data["success"] is False

    def test_api_notebook_execute(self):
        """Test /api/notebook/execute."""
        response = self.client.post("/api/notebook/execute", json={
            "code": "x = 42\nprint(x)"
        })
        assert response.status_code == 200
        data = response.json()
        assert "outputs" in data

    # =============================================================================
    # Report API
    # =============================================================================

    def test_api_report_templates(self):
        """Test /api/report/templates."""
        response = self.client.get("/api/report/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "technical" in data["templates"]
        assert "executive" in data["templates"]

    def test_api_report_generate_html(self):
        """Test /api/report/generate for HTML."""
        response = self.client.post("/api/report/generate", json={
            "template": "technical",
            "title": "Test Report",
            "format": "html",
            "findings": [
                {"title": "SQL Injection", "severity": "Critical", "description": "Found SQLi", "remediation": "Fix queries"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert "path" in data
            assert data["format"] == "html"

    def test_api_report_generate_md(self):
        """Test /api/report/generate for Markdown."""
        response = self.client.post("/api/report/generate", json={
            "template": "executive",
            "title": "Test MD Report",
            "format": "markdown"
        })
        assert response.status_code == 200
        data = response.json()
        if data["success"]:
            assert data["format"] == "markdown"

    def test_api_report_invalid_template(self):
        """Test /api/report/generate with invalid template."""
        response = self.client.post("/api/report/generate", json={
            "template": "nonexistent_template"
        })
        data = response.json()
        assert data["success"] is False

    # =============================================================================
    # Wordlist API
    # =============================================================================

    def test_api_wordlist_analyze_no_file(self):
        """Test /api/wordlist/analyze without file."""
        response = self.client.post("/api/wordlist/analyze", json={
            "path": ""
        })
        data = response.json()
        assert data["success"] is False

    def test_api_wordlist_analyze_not_found(self):
        """Test /api/wordlist/analyze with non-existent file."""
        response = self.client.post("/api/wordlist/analyze", json={
            "path": "/nonexistent/wordlist.txt"
        })
        data = response.json()
        assert data["success"] is False

    # =============================================================================
    # Recording API
    # =============================================================================

    def test_api_recording_list(self):
        """Test /api/recording/list."""
        response = self.client.get("/api/recording/list")
        assert response.status_code == 200
        data = response.json()
        assert "recordings" in data

    def test_api_recording_save(self):
        """Test /api/recording/save."""
        response = self.client.post("/api/recording/save", json={
            "name": "Test Recording",
            "commands": [
                {"command": "ls", "timestamp": 0},
                {"command": "pwd", "timestamp": 500}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_api_recording_load(self):
        """Test /api/recording/load."""
        # Save first
        save_resp = self.client.post("/api/recording/save", json={
            "name": "Test Load",
            "commands": [{"command": "echo test", "timestamp": 0}]
        })
        rec_id = save_resp.json().get("id")

        if rec_id:
            response = self.client.get(f"/api/recording/load/{rec_id}")
            data = response.json()
            assert data["success"] is True

    def test_api_recording_load_not_found(self):
        """Test /api/recording/load with non-existent recording."""
        response = self.client.get("/api/recording/load/nonexistent_recording")
        data = response.json()
        assert data["success"] is False

    def test_api_recording_delete(self):
        """Test /api/recording/delete."""
        # Save first
        save_resp = self.client.post("/api/recording/save", json={
            "name": "To Delete",
            "commands": []
        })
        rec_id = save_resp.json().get("id")

        if rec_id:
            response = self.client.delete(f"/api/recording/{rec_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    # =============================================================================
    # Attack Graph API
    # =============================================================================

    def test_api_attack_graph(self):
        """Test /api/attack-graph."""
        response = self.client.get("/api/attack-graph")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "nodes" in data
        assert "edges" in data
        assert "total_nodes" in data
        assert "total_edges" in data

    # =============================================================================
    # Session & Completions
    # =============================================================================

    def test_api_session_state(self):
        """Test /api/session/{id}/state."""
        response = self.client.get("/api/session/test_session/state")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_api_session_execute(self):
        """Test /api/session/{id}/execute."""
        response = self.client.post(
            "/api/session/test_session/execute",
            json={"command": "ls"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "stdout" in data

    def test_api_history(self):
        """Test /api/history."""
        response = self.client.get("/api/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data

    def test_api_completions_empty(self):
        """Test /api/completions with empty prefix."""
        response = self.client.get("/api/completions?prefix=")
        assert response.status_code == 200
        data = response.json()
        assert "completions" in data

    def test_api_completions_with_prefix(self):
        """Test /api/completions with prefix."""
        response = self.client.get("/api/completions?prefix=scan")
        assert response.status_code == 200
        data = response.json()
        assert "completions" in data


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
