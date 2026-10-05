"""ROAR's Python API. Importing this package does not start a GUI.

Use Design for headless input/serialization, Technologies for LUT discovery,
and Session for live Qt plots. Equations are trusted input, not a sandbox.
"""

from .design import Design, Graph
from .evaluation import EvaluationResult, Technologies
from .session import LiveGraph, Session

__version__ = "1.0.2"
__all__ = ["Design", "Graph", "Session", "LiveGraph", "Technologies", "EvaluationResult", "launch"]


def launch(design=None, *, home=None, run=False):
    """Show a design (or saved-state path); optionally run a standalone Qt loop.

    In notebooks enable Qt integration first; leave run=False and retain the
    returned Session. Standalone scripts can use Session(...).run() instead.
    """
    if design is not None and not isinstance(design, Design):
        design = Design.load(design)
    session = Session(design, home=home, show=True)
    if run:
        session.run()
    return session