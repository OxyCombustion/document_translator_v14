"""Visualization utilities."""

# Lazy imports to avoid tkinter dependency in headless environments
__all__ = ['GUIViewerAgent']

def __getattr__(name):
    if name == 'GUIViewerAgent':
        try:
            from .gui_viewer_agent import GUIViewerAgent
            return GUIViewerAgent
        except ImportError as e:
            raise ImportError(f"GUIViewerAgent requires tkinter: {e}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
