"""Live reload service for theme development.

Watches theme directories for file changes and notifies connected
WebSocket clients to reload the page. Only active in debug mode.
"""

import asyncio
import logging
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from squishmark.config import get_settings

logger = logging.getLogger("squishmark.livereload")


class LiveReloadService:
    """Manages file watching and WebSocket client notifications."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._watch_task: asyncio.Task[None] | None = None

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a WebSocket connection and add it to the client set."""
        await websocket.accept()
        self._clients.add(websocket)
        logger.debug("LiveReload client connected (%d total)", len(self._clients))

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the client set."""
        self._clients.discard(websocket)
        logger.debug("LiveReload client disconnected (%d remaining)", len(self._clients))

    async def _notify_clients(self) -> None:
        """Send reload message to all connected clients."""
        if not self._clients:
            return

        disconnected: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text("reload")
            except Exception:
                disconnected.append(ws)

        for ws in disconnected:
            self._clients.discard(ws)

    def _get_watch_paths(self) -> list[Path]:
        """Determine which directories to watch for changes."""
        settings = get_settings()
        paths: list[Path] = []

        # Watch bundled themes directory
        themes_path = Path(settings.resolved_themes_path)
        if themes_path.exists():
            paths.append(themes_path)

        # Watch content repo's theme/ directory (local dev only)
        if settings.is_local_content:
            content_path = Path(settings.github_content_repo[7:])  # Strip file://
            theme_dir = content_path / "theme"
            if theme_dir.exists():
                paths.append(theme_dir)

        return paths

    async def _watch_loop(self) -> None:
        """Watch theme directories and notify clients on changes."""
        try:
            from watchfiles import awatch
        except ImportError:
            logger.warning("watchfiles not installed — live reload file watching disabled")
            return

        paths = self._get_watch_paths()
        if not paths:
            logger.warning("No theme directories found to watch")
            return

        logger.info("LiveReload watching: %s", ", ".join(str(p) for p in paths))

        try:
            async for changes in awatch(*paths):
                changed_files = [str(p) for _, p in changes]
                logger.info("Theme files changed: %s", ", ".join(changed_files))
                await self._notify_clients()
        except asyncio.CancelledError:
            pass

    async def start(self) -> None:
        """Start the file watcher background task."""
        if self._watch_task is not None:
            return
        self._watch_task = asyncio.create_task(self._watch_loop())
        logger.info("LiveReload watcher started")

    async def stop(self) -> None:
        """Stop the file watcher and disconnect all clients."""
        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

        # Close all WebSocket connections
        for ws in list(self._clients):
            try:
                await ws.close()
            except Exception:
                pass
        self._clients.clear()
        logger.info("LiveReload watcher stopped")

    async def handle_websocket(self, websocket: WebSocket) -> None:
        """Handle a single WebSocket client connection."""
        await self.connect(websocket)
        try:
            # Keep the connection alive until client disconnects
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            self.disconnect(websocket)


# Script tag injected before </body> in HTML responses during debug mode.
_SCRIPT_PATH = Path(__file__).parent / "livereload.js"
_LIVERELOAD_SCRIPT = "<script>" + _SCRIPT_PATH.read_text() + "</script>"


class LiveReloadMiddleware:
    """ASGI middleware that injects the LiveReload script into HTML responses.

    Only active when debug mode is enabled. Inserts a small ``<script>`` tag
    just before ``</body>`` so that every page automatically connects to the
    LiveReload WebSocket.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Buffer response headers so we can check content-type before sending
        is_html = False
        original_status: int = 200
        original_headers: list[tuple[bytes, bytes]] = []
        body_chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal is_html, original_status, original_headers

            if message["type"] == "http.response.start":
                original_status = message.get("status", 200)
                original_headers = list(message.get("headers", []))
                # Check if this is an HTML response
                for name, value in original_headers:
                    if name.lower() == b"content-type" and b"text/html" in value.lower():
                        is_html = True
                        break

                if not is_html:
                    # Not HTML — pass through immediately
                    await send(message)
                # If HTML, buffer the start message until we can fix content-length

            elif message["type"] == "http.response.body":
                if not is_html:
                    await send(message)
                    return

                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                body_chunks.append(body)

                if not more_body:
                    # Final chunk — inject the script
                    full_body = b"".join(body_chunks)
                    full_body = _inject_script(full_body)

                    # Update content-length header
                    new_headers = [
                        (name, value) for name, value in original_headers if name.lower() != b"content-length"
                    ]
                    new_headers.append((b"content-length", str(len(full_body)).encode()))

                    await send({"type": "http.response.start", "status": original_status, "headers": new_headers})
                    await send({"type": "http.response.body", "body": full_body, "more_body": False})
            else:
                await send(message)

        await self.app(scope, receive, send_wrapper)


def _inject_script(body: bytes) -> bytes:
    """Inject the LiveReload script before </body> in HTML."""
    marker = b"</body>"
    idx = body.lower().rfind(marker)
    if idx == -1:
        return body
    return body[:idx] + _LIVERELOAD_SCRIPT.encode() + body[idx:]


# Global service instance
_livereload_service: LiveReloadService | None = None


def get_livereload_service() -> LiveReloadService:
    """Get or create the global LiveReload service instance."""
    global _livereload_service
    if _livereload_service is None:
        _livereload_service = LiveReloadService()
    return _livereload_service


def reset_livereload_service() -> None:
    """Reset the global LiveReload service."""
    global _livereload_service
    _livereload_service = None
