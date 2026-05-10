"""
Manatrix Web Application Factory

Creates and configures the FastAPI application with all required
middleware, routes, and WebSocket support.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# Global app instance
_app: Optional[FastAPI] = None


def create_app(
    title: str = "Manatrix",
    version: str = "1.0.0",
    debug: bool = False,
    cors_origins: Optional[list] = None,
    static_path: Optional[str] = None,
    template_path: Optional[str] = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: Application title
        version: Application version
        debug: Enable debug mode
        cors_origins: CORS allowed origins
        static_path: Path to static files directory
        template_path: Path to templates directory

    Returns:
        Configured FastAPI application instance

    Example:
        >>> app = create_app(title="MyApp", debug=True)
        >>> # Add custom routes...
    """
    global _app

    # Determine default paths
    if static_path is None:
        static_path = str(Path(__file__).parent / "static")
    if template_path is None:
        template_path = str(Path(__file__).parent / "templates")

    # Create app
    app = FastAPI(
        title=title,
        version=version,
        debug=debug,
        description="Manatrix - Password Guessing & PenTest Framework",
    )

    # CORS middleware
    if cors_origins is None:
        cors_origins = ["*"]  # Allow all in development

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    # Templates
    if os.path.exists(template_path):
        templates = Jinja2Templates(directory=template_path)

        @app.get("/")
        async def root():
            return {"message": "Manatrix API", "version": version}

        @app.get("/health")
        async def health():
            return {"status": "ok", "version": version}

    # Store app
    _app = app

    return app


def get_app() -> Optional[FastAPI]:
    """
    Get the current application instance.

    Returns:
        FastAPI app instance or None
    """
    return _app


async def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """
    Run the Manatrix web server.

    Args:
        host: Server host address
        port: Server port
        reload: Enable auto-reload
        log_level: Logging level
    """
    import uvicorn

    if _app is None:
        create_app()

    uvicorn.run(
        _app,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


def get_app_info() -> Dict[str, Any]:
    """
    Get application information.

    Returns:
        Dictionary with app metadata
    """
    return {
        "name": "Manatrix",
        "version": "1.0.0",
        "description": "Password Guessing & PenTest Framework",
        "framework": "FastAPI",
        "features": [
            "REST API",
            "WebSocket",
            "Static Files",
            "Templates",
            "CORS",
        ],
    }


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)


# Global connection manager
manager = ConnectionManager()


# WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.

    Usage:
        ws://localhost:8000/ws
    """
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Echo back (customize as needed)
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        print(f"WebSocket error: {e}")


# Add WebSocket route if app exists
if _app is not None:
    @_app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket_endpoint(websocket)