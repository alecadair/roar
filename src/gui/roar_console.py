"""
ROARConsole  – Interactive Python console widget (PyQt6 + QScintilla)
ROARTextEditor – Python code editor with syntax & error highlighting

Both widgets use PyQt6-QScintilla (``PyQt6.Qsci``) so there is no need
for hand-rolled lexers or regex-based colouring.

Dependencies (pip install):
    PyQt6  PyQt6-QScintilla  jedi
"""

from __future__ import annotations

import code
import contextlib
import io
import sys
import traceback
import threading
from typing import Any, Dict, Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QKeyEvent

from PyQt6.Qsci import (
    QsciScintilla,
    QsciLexerPython,
)


# ---------------------------------------------------------------------------
#  Shared dark-theme colour palette
# ---------------------------------------------------------------------------
_BG         = QColor("#1e1e1e")
_FG         = QColor("#d4d4d4")
_MARGIN_BG  = QColor("#2a2a2a")
_MARGIN_FG  = QColor("#858585")
_CARET_LINE = QColor("#2a2d2e")
_SEL_BG     = QColor("#264f78")
_ERR_MARKER = QColor("#ff4444")
_WARN_MARKER = QColor("#ffcc00")


def _apply_dark_python_lexer(editor: QsciScintilla, font: QFont) -> QsciLexerPython:
    """Create a dark-themed Python lexer and attach it to *editor*."""
    lexer = QsciLexerPython(editor)
    lexer.setFont(font)
    lexer.setDefaultPaper(_BG)
    lexer.setDefaultColor(_FG)

    # Token colours (VS-Code-ish dark palette)
    _token_colours = {
        QsciLexerPython.Default:            _FG,
        QsciLexerPython.Comment:            QColor("#6a9955"),
        QsciLexerPython.CommentBlock:       QColor("#6a9955"),
        QsciLexerPython.Number:             QColor("#b5cea8"),
        QsciLexerPython.DoubleQuotedString: QColor("#ce9178"),
        QsciLexerPython.SingleQuotedString: QColor("#ce9178"),
        QsciLexerPython.TripleSingleQuotedString: QColor("#ce9178"),
        QsciLexerPython.TripleDoubleQuotedString: QColor("#ce9178"),
        QsciLexerPython.Keyword:            QColor("#569cd6"),
        QsciLexerPython.ClassName:          QColor("#4ec9b0"),
        QsciLexerPython.FunctionMethodName: QColor("#dcdcaa"),
        QsciLexerPython.Operator:           QColor("#d4d4d4"),
        QsciLexerPython.Identifier:         QColor("#9cdcfe"),
        QsciLexerPython.Decorator:          QColor("#dcdcaa"),
        QsciLexerPython.UnclosedString:     QColor("#ff4444"),
    }
    for style_id, colour in _token_colours.items():
        lexer.setColor(colour, style_id)
        lexer.setPaper(_BG, style_id)

    editor.setLexer(lexer)
    return lexer


def _base_editor_setup(editor: QsciScintilla, font: QFont, *, read_only: bool = False):
    """Common look & feel shared by the console and the editor."""
    editor.setFont(font)
    editor.setMarginsFont(font)

    # Colours
    editor.setPaper(_BG)
    editor.setColor(_FG)
    editor.setCaretForegroundColor(_FG)
    editor.setCaretLineVisible(True)
    editor.setCaretLineBackgroundColor(_CARET_LINE)
    editor.setSelectionBackgroundColor(_SEL_BG)
    editor.setMarginsBackgroundColor(_MARGIN_BG)
    editor.setMarginsForegroundColor(_MARGIN_FG)
    editor.setMatchedBraceBackgroundColor(QColor("#3a3a3a"))
    editor.setMatchedBraceForegroundColor(QColor("#dcdcaa"))
    editor.setUnmatchedBraceBackgroundColor(QColor("#5a1d1d"))
    editor.setUnmatchedBraceForegroundColor(QColor("#ff4444"))

    # Brace matching
    editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

    # Indentation
    editor.setIndentationsUseTabs(False)
    editor.setTabWidth(4)
    editor.setAutoIndent(True)
    editor.setIndentationGuides(True)
    editor.setIndentationGuidesBackgroundColor(QColor("#3a3a3a"))
    editor.setIndentationGuidesForegroundColor(QColor("#3a3a3a"))

    # Miscellaneous
    editor.setUtf8(True)
    editor.setEolMode(QsciScintilla.EolMode.EolUnix)
    if read_only:
        editor.setReadOnly(True)


# ═══════════════════════════════════════════════════════════════════════════
#  ROARConsole – interactive Python console
# ═══════════════════════════════════════════════════════════════════════════

class _ConsoleScintilla(QsciScintilla):
    """Scintilla sub-class that restricts editing to the current input area."""

    execute_requested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._prompt = ">>> "
        self._continuation = "... "
        self._input_start: int = 0
        self._history: list[str] = []
        self._history_idx: int = 0

    # -- public helpers -----------------------------------------------------

    @property
    def input_start(self) -> int:
        return self._input_start

    def append_text(self, text: str, *, colour: Optional[QColor] = None):
        """Append *text* at the very end (output area)."""
        read_only_was = self.isReadOnly()
        self.setReadOnly(False)
        end_pos = self.length()
        self.SendScintilla(QsciScintilla.SCI_SETSEL, end_pos, end_pos)
        self.insert(text)
        # If a colour was requested, style the newly-inserted text
        if colour is not None:
            new_end = self.length()
            # Use indicator 1 for coloured output
            self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, 1)
            self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE,
                               end_pos, new_end - end_pos)
        self.SendScintilla(QsciScintilla.SCI_DOCUMENTEND)
        self.setReadOnly(read_only_was)

    def show_prompt(self, continuation: bool = False):
        """Write the prompt string and mark the start of user input."""
        prompt = self._continuation if continuation else self._prompt
        self.append_text(prompt)
        self._input_start = self.length()

    def current_input(self) -> str:
        """Return text the user has typed after the last prompt."""
        # _input_start is a Scintilla byte offset (UTF-8), so slice in bytes
        return self.text().encode("utf-8")[self._input_start:].decode("utf-8", errors="replace")

    # -- key handling -------------------------------------------------------

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        mod = event.modifiers()
        cur_pos = self.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS)

        # Prevent editing before the input area
        if cur_pos < self._input_start:
            if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
                return
            if mod & Qt.KeyboardModifier.ControlModifier:
                if key in (Qt.Key.Key_C, Qt.Key.Key_A):
                    super().keyPressEvent(event)
                    return
            self.SendScintilla(QsciScintilla.SCI_DOCUMENTEND)

        # Backspace: don't delete past prompt
        if key == Qt.Key.Key_Backspace:
            if cur_pos <= self._input_start:
                return

        # Enter / Return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            src = self.current_input().rstrip("\n")
            self.append_text("\n")
            self.execute_requested.emit(src)
            return

        # History navigation
        if key == Qt.Key.Key_Up:
            self._navigate_history(-1)
            return
        if key == Qt.Key.Key_Down:
            self._navigate_history(1)
            return

        # Home key goes to start of input, not start of line
        if key == Qt.Key.Key_Home and not (mod & Qt.KeyboardModifier.ControlModifier):
            self.SendScintilla(QsciScintilla.SCI_SETSEL,
                               self._input_start, self._input_start)
            return

        super().keyPressEvent(event)

    def _navigate_history(self, direction: int):
        if not self._history:
            return
        self._history_idx = max(0, min(self._history_idx + direction,
                                       len(self._history)))
        end = self.length()
        self.SendScintilla(QsciScintilla.SCI_SETSEL, self._input_start, end)
        self.removeSelectedText()
        if self._history_idx < len(self._history):
            self.insert(self._history[self._history_idx])
        self.SendScintilla(QsciScintilla.SCI_DOCUMENTEND)


class ROARConsole(QWidget):
    """Interactive Python console widget backed by ``code.InteractiveConsole``.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.
    locals_ : dict, optional
        Namespace exposed to the console.  Defaults to a minimal namespace.
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 locals_: Optional[Dict[str, Any]] = None):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 60)

        if locals_ is None:
            locals_ = {"__name__": "__console__", "__doc__": None}

        self._locals = locals_
        self._shell = code.InteractiveConsole(self._locals)
        self._command_running = False
        self._multiline_buffer: list[str] = []

        # ---- UI -----------------------------------------------------------
        font = QFont("Courier", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)

        self._editor = _ConsoleScintilla(self)
        _base_editor_setup(self._editor, font)
        _apply_dark_python_lexer(self._editor, font)

        # Red-text indicator for stderr output
        self._editor.indicatorDefine(
            QsciScintilla.IndicatorStyle.TextColorIndicator, 1)
        self._editor.setIndicatorForegroundColor(_ERR_MARKER, 1)

        # Disable line-number margin for the console
        self._editor.setMarginWidth(0, 0)

        self._editor.execute_requested.connect(self._on_execute)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)

        # Banner
        banner = (f"Python {sys.version} on {sys.platform}\n"
                  f"ROAR Interactive Console — Type 'help()' for help.\n")
        self._editor.append_text(banner)
        self._editor.show_prompt()

    # -- public API ---------------------------------------------------------

    def push_locals(self, **kwargs):
        """Inject variables into the console namespace."""
        self._locals.update(kwargs)

    def run_source(self, source: str):
        """Programmatically execute *source* in the console."""
        self._execute_source(source)

    # -- internals ----------------------------------------------------------

    @pyqtSlot(str)
    def _on_execute(self, source: str):
        if self._command_running:
            return

        self._multiline_buffer.append(source)
        full_source = "\n".join(self._multiline_buffer)

        try:
            compiled = code.compile_command(full_source)
        except (SyntaxError, OverflowError, ValueError):
            self._multiline_buffer.clear()
            self._show_exception()
            self._editor.show_prompt()
            return

        if compiled is None:
            # Incomplete — ask for continuation
            self._editor.show_prompt(continuation=True)
            return

        # Complete command — record & execute
        self._record_history(full_source)
        self._multiline_buffer.clear()
        self._execute_compiled(compiled)

    def _execute_compiled(self, compiled):
        self._command_running = True

        stdout_cap = io.StringIO()
        stderr_cap = io.StringIO()

        def _run():
            with contextlib.redirect_stdout(stdout_cap), \
                 contextlib.redirect_stderr(stderr_cap):
                try:
                    self._shell.runcode(compiled)
                except SystemExit:
                    stderr_cap.write("SystemExit\n")

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        thread.join(timeout=30)

        out = stdout_cap.getvalue()
        err = stderr_cap.getvalue()
        if out:
            self._editor.append_text(out)
        if err:
            self._editor.append_text(err, colour=_ERR_MARKER)

        self._command_running = False
        self._editor.show_prompt()

    def _execute_source(self, source: str):
        """Execute arbitrary source (may be multi-line)."""
        self._editor.append_text(source + "\n")
        stdout_cap = io.StringIO()
        stderr_cap = io.StringIO()
        with contextlib.redirect_stdout(stdout_cap), \
             contextlib.redirect_stderr(stderr_cap):
            try:
                self._shell.runsource(source, symbol="exec")
            except SystemExit:
                stderr_cap.write("SystemExit\n")
        out = stdout_cap.getvalue()
        err = stderr_cap.getvalue()
        if out:
            self._editor.append_text(out)
        if err:
            self._editor.append_text(err, colour=_ERR_MARKER)
        self._editor.show_prompt()

    def _show_exception(self):
        tb = traceback.format_exc()
        if "NoneType" not in tb:
            self._editor.append_text(tb, colour=_ERR_MARKER)

    def _record_history(self, source: str):
        source = source.strip()
        if source and (not self._editor._history
                       or self._editor._history[-1] != source):
            self._editor._history.append(source)
        self._editor._history_idx = len(self._editor._history)


# ═══════════════════════════════════════════════════════════════════════════
#  ROARTextEditor – Python code editor with live syntax-error highlighting
# ═══════════════════════════════════════════════════════════════════════════

_MARKER_ERROR   = 8
_MARKER_WARNING = 9
_INDICATOR_ERROR = 0


class _EditorScintilla(QsciScintilla):
    """Scintilla subclass wired up for a Python code-editing experience."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def setup(self, font: QFont):
        _base_editor_setup(self, font)
        _apply_dark_python_lexer(self, font)

        # --- Line-number margin ---
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginWidth(0, "00000")
        self.setMarginLineNumbers(0, True)

        # --- Folding margin ---
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)
        self.setFoldMarginColors(_MARGIN_BG, _MARGIN_BG)

        # --- Error marker (red circle in margin) ---
        self.markerDefine(QsciScintilla.MarkerSymbol.Circle, _MARKER_ERROR)
        self.setMarkerBackgroundColor(_ERR_MARKER, _MARKER_ERROR)
        self.setMarkerForegroundColor(_ERR_MARKER, _MARKER_ERROR)

        # --- Marker margin (margin 1) ---
        self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
        self.setMarginWidth(1, 16)
        self.setMarginMarkerMask(1, (1 << _MARKER_ERROR) | (1 << _MARKER_WARNING))

        # --- Squiggly-underline indicator for errors ---
        self.indicatorDefine(
            QsciScintilla.IndicatorStyle.SquiggleIndicator, _INDICATOR_ERROR)
        self.setIndicatorForegroundColor(_ERR_MARKER, _INDICATOR_ERROR)
        self.setIndicatorDrawUnder(True, _INDICATOR_ERROR)

        # --- Autocompletion from document ---
        self.setAutoCompletionSource(
            QsciScintilla.AutoCompletionSource.AcsAll)
        self.setAutoCompletionThreshold(2)
        self.setAutoCompletionCaseSensitivity(False)
        self.setAutoCompletionReplaceWord(True)


class ROARTextEditor(QWidget):
    """Python code editor with real-time syntax-error highlighting.

    Features
    --------
    * Full Python syntax highlighting via ``QsciLexerPython``
    * Red squiggly underlines + margin markers on syntax-error lines
    * Line numbers, code folding, brace matching, auto-indent
    * Built-in auto-completion from the document
    * Open / Save / Check Syntax / Run toolbar
    """

    syntax_errors_changed = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None, *,
                 show_toolbar: bool = True):
        super().__init__(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(100, 60)

        font = QFont("Courier", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)

        self._editor = _EditorScintilla(self)
        self._editor.setup(font)

        # Toolbar
        self._toolbar = QHBoxLayout()
        if show_toolbar:
            btn_open  = QPushButton("Open")
            btn_save  = QPushButton("Save")
            btn_check = QPushButton("Check Syntax")
            btn_run   = QPushButton("Run")
            btn_open.clicked.connect(self._on_open)
            btn_save.clicked.connect(self._on_save)
            btn_check.clicked.connect(self.check_syntax)
            btn_run.clicked.connect(self._on_run)
            for btn in (btn_open, btn_save, btn_check, btn_run):
                self._toolbar.addWidget(btn)
            self._toolbar.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if show_toolbar:
            layout.addLayout(self._toolbar)
        layout.addWidget(self._editor)

        # Live syntax checking (debounced 500 ms)
        self._check_timer = QTimer(self)
        self._check_timer.setSingleShot(True)
        self._check_timer.setInterval(500)
        self._check_timer.timeout.connect(self.check_syntax)
        self._editor.textChanged.connect(self._on_text_changed)

        self._current_file: Optional[str] = None
        self._errors: list[tuple[int, int, str]] = []

    # -- public API ---------------------------------------------------------

    def get_text(self) -> str:
        return self._editor.text()

    def set_text(self, text: str):
        self._editor.setText(text)

    def get_editor(self) -> QsciScintilla:
        """Return the underlying QsciScintilla widget."""
        return self._editor

    def check_syntax(self):
        """Parse the current buffer and mark syntax errors."""
        self._clear_error_indicators()
        source = self._editor.text()
        if not source.strip():
            self._errors = []
            self.syntax_errors_changed.emit(self._errors)
            return

        self._errors = self._find_syntax_errors(source)
        for line_no, col, msg in self._errors:
            self._mark_error_line(line_no, col, msg)
        self.syntax_errors_changed.emit(self._errors)

    # -- internals ----------------------------------------------------------

    def _on_text_changed(self):
        self._check_timer.start()

    @staticmethod
    def _find_syntax_errors(source: str) -> list[tuple[int, int, str]]:
        """Return ``(line_0based, column, message)`` for syntax errors."""
        errors: list[tuple[int, int, str]] = []
        try:
            compile(source, "<editor>", "exec")
        except SyntaxError as exc:
            line = (exc.lineno or 1) - 1
            col  = (exc.offset or 1) - 1
            errors.append((line, col, str(exc.msg)))
        return errors

    def _mark_error_line(self, line: int, col: int, msg: str):
        """Add a margin marker and squiggly underline on *line*."""
        self._editor.markerAdd(line, _MARKER_ERROR)

        line_length = self._editor.lineLength(line)
        if line_length <= 0:
            return
        start_pos = self._editor.positionFromLineIndex(line, max(col, 0))
        end_pos   = self._editor.positionFromLineIndex(
            line, max(line_length - 1, 0))
        if end_pos <= start_pos:
            end_pos = start_pos + 1

        self._editor.SendScintilla(
            QsciScintilla.SCI_SETINDICATORCURRENT, _INDICATOR_ERROR)
        self._editor.SendScintilla(
            QsciScintilla.SCI_INDICATORFILLRANGE,
            start_pos, end_pos - start_pos)

        # Boxed annotation below the offending line
        self._editor.SendScintilla(
            QsciScintilla.SCI_ANNOTATIONSETVISIBLE, 2)
        self._editor.SendScintilla(
            QsciScintilla.SCI_ANNOTATIONSETTEXT, line, msg.encode("utf-8"))

    def _clear_error_indicators(self):
        self._editor.markerDeleteAll(_MARKER_ERROR)
        total_len = self._editor.length()
        if total_len > 0:
            self._editor.SendScintilla(
                QsciScintilla.SCI_SETINDICATORCURRENT, _INDICATOR_ERROR)
            self._editor.SendScintilla(
                QsciScintilla.SCI_INDICATORCLEARRANGE, 0, total_len)
        self._editor.SendScintilla(QsciScintilla.SCI_ANNOTATIONCLEARALL)

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Python File", "",
            "Python Files (*.py);;All Files (*)")
        if path:
            with open(path, "r", encoding="utf-8") as fh:
                self._editor.setText(fh.read())
            self._current_file = path

    def _on_save(self):
        path = self._current_file
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Python File", "",
                "Python Files (*.py);;All Files (*)")
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self._editor.text())
            self._current_file = path

    def _on_run(self):
        """Execute editor contents in a fresh namespace."""
        source = self.get_text()
        try:
            compiled = compile(source, self._current_file or "<editor>", "exec")
            exec(compiled, {"__name__": "__main__"})
        except Exception:
            traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════════
#  Design → Python script exporter
# ═══════════════════════════════════════════════════════════════════════════

def export_design_to_python(
    expressions: dict[str, str],
    constraints: dict[str, str],
    instances: list[dict],
    device_corners: dict | None = None,
) -> str:
    """Generate a self-contained Python script from the ROAR design editor state.

    Parameters
    ----------
    expressions : dict
        ``{symbol: expression_string}`` from the Expression Editor.
        Entries whose expression contains ``':'`` are treated as device-parameter
        lookups (e.g. ``"kgm:M1"``); everything else is a symbolic equation or
        a numeric constant.
    constraints : dict
        ``{symbol: constraint_expression}`` from the Constraint Editor.
    instances : list[dict]
        Rows from the Instance Table.  Each dict has at least an ``"Instance"``
        key and optional ``"kgm"``, ``"ID"``, ``"W"``, ``"L"``, ``"Corners"``
        keys.
    device_corners : dict or None
        Output of ``ROAREditorWindow.get_device_corners()`` – maps instance
        names to corner metadata (pdk, model, length …).

    Returns
    -------
    str
        A complete, runnable Python script string.
    """
    if device_corners is None:
        device_corners = {}

    lines: list[str] = []
    _a = lines.append  # shorthand

    # ── file header ──────────────────────────────────────────────────────
    _a("#!/usr/bin/env python3")
    _a('"""')
    _a("Auto-generated ROAR design script.")
    _a("")
    _a("This script reproduces the equations and lookup-table references")
    _a("defined in the ROAR Design Editor so they can be run, modified,")
    _a("and version-controlled outside the GUI.")
    _a('"""')
    _a("")
    _a("import os, sys, math")
    _a("import numpy as np")
    _a("")
    _a("# ── ROAR environment ─────────────────────────────────────────────")
    _a('ROAR_HOME = os.environ.get("ROAR_HOME", "")')
    _a('ROAR_SRC = os.environ.get("ROAR_SRC", "")')
    _a('ROAR_CHARACTERIZATION = os.environ.get("ROAR_CHARACTERIZATION", "")')
    _a("sys.path.append(ROAR_SRC)")
    _a("sys.path.append(os.path.join(ROAR_SRC, 'gui'))")
    _a("")
    _a("from cid import CIDDevice, CIDCorner")
    _a("")

    # ── Collect unique device names referenced by lookups ────────────────
    lookup_map: dict[str, list[tuple[str, str]]] = {}  # device -> [(symbol, param)]
    equation_map: dict[str, str] = {}                   # symbol -> expression (non-lookup)
    constant_map: dict[str, str] = {}                   # symbol -> numeric literal

    import re as _re
    _SCI_RE = _re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$')

    for sym, expr in expressions.items():
        expr = expr.strip()
        if ":" in expr:
            # Lookup expression like "kgm:M1"
            parts = expr.split(":", 1)
            param = parts[0].strip()
            device = parts[1].strip()
            lookup_map.setdefault(device, []).append((sym, param))
        elif _SCI_RE.match(expr):
            constant_map[sym] = expr
        else:
            equation_map[sym] = expr

    # Determine all unique devices (from lookups AND from the instance table)
    all_devices: list[str] = []
    for inst in instances:
        name = inst.get("Instance", "").strip()
        if name and name not in all_devices:
            all_devices.append(name)
    for dev in lookup_map:
        if dev not in all_devices:
            all_devices.append(dev)

    # ── Section: Devices & LUT loading ──────────────────────────────────
    _a("# ═══════════════════════════════════════════════════════════════════")
    _a("#  Device / LUT loading")
    _a("# ═══════════════════════════════════════════════════════════════════")
    _a("")

    if all_devices:
        _a("# --- Adjust the paths below to point at your LUT directories ---")
        _a("# Each device maps to a directory that contains per-corner CSV files.")
        _a("devices = {}")
        _a("")

        for dev in all_devices:
            info = device_corners.get(dev, {})
            pdk = info.get("pdk") or "<pdk>"
            model = info.get("model") or "<model>"
            length = info.get("length") or "<length>"
            corner_names = info.get("corners")
            corner_paths = info.get("corner_paths")

            _a(f"# Instance: {dev}  (PDK={pdk}, model={model}, L={length})")

            # Build a sensible LUT directory path from the metadata when we can
            if pdk != "<pdk>" and model != "<model>" and length != "<length>":
                lut_dir_expr = (
                    f'os.path.join(ROAR_CHARACTERIZATION, "{pdk}", '
                    f'"LUTs_{pdk.upper()}", "{model}_{length}")'
                )
            else:
                lut_dir_expr = (
                    f'"<set LUT directory for {dev}>"  '
                    f"# e.g. os.path.join(ROAR_CHARACTERIZATION, ...)"
                )

            _a(f'{dev}_lut_dir = {lut_dir_expr}')
            _a(f'devices["{dev}"] = CIDDevice(device_name="{dev}",')
            _a(f'    lut_directory={dev}_lut_dir)')

            if corner_names and corner_names[0]:
                names_str = ", ".join(f'"{c}"' for c in corner_names)
                _a(f'{dev}_corner_names = [{names_str}]  # selected corners')
            else:
                _a(f'{dev}_corner_names = None  # using all (global) corners')

            _a("")
    else:
        _a("# (No device instances defined)")
        _a("")

    # ── Section: Helper – build corner DataFrames dict ───────────────────
    _a("# ═══════════════════════════════════════════════════════════════════")
    _a("#  Helper: collect corner DataFrames for each device")
    _a("# ═══════════════════════════════════════════════════════════════════")
    _a("")
    _a("def get_corner_dfs(device_obj, corner_filter=None):")
    _a('    """Return {corner_name: DataFrame} for a CIDDevice, optionally filtered."""')
    _a("    dfs = {}")
    _a("    for corner in device_obj.corners:")
    _a("        if corner_filter and corner.corner_name not in corner_filter:")
    _a("            continue")
    _a("        dfs[corner.corner_name] = corner.df")
    _a("    return dfs")
    _a("")

    # ── Section: Constants ──────────────────────────────────────────────
    if constant_map:
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("#  Constants")
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("")
        for sym, val in constant_map.items():
            _a(f"{sym} = {val}")
        _a("")

    # ── Section: Lookups ─────────────────────────────────────────────────
    if lookup_map:
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("#  Device-parameter lookups")
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("#")
        _a("#  Each lookup extracts a column from every corner DataFrame of the")
        _a("#  referenced device and stacks the columns into a 2-D NumPy array")
        _a("#  of shape (n_bias_points, n_corners).")
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("")
        _a("def lookup_param(device_obj, param, corner_filter=None):")
        _a('    """Extract *param* from every corner of *device_obj* → 2-D array."""')
        _a("    cols = []")
        _a("    for corner in device_obj.corners:")
        _a("        if corner_filter and corner.corner_name not in corner_filter:")
        _a("            continue")
        _a("        if param in corner.df.columns:")
        _a("            cols.append(corner.df[param].values)")
        _a("    if not cols:")
        _a(f'        raise KeyError(f"Parameter \'{{param}}\' not found in any corner")')
        _a("    return np.column_stack(cols)")
        _a("")

        for dev, lookups in lookup_map.items():
            _a(f"# ── Lookups for device {dev} ──")
            for sym, param in lookups:
                _a(f'{sym} = lookup_param(devices["{dev}"], "{param}", '
                   f'{dev}_corner_names)')
            _a("")

    # ── Section: Equations ──────────────────────────────────────────────
    if equation_map:
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("#  Equations  (evaluated in dependency order)")
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("")
        for sym, expr in equation_map.items():
            _a(f"{sym} = {expr}")
        _a("")

    # ── Section: Constraints ─────────────────────────────────────────────
    if constraints:
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("#  Constraints  (boolean masks)")
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("")
        for sym, expr in constraints.items():
            _a(f"{sym} = {expr}  # constraint")
        _a("")

    # ── Section: Instance summary ────────────────────────────────────────
    if instances:
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("#  Instance table summary")
        _a("# ═══════════════════════════════════════════════════════════════════")
        _a("")
        _a("instance_info = {")
        for inst in instances:
            name = inst.get("Instance", "")
            kgm_val = inst.get("kgm", "")
            id_val = inst.get("ID", "")
            w_val = inst.get("W", "")
            l_val = inst.get("L", "")
            corners = inst.get("Corners", "")
            _a(f'    "{name}": {{"kgm": "{kgm_val}", "ID": "{id_val}", '
               f'"W": "{w_val}", "L": "{l_val}", "Corners": "{corners}"}},')
        _a("}")
        _a("")

    # ── Section: Results printout ────────────────────────────────────────
    _a("# ═══════════════════════════════════════════════════════════════════")
    _a("#  Print results")
    _a("# ═══════════════════════════════════════════════════════════════════")
    _a("")
    all_syms = list(constant_map) + [s for dev_lookups in lookup_map.values()
                                     for s, _ in dev_lookups] + list(equation_map)
    if all_syms:
        _a("results = {}")
        for sym in all_syms:
            _a(f'results["{sym}"] = {sym}')
        _a("")
        _a("for name, val in results.items():")
        _a("    if isinstance(val, np.ndarray):")
        _a('        print(f"{name}: shape={val.shape}, '
           'min={np.min(val):.6g}, max={np.max(val):.6g}")')
        _a("    else:")
        _a('        print(f"{name} = {val}")')
    else:
        _a("print('No expressions defined.')")

    _a("")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  Standalone demo
# ═══════════════════════════════════════════════════════════════════════════

def _demo():
    """Quick standalone test: editor + console side-by-side."""
    from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter

    app = QApplication(sys.argv)

    try:
        import qdarktheme
        qdarktheme.setup_theme("dark")
    except ImportError:
        pass

    win = QMainWindow()
    win.setWindowTitle("ROAR – Python Editor & Console")
    win.resize(1200, 700)

    splitter = QSplitter(Qt.Orientation.Vertical)

    editor = ROARTextEditor(show_toolbar=True)
    editor.set_text(
        '# ROAR Python Editor\n'
        'import math\n'
        '\n'
        'def hello(name):\n'
        '    """Greet someone."""\n'
        '    print(f"Hello, {name}!")\n'
        '\n'
        'hello("ROAR")\n'
    )

    console = ROARConsole()
    console.push_locals(editor=editor)

    splitter.addWidget(editor)
    splitter.addWidget(console)
    splitter.setSizes([400, 300])

    win.setCentralWidget(splitter)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    _demo()

