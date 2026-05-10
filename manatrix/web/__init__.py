"""
Manatrix Web - Web Interface Module

Provides a unified web interface for the Manatrix framework,
integrating FastAPI, WebSocket, and studio components.
"""

from .app import create_app, run_server, get_app_info

__all__ = [
    "create_app",
    "run_server",
    "get_app_info",
]