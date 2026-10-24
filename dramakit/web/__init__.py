"""Local web console: a zero-dependency (stdlib http.server) single-page app
that drives the whole DramaKit pipeline through the AI-native layer.

`dj serve` starts it. Everything the CLI can do, the console can do, plus the
AI setup / search / action panels.
"""
from .server import serve

__all__ = ["serve"]
