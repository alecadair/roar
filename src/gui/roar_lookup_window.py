import os
import sys
import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QSizePolicy, QGridLayout, QRadioButton, QCheckBox, QHBoxLayout,
    QComboBox, QLabel, QPushButton, QColorDialog, QDoubleSpinBox, QGraphicsItem
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QColor, QCursor, QIcon

# Use pyqtgraph.opengl for 3D rendering (faster, native GL)
# Requires pyqtgraph and PyOpenGL to be available
from pyqtgraph.opengl import MeshData, GLMeshItem, GLScatterPlotItem

try:
    from pyqtgraph.opengl import GLTextItem, GLLinePlotItem
except ImportError:
    GLTextItem = None
    GLLinePlotItem = None


class ROAR3DViewWidget(gl.GLViewWidget):
    """Custom GLViewWidget with 3-D point-marker support.

    Behaviour mirrors the 2-D ``ROARPlotWidget`` markers:

        Left-click  – place a red dot on the nearest data point and show an
                      ``(x, y, z)`` label.  Clicking near an existing marker
                      removes it (toggle).
        Delete      – remove all markers at once.
        Escape      – (reserved, currently same as Delete).
        F           – auto-fit camera.

    Camera rotation / pan / zoom with the mouse are **not** affected because
    marker placement only triggers when the mouse has **not moved** between
    press and release (i.e. a true click, not a drag).
    """

    # Pixel-distance threshold: a click must land within this many pixels of
    # a data point to create a marker, and within this distance of an existing
    # marker to delete it.
    PICK_TOLERANCE_PX = 25
    # Maximum mouse-move (pixels) between press/release to still count as a
    # click rather than a camera drag.
    CLICK_DRAG_THRESHOLD = 5

    # Visual style constants
    MARKER_SIZE_NORMAL = 14
    MARKER_COLOR_NORMAL = (1.0, 0.0, 0.0, 1.0)        # red
    MARKER_SIZE_HOVER = 20
    MARKER_COLOR_HOVER = (1.0, 0.65, 0.0, 1.0)         # orange
    LABEL_COLOR_NORMAL = QColor(255, 255, 100)           # light yellow
    LABEL_COLOR_HOVER = QColor(255, 200, 50)             # brighter gold

    def __init__(self, *args, parent_lookup_window=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_lookup_window = parent_lookup_window
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)  # receive move events without button held

        # 3-D point markers: list of dicts
        #   {'scatter': GLScatterPlotItem, 'text': GLTextItem,
        #    'pos_norm': ndarray(3,), 'pos_orig': ndarray(3,)}
        self._3d_point_markers = []

        # Data points registered by the render pass for mouse picking.
        self._all_norm_points = []   # list of Nx3 float64 arrays (GL coords)
        self._all_orig_points = []   # list of Nx3 float64 arrays (real coords)
        self._all_point_colors = []  # list of (r, g, b, a) tuples – one per set

        # Track mouse-press position to distinguish click from drag.
        self._press_pos = None

        # Hover tracking – mirrors the 2-D _hovered_marker pattern.
        self._hovered_marker = None


    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def _get_axis_names(self):
        """Return (x_name, y_name, z_name) from the parent combo boxes."""
        lw = self.parent_lookup_window
        if lw is None:
            return ('X', 'Y', 'Z')
        return (
            getattr(lw, 'combo_x', None) and lw.combo_x.currentText() or 'X',
            getattr(lw, 'combo_y', None) and lw.combo_y.currentText() or 'Y',
            getattr(lw, 'combo_z', None) and lw.combo_z.currentText() or 'Z',
        )

    # ------------------------------------------------------------------
    # Screen-space projection (used for mouse picking)
    # ------------------------------------------------------------------
    def _project_to_screen(self, pts_3d):
        """Project Nx3 GL-space points → Nx2 *widget* pixel coordinates.

        Uses pyqtgraph's own ``viewMatrix()`` and ``projectionMatrix()``
        so the projection is always consistent with what is actually
        rendered on screen.  The returned coordinates are in Qt logical
        pixels and match ``event.position()`` directly.
        """
        try:
            # Logical-pixel viewport – same one pyqtgraph uses for rendering
            vp = self.getViewport()          # (x0, y0, w, h) in logical px
            x0, y0, w, h = vp
            if w == 0 or h == 0:
                return None

            # Grab the matrices pyqtgraph builds from its camera opts
            mv_q = self.viewMatrix()
            proj_q = self.projectionMatrix(region=vp, viewport=vp)

            # QMatrix4x4.data() returns 16 floats in column-major order.
            # reshape(4,4) gives the transposed matrix; .T restores row-major.
            mv = np.array(mv_q.data(), dtype=np.float64).reshape(4, 4).T
            proj = np.array(proj_q.data(), dtype=np.float64).reshape(4, 4).T
        except Exception:
            return None

        pts = np.asarray(pts_3d, dtype=np.float64)
        n = pts.shape[0]
        pts4 = np.hstack([pts, np.ones((n, 1), dtype=np.float64)])

        # model-view → clip space  (row-vector convention)
        clip = (pts4 @ mv.T) @ proj.T
        wc = clip[:, 3:4].copy()
        wc[wc == 0] = 1e-30
        ndc = clip[:, :3] / wc          # normalised device coords [-1..1]

        # NDC → logical widget pixels
        sx = x0 + w * (ndc[:, 0] + 1.0) / 2.0
        # GL y=0 is at the bottom; Qt y=0 is at the top
        gl_sy = y0 + h * (ndc[:, 1] + 1.0) / 2.0
        sy = float(self.height()) - gl_sy

        return np.column_stack([sx, sy])

    def _find_nearest_point(self, mouse_x, mouse_y):
        """Find the nearest data point to widget coords (*mouse_x*, *mouse_y*).

        Returns ``(norm_xyz, orig_xyz, dist_px, color_rgba)`` or
        ``(None, None, inf, None)``.
        Mouse coords are in Qt widget-logical pixels (from ``event.position()``).
        """
        if not self._all_norm_points:
            return None, None, float('inf'), None

        best_dist = float('inf')
        best_norm = best_orig = None
        best_color = None

        colors = self._all_point_colors
        for i, (norm_pts, orig_pts) in enumerate(
                zip(self._all_norm_points, self._all_orig_points)):
            screen = self._project_to_screen(norm_pts)
            if screen is None:
                continue
            dsq = (screen[:, 0] - mouse_x) ** 2 + (screen[:, 1] - mouse_y) ** 2
            idx = int(np.argmin(dsq))
            d = float(np.sqrt(dsq[idx]))
            if d < best_dist:
                best_dist = d
                best_norm = norm_pts[idx].copy()
                best_orig = orig_pts[idx].copy()
                best_color = colors[i] if i < len(colors) else (1.0, 0.0, 0.0, 1.0)

        return best_norm, best_orig, best_dist, best_color

    def _find_nearest_marker(self, mouse_x, mouse_y):
        """Return the existing marker dict closest to the mouse, or *None*."""
        if not self._3d_point_markers:
            return None
        pts = np.array([m['pos_norm'] for m in self._3d_point_markers], dtype=np.float64)
        screen = self._project_to_screen(pts)
        if screen is None:
            return None
        dsq = (screen[:, 0] - mouse_x) ** 2 + (screen[:, 1] - mouse_y) ** 2
        idx = int(np.argmin(dsq))
        if np.sqrt(dsq[idx]) < self.PICK_TOLERANCE_PX:
            return self._3d_point_markers[idx]
        return None

    # ------------------------------------------------------------------
    # Marker add / remove
    # ------------------------------------------------------------------
    # Z floor of the normalised cube (where the grid sits)
    _Z_FLOOR = -5.0

    def add_point_marker(self, norm_xyz, orig_xyz, surface_color=None):
        """Place a marker dot (colored to match its surface), a label,
        a vertical drop-line to the z = -5 floor, and a floor dot."""
        if GLTextItem is None or GLLinePlotItem is None:
            return

        norm_xyz = np.asarray(norm_xyz, dtype=np.float64)
        orig_xyz = np.asarray(orig_xyz, dtype=np.float64)

        # Resolve marker colour from the surface it sits on
        if surface_color is not None:
            mc = tuple(float(c) for c in surface_color[:4])
        else:
            mc = self.MARKER_COLOR_NORMAL
        # Store the base colour on the marker dict so hover can restore it
        marker_color = mc

        # ── Scatter dot at the data point (surface colour) ──
        scatter = GLScatterPlotItem(
            pos=np.array([norm_xyz], dtype=np.float32),
            size=self.MARKER_SIZE_NORMAL,
            color=marker_color,
            pxMode=True,
        )
        self.addItem(scatter)

        # ── Label at the data point ──
        ax, ay, az = self._get_axis_names()
        label = (f"{ax}={format_eng(orig_xyz[0])},  "
                 f"{ay}={format_eng(orig_xyz[1])},  "
                 f"{az}={format_eng(orig_xyz[2])}")
        text = GLTextItem(
            pos=norm_xyz + np.array([0.3, 0.3, 0.3]),
            text=label, color=self.LABEL_COLOR_NORMAL,
        )
        self.addItem(text)

        # ── Vertical drop-line from data point to the z-floor ──
        floor_pt = np.array([norm_xyz[0], norm_xyz[1], self._Z_FLOOR],
                            dtype=np.float32)
        drop_color = (mc[0], mc[1], mc[2], 0.35)
        drop_line = GLLinePlotItem(
            pos=np.array([norm_xyz.astype(np.float32), floor_pt]),
            color=drop_color, width=1.5, antialias=True,
        )
        self.addItem(drop_line)

        # ── Small scatter dot on the floor ──
        floor_dot = GLScatterPlotItem(
            pos=np.array([floor_pt], dtype=np.float32),
            size=8, color=(mc[0], mc[1], mc[2], 0.5), pxMode=True,
        )
        self.addItem(floor_dot)

        self._3d_point_markers.append({
            'scatter': scatter,
            'text': text,
            'drop_line': drop_line,
            'floor_dot': floor_dot,
            'pos_norm': norm_xyz.copy(),
            'pos_orig': orig_xyz.copy(),
            'base_color': marker_color,      # for restoring after hover
        })

        # Push values to the spin boxes
        self._update_spin_boxes(orig_xyz)

    def _update_spin_boxes(self, orig_xyz):
        lw = self.parent_lookup_window
        if lw is None:
            return
        try:
            for spin, val in [(lw.spin_x, orig_xyz[0]),
                              (lw.spin_y, orig_xyz[1]),
                              (lw.spin_z, orig_xyz[2])]:
                if val < spin.minimum():
                    spin.setMinimum(val)
                if val > spin.maximum():
                    spin.setMaximum(val)
                spin.setValue(val)
        except Exception:
            pass

    def _remove_point_marker(self, marker):
        # If this was the hovered marker, clear the hover state
        if self._hovered_marker is marker:
            self._hovered_marker = None
        for key in ('scatter', 'text', 'drop_line', 'floor_dot'):
            try:
                self.removeItem(marker[key])
            except Exception:
                pass
        try:
            self._3d_point_markers.remove(marker)
        except ValueError:
            pass

    def _set_marker_style(self, marker, hovered):
        """Apply normal or hovered visual style to a marker and its drop-line."""
        scatter = marker.get('scatter')
        text = marker.get('text')
        drop_line = marker.get('drop_line')
        floor_dot = marker.get('floor_dot')
        bc = marker.get('base_color', self.MARKER_COLOR_NORMAL)

        if hovered:
            size = self.MARKER_SIZE_HOVER
            color = self.MARKER_COLOR_HOVER
            text_color = self.LABEL_COLOR_HOVER
            line_color = (1.0, 1.0, 0.3, 0.6)
            floor_dot_color = (1.0, 0.65, 0.0, 0.8)
        else:
            size = self.MARKER_SIZE_NORMAL
            color = bc
            text_color = self.LABEL_COLOR_NORMAL
            line_color = (bc[0], bc[1], bc[2], 0.35)
            floor_dot_color = (bc[0], bc[1], bc[2], 0.5)

        if scatter is not None:
            try:
                scatter.setData(size=size, color=np.array([color], dtype=np.float32))
            except Exception:
                pass
        if text is not None:
            try:
                text.setData(color=text_color)
            except Exception:
                pass
        if drop_line is not None:
            try:
                drop_line.setData(color=line_color, width=2.5 if hovered else 1.5)
            except Exception:
                pass
        if floor_dot is not None:
            try:
                floor_dot.setData(size=12 if hovered else 8,
                                  color=np.array([floor_dot_color], dtype=np.float32))
            except Exception:
                pass

    def _update_marker_hover(self, mouse_x, mouse_y):
        """Check proximity to existing markers and highlight/unhighlight."""
        nearest = self._find_nearest_marker(mouse_x, mouse_y)

        if nearest is self._hovered_marker:
            return  # no change

        # Un-highlight previous
        if self._hovered_marker is not None:
            self._set_marker_style(self._hovered_marker, hovered=False)

        # Highlight new
        if nearest is not None:
            self._set_marker_style(nearest, hovered=True)

        self._hovered_marker = nearest
        self.update()  # repaint

    def clear_all_3d_markers(self):
        """Remove every marker."""
        for m in list(self._3d_point_markers):
            self._remove_point_marker(m)

    # ------------------------------------------------------------------
    # Qt event overrides – click-vs-drag disambiguation
    # ------------------------------------------------------------------
    def mousePressEvent(self, event):
        """Record press position; always forward to base class for camera."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = (event.position().x(), event.position().y())
        super().mousePressEvent(event)          # camera orbit still works

    def mouseReleaseEvent(self, event):
        """On release, check if it was a *click* (not a drag) and handle markers."""
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            rx, ry = event.position().x(), event.position().y()
            dx = abs(rx - self._press_pos[0])
            dy = abs(ry - self._press_pos[1])
            self._press_pos = None

            if dx <= self.CLICK_DRAG_THRESHOLD and dy <= self.CLICK_DRAG_THRESHOLD:
                # True click – try to toggle a marker
                self._handle_click(rx, ry)

        super().mouseReleaseEvent(event)

    def _handle_click(self, mx, my):
        """Toggle marker at click position: remove if near existing, else add."""
        # First check if clicking on an existing marker (to remove it)
        existing = self._find_nearest_marker(mx, my)
        if existing is not None:
            self._remove_point_marker(existing)
            self.update()
            return

        # Otherwise add a new one
        norm_xyz, orig_xyz, dist, color = self._find_nearest_point(mx, my)
        if dist <= self.PICK_TOLERANCE_PX and norm_xyz is not None:
            self.add_point_marker(norm_xyz, orig_xyz, surface_color=color)
            self.update()

    def mouseMoveEvent(self, event):
        """Update marker hover highlight and show nearest-point coords."""
        super().mouseMoveEvent(event)
        mx, my = event.position().x(), event.position().y()

        # ── Marker hover highlighting ──
        self._update_marker_hover(mx, my)

        # Change cursor when over an existing marker
        if self._hovered_marker is not None:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

        # ── Status-bar coordinate readout ──
        norm_xyz, orig_xyz, dist, _color = self._find_nearest_point(mx, my)
        if dist <= self.PICK_TOLERANCE_PX * 2 and orig_xyz is not None:
            ax, ay, az = self._get_axis_names()
            coord_str = (f"{ax}={format_eng(orig_xyz[0])},  "
                         f"{ay}={format_eng(orig_xyz[1])},  "
                         f"{az}={format_eng(orig_xyz[2])}")
            lw = self.parent_lookup_window
            if lw is not None:
                app = getattr(lw, 'top_level_app', None)
                if app is not None and hasattr(app, 'coord_label'):
                    try:
                        app.coord_label.setText(f"Coordinates: ({coord_str})")
                    except Exception:
                        pass

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Escape:
            self.clear_all_3d_markers()
            self.update()
            event.accept()
        elif key == Qt.Key.Key_F:
            lw = self.parent_lookup_window
            if lw is not None:
                try:
                    lw.auto_fit_3d()
                except Exception:
                    pass
            event.accept()
        else:
            super().keyPressEvent(event)

    def leaveEvent(self, event):
        """Reset hover highlight when the mouse leaves the widget."""
        if self._hovered_marker is not None:
            self._set_marker_style(self._hovered_marker, hovered=False)
            self._hovered_marker = None
            self.update()
        self.unsetCursor()
        super().leaveEvent(event)


# Import debug_print function - handles case where this module is imported before roar_gui
try:
    from roar_gui import debug_print
except ImportError:
    try:
        from gui.roar_gui import debug_print
    except ImportError:
        # Fallback: define a no-op debug_print if roar_gui isn't available
        def debug_print(*args, **kwargs):
            pass


def format_eng(num):
    # Handle NaN, inf, and zero cases
    if np.isnan(num):
        return "NaN"
    if np.isinf(num):
        return "inf" if num > 0 else "-inf"
    if num == 0:
        return "0"

    exp = int(np.floor(np.log10(abs(num))))
    exp3 = exp - (exp % 3)

    mant = num / 10**exp3

    if mant == int(mant):
        mant_str = f"{int(mant)}"
    else:
        mant_str = f"{mant:.2f}".rstrip('0').rstrip('.')

    if exp3 == 0:
        return mant_str
    else:
        return f"{mant_str}e{exp3}"


class EngSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDecimals(12)

    def textFromValue(self, value: float) -> str:
        try:
            return format_eng(float(value))
        except Exception:
            return super().textFromValue(value)

    def valueFromText(self, text: str) -> float:
        try:
            return float(text)
        except Exception:
            return super().valueFromText(text)

    def sizeHint(self):
        try:
            fm = self.fontMetrics()
            candidates = [format_eng(self.minimum()), format_eng(self.maximum()), format_eng(self.value())]
            candidates.append('-1.00e-12')
            widest = max((fm.horizontalAdvance(str(t)) for t in candidates), default=80)
            base = super().sizeHint()
            return QSize(max(base.width(), widest + 40), base.height())
        except Exception:
            return super().sizeHint()


class ROARPlotWidget(pg.PlotWidget):
    # Percent calculation modes
    PERCENT_CHANGE = "percent_change"  # Traditional: (max - min) / min * 100
    SYMMETRIC_PERCENT = "symmetric_percent"  # Symmetric: 200 * (max - min) / (max + min)

    def __init__(self, *args, top_level_app=None, parent_lookup_window=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.top_level_app = top_level_app
        self.parent_lookup_window = parent_lookup_window
        self._mouse_inside = False

        # Percent calculation mode (default to percent change)
        self.percent_mode = self.PERCENT_CHANGE

        # Add timer for debouncing marker label updates during dragging
        self._marker_update_timer = None
        self._pending_marker_updates = []  # Use list instead of set since dicts aren't hashable

        # Add crosshair lines (legend removed - not wanted)
        self.v_line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DotLine))
        self.h_line = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('k', style=Qt.PenStyle.DotLine))
        self.plotItem.addItem(self.v_line, ignoreBounds=True)
        self.plotItem.addItem(self.h_line, ignoreBounds=True)
        # Add text item for coordinates
        self.coord_text = pg.TextItem(anchor=(0, 1))
        self.plotItem.addItem(self.coord_text)
        self.coord_text.setZValue(100)

        # Initialize markers list
        self.markers = []  # for scatter markers
        self.line_markers = []  # for line markers
        self.difference_items = []  # for difference lines and texts
        self._hovered_marker = None  # Track currently hovered scatter marker for highlighting
        self._hovered_text = None  # Track currently hovered line marker text for highlighting
        self._hovered_text_original_html = None  # Store original HTML to restore on unhover
        # Track selected (locked) texts - one regular text per marker + one summary text
        self._selected_text = None  # Currently selected regular marker text (stays highlighted)
        self._selected_text_original_html = None  # Original HTML of selected text
        self._selected_summary_text = None  # Currently selected summary/percent text (can be selected in addition)
        self._selected_summary_original_html = None  # Original HTML of selected summary

        # Connect mouse events
        try:
            self.scene().sigMouseMoved.connect(self.on_mouse_moved)
            self.scene().sigMouseClicked.connect(self.on_mouse_clicked)
            self.plotItem.vb.sigStateChanged.connect(self.on_state_changed)
            self.plotItem.sigRangeChanged.connect(self.on_range_changed)
            self.plotItem.scene().itemChanged.connect(self.on_item_changed)
        except Exception:
            pass

        # Setup percent calculation menu actions (will be added to ViewBox menu)
        self._setup_percent_menu()

        # Create an OpenGL 3D view widget (pyqtgraph.opengl)
        try:
            self.gl_widget = gl.GLViewWidget()
            self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.gl_widget.setVisible(False)
            # Add a grid for reference
            try:
                grid = gl.GLGridItem()
                grid.setSize(10, 10)
                grid.setSpacing(1, 1)
                self.gl_widget.addItem(grid)
            except Exception:
                grid = None
            self.gl_items = []  # Track GL items added to the view
            self.mpl_canvas = None
            self.mpl_figure = None
            self.mpl_ax = None
            self.mpl_toolbar = None
        except Exception as e:
            debug_print(f"Could not create GLViewWidget: {e}")
            self.gl_widget = None
            self.gl_items = []

    def _setup_percent_menu(self):
        """Add percent calculation mode options to the plot's context menu"""
        try:
            from PyQt6.QtWidgets import QMenu, QActionGroup
            from PyQt6.QtGui import QAction

            # Create our percent calculation menu
            self._percent_menu = QMenu("Percent Calculation")

            # Create action group for exclusive selection
            self._percent_action_group = QActionGroup(self._percent_menu)
            self._percent_action_group.setExclusive(True)

            # Traditional Percent Change option (default, listed first)
            self._traditional_action = QAction("Percent Change", self._percent_menu)
            self._traditional_action.setCheckable(True)
            self._traditional_action.setChecked(self.percent_mode == self.PERCENT_CHANGE)
            self._traditional_action.triggered.connect(lambda: self._set_percent_mode(self.PERCENT_CHANGE))
            self._percent_action_group.addAction(self._traditional_action)
            self._percent_menu.addAction(self._traditional_action)

            # Symmetric Percent Change option
            self._symmetric_action = QAction("Symmetric Percent Change", self._percent_menu)
            self._symmetric_action.setCheckable(True)
            self._symmetric_action.setChecked(self.percent_mode == self.SYMMETRIC_PERCENT)
            self._symmetric_action.triggered.connect(lambda: self._set_percent_mode(self.SYMMETRIC_PERCENT))
            self._percent_action_group.addAction(self._symmetric_action)
            self._percent_menu.addAction(self._symmetric_action)

            # Store references to update checked state
            self._percent_menu_actions = {
                self.SYMMETRIC_PERCENT: self._symmetric_action,
                self.PERCENT_CHANGE: self._traditional_action
            }

            # Try to add to the ViewBox menu directly
            self._add_percent_menu_to_viewbox()

        except Exception as e:
            debug_print(f"[DEBUG] Could not setup percent menu: {e}")

    def _add_percent_menu_to_viewbox(self):
        """Add the percent menu to the ViewBox's context menu"""
        try:
            vb = self.plotItem.vb
            # PyQtGraph ViewBox has a 'menu' attribute that is the context menu
            if hasattr(vb, 'menu') and vb.menu is not None:
                # Check if we already added our menu
                for action in vb.menu.actions():
                    if action.text() == "Percent Calculation":
                        return  # Already added
                vb.menu.addSeparator()
                vb.menu.addMenu(self._percent_menu)
            else:
                # Menu might be created lazily, try again later
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, self._add_percent_menu_to_viewbox)
        except Exception as e:
            debug_print(f"[DEBUG] Could not add percent menu to viewbox: {e}")


    def _set_percent_mode(self, mode):
        """Set the percent calculation mode and update marker labels"""
        self.percent_mode = mode
        # Update checked state in menu
        if hasattr(self, '_percent_menu_actions'):
            for m, action in self._percent_menu_actions.items():
                action.setChecked(m == mode)
        # Update all marker labels to reflect new calculation
        for marker in self.line_markers:
            self.update_marker_labels(marker, sync=False)

    def on_state_changed(self, _):
        if self.parent_lookup_window:
            self.parent_lookup_window.sync_log_checkboxes()

    def enterEvent(self, event):
        self._mouse_inside = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._mouse_inside = False
        if self.top_level_app and hasattr(self.top_level_app, "coord_label"):
            self.top_level_app.coord_label.setText("Coordinates: ")
        # Reset any hovered marker highlighting
        if self._hovered_marker is not None:
            try:
                marker = self._hovered_marker.get("marker")
                if marker:
                    marker.setSize(10)
                    marker.setPen(pg.mkPen('r'))
                    marker.setBrush(pg.mkBrush('r'))
            except Exception:
                pass
            self._hovered_marker = None
        # Reset any hovered text highlighting (but not if it's selected)
        if self._hovered_text is not None and self._hovered_text_original_html is not None:
            # Don't reset if this text is selected
            if self._hovered_text != self._selected_text and self._hovered_text != self._selected_summary_text:
                try:
                    self._hovered_text.setHtml(self._hovered_text_original_html)
                    self._hovered_text.setZValue(0)
                except Exception:
                    pass
            self._hovered_text = None
            self._hovered_text_original_html = None
        super().leaveEvent(event)

    def on_mouse_moved(self, pos):
        if self._mouse_inside and self.plotItem.sceneBoundingRect().contains(pos):
            # Only update coordinates if there are items in the plot
            if not getattr(self.plotItem, 'curves', None):
                return

            mouse_point = self.plotItem.vb.mapSceneToView(pos)
            x, y = mouse_point.x(), mouse_point.y()

            x_log = self.plotItem.getAxis('bottom').logMode
            y_log = self.plotItem.getAxis('left').logMode

            display_x = 10**x if x_log else x
            display_y = 10**y if y_log else y

            if self.top_level_app and hasattr(self.top_level_app, "coord_label"):
                try:
                    self.top_level_app.coord_label.setText(f"Coordinates: ({format_eng(display_x)}, {format_eng(display_y)})")
                except Exception:
                    pass

            try:
                self.coord_text.setText(f"x={format_eng(display_x)}, y={format_eng(display_y)}")
                self.coord_text.setPos(mouse_point)
                self.v_line.setPos(x)
                self.h_line.setPos(y)
            except Exception:
                pass

            # Check for hover over scatter markers and highlight them
            self._update_marker_hover(mouse_point)

            # Check for hover over line marker texts and highlight them
            self._update_text_hover(pos)

    def on_mouse_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.scenePos()

            # Check if clicking on a marker text to select/deselect it
            if self._handle_text_click(scene_pos):
                return  # Text click was handled, don't process other click actions

            if self.plotItem.sceneBoundingRect().contains(scene_pos):
                mouse_point = self.plotItem.vb.mapSceneToView(scene_pos)

                for marker_info in list(self.markers):
                    marker_item = marker_info.get("marker")
                    try:
                        if marker_item and self.is_close(marker_item.getData()[0][0], marker_item.getData()[1][0], mouse_point.x(), mouse_point.y()):
                            self.plotItem.removeItem(marker_info.get("marker"))
                            self.plotItem.removeItem(marker_info.get("text"))
                            self.markers.remove(marker_info)
                            return
                    except Exception:
                        pass

                closest_curve, closest_point_index = self.find_closest_point(mouse_point)

                if closest_curve is not None and closest_point_index is not None:
                    x_data, y_data = closest_curve.getData()
                    x, y = x_data[closest_point_index], y_data[closest_point_index]

                    x_log = self.plotItem.getAxis('bottom').logMode
                    y_log = self.plotItem.getAxis('left').logMode

                    # Store the true linear value of the marker
                    store_x = 10**x if x_log else x
                    store_y = 10**y if y_log else y

                    marker = pg.ScatterPlotItem(x=[x], y=[y], symbol='o', size=10, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
                    self.plotItem.addItem(marker)

                    text = pg.TextItem(f"({format_eng(store_x)}, {format_eng(store_y)})", anchor=(0.5, 1.5))
                    text.setPos(x, y)
                    self.plotItem.addItem(text)
                    text.setFlags(text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

                    self.markers.append({"marker": marker, "text": text, "pos": (store_x, store_y)})

                    # Place marker on attached graphs
                    for attached_window in self.parent_lookup_window.get_attached_windows():
                        closest_curve = None
                        closest_index = None
                        min_dist = float('inf')
                        for curve in attached_window.plot_widget.getPlotItem().curves:
                            try:
                                x_data, y_data = curve.getData()
                                if x_data is None or len(x_data) == 0:
                                    continue
                                idx = np.argmin(np.abs(x_data - store_x))
                                dist = abs(x_data[idx] - store_x)
                                if dist < min_dist:
                                    min_dist = dist
                                    closest_curve = curve
                                    closest_index = idx
                            except:
                                pass
                        if closest_curve and closest_index is not None:
                            x_data, y_data = closest_curve.getData()
                            x_att = x_data[closest_index]
                            y_att = y_data[closest_index]
                            marker_att = pg.ScatterPlotItem(x=[x_att], y=[y_att], symbol='o', size=10, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
                            attached_window.plot_widget.plotItem.addItem(marker_att)
                            text_att = pg.TextItem(f"({format_eng(store_x)}, {format_eng(y_att)})", anchor=(0.5, 1.5))
                            text_att.setPos(x_att, y_att)
                            attached_window.plot_widget.plotItem.addItem(text_att)
                            text_att.setFlags(text_att.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
                            attached_window.plot_widget.markers.append({"marker": marker_att, "text": text_att, "pos": (store_x, y_att)})

                    plw = getattr(self, "parent_lookup_window", None)
                    if plw:
                        try:
                            spinx = getattr(plw, "spin_x", None)
                            spiny = getattr(plw, "spin_y", None)
                            if isinstance(spinx, QDoubleSpinBox):
                                try:
                                    cur_min = spinx.minimum(); cur_max = spinx.maximum()
                                    if store_x < cur_min:
                                        spinx.setMinimum(store_x)
                                    if store_x > cur_max:
                                        spinx.setMaximum(store_x)
                                except Exception:
                                    pass
                                try:
                                    spinx.setValue(store_x)
                                except Exception:
                                    pass
                            if isinstance(spiny, QDoubleSpinBox):
                                try:
                                    cur_min = spiny.minimum(); cur_max = spiny.maximum()
                                    if store_y < cur_min:
                                        spiny.setMinimum(store_y)
                                    if store_y > cur_max:
                                        spiny.setMaximum(store_y)
                                except Exception:
                                    pass
                                try:
                                    spiny.setValue(store_y)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                # Check for line marker selection
                scene_pos = event.scenePos()
                for marker in self.line_markers:
                    line = marker['line']
                    pos = line.value()
                    if marker['vertical']:
                        view_pos = self.plotItem.vb.mapViewToScene(pg.Point(pos, 0))
                        if abs(scene_pos.x() - view_pos.x()) < 5:  # 5 pixels tolerance
                            self.select_marker(marker)
                            break
                    else:
                        view_pos = self.plotItem.vb.mapViewToScene(pg.Point(0, pos))
                        if abs(scene_pos.y() - view_pos.y()) < 5:  # 5 pixels tolerance
                            self.select_marker(marker)
                            break

    def find_closest_point(self, mouse_point):
        closest_curve = None
        closest_point_index = None
        min_dist_sq = float('inf')

        mouse_pos_scene = self.plotItem.vb.mapViewToScene(mouse_point)

        for curve in getattr(self.getPlotItem(), 'curves', []):
            try:
                x_data, y_data = curve.getData()
            except Exception:
                continue
            if x_data is None or y_data is None:
                continue

            for i in range(len(x_data)):
                point_view = pg.Point(x_data[i], y_data[i])
                point_scene = self.plotItem.vb.mapViewToScene(point_view)

                dist_sq = (point_scene.x() - mouse_pos_scene.x())**2 + (point_scene.y() - mouse_pos_scene.y())**2

                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_curve = curve
                    closest_point_index = i

        # Check if the closest point is reasonably close to the mouse click (in pixels)
        # Use a smaller tolerance so markers only appear when clicking close to a trace
        if min_dist_sq > 15**2: # 15 pixels tolerance
            return None, None

        return closest_curve, closest_point_index

    def is_close(self, x1, y1, x2, y2):
        try:
            p1 = self.plotItem.vb.mapViewToScene(pg.Point(x1, y1))
            p2 = self.plotItem.vb.mapViewToScene(pg.Point(x2, y2))
            return (p1.x() - p2.x())**2 + (p1.y() - p2.y())**2 < 10**2 # 10 pixels tolerance
        except Exception:
            return False

    def _update_marker_hover(self, mouse_point):
        """Check if mouse is hovering over a scatter marker and highlight it."""
        hovered_marker = None

        # Check each marker to see if mouse is close (using same tolerance as deletion)
        for marker_info in self.markers:
            marker_item = marker_info.get("marker")
            try:
                if marker_item:
                    marker_x = marker_item.getData()[0][0]
                    marker_y = marker_item.getData()[1][0]
                    if self.is_close(marker_x, marker_y, mouse_point.x(), mouse_point.y()):
                        hovered_marker = marker_info
                        break
            except Exception:
                pass

        # If hovered marker changed, update highlighting
        if hovered_marker != self._hovered_marker:
            # Reset previous hovered marker to normal style
            if self._hovered_marker is not None:
                try:
                    old_marker = self._hovered_marker.get("marker")
                    if old_marker:
                        old_marker.setSize(10)
                        old_marker.setPen(pg.mkPen('r'))
                        old_marker.setBrush(pg.mkBrush('r'))
                except Exception:
                    pass

            # Highlight new hovered marker
            if hovered_marker is not None:
                try:
                    new_marker = hovered_marker.get("marker")
                    if new_marker:
                        new_marker.setSize(14)
                        new_marker.setPen(pg.mkPen('yellow', width=2))
                        new_marker.setBrush(pg.mkBrush('orange'))
                except Exception:
                    pass

            self._hovered_marker = hovered_marker

    def _update_text_hover(self, scene_pos):
        """Check if mouse is hovering over a line marker text and highlight it.

        If a regular text is selected (locked), other regular texts won't highlight.
        Summary/percent texts can be highlighted and selected independently.
        """
        hovered_text = None
        is_summary_text = False

        # Check all line marker texts
        for marker in self.line_markers:
            # Check regular texts (only if no regular text is currently selected)
            if self._selected_text is None:
                for text in marker.get('texts', []):
                    try:
                        if text.sceneBoundingRect().contains(scene_pos):
                            hovered_text = text
                            is_summary_text = False
                            break
                    except Exception:
                        pass
                if hovered_text:
                    break

            # Check summary text (can always be hovered, independent of regular text selection)
            summary = marker.get('summary_text')
            if summary and self._selected_summary_text is None:
                try:
                    if summary.sceneBoundingRect().contains(scene_pos):
                        # Only set if we haven't found a regular text OR if regular text is selected
                        if hovered_text is None:
                            hovered_text = summary
                            is_summary_text = True
                            break
                except Exception:
                    pass

        # Also check difference items texts (treated like summary texts)
        if hovered_text is None and self._selected_summary_text is None:
            for diff_item in self.difference_items:
                diff_text = diff_item.get('text')
                if diff_text:
                    try:
                        if diff_text.sceneBoundingRect().contains(scene_pos):
                            hovered_text = diff_text
                            is_summary_text = True
                            break
                    except Exception:
                        pass

        # If hovered text changed, update highlighting
        if hovered_text != self._hovered_text:
            # Reset previous hovered text (but not if it's selected)
            if self._hovered_text is not None and self._hovered_text_original_html is not None:
                # Don't reset if this text is selected
                if self._hovered_text != self._selected_text and self._hovered_text != self._selected_summary_text:
                    try:
                        self._hovered_text.setHtml(self._hovered_text_original_html)
                        self._hovered_text.setZValue(0)
                    except Exception:
                        pass

            # Highlight new hovered text
            if hovered_text is not None:
                try:
                    # Store original HTML
                    self._hovered_text_original_html = hovered_text.toHtml()
                    original_text = hovered_text.toPlainText()
                    # Create highlighted HTML with yellow background (keep same font size)
                    highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                    hovered_text.setHtml(highlighted_html)
                    # Bring to front
                    hovered_text.setZValue(1000)
                except Exception:
                    pass
            else:
                self._hovered_text_original_html = None

            self._hovered_text = hovered_text

    def _handle_text_click(self, scene_pos):
        """Handle clicking on marker texts to select/deselect them.

        Returns True if a text click was handled, False otherwise.
        """
        clicked_text = None
        is_summary = False

        # Check all line marker texts
        for marker in self.line_markers:
            # Check regular texts
            texts = marker.get('texts', [])
            for text in texts:
                try:
                    rect = text.sceneBoundingRect()
                    if rect.contains(scene_pos):
                        clicked_text = text
                        is_summary = False
                        break
                except Exception:
                    pass
            if clicked_text:
                break

            # Check summary text
            summary = marker.get('summary_text')
            if summary:
                try:
                    rect = summary.sceneBoundingRect()
                    if rect.contains(scene_pos):
                        clicked_text = summary
                        is_summary = True
                        break
                except Exception:
                    pass

        # Also check difference items texts (treated like summary texts)
        if clicked_text is None:
            for diff_item in self.difference_items:
                diff_text = diff_item.get('text')
                if diff_text:
                    try:
                        if diff_text.sceneBoundingRect().contains(scene_pos):
                            clicked_text = diff_text
                            is_summary = True
                            break
                    except Exception:
                        pass

        if clicked_text is None:
            return False  # No text was clicked

        # Handle selection/deselection
        if is_summary:
            # Summary/percent text - can be selected independently
            if self._selected_summary_text is clicked_text:
                # Deselect - restore original HTML
                try:
                    if self._selected_summary_original_html:
                        clicked_text.setHtml(self._selected_summary_original_html)
                        clicked_text.setZValue(0)
                except Exception:
                    pass
                self._selected_summary_text = None
                self._selected_summary_original_html = None
            else:
                # Deselect any previously selected summary text
                if self._selected_summary_text is not None:
                    try:
                        if self._selected_summary_original_html:
                            self._selected_summary_text.setHtml(self._selected_summary_original_html)
                            self._selected_summary_text.setZValue(0)
                    except Exception:
                        pass

                # Select this summary text
                self._selected_summary_text = clicked_text
                # Store original HTML before highlighting (use current hover original if this is hovered)
                if clicked_text == self._hovered_text and self._hovered_text_original_html:
                    self._selected_summary_original_html = self._hovered_text_original_html
                else:
                    self._selected_summary_original_html = clicked_text.toHtml()

                # Apply highlight
                try:
                    original_text = clicked_text.toPlainText()
                    highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                    clicked_text.setHtml(highlighted_html)
                    clicked_text.setZValue(1000)
                except Exception:
                    pass
        else:
            # Regular text - only one can be selected at a time
            if self._selected_text is clicked_text:
                # Deselect - restore original HTML
                try:
                    if self._selected_text_original_html:
                        clicked_text.setHtml(self._selected_text_original_html)
                        clicked_text.setZValue(0)
                except Exception:
                    pass
                self._selected_text = None
                self._selected_text_original_html = None
            else:
                # Deselect any previously selected regular text
                if self._selected_text is not None:
                    try:
                        if self._selected_text_original_html:
                            self._selected_text.setHtml(self._selected_text_original_html)
                            self._selected_text.setZValue(0)
                    except Exception:
                        pass

                # Select this text
                self._selected_text = clicked_text
                # Store original HTML before highlighting (use current hover original if this is hovered)
                if clicked_text == self._hovered_text and self._hovered_text_original_html:
                    self._selected_text_original_html = self._hovered_text_original_html
                else:
                    self._selected_text_original_html = clicked_text.toHtml()

                # Apply highlight
                try:
                    original_text = clicked_text.toPlainText()
                    highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                    clicked_text.setHtml(highlighted_html)
                    clicked_text.setZValue(1000)
                except Exception:
                    pass

        return True  # Text click was handled

    def _handle_text_selection(self, clicked_text):
        """Handle text selection when a text item is clicked directly.

        This is called from the text item's mouseReleaseEvent.
        """
        # Determine if this is a summary text
        is_summary = clicked_text.property('is_summary') or False

        # Handle selection/deselection
        if is_summary:
            # Summary/percent text - can be selected independently
            if self._selected_summary_text is clicked_text:
                # Deselect - restore original HTML
                try:
                    if self._selected_summary_original_html:
                        clicked_text.setHtml(self._selected_summary_original_html)
                        clicked_text.setZValue(0)
                except Exception:
                    pass
                self._selected_summary_text = None
                self._selected_summary_original_html = None
            else:
                # Deselect any previously selected summary text
                if self._selected_summary_text is not None:
                    try:
                        if self._selected_summary_original_html:
                            self._selected_summary_text.setHtml(self._selected_summary_original_html)
                            self._selected_summary_text.setZValue(0)
                    except Exception:
                        pass

                # Select this summary text
                self._selected_summary_text = clicked_text
                self._selected_summary_original_html = clicked_text.toHtml()

                # Apply highlight
                try:
                    original_text = clicked_text.toPlainText()
                    highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                    clicked_text.setHtml(highlighted_html)
                    clicked_text.setZValue(1000)
                except Exception:
                    pass
        else:
            # Regular text - only one can be selected at a time
            if self._selected_text is clicked_text:
                # Deselect - restore original HTML
                try:
                    if self._selected_text_original_html:
                        clicked_text.setHtml(self._selected_text_original_html)
                        clicked_text.setZValue(0)
                except Exception:
                    pass
                self._selected_text = None
                self._selected_text_original_html = None
            else:
                # Deselect any previously selected regular text
                if self._selected_text is not None:
                    try:
                        if self._selected_text_original_html:
                            self._selected_text.setHtml(self._selected_text_original_html)
                            self._selected_text.setZValue(0)
                    except Exception:
                        pass

                # Select this text
                self._selected_text = clicked_text
                self._selected_text_original_html = clicked_text.toHtml()

                # Apply highlight
                try:
                    original_text = clicked_text.toPlainText()
                    highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                    clicked_text.setHtml(highlighted_html)
                    clicked_text.setZValue(1000)
                except Exception:
                    pass

    def add_vertical_marker(self, linear_pos=None, sync=True):
        if linear_pos is None:
            cursor_pos = QCursor.pos()
            global_pos = self.mapToGlobal(QPoint(0, 0))
            local_pos = cursor_pos - global_pos
            if not self.rect().contains(local_pos):
                return  # not over the widget
            mouse_point = self.plotItem.vb.mapSceneToView(self.mapToScene(local_pos))
            view_pos = mouse_point.x()
            x_log = self.plotItem.getAxis('bottom').logMode
            linear_pos = 10**view_pos if x_log else view_pos
        else:
            x_log = self.plotItem.getAxis('bottom').logMode
        view_pos = np.log10(linear_pos) if x_log and linear_pos > 0 else linear_pos
        line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine), hoverPen=pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4), pos=view_pos)
        self.plotItem.addItem(line)
        marker = {'line': line, 'vertical': True, 'texts': [], 'selected': False, 'linear_pos': linear_pos}
        self.line_markers.append(marker)
        # Signal doesn't pass arguments, so use a proper lambda closure
        line.sigPositionChanged.connect(lambda: self.update_marker_labels(marker, sync=True))
        line.mouseReleaseEvent = lambda event, m=marker: self.select_marker(m)
        self.update_marker_labels(marker, sync=False)  # Don't sync on initial creation

        # Place marker on attached graphs only if sync=True
        if sync:
            plw = getattr(self, "parent_lookup_window", None)
            if plw:
                for attached_window in plw.get_attached_windows():
                    attached_window.plot_widget.add_vertical_marker(linear_pos=linear_pos, sync=False)

    def add_horizontal_marker(self, linear_pos=None, sync=True):
        if linear_pos is None:
            cursor_pos = QCursor.pos()
            global_pos = self.mapToGlobal(QPoint(0, 0))
            local_pos = cursor_pos - global_pos
            if not self.rect().contains(local_pos):
                return  # not over the widget
            mouse_point = self.plotItem.vb.mapSceneToView(self.mapToScene(local_pos))
            view_pos = mouse_point.y()
            y_log = self.plotItem.getAxis('left').logMode
            linear_pos = 10**view_pos if y_log else view_pos
        else:
            y_log = self.plotItem.getAxis('left').logMode
        view_pos = np.log10(linear_pos) if y_log and linear_pos > 0 else linear_pos
        line = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine), hoverPen=pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4), pos=view_pos)
        self.plotItem.addItem(line)
        marker = {'line': line, 'vertical': False, 'texts': [], 'selected': False, 'linear_pos': linear_pos}
        self.line_markers.append(marker)
        # Signal doesn't pass arguments, so use a proper lambda closure
        line.sigPositionChanged.connect(lambda: self.update_marker_labels(marker, sync=True))
        line.mouseReleaseEvent = lambda event, m=marker: self.select_marker(m)
        self.update_marker_labels(marker, sync=False)  # Don't sync on initial creation

        # Place marker on attached graphs only if sync=True
        if sync:
            plw = getattr(self, "parent_lookup_window", None)
            if plw:
                for attached_window in plw.get_attached_windows():
                    attached_window.plot_widget.add_horizontal_marker(linear_pos=linear_pos, sync=False)

    def update_marker_labels(self, marker, sync=True):
        line = marker['line']
        vertical = marker['vertical']
        pos = line.value()

        # Get log mode status
        x_log = self.plotItem.getAxis('bottom').logMode
        y_log = self.plotItem.getAxis('left').logMode

        # Update linear_pos based on current position
        if vertical:
            marker['linear_pos'] = 10**pos if x_log else pos
        else:
            marker['linear_pos'] = 10**pos if y_log else pos

        # Save current text offsets before removing them
        # Key by curve index to persist offsets when marker moves
        if 'text_offsets' not in marker:
            marker['text_offsets'] = {}

        for i, text in enumerate(marker.get('texts', [])):
            try:
                # Get curve index from text property
                curve_idx = text.property('curve_idx')
                if curve_idx is None:
                    curve_idx = i
                # Get current position and base position to calculate offset
                current_pos = text.pos()
                base_pos = text.property('base_pos')
                if base_pos is not None:
                    offset_x = current_pos.x() - base_pos[0]
                    offset_y = current_pos.y() - base_pos[1]
                    if offset_x != 0 or offset_y != 0:
                        marker['text_offsets'][curve_idx] = (offset_x, offset_y)
            except Exception:
                pass

        # Save summary text offset
        if 'summary_text' in marker:
            try:
                summary = marker['summary_text']
                current_pos = summary.pos()
                base_pos = summary.property('base_pos')
                if base_pos is not None:
                    offset_x = current_pos.x() - base_pos[0]
                    offset_y = current_pos.y() - base_pos[1]
                    if offset_x != 0 or offset_y != 0:
                        marker['text_offsets']['__summary__'] = (offset_x, offset_y)
            except Exception:
                pass

        # Save selected text state before removing texts
        selected_curve_idx = None
        selected_summary = False
        for text in marker.get('texts', []):
            if text == self._selected_text:
                selected_curve_idx = text.property('curve_idx')
                # Clear the reference since text will be removed
                self._selected_text = None
                break
        if 'summary_text' in marker:
            if marker['summary_text'] == self._selected_summary_text:
                selected_summary = True
                self._selected_summary_text = None

        # remove old texts
        for text in marker.get('texts', []):
            self.plotItem.removeItem(text)
        marker['texts'] = []
        if 'summary_text' in marker:
            self.plotItem.removeItem(marker['summary_text'])
            del marker['summary_text']

        pos = line.value()
        text_list = []
        y_values = []
        x_values = []
        curve_idx = 0
        for curve in getattr(self.plotItem, 'curves', []):
            try:
                xdata, ydata = curve.getData()
                if xdata is None or ydata is None or len(xdata) == 0 or len(ydata) == 0:
                    continue
                if vertical:
                    # Vertical line at x=pos, find closest y
                    idx = np.argmin(np.abs(xdata - pos))
                    x = xdata[idx]
                    y = ydata[idx]
                    # Convert to linear values for display
                    display_x = 10**pos if x_log else pos
                    display_y = 10**y if y_log else y
                    text_content = f"({format_eng(display_x)}, {format_eng(display_y)})"
                    text = pg.TextItem(text_content, anchor=(0.5, 0.5))
                    base_x, base_y = pos, y
                    text.setPos(base_x, base_y)
                    text.setProperty('base_pos', (base_x, base_y))
                    text.setProperty('curve_idx', curve_idx)
                    # Apply stored offset if exists for this curve
                    if curve_idx in marker['text_offsets']:
                        offset = marker['text_offsets'][curve_idx]
                        text.setPos(base_x + offset[0], base_y + offset[1])
                    y_values.append(display_y)
                else:
                    # Horizontal line at y=pos, find closest x
                    idx = np.argmin(np.abs(ydata - pos))
                    x = xdata[idx]
                    y = ydata[idx]
                    # Convert to linear values for display
                    display_x = 10**x if x_log else x
                    display_y = 10**pos if y_log else pos
                    text_content = f"({format_eng(display_x)}, {format_eng(display_y)})"
                    text = pg.TextItem(text_content, anchor=(0.5, 0.5))
                    base_x, base_y = x, pos
                    text.setPos(base_x, base_y)
                    text.setProperty('base_pos', (base_x, base_y))
                    text.setProperty('curve_idx', curve_idx)
                    # Apply stored offset if exists for this curve
                    if curve_idx in marker['text_offsets']:
                        offset = marker['text_offsets'][curve_idx]
                        text.setPos(base_x + offset[0], base_y + offset[1])
                    x_values.append(display_x)
                text_list.append(text)
                curve_idx += 1
            except Exception:
                pass

        # Filter out overlapping texts
        visible_texts = []
        for text in text_list:
            overlap = False
            for vt in visible_texts:
                if text.sceneBoundingRect().intersects(vt.sceneBoundingRect()):
                    overlap = True
                    break
            if not overlap:
                visible_texts.append(text)
                self.plotItem.addItem(text)
                text.setFlags(text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
                # Add click handler for text selection - use mouseReleaseEvent to detect clicks
                # Store reference to self and whether this is a summary text
                text.setProperty('is_summary', False)
                text.setProperty('plot_widget', self)
                # Track mouse press position to detect drag vs click
                original_mouse_press = text.mousePressEvent
                original_mouse_release = text.mouseReleaseEvent
                def make_press_handler(txt, orig_handler):
                    def handler(event):
                        # Store press position to detect drag
                        txt.setProperty('press_pos', event.scenePos())
                        if orig_handler:
                            orig_handler(event)
                    return handler
                def make_click_handler(txt, orig_handler):
                    def handler(event):
                        # Check if this was a click (not a drag) by checking if position changed minimally
                        press_pos = txt.property('press_pos')
                        release_pos = event.scenePos()
                        is_click = True
                        if press_pos is not None:
                            # If moved more than 5 pixels, it's a drag not a click
                            dx = abs(release_pos.x() - press_pos.x())
                            dy = abs(release_pos.y() - press_pos.y())
                            if dx > 5 or dy > 5:
                                is_click = False
                        if is_click:
                            pw = txt.property('plot_widget')
                            if pw and hasattr(pw, '_handle_text_selection'):
                                pw._handle_text_selection(txt)
                        if orig_handler:
                            orig_handler(event)
                    return handler
                text.mousePressEvent = make_press_handler(text, original_mouse_press)
                text.mouseReleaseEvent = make_click_handler(text, original_mouse_release)
                marker['texts'].append(text)

        # Helper function to calculate percent based on mode
        def calc_percent(min_val, max_val, mode):
            if mode == self.PERCENT_CHANGE:
                # Traditional percent change: (max - min) / min * 100
                if min_val != 0:
                    return 100 * (max_val - min_val) / abs(min_val)
                return 0
            else:
                # Symmetric percent change: 200 * (max - min) / (max + min)
                if (max_val + min_val) != 0:
                    return 200 * (max_val - min_val) / (max_val + min_val)
                return 0

        # Add summary text for single marker
        if vertical and y_values:
            min_y = min(y_values)
            max_y = max(y_values)
            percent = calc_percent(min_y, max_y, self.percent_mode)
            label = f"ΔY: {percent:.1f}%"
            summary_text = pg.TextItem(label, anchor=(0.5, 1.0))  # anchor at bottom so text appears above the point

            # Find the highest y position among all newly created texts (in plot coordinates)
            max_text_y = None
            for text in text_list:  # Use text_list directly, not visible_texts
                try:
                    text_y = text.pos().y()
                    if max_text_y is None or text_y > max_text_y:
                        max_text_y = text_y
                except Exception:
                    pass

            # If no texts found, calculate from y_values
            if max_text_y is None:
                y_log = self.plotItem.getAxis('left').logMode
                max_y_linear = max(y_values)
                max_text_y = np.log10(max_y_linear) if y_log and max_y_linear > 0 else max_y_linear

            # Calculate offset as 5% of the y-range visible in the texts, minimum of a small value
            if len(text_list) > 1:
                text_y_values = [t.pos().y() for t in text_list]
                y_range = max(text_y_values) - min(text_y_values)
                y_offset = max(y_range * 0.15, abs(max_text_y) * 0.02) if y_range > 0 else abs(max_text_y) * 0.05
            else:
                y_offset = abs(max_text_y) * 0.05 if max_text_y != 0 else 0.1

            base_x, base_y = pos, max_text_y + y_offset
            summary_text.setPos(base_x, base_y)
            summary_text.setProperty('base_pos', (base_x, base_y))
            # Apply stored offset if exists
            if '__summary__' in marker['text_offsets']:
                offset = marker['text_offsets']['__summary__']
                summary_text.setPos(base_x + offset[0], base_y + offset[1])
            self.plotItem.addItem(summary_text)
            summary_text.setFlags(summary_text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            # Add click handler for summary text selection
            summary_text.setProperty('is_summary', True)
            summary_text.setProperty('plot_widget', self)
            original_mouse_press_v = summary_text.mousePressEvent
            original_mouse_release_v = summary_text.mouseReleaseEvent
            def make_summary_press_handler_v(txt, orig_handler):
                def handler(event):
                    txt.setProperty('press_pos', event.scenePos())
                    if orig_handler:
                        orig_handler(event)
                return handler
            def make_summary_click_handler_v(txt, orig_handler):
                def handler(event):
                    press_pos = txt.property('press_pos')
                    release_pos = event.scenePos()
                    is_click = True
                    if press_pos is not None:
                        dx = abs(release_pos.x() - press_pos.x())
                        dy = abs(release_pos.y() - press_pos.y())
                        if dx > 5 or dy > 5:
                            is_click = False
                    if is_click:
                        pw = txt.property('plot_widget')
                        if pw and hasattr(pw, '_handle_text_selection'):
                            pw._handle_text_selection(txt)
                    if orig_handler:
                        orig_handler(event)
                return handler
            summary_text.mousePressEvent = make_summary_press_handler_v(summary_text, original_mouse_press_v)
            summary_text.mouseReleaseEvent = make_summary_click_handler_v(summary_text, original_mouse_release_v)
            marker['summary_text'] = summary_text
        elif not vertical and x_values:
            min_x = min(x_values)
            max_x = max(x_values)
            percent = calc_percent(min_x, max_x, self.percent_mode)
            label = f"ΔX: {percent:.1f}%"
            summary_text = pg.TextItem(label, anchor=(0.0, 0.5))  # anchor at left so text appears to the right

            # Find the rightmost x position among all newly created texts (in plot coordinates)
            max_text_x = None
            for text in text_list:  # Use text_list directly
                try:
                    text_x = text.pos().x()
                    if max_text_x is None or text_x > max_text_x:
                        max_text_x = text_x
                except Exception:
                    pass

            # If no texts found, calculate from x_values
            if max_text_x is None:
                x_log = self.plotItem.getAxis('bottom').logMode
                max_x_linear = max(x_values)
                max_text_x = np.log10(max_x_linear) if x_log and max_x_linear > 0 else max_x_linear

            # Calculate offset as 5% of the x-range visible in the texts
            if len(text_list) > 1:
                text_x_values = [t.pos().x() for t in text_list]
                x_range = max(text_x_values) - min(text_x_values)
                x_offset = max(x_range * 0.15, abs(max_text_x) * 0.02) if x_range > 0 else abs(max_text_x) * 0.05
            else:
                x_offset = abs(max_text_x) * 0.05 if max_text_x != 0 else 0.1

            base_x, base_y = max_text_x + x_offset, pos
            summary_text.setPos(base_x, base_y)
            summary_text.setProperty('base_pos', (base_x, base_y))
            # Apply stored offset if exists
            if '__summary__' in marker['text_offsets']:
                offset = marker['text_offsets']['__summary__']
                summary_text.setPos(base_x + offset[0], base_y + offset[1])
            self.plotItem.addItem(summary_text)
            summary_text.setFlags(summary_text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            # Add click handler for summary text selection
            summary_text.setProperty('is_summary', True)
            summary_text.setProperty('plot_widget', self)
            original_mouse_press_h = summary_text.mousePressEvent
            original_mouse_release_h = summary_text.mouseReleaseEvent
            def make_summary_press_handler_h(txt, orig_handler):
                def handler(event):
                    txt.setProperty('press_pos', event.scenePos())
                    if orig_handler:
                        orig_handler(event)
                return handler
            def make_summary_click_handler_h(txt, orig_handler):
                def handler(event):
                    press_pos = txt.property('press_pos')
                    release_pos = event.scenePos()
                    is_click = True
                    if press_pos is not None:
                        dx = abs(release_pos.x() - press_pos.x())
                        dy = abs(release_pos.y() - press_pos.y())
                        if dx > 5 or dy > 5:
                            is_click = False
                    if is_click:
                        pw = txt.property('plot_widget')
                        if pw and hasattr(pw, '_handle_text_selection'):
                            pw._handle_text_selection(txt)
                    if orig_handler:
                        orig_handler(event)
                return handler
            summary_text.mousePressEvent = make_summary_press_handler_h(summary_text, original_mouse_press_h)
            summary_text.mouseReleaseEvent = make_summary_click_handler_h(summary_text, original_mouse_release_h)
            marker['summary_text'] = summary_text

        # Restore selected text state after creating new texts
        if selected_curve_idx is not None:
            # Find the text with the same curve_idx and re-select it
            for text in marker.get('texts', []):
                if text.property('curve_idx') == selected_curve_idx:
                    self._selected_text = text
                    self._selected_text_original_html = text.toHtml()
                    # Apply highlight
                    try:
                        original_text = text.toPlainText()
                        highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                        text.setHtml(highlighted_html)
                        text.setZValue(1000)
                    except Exception:
                        pass
                    break
        if selected_summary and 'summary_text' in marker:
            self._selected_summary_text = marker['summary_text']
            self._selected_summary_original_html = marker['summary_text'].toHtml()
            # Apply highlight
            try:
                original_text = marker['summary_text'].toPlainText()
                highlighted_html = f'<div style="background-color: rgba(255, 255, 0, 200); padding: 2px; border: 1px solid orange; border-radius: 2px;"><span style="color: black;">{original_text}</span></div>'
                marker['summary_text'].setHtml(highlighted_html)
                marker['summary_text'].setZValue(1000)
            except Exception:
                pass

        # Synchronize marker position with attached plots (only if sync=True)
        if sync:
            plw = getattr(self, "parent_lookup_window", None)
            if plw:
                attached_windows = plw.get_attached_windows()

                # Get the index of this marker in the list
                try:
                    marker_index = self.line_markers.index(marker)
                except (ValueError, AttributeError):
                    marker_index = -1

                for attached_window in attached_windows:
                    matched_marker = None

                    # Strategy 1: Try to match by index (for markers created together)
                    if marker_index >= 0 and marker_index < len(attached_window.plot_widget.line_markers):
                        candidate = attached_window.plot_widget.line_markers[marker_index]
                        if candidate['vertical'] == marker['vertical']:
                            matched_marker = candidate

                    # Strategy 2: If no match by index, try matching by position and orientation
                    if matched_marker is None:
                        for attached_marker in attached_window.plot_widget.line_markers:
                            if attached_marker['vertical'] == marker['vertical']:
                                pos_diff = abs(attached_marker['linear_pos'] - marker['linear_pos'])
                                # Use a more generous tolerance for matching
                                tolerance = max(abs(marker['linear_pos']) * 0.1, 0.1)
                                if pos_diff < tolerance:
                                    matched_marker = attached_marker
                                    break

                    # If we found a match, update it
                    if matched_marker is not None:
                        # Update the matched marker's position
                        matched_marker['linear_pos'] = marker['linear_pos']
                        axis = 'bottom' if vertical else 'left'
                        log_mode = attached_window.plot_widget.plotItem.getAxis(axis).logMode
                        new_pos = np.log10(marker['linear_pos']) if log_mode and marker['linear_pos'] > 0 else marker['linear_pos']

                        # Temporarily block signals to prevent cascading updates during drag
                        try:
                            matched_marker['line'].blockSignals(True)
                        except Exception:
                            pass

                        # Update position without triggering signal
                        matched_marker['line'].setValue(new_pos)

                        # Re-enable signals
                        try:
                            matched_marker['line'].blockSignals(False)
                        except Exception:
                            pass

                        # Update labels immediately for smooth text following
                        # This is more responsive than debouncing
                        attached_window.plot_widget.update_marker_labels(matched_marker, sync=False)

    def on_marker_selected(self, marker, selected):
        # Optional: change appearance when selected
        pass

    def _perform_pending_marker_updates(self):
        """Execute pending marker label updates after debounce timer expires"""
        for marker in self._pending_marker_updates:
            try:
                # Do a full label update without syncing
                self.update_marker_labels(marker, sync=False)
            except Exception as e:
                pass  # Marker might have been deleted
        self._pending_marker_updates.clear()
        self._marker_update_timer = None

    def _schedule_marker_update(self, marker):
        """Schedule a full marker label update after a short delay to reduce lag during dragging"""
        # Add to pending updates if not already there (check by marker identity)
        if marker not in self._pending_marker_updates:
            self._pending_marker_updates.append(marker)

        # Cancel existing timer and create a new one
        if self._marker_update_timer is not None:
            try:
                self._marker_update_timer.stop()
            except Exception:
                pass

        # Import QTimer here to avoid issues
        try:
            from PyQt6.QtCore import QTimer
            self._marker_update_timer = QTimer()
            self._marker_update_timer.setSingleShot(True)
            self._marker_update_timer.timeout.connect(self._perform_pending_marker_updates)
            self._marker_update_timer.start(50)  # 50ms delay - feels instant but reduces updates
        except Exception:
            # Fallback: just do the update immediately
            self.update_marker_labels(marker, sync=False)

    def select_marker(self, marker, sync=True):
        if marker['selected']:
            marker['selected'] = False
            marker['line'].setPen(pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=1))
            marker['line'].setHoverPen(pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4))
            marker['line'].update()
        else:
            marker['selected'] = True
            marker['line'].setPen(pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=5))
            marker['line'].setHoverPen(pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=5))
            marker['line'].update()

        # Synchronize selection with attached plots (only if sync=True to prevent infinite recursion)
        if sync:
            plw = getattr(self, "parent_lookup_window", None)
            if plw:
                for attached_window in plw.get_attached_windows():
                    for m in attached_window.plot_widget.line_markers:
                        if m['linear_pos'] == marker['linear_pos'] and m['vertical'] == marker['vertical']:
                            # Pass sync=False to prevent infinite recursion
                            attached_window.plot_widget.select_marker(m, sync=False)
                            break

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            to_remove = [m for m in self.line_markers if m.get('selected', False)]

            # Clear selected text state if the selected text belongs to a deleted marker
            for m in to_remove:
                for text in m.get('texts', []):
                    if text == self._selected_text:
                        self._selected_text = None
                        self._selected_text_original_html = None
                    if text == self._hovered_text:
                        self._hovered_text = None
                        self._hovered_text_original_html = None
                summary = m.get('summary_text')
                if summary:
                    if summary == self._selected_summary_text:
                        self._selected_summary_text = None
                        self._selected_summary_original_html = None
                    if summary == self._hovered_text:
                        self._hovered_text = None
                        self._hovered_text_original_html = None

            # Remove the markers
            for m in to_remove:
                self.plotItem.removeItem(m['line'])
                for text in m['texts']:
                    self.plotItem.removeItem(text)
                if 'summary_text' in m:
                    self.plotItem.removeItem(m['summary_text'])
                self.line_markers.remove(m)

            # Remove any difference items that involve the deleted markers
            diff_to_remove = []
            for diff_item in self.difference_items:
                if isinstance(diff_item, dict):
                    # Check if either marker in the difference was deleted
                    marker1 = diff_item.get('marker1')
                    marker2 = diff_item.get('marker2')
                    if marker1 in to_remove or marker2 in to_remove:
                        # Clear selected state if this diff text was selected
                        diff_text = diff_item.get('text')
                        if diff_text:
                            if diff_text == self._selected_summary_text:
                                self._selected_summary_text = None
                                self._selected_summary_original_html = None
                            if diff_text == self._hovered_text:
                                self._hovered_text = None
                                self._hovered_text_original_html = None
                        # Remove the difference line and text from the plot
                        self.plotItem.removeItem(diff_item['line'])
                        self.plotItem.removeItem(diff_item['text'])
                        diff_to_remove.append(diff_item)

            # Remove the difference items from the list
            for diff_item in diff_to_remove:
                self.difference_items.remove(diff_item)

            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            # Unselect all markers
            for m in self.line_markers:
                if m.get('selected', False):
                    m['selected'] = False
                    m['line'].setPen(pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=1))
                    m['line'].setHoverPen(pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4))
                    m['line'].update()
            event.accept()
        elif event.key() == Qt.Key.Key_V:
            self.add_vertical_marker()
            event.accept()
        elif event.key() == Qt.Key.Key_H:
            self.add_horizontal_marker()
            event.accept()
        elif event.key() == Qt.Key.Key_D:
            self.show_difference()
            event.accept()
        else:
            super().keyPressEvent(event)

    def add_vertical_marker_old(self):
        line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('k', style=Qt.PenStyle.DashLine))
        self.plotItem.addItem(line)
        line.sigPositionChanged.connect(lambda: self.update_marker_labels(line, vertical=True))
        self.update_marker_labels(line, vertical=True)

    def add_horizontal_marker_old(self):
        line = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('k', style=Qt.PenStyle.DashLine))
        self.plotItem.addItem(line)
        line.sigPositionChanged.connect(lambda: self.update_marker_labels(line, vertical=False))
        self.update_marker_labels(line, vertical=False)

    def update_marker_labels_old(self, line, vertical):
        # Remove old labels
        for text in self.marker_texts:
            self.plotItem.removeItem(text)
        self.marker_texts.clear()

        pos = line.value()
        for curve in getattr(self.plotItem, 'curves', []):
            try:
                xdata, ydata = curve.getData()
                if xdata is None or ydata is None or len(xdata) == 0 or len(ydata) == 0:
                    continue
                if vertical:
                    # Vertical line at x=pos, find closest y
                    idx = np.argmin(np.abs(xdata - pos))
                    x = xdata[idx]
                    y = ydata[idx]
                    text = pg.TextItem(f"({format_eng(pos)}, {format_eng(y)})", anchor=(0.5, 0.5))
                    text.setPos(pos, y)
                else:
                    # Horizontal line at y=pos, find closest x
                    idx = np.argmin(np.abs(ydata - pos))
                    x = xdata[idx]
                    y = ydata[idx]
                    text = pg.TextItem(f"({format_eng(x)}, {format_eng(pos)})", anchor=(0.5, 0.5))
                    text.setPos(x, pos)
                if self.should_show_texts():
                    self.plotItem.addItem(text)
                    self.marker_texts.append(text)
            except Exception:
                pass

    def show_difference(self):
        selected = [m for m in self.line_markers if m['selected']]
        if len(selected) == 2 and selected[0]['vertical'] == selected[1]['vertical']:
            # clear previous
            for item in self.difference_items:
                if isinstance(item, dict):
                    self.plotItem.removeItem(item['line'])
                    self.plotItem.removeItem(item['text'])
                else:
                    self.plotItem.removeItem(item)
            self.difference_items.clear()

            m1, m2 = selected
            pos1 = m1['line'].value()
            pos2 = m2['line'].value()

            if m1['vertical']:
                # vertical, difference in x
                diff = abs(pos2 - pos1)
                # draw horizontal line segment between pos1 and pos2 at center y
                y_center = (self.plotItem.viewRange()[1][0] + self.plotItem.viewRange()[1][1]) / 2
                x_vals = [pos1, pos2]
                y_vals = [y_center, y_center]
                line = pg.PlotCurveItem(x=x_vals, y=y_vals, pen=pg.mkPen('gray', width=2))
                self.plotItem.addItem(line)

                # text in middle
                x_mid = (pos1 + pos2) / 2
                text = pg.TextItem(f"ΔX: {format_eng(diff)}", anchor=(0.5, 0.5))
                text.setPos(x_mid, y_center)
                self.plotItem.addItem(text)
                text.setFlags(text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

                diff_dict = {
                    'line': line,
                    'text': text,
                    'horizontal': True,
                    'center_x': x_mid,
                    'center_y': y_center,
                    'relative_x': 0,
                    'relative_y': 0,
                    'x_vals': x_vals,
                    'y_vals': y_vals,
                    'marker1': m1,  # Track which markers are involved
                    'marker2': m2
                }
                self.difference_items.append(diff_dict)

            else:
                # horizontal, difference in y
                diff = abs(pos2 - pos1)
                x_center = (self.plotItem.viewRange()[0][0] + self.plotItem.viewRange()[0][1]) / 2
                x_vals = [x_center, x_center]
                y_vals = [pos1, pos2]
                line = pg.PlotCurveItem(x=x_vals, y=y_vals, pen=pg.mkPen('gray', width=2))
                self.plotItem.addItem(line)

                y_mid = (pos1 + pos2) / 2
                text = pg.TextItem(f"ΔY: {format_eng(diff)}", anchor=(0.5, 0.5))
                text.setPos(x_center, y_mid)
                self.plotItem.addItem(text)
                text.setFlags(text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

                diff_dict = {
                    'line': line,
                    'text': text,
                    'horizontal': False,
                    'center_x': y_mid,
                    'center_y': y_mid,
                    'relative_x': 0,
                    'relative_y': 0,
                    'x_vals': x_vals,
                    'y_vals': y_vals,
                    'marker1': m1,  # Track which markers are involved
                    'marker2': m2
                }
                self.difference_items.append(diff_dict)

        # Synchronize difference markers with attached plots
        plw = getattr(self, "parent_lookup_window", None)
        if plw:
            for attached_window in plw.get_attached_windows():
                attached_window.plot_widget.show_difference()

    def on_item_changed(self, item):
        # Update the position of the text items when the item is moved
        if isinstance(item, pg.TextItem):
            try:
                for marker_info in self.markers:
                    if marker_info.get("text") == item:
                        marker_info.get("marker").setPos(item.pos())
            except Exception:
                pass
            try:
                for diff in self.difference_items:
                    if isinstance(diff, dict) and diff.get('text') == item:
                        if diff['horizontal']:
                            diff['relative_x'] = item.pos().x() - diff['center_x']
                            diff['relative_y'] = item.pos().y() - diff['center_y']
                            new_y = diff['center_y'] + diff['relative_y']
                            diff['line'].setData(x=diff['x_vals'], y=[new_y, new_y])
                        else:
                            diff['relative_x'] = item.pos().x() - diff['center_x']
                            diff['relative_y'] = item.pos().y() - diff['center_y']
                            new_x = diff['center_x'] + diff['relative_x']
                            diff['line'].setData(x=[new_x, new_x], y=diff['y_vals'])
            except Exception:
                pass

class ROARLookupWindow(QWidget):
    def __init__(self, parent, expand_callback, top_level_app, graph_grid=None):
        super().__init__(parent)
        # Avoid importing large parts of roar_gui at module import time to prevent circular imports.
        # ROARTechBrowser and ROARPlotWidget are imported lazily below where needed.

        self.expand_callback = expand_callback
        self.top_level_app = top_level_app
        self.graph_grid = graph_grid  # Store reference to ROARGraphGrid
        self.is_expanded = False  # Track expansion state
        self.original_state = None  # Store splitter state
        self.expression_symbols = []
        self._is_updating = False

        # Create the main layout and restore moderate margins so the rest of the app spacing is preserved
        self.main_layout = QVBoxLayout(self)
        # Use comfortable default margins so other UI areas don't appear too tight
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)

        # Create the horizontal splitter for tech browser + controls (left) and graphing window (right)
        self.top_level_pane = QSplitter(Qt.Orientation.Horizontal, self)

        # Create the vertical splitter to split tech browser (top) from controls (bottom)
        self.tech_splitter = QSplitter(Qt.Orientation.Vertical, self)

        # Initialize the tech browser widget. Use the top-level app's tech_dict
        # when available to avoid referencing a possibly undefined global `tech_dict`.
        try:
            td = self.top_level_app.tech_dict if (self.top_level_app and hasattr(self.top_level_app, 'tech_dict')) else None
        except Exception:
            td = None

        # Delayed import of ROARTechBrowser to avoid circular import at module load
        try:
            from .roar_gui import ROARTechBrowser
        except Exception:
            from roar_gui import ROARTechBrowser

        self.tech_browser = ROARTechBrowser(self, lookup_window=self, top_level_app=self.top_level_app, tech_dict=td)

        # if DEBUG == False:
        self.tech_browser.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tech_browser.startup = False

        # Create a container for control widgets and use moderate internal spacing
        self.controls_container = QWidget()
        self.controls_layout = QGridLayout(self.controls_container)
        # Restore moderate internal margins so the rest of the controls keep their original spacing
        self.controls_layout.setContentsMargins(2, 2, 2, 2)
        self.controls_layout.setHorizontalSpacing(6)
        self.controls_layout.setVerticalSpacing(4)

        # Radio buttons for parameter source
        self.radio_device_params = QRadioButton("Device Params")
        self.radio_design_eq = QRadioButton("Design Eqs")
        self.radio_device_params.setChecked(True)
        # Track current mode on the instance (True = Device Params, False = Design Eqs)
        self.is_device_params_mode = self.radio_device_params.isChecked()

        # store the radio layout on the instance so other methods can reference it
        self.radio_layout = QHBoxLayout()
        # Tighten radio layout margins so it doesn't add extra vertical padding
        self.radio_layout.setContentsMargins(0, 0, 0, 0)
        self.radio_layout.setSpacing(2)
        self.radio_layout.addWidget(self.radio_device_params)
        self.radio_layout.addWidget(self.radio_design_eq)
        self.radio_layout.addStretch()
        self.controls_layout.addLayout(self.radio_layout, 0, 0, 1, 4)

        # Connect toggled signal(s) to keep mode variable in sync and update UI
        self.radio_device_params.toggled.connect(self.on_mode_changed)
        self.radio_design_eq.toggled.connect(self.on_mode_changed)

        # Individual Labels, ComboBoxes, and SpinBoxes for X, Y, and Z
        self.label_x = QLabel("X:")
        self.combo_x = QComboBox()
        if self.top_level_app:
            try:
                self.combo_x.addItems(self.top_level_app.lookups)
            except Exception:
                pass
        self.combo_x.setCurrentText("kgm")
        # Keep combo boxes left-aligned and do not allow them to expand horizontally
        self.combo_x.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.spin_x = EngSpinBox()
        self.spin_x.setMinimumWidth(80)
        # Make spinboxes expand horizontally to absorb extra space
        self.spin_x.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logx = QCheckBox("LogX")

        self.label_y = QLabel("Y:")
        self.combo_y = QComboBox()
        if self.top_level_app:
            try:
                self.combo_y.addItems(self.top_level_app.lookups)
            except Exception:
                pass
        self.combo_y.setCurrentText("kcgs")
        self.combo_y.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.spin_y = EngSpinBox()
        self.spin_y.setMinimumWidth(80)
        self.spin_y.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logy = QCheckBox("LogY")

        self.label_z = QLabel("Z:")
        self.combo_z = QComboBox()
        if self.top_level_app:
            try:
                self.combo_z.addItems(self.top_level_app.lookups)
            except Exception:
                pass
        self.combo_z.setCurrentText("iden")
        self.combo_z.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.spin_z = EngSpinBox()
        self.spin_z.setMinimumWidth(80)
        self.spin_z.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logz = QCheckBox("LogZ")

        # Clear markers / update graph when changing axes
        self.combo_x.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.combo_y.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.combo_z.currentIndexChanged.connect(self.on_axis_selection_changed)

        # Create a single splitter for each row to allow adjusting combo/spin widths
        # X row splitter
        self.splitter_x = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_x.setChildrenCollapsible(False)
        self.splitter_x.addWidget(self.combo_x)
        self.splitter_x.addWidget(self.spin_x)
        self.splitter_x.setSizes([200, 120])  # Favor combobox with more space

        # Y row splitter
        self.splitter_y = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_y.setChildrenCollapsible(False)
        self.splitter_y.addWidget(self.combo_y)
        self.splitter_y.addWidget(self.spin_y)
        self.splitter_y.setSizes([200, 120])  # Favor combobox with more space

        # Z row splitter
        self.splitter_z = QSplitter(Qt.Orientation.Horizontal)
        self.splitter_z.setChildrenCollapsible(False)
        self.splitter_z.addWidget(self.combo_z)
        self.splitter_z.addWidget(self.spin_z)
        self.splitter_z.setSizes([200, 120])  # Favor combobox with more space

               # Synchronize all three splitters to move together
        def sync_all_splitters(moved_splitter):
            sizes = moved_splitter.sizes()
            if moved_splitter is not self.splitter_x:
                self.splitter_x.blockSignals(True)
                self.splitter_x.setSizes(sizes)
                self.splitter_x.blockSignals(False)
            if moved_splitter is not self.splitter_y:
                self.splitter_y.blockSignals(True)
                self.splitter_y.setSizes(sizes)
                self.splitter_y.blockSignals(False)
            if moved_splitter is not self.splitter_z:
                self.splitter_z.blockSignals(True)
                self.splitter_z.setSizes(sizes)
                self.splitter_z.blockSignals(False)

        self.splitter_x.splitterMoved.connect(lambda: sync_all_splitters(self.splitter_x))
        self.splitter_y.splitterMoved.connect(lambda: sync_all_splitters(self.splitter_y))
        self.splitter_z.splitterMoved.connect(lambda: sync_all_splitters(self.splitter_z))

        self.controls_layout.addWidget(self.label_x, 1, 0)
        self.controls_layout.addWidget(self.splitter_x, 1, 1, 1, 2)  # Span columns 1 and 2
        self.controls_layout.addWidget(self.checkbox_logx, 1, 3)

        self.controls_layout.addWidget(self.label_y, 2, 0)
        self.controls_layout.addWidget(self.splitter_y, 2, 1, 1, 2)  # Span columns 1 and 2
        self.controls_layout.addWidget(self.checkbox_logy, 2, 3)

        self.controls_layout.addWidget(self.label_z, 3, 0)
        self.controls_layout.addWidget(self.splitter_z, 3, 1, 1, 2)  # Span columns 1 and 2
        self.controls_layout.addWidget(self.checkbox_logz, 3, 3)

        # Set column stretch factors
        self.controls_layout.setColumnStretch(0, 0)  # Labels
        self.controls_layout.setColumnStretch(1, 1)  # Splitters expand
        self.controls_layout.setColumnStretch(2, 0)  # (Splitters span this column too)
        self.controls_layout.setColumnStretch(3, 0)  # Checkboxes

        # Individual Checkboxes with specific callbacks
        self.checkbox_3d = QCheckBox("3-D")
        self.checkbox_contour = QCheckBox("Contour")
        self.checkbox_black_bg = QCheckBox("Black BG")

        self.copy_button = QPushButton("Copy")
        self.copy_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.copy_button.setFixedSize(56, 22)

        # Settings container
        self.settings_container = QWidget()
        s_layout = QHBoxLayout(self.settings_container)
        s_layout.setContentsMargins(0, 0, 0, 0)
        s_layout.setSpacing(0)
        s_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        indicator_size = 12
        cb_widget_size = 14

        self.settings_lock_button = QPushButton("🔒")
        lock_h = cb_widget_size * 2
        lock_w = lock_h
        self.settings_lock_button.setFixedSize(lock_w, lock_h)
        self.settings_lock_button.setToolTip("Lock / Settings")
        self.settings_lock_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        try:
            self.settings_lock_button.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 18px; }")
        except Exception:
            pass
        s_layout.addWidget(self.settings_lock_button)

        self.settings_grid = QWidget()
        g_layout = QGridLayout(self.settings_grid)
        g_layout.setContentsMargins(0, 0, 0, 0)
        g_layout.setHorizontalSpacing(0)
        g_layout.setVerticalSpacing(0)
        self.settings_grid.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.setting_checkboxes = []
        cb_style = ("QCheckBox { margin: 0px; padding: 0px; spacing: 0px; }"
                    f"QCheckBox::indicator {{ width: {indicator_size}px; height: {indicator_size}px; margin: 0px; }}")
        for i in range(4):
            cb = QCheckBox()
            cb.setToolTip(f"Option {i+1}")
            cb.setStyleSheet(cb_style)
            try:
                cb.setContentsMargins(0, 0, 0, 0)
            except Exception:
                pass
            cb.setFixedSize(cb_widget_size, cb_widget_size)
            cb.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self.setting_checkboxes.append(cb)

        g_layout.addWidget(self.setting_checkboxes[0], 0, 0)
        g_layout.addWidget(self.setting_checkboxes[1], 0, 1)
        g_layout.addWidget(self.setting_checkboxes[2], 1, 0)
        g_layout.addWidget(self.setting_checkboxes[3], 1, 1)

        grid_w = cb_widget_size * 2
        grid_h = cb_widget_size * 2
        self.settings_grid.setFixedSize(grid_w, grid_h)

        s_layout.addWidget(self.settings_grid)

        # Expand button
        self.expand_button = QPushButton("Expand")
        self.expand_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        try:
            self.expand_button.setFixedHeight(22)
        except Exception:
            pass
        try:
            self.expand_button.setStyleSheet("QPushButton { margin: 0px; padding: 0px; }")
        except Exception:
            pass

        self.row5_layout = QHBoxLayout()
        self.row5_layout.setContentsMargins(0, 0, 0, 0)
        self.row5_layout.setSpacing(2)
        self.row5_layout.addWidget(self.checkbox_3d)
        self.row5_layout.addWidget(self.checkbox_contour)
        self.row5_layout.addWidget(self.copy_button)
        self.row5_layout.addWidget(self.expand_button)
        self.row5_layout.addWidget(self.settings_container)

        self.controls_layout.addLayout(self.row5_layout, 5, 0, 1, 4)

        try:
            self.controls_layout.setRowMinimumHeight(5, lock_h)
        except Exception:
            pass

        # Add widgets to the vertical splitter
        self.tech_splitter.addWidget(self.tech_browser)  # Tech browser (top)
        self.tech_splitter.addWidget(self.controls_container)  # Controls (bottom)

        # Adjust stretch factors for tech splitter (tech browser gets more space than controls)
        self.tech_splitter.setStretchFactor(0, 3)
        self.tech_splitter.setStretchFactor(1, 1)

        self.plot_widget = ROARPlotWidget(parent_lookup_window=self, top_level_app=self.top_level_app)

        # Initialize marker lists for this window
        self.line_markers = []  # Horizontal and vertical line markers
        self.selected_marker = None  # Currently selected marker

        # Create pyqtgraph OpenGL widget for 3D mesh plotting
        try:
            self.gl_widget = ROAR3DViewWidget(parent_lookup_window=self)
            self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.gl_widget.setVisible(False)
            self.gl_items = []
        except Exception as e:
            debug_print(f"Could not create ROAR3DViewWidget: {e}")
            self.gl_widget = None
            self.gl_items = []

        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.plot_widget)
        # Add GL widget (3D) and keep it hidden until used
        if self.gl_widget is not None:
            right_layout.addWidget(self.gl_widget)
        self.top_level_pane.addWidget(self.tech_splitter)  # Left side (tech browser + controls)
        self.top_level_pane.addWidget(right_container)  # Right side (graphing window container)

        # Adjust stretch factors for main splitter (tech section gets less space than graphing)
        self.top_level_pane.setStretchFactor(0, 1)
        self.top_level_pane.setStretchFactor(1, 2)

        # Add splitter to the main layout
        self.main_layout.addWidget(self.top_level_pane)

        self.is_dark_mode = False
        self.is_3d_mode = False
        self.colors = [pg.mkPen(color) for color in ['r', 'g', 'b', 'y']]
        self.color_list = [Qt.GlobalColor.red, Qt.GlobalColor.green, Qt.GlobalColor.blue,
                           Qt.GlobalColor.cyan, Qt.GlobalColor.magenta, Qt.GlobalColor.yellow]
        self.style_list = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine]
        self.current_color_index = 0
        self.current_style_index = 0

        self.expand_button.clicked.connect(self.toggle_expand)

        self.checkbox_logx.stateChanged.connect(self.update_log_scale)
        self.checkbox_logy.stateChanged.connect(self.update_log_scale)
        self.checkbox_logz.stateChanged.connect(lambda _: self.update_graph_from_tech_browser())

        self.checkbox_3d.stateChanged.connect(self._update_z_controls_state)
        self.checkbox_black_bg.stateChanged.connect(self.on_background_color_changed)
        self._update_z_controls_state()

        # Ensure combo boxes and visibility reflect the current radio selection
        self.update_combobox_items()

        # Initialize attachment checkboxes
        self.update_attachment_checkboxes()

        # Connect copy button
        self.copy_button.clicked.connect(self.on_copy_button_clicked)

        # Track copy/paste state
        self.copied_state = None  # Stores the state when in copy mode

    # ...existing code...

    def update_combobox_items(self):
        is_device_params = self.radio_device_params.isChecked()

        # Save current selections before clearing
        current_x = self.combo_x.currentText()
        current_y = self.combo_y.currentText()
        current_z = self.combo_z.currentText()

        # Block signals to prevent cascading updates during clear/addItems
        self.combo_x.blockSignals(True)
        self.combo_y.blockSignals(True)
        self.combo_z.blockSignals(True)

        try:
            # Update visibility of Z-axis and 3D controls
            self.label_z.setVisible(not is_device_params)
            self.combo_z.setVisible(not is_device_params)
            self.spin_z.setVisible(not is_device_params)
            self.checkbox_logz.setVisible(not is_device_params)
            self.checkbox_3d.setVisible(not is_device_params)
            self.checkbox_contour.setVisible(not is_device_params)


            if is_device_params:
                items = list(self.top_level_app.lookups) if self.top_level_app else []
                self.combo_x.clear()
                self.combo_y.clear()
                self.combo_z.clear()
                self.combo_x.addItems(items)
                self.combo_y.addItems(items)
                self.combo_z.addItems(items)

                # Restore previous selections if they exist, otherwise use defaults
                if current_x in items:
                    self.combo_x.setCurrentText(current_x)
                else:
                    self.combo_x.setCurrentText("kgm")
                if current_y in items:
                    self.combo_y.setCurrentText(current_y)
                else:
                    self.combo_y.setCurrentText("kcgs")
                if current_z in items:
                    self.combo_z.setCurrentText(current_z)
                else:
                    self.combo_z.setCurrentText("iden")
            else:
                items = list(self.expression_symbols) if self.expression_symbols else []
                self.combo_x.clear()
                self.combo_y.clear()
                self.combo_z.clear()
                self.combo_x.addItems(items)
                self.combo_y.addItems(items)
                self.combo_z.addItems(items)

                # Restore previous selections if they exist, otherwise use defaults
                if current_x in items:
                    self.combo_x.setCurrentText(current_x)
                elif items:
                    self.combo_x.setCurrentIndex(0)
                if current_y in items:
                    self.combo_y.setCurrentText(current_y)
                elif items:
                    self.combo_y.setCurrentIndex(min(1, len(items) - 1))
                if current_z in items:
                    self.combo_z.setCurrentText(current_z)
                elif items:
                    self.combo_z.setCurrentIndex(min(2, len(items) - 1))
        finally:
            # Always unblock signals
            self.combo_x.blockSignals(False)
            self.combo_y.blockSignals(False)
            self.combo_z.blockSignals(False)

        try:
            self.controls_layout.removeWidget(self.checkbox_3d)
            self.controls_layout.removeWidget(self.checkbox_contour)
        except Exception:
            pass

        if is_device_params:
            self.checkbox_3d.hide()
            self.checkbox_contour.hide()
            try:
                self.expand_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                self.expand_button.setMinimumWidth(0)
                self.expand_button.setMaximumWidth(16777215)
                self.expand_button.setFixedHeight(22)
            except Exception:
                pass
        else:
            self.checkbox_3d.show()
            self.checkbox_contour.show()
            try:
                self.expand_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
                self.expand_button.setFixedWidth(56)
                self.expand_button.setFixedHeight(22)
            except Exception:
                pass

        self.settings_container.setVisible(True)

        try:
            self.controls_layout.update()
        except Exception:
            pass

    def on_mode_changed(self, _checked):
        self.is_device_params_mode = self.radio_device_params.isChecked()

        # When switching to Device Params mode, hide any 3D plots
        if self.is_device_params_mode:
            if self.gl_widget is not None:
                self.gl_widget.setVisible(False)
            self.plot_widget.show()

        self.update_combobox_items()
        self.update_attachment_checkboxes()

    def on_background_color_changed(self):
        """Update the 3D plot background when the Black BG checkbox changes"""
        if self.gl_widget is not None and self.gl_widget.isVisible():
            # 3D plots always use black background
            self.gl_widget.setBackgroundColor(0, 0, 0)
        # Redraw the plot with new background color
        self.update_graph_from_tech_browser()

    def auto_fit_3d(self):
        """Reset the 3D GL camera so the entire scene fits in view.

        Data is normalised to a [-5, 5] cube, so a distance of 20 with a
        moderate elevation gives a good overview.  The centre of the view is
        placed at the origin of the normalised cube.
        """
        if self.gl_widget is None or not self.gl_widget.isVisible():
            return
        try:
            self.gl_widget.setCameraPosition(distance=20, elevation=30, azimuth=-135)
            # Reset the centre of rotation to the origin of the normalised cube
            self.gl_widget.opts['center'] = pg.Vector(0, 0, 0)
            self.gl_widget.update()
        except Exception:
            pass


    def update_expression_symbols(self, symbols):
        self.expression_symbols = symbols
        self.update_combobox_items()

    def _update_z_controls_state(self):
        is_3d = self.checkbox_3d.isChecked()
        self.label_z.setEnabled(is_3d)
        self.combo_z.setEnabled(is_3d)
        self.spin_z.setEnabled(is_3d)
        self.checkbox_logz.setEnabled(is_3d)
        self.checkbox_contour.setEnabled(is_3d)

    def set_corner_boldness(self, path, bold: bool):
        """Set pen width of the trace corresponding to `path` (full corner path).

        This method is called from `ROARTechBrowser` when a corner is both checked
        and selected; it will search the current `plot_widget` for curves whose
        name/legend matches `path` and set a bolder pen.
        """
        try:
            pw = getattr(self, 'plot_widget', None)
            if pw is None:
                return
            plot_item = pw.getPlotItem()
            if not hasattr(plot_item, 'curves'):
                return

            width = 3 if bold else 1

            # Build the legend string format used when plotting: "PDK: {pdk}, L: {length}, corner: {corner}"
            legend_str = None
            try:
                parts = [p.strip() for p in path.split('>') if p.strip()]
                if len(parts) >= 5:
                    # Path format: PDK > pdk_name > model > length > corner
                    _, pdk, _model, length, corner = parts[:5]
                    legend_str = f"PDK: {pdk}, L: {length}, corner: {corner}"
                elif len(parts) >= 4:
                    # Fallback if top-level 'PDK' is omitted
                    pdk, _model, length, corner = parts[:4]
                    legend_str = f"PDK: {pdk}, L: {length}, corner: {corner}"
            except Exception:
                legend_str = None

            for curve in list(getattr(plot_item, 'curves', [])):
                try:
                    name = curve.opts.get('name') if hasattr(curve, 'opts') else None

                    # Match by legend string (primary) or path (fallback)
                    matched = False
                    if legend_str and name == legend_str:
                        matched = True
                    elif name == path:
                        matched = True
                    elif legend_str and isinstance(name, str) and legend_str in name:
                        matched = True
                    elif isinstance(name, str) and path in name:
                        matched = True

                    if matched:
                        # Get current pen color and create new pen with updated width
                        pen = curve.opts.get('pen') if hasattr(curve, 'opts') else None
                        try:
                            if pen is not None and hasattr(pen, 'color'):
                                col = pen.color()
                                curve.setPen(pg.mkPen(col, width=width))
                            else:
                                curve.setPen(pg.mkPen(width=width))
                        except Exception:
                            curve.setPen(pg.mkPen(width=width))
                except Exception:
                    pass
        except Exception:
            pass

    def clear_markers(self):
        pw = getattr(self, "plot_widget", None)
        if not pw:
            return
        for marker_info in pw.markers[:]:
            try:
                if "marker" in marker_info and marker_info["marker"] is not None:
                    pw.plotItem.removeItem(marker_info["marker"])
                if "text" in marker_info and marker_info["text"] is not None:
                    pw.plotItem.removeItem(marker_info["text"])
            except Exception:
                pass
        pw.markers.clear()
        for marker in pw.line_markers[:]:
            pw.plotItem.removeItem(marker['line'])
            for text in marker['texts']:
                pw.plotItem.removeItem(text)
            if 'summary_text' in marker:
                pw.plotItem.removeItem(marker['summary_text'])
        pw.line_markers.clear()
        for item in pw.difference_items:
            if isinstance(item, dict):
                pw.plotItem.removeItem(item['line'])
                pw.plotItem.removeItem(item['text'])
            else:
                pw.plotItem.removeItem(item)
        pw.difference_items.clear()

        # Also clear 3-D markers on the GL widget
        gl_w = getattr(self, 'gl_widget', None)
        if gl_w is not None and hasattr(gl_w, 'clear_all_3d_markers'):
            try:
                gl_w.clear_all_3d_markers()
            except Exception:
                pass

    def sync_log_checkboxes(self):
        x_log = self.plot_widget.getPlotItem().getAxis('bottom').logMode
        y_log = self.plot_widget.getPlotItem().getAxis('left').logMode

        self.checkbox_logx.setChecked(x_log)
        self.checkbox_logy.setChecked(y_log)

    def update_log_scale(self):
        x_log = self.checkbox_logx.isChecked()
        y_log = self.checkbox_logy.isChecked()

        # Set log mode
        self.plot_widget.getPlotItem().setLogMode(x=x_log, y=y_log)

        # Force autorange to recalculate axis ranges with the new log mode
        # This fixes the issue where Y-axis exponents become extremely small
        try:
            self.plot_widget.plotItem.autoRange()
        except Exception:
            pass

        # Reposition markers after log scale change
        for marker in self.plot_widget.line_markers:
            linear_pos = marker['linear_pos']
            if marker['vertical']:
                new_pos = np.log10(linear_pos) if x_log and linear_pos > 0 else linear_pos
            else:
                new_pos = np.log10(linear_pos) if y_log and linear_pos > 0 else linear_pos
            marker['line'].setPos(new_pos)
            # Clear summary text offset when scale changes - offsets from old coordinate system
            # don't translate properly to new coordinate system
            if 'text_offsets' in marker and '__summary__' in marker['text_offsets']:
                del marker['text_offsets']['__summary__']
            # Update the text labels for the line marker
            self.plot_widget.update_marker_labels(marker, sync=False)
        for marker_info in self.plot_widget.markers:
            x, y = marker_info['pos']
            plot_x = np.log10(x) if x_log and x > 0 else x
            plot_y = np.log10(y) if y_log and y > 0 else y
            marker_info['marker'].setData(x=[plot_x], y=[plot_y])
            marker_info['text'].setPos(plot_x, plot_y)
        self.update_graph_from_tech_browser()

        # NOTE: Do NOT synchronize log scale with attached windows.
        # When windows are 'locked' together we still want only the originating
        # window to change its axis scale (log/linear). Propagating the
        # checkbox state to attached windows caused both windows to flip scale
        # together, which is undesirable. Markers and other synced behaviors
        # remain controlled elsewhere (marker sync uses separate logic).
        # If an opt-in sync of axis scale is desired in future, add a
        # per-window setting (e.g. self.sync_scale) and check it here.
        pass

    def on_copy_button_clicked(self):
        """Handle copy/paste button click"""
        if self.copy_button.text() == "Copy":
            # Start copy mode
            self.start_copy_mode()
        else:
            # Paste mode - apply the copied state to this window
            self.apply_paste()

    def start_copy_mode(self):
        """Capture current state and switch other windows to paste mode"""
        # Capture the current state
        self.copied_state = self.capture_state()

        # Change other windows' copy buttons to "Paste"
        if self.graph_grid:
            for window in self.graph_grid.lookup_windows:
                if window != self:
                    window.copy_button.setText("Paste")

        # Set focus to enable escape key handling
        self.setFocus()

    def apply_paste(self):
        """Apply the copied state from the source window to this window"""
        if not self.graph_grid:
            return

        # Find the source window (the one still showing "Copy")
        source_window = None
        for window in self.graph_grid.lookup_windows:
            if window.copy_button.text() == "Copy" and window.copied_state is not None:
                source_window = window
                break

        if source_window and source_window.copied_state:
            # Apply the copied state to this window
            self.restore_state(source_window.copied_state)

            # Cancel copy mode
            self.cancel_copy_mode()

    def cancel_copy_mode(self):
        """Cancel copy mode and reset all buttons to 'Copy'"""
        if self.graph_grid:
            for window in self.graph_grid.lookup_windows:
                window.copy_button.setText("Copy")
                window.copied_state = None

    def capture_state(self):
        """Capture the current state of this window for copying"""
        state = {
            # Radio button state
            'is_device_params_mode': self.radio_device_params.isChecked(),

            # Combo box selections
            'combo_x_text': self.combo_x.currentText(),
            'combo_y_text': self.combo_y.currentText(),
            'combo_z_text': self.combo_z.currentText(),

            # Spin box values
            'spin_x_value': self.spin_x.value(),
            'spin_y_value': self.spin_y.value(),
            'spin_z_value': self.spin_z.value(),

            # Checkbox states
            'checkbox_logx': self.checkbox_logx.isChecked(),
            'checkbox_logy': self.checkbox_logy.isChecked(),
            'checkbox_logz': self.checkbox_logz.isChecked(),
            'checkbox_3d': self.checkbox_3d.isChecked(),
            'checkbox_contour': self.checkbox_contour.isChecked(),
            'checkbox_black_bg': self.checkbox_black_bg.isChecked(),

            # NOTE: setting_checkboxes are NOT included - these represent window attachments/locks
            # which should not be copied to other windows

            # Tech browser state - checked items
            'checked_paths': self.tech_browser.get_checked_item_paths(),

            # Tech browser color map
            'color_map': dict(self.tech_browser.color_map),  # Make a copy

            # Markers - capture linear positions and orientations
            'markers': [
                {
                    'vertical': m['vertical'],
                    'linear_pos': m['linear_pos'],
                    'selected': False  # Don't copy selection state
                }
                for m in self.plot_widget.line_markers
            ],
        }
        return state

    def restore_state(self, state):
        """Restore the window state from a captured state dictionary"""
        try:
            # Temporarily disable updates to prevent repeated graph updates
            self._is_updating = True

            # Restore radio button and explicitly set the mode variable
            if state.get('is_device_params_mode', True):
                self.radio_device_params.setChecked(True)
                self.is_device_params_mode = True
            else:
                self.radio_design_eq.setChecked(True)
                self.is_device_params_mode = False

            # Update combo boxes to match the mode
            self.update_combobox_items()

            # Restore combo boxes
            self.combo_x.setCurrentText(state.get('combo_x_text', ''))
            self.combo_y.setCurrentText(state.get('combo_y_text', ''))
            self.combo_z.setCurrentText(state.get('combo_z_text', ''))

            # Restore spin boxes
            self.spin_x.setValue(state.get('spin_x_value', 0))
            self.spin_y.setValue(state.get('spin_y_value', 0))
            self.spin_z.setValue(state.get('spin_z_value', 0))

            # Restore checkboxes
            self.checkbox_logx.setChecked(state.get('checkbox_logx', False))
            self.checkbox_logy.setChecked(state.get('checkbox_logy', False))
            self.checkbox_logz.setChecked(state.get('checkbox_logz', False))
            self.checkbox_3d.setChecked(state.get('checkbox_3d', False))
            self.checkbox_contour.setChecked(state.get('checkbox_contour', False))
            self.checkbox_black_bg.setChecked(state.get('checkbox_black_bg', False))

            # NOTE: setting_checkboxes are NOT restored - these represent window attachments/locks
            # which should not be copied to other windows

            # Restore checked items in tech browser first
            if 'checked_paths' in state:
                self.restore_tech_browser_checks(state['checked_paths'])

            # Restore tech browser color map after check states are set
            if 'color_map' in state:
                # First, clear all existing icons to prevent artifacts
                for path, item in self.tech_browser.path_to_item.items():
                    if item.childCount() == 0:  # Only clear icons on leaf nodes
                        item.setIcon(0, QIcon())  # Empty icon

                # Now set the color map and icons
                self.tech_browser.color_map = dict(state['color_map'])
                # Update icons with new colors - only for items that exist and are leaf nodes
                for path, color in self.tech_browser.color_map.items():
                    if path in self.tech_browser.path_to_item:
                        item = self.tech_browser.path_to_item[path]
                        # Only set icon on leaf nodes (corners)
                        if item.childCount() == 0:
                            self.tech_browser.set_item_icon(item, color)

            # Re-enable updates
            self._is_updating = False

            # Update the graph
            self.update_graph_from_tech_browser()

            # Restore markers after the graph is updated
            if 'markers' in state:
                self.restore_markers(state['markers'])

        except Exception as e:
            self._is_updating = False
            debug_print(f"Error restoring state: {e}")

    def restore_markers(self, markers_data):
        """Restore markers from captured marker data"""
        try:
            # Clear existing markers first
            for m in list(self.plot_widget.line_markers):
                self.plot_widget.plotItem.removeItem(m['line'])
                for text in m['texts']:
                    self.plot_widget.plotItem.removeItem(text)
                if 'summary_text' in m:
                    self.plot_widget.plotItem.removeItem(m['summary_text'])
            self.plot_widget.line_markers.clear()

            # Recreate markers from data WITHOUT syncing to attached windows
            # This prevents duplicate markers when pasting
            for marker_data in markers_data:
                if marker_data['vertical']:
                    self.plot_widget.add_vertical_marker(linear_pos=marker_data['linear_pos'], sync=False)
                else:
                    self.plot_widget.add_horizontal_marker(linear_pos=marker_data['linear_pos'], sync=False)

        except Exception as e:
            debug_print(f"Error restoring markers: {e}")

    def restore_tech_browser_checks(self, checked_paths):
        """Restore the checked state of items in the tech browser"""
        try:
            # Set updating flag on both the lookup window and tech browser
            self._is_updating = True
            if hasattr(self.tech_browser, 'startup'):
                old_startup = self.tech_browser.startup
                self.tech_browser.startup = True

            # Temporarily block signals to prevent handle_item_changed from propagating checks
            self.tech_browser.tree.blockSignals(True)

            # First, uncheck all items
            def uncheck_all(item):
                item.setCheckState(0, Qt.CheckState.Unchecked)
                for i in range(item.childCount()):
                    uncheck_all(item.child(i))

            root = self.tech_browser.tree.invisibleRootItem()
            for i in range(root.childCount()):
                uncheck_all(root.child(i))

            # Now check only the leaf items (corners) that should be checked
            for path in checked_paths:
                if path in self.tech_browser.path_to_item:
                    item = self.tech_browser.path_to_item[path]
                    # Only check the actual item, not parents
                    # This ensures only the exact items from the source are checked
                    item.setCheckState(0, Qt.CheckState.Checked)

            # Update parent check states to reflect children
            # This shows PartiallyChecked for parents with some (but not all) children checked
            def update_parent_states(item):
                if item.childCount() == 0:
                    return

                # Check children first (bottom-up approach)
                for i in range(item.childCount()):
                    update_parent_states(item.child(i))

                # Count checked children
                checked_count = 0
                total_count = item.childCount()

                for i in range(total_count):
                    child = item.child(i)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        checked_count += 1
                    elif child.checkState(0) == Qt.CheckState.PartiallyChecked:
                        # If any child is partially checked, parent should be partially checked
                        item.setCheckState(0, Qt.CheckState.PartiallyChecked)
                        return

                # Set parent state based on children
                if checked_count == 0:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                elif checked_count == total_count:
                    item.setCheckState(0, Qt.CheckState.Checked)
                else:
                    item.setCheckState(0, Qt.CheckState.PartiallyChecked)

            # Update all parent states
            for i in range(root.childCount()):
                update_parent_states(root.child(i))

            # Re-enable signals
            self.tech_browser.tree.blockSignals(False)

            # Restore startup flag
            if hasattr(self.tech_browser, 'startup'):
                self.tech_browser.startup = old_startup

        except Exception as e:
            debug_print(f"Error restoring tech browser checks: {e}")
        finally:
            # Note: Don't reset _is_updating here - let the caller handle it
            pass

    def keyPressEvent(self, event):
        """Handle keyboard events for the lookup window"""
        if event.key() == Qt.Key.Key_Escape:
            # Check if we're in copy mode
            if self.graph_grid:
                in_copy_mode = False
                for window in self.graph_grid.lookup_windows:
                    if window.copied_state is not None or window.copy_button.text() == "Paste":
                        in_copy_mode = True
                        break

                if in_copy_mode:
                    # Cancel copy mode
                    self.cancel_copy_mode()
                    event.accept()
                    return

        # Pass to parent class for default handling
        super().keyPressEvent(event)

    def on_axis_selection_changed(self, _idx=None):
        try:
            self.clear_markers()
        except Exception:
            pass
        try:
            self.update_graph_from_tech_browser()
        except Exception:
            pass
        try:
            if hasattr(self, 'plot_widget') and self.plot_widget is not None:
                self.plot_widget.plotItem.autoRange()
        except Exception:
            pass
        self.update_attachment_checkboxes()
        for other in self.graph_grid.lookup_windows:
            if other != self:
                other.update_attachment_checkboxes()

    def toggle_expand(self):
        if not self.is_expanded:
            self.expand_plot()
        else:
            self.contract_plot()

    def expand_plot(self):
        if not self.graph_grid:
            return

        grid = self.graph_grid
        self.original_state = grid.grid_splitter.saveState()

        grid.lookup_window_1.setParent(None)
        grid.lookup_window_2.setParent(None)
        grid.lookup_window_3.setParent(None)
        grid.lookup_window_4.setParent(None)

        grid.grid_splitter.addWidget(self)
        grid.grid_splitter.setStretchFactor(0, 1)

        self.is_expanded = True
        self.expand_button.setText("Contract")

    def contract_plot(self):
        if not self.graph_grid or not self.original_state:
            return

        grid = self.graph_grid
        grid.grid_splitter.restoreState(self.original_state)

        grid.grid_splitter.addWidget(grid.top_splitter)
        grid.grid_splitter.addWidget(grid.bottom_splitter)

        grid.top_splitter.addWidget(grid.lookup_window_1)
        grid.top_splitter.addWidget(grid.lookup_window_2)
        grid.bottom_splitter.addWidget(grid.lookup_window_3)
        grid.bottom_splitter.addWidget(grid.lookup_window_4)

        self.is_expanded = False
        self.expand_button.setText("Expand")

    def toggle_dark_mode(self):
        self.is_dark_mode = self.dark_mode_checkbox.isChecked()
        self.plot_widget.setBackground('k' if self.is_dark_mode else 'w')
        self.plot_scientific_data()

    def toggle_three_d_mode(self):
        self.is_3d_mode = self.three_d_checkbox.isChecked()

        # If turning OFF 3D mode, hide the GL widget and show the 2D plot widget
        if not self.is_3d_mode:
            if self.gl_widget is not None:
                self.gl_widget.setVisible(False)
            self.plot_widget.show()

        self.plot_scientific_data()

    def change_plot_colors(self):
        for i in range(len(self.colors)):
            color = QColorDialog.getColor()
            if color.isValid():
                self.colors[i] = pg.mkPen(color.name())
        self.plot_scientific_data()

    def plot_scientific_data(self):
        self.plot_widget.clear()
        x = np.linspace(0, 10, 100)
        for i, color in enumerate(self.colors):
            y = np.sin(x + i)
            self.plot_widget.plot(x, y, pen=color)

    def select_item(self, item, column):
        if self.lookup_window is not None:
            self.lookup_window.update_graph_from_tech_browser()

    def get_corner_dfs_from_models_selected(self):
        models_selected = self.tech_browser.get_checked_item_paths()
        corner_dfs = []
        for model in models_selected:
            model_tokens = model.split(">")
            pdk = model_tokens[1]
            model_name = model_tokens[2]
            length = model_tokens[3]
            corner = model_tokens[4]
            cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
            corner_df = cid_corner.df
            corner_dfs.append(corner_df)
        return corner_dfs

    # ------------------------------------------------------------------
    #  Corner-tuple builder for Design-Equations mode
    # ------------------------------------------------------------------
    def _build_corner_tuples(self, device_corners, models_selected):
        """Build matched corner tuples for per-device equation evaluation.

        Returns a list of tuples.  Each tuple is a dict mapping
        device_name -> {"path": ..., "df": DataFrame, "corner_name": ...}.

        When all devices are Global the list has one entry per
        tech-browser-selected corner (same as before).

        When any device has a custom corner list the function builds
        index-matched tuples (tuple-0 = every device's first corner,
        tuple-1 = every device's second corner, etc).
        """
        tech_dict = self.tech_browser.tech_dict

        # Resolve each device's corner list
        per_device = {}  # device_name -> list of {path, df, corner_name}

        for dev_name, dev_info in device_corners.items():
            corners_list = dev_info.get('corners')  # None => global

            if corners_list is None:
                # Global: use the tech-browser-selected corners
                resolved = []
                for mpath in models_selected:
                    tokens = mpath.split('>')
                    if len(tokens) >= 5:
                        _pdk, _model, _length, _corner = tokens[1], tokens[2], tokens[3], tokens[4]
                        try:
                            df = tech_dict[_pdk][_model][_length]["corners"][_corner].df
                            resolved.append({
                                "path": f"{_pdk}>{_model}>{_length}>{_corner}",
                                "df": df,
                                "corner_name": _corner,
                            })
                        except (KeyError, AttributeError):
                            debug_print(f"[TUPLES] Could not resolve global corner {mpath} for device {dev_name}")
                per_device[dev_name] = resolved
            else:
                # Device-specific corners
                corner_paths = dev_info.get('corner_paths') or []
                pdk = dev_info.get('pdk')
                model = dev_info.get('model')
                length = dev_info.get('length')
                resolved = []
                for idx, cname in enumerate(corners_list):
                    df = None
                    # Try stored path first
                    if idx < len(corner_paths) and corner_paths[idx]:
                        cpath = corner_paths[idx]
                        cp_tokens = cpath.split('>')
                        if len(cp_tokens) >= 5:
                            try:
                                df = tech_dict[cp_tokens[1]][cp_tokens[2]][cp_tokens[3]]["corners"][cp_tokens[4]].df
                                pdk = cp_tokens[1]
                                model = cp_tokens[2]
                                length = cp_tokens[3]
                            except (KeyError, AttributeError):
                                pass
                    # Fallback: use pdk/model/length from device_corners metadata
                    if df is None and pdk and model and length:
                        try:
                            df = tech_dict[pdk][model][length]["corners"][cname].df
                        except (KeyError, AttributeError):
                            pass
                    if df is not None:
                        resolved.append({
                            "path": f"{pdk}>{model}>{length}>{cname}",
                            "df": df,
                            "corner_name": cname,
                        })
                    else:
                        debug_print(f"[TUPLES] Could not resolve corner '{cname}' "
                                    f"for device {dev_name} (pdk={pdk}, model={model}, length={length})")
                per_device[dev_name] = resolved

        if not per_device:
            return []

        # Build index-matched tuples
        min_len = min(len(v) for v in per_device.values()) if per_device else 0
        if min_len == 0:
            debug_print("[TUPLES] At least one device has 0 resolved corners")
            return []

        max_len = max(len(v) for v in per_device.values())
        if max_len != min_len:
            debug_print(f"[TUPLES] Corner-count mismatch (min={min_len}, max={max_len}); truncating to {min_len}")

        tuples_list = []
        for i in range(min_len):
            tup = {}
            for dev_name, resolved in per_device.items():
                tup[dev_name] = resolved[i]
            tuples_list.append(tup)

        debug_print(f"[TUPLES] Built {len(tuples_list)} corner tuple(s) for "
                    f"{len(per_device)} device(s): "
                    + ", ".join(f"{d}({len(v)})" for d, v in per_device.items()))
        return tuples_list

    def update_graph_from_tech_browser(self, equation_eval=None, skip_post_processing=False):
        if self._is_updating:
            return
        self._is_updating = True
        self._custom_tuples_done = set()  # Reset per-call tracking for all-custom corner tuples

        try:
            # Top-level try to ensure the finally block below always executes
            # (this was missing and caused a SyntaxError during import).
            models_selected = self.tech_browser.get_checked_item_paths()

            marker_positions = []
            for marker_info in self.plot_widget.markers:
                marker_positions.append(marker_info)

            line_marker_positions = []
            for m in self.plot_widget.line_markers:
                # Save text offsets before markers are cleared
                text_offsets = m.get('text_offsets', {}).copy()
                # Also capture any current offsets from texts that haven't been saved yet
                for i, text in enumerate(m.get('texts', [])):
                    try:
                        curve_idx = text.property('curve_idx')
                        if curve_idx is None:
                            curve_idx = i
                        current_pos = text.pos()
                        base_pos = text.property('base_pos')
                        if base_pos is not None:
                            offset_x = current_pos.x() - base_pos[0]
                            offset_y = current_pos.y() - base_pos[1]
                            if offset_x != 0 or offset_y != 0:
                                text_offsets[curve_idx] = (offset_x, offset_y)
                    except Exception:
                        pass
                # Save summary text offset
                if 'summary_text' in m:
                    try:
                        summary = m['summary_text']
                        current_pos = summary.pos()
                        base_pos = summary.property('base_pos')
                        if base_pos is not None:
                            offset_x = current_pos.x() - base_pos[0]
                            offset_y = current_pos.y() - base_pos[1]
                            if offset_x != 0 or offset_y != 0:
                                text_offsets['__summary__'] = (offset_x, offset_y)
                    except Exception:
                        pass
                line_marker_positions.append({
                    'vertical': m['vertical'],
                    'linear_pos': m['linear_pos'],
                    'selected': m['selected'],
                    'text_offsets': text_offsets
                })

            auto_fit = not self.plot_widget.plotItem.curves

            self.plot_widget.clear()
            self.plot_widget.markers.clear()
            self.plot_widget.line_markers.clear()

            if not models_selected:
                # ── Design Eqs with all-custom corners: synthesize iterations ──
                # When every device in the instance table has explicit corners
                # the user does not need to check anything in the tech browser.
                # Build synthetic models_selected entries from the first corner
                # tuple so the plotting loop has something to iterate over.
                if (not self.is_device_params_mode
                        and self.top_level_app
                        and hasattr(self.top_level_app, 'editor_window')):
                    try:
                        device_corners = self.top_level_app.editor_window.get_device_corners()
                        all_custom = device_corners and all(
                            dc.get('corners') is not None
                            for dc in device_corners.values()
                        )
                        if all_custom:
                            tuples = self._build_corner_tuples(device_corners, [])
                            if tuples:
                                # Use one synthetic entry per tuple so each gets
                                # its own plotting iteration.
                                for tup in tuples:
                                    first_dev_info = next(iter(tup.values()))
                                    # Construct a path the outer loop can parse:
                                    # "PDK>pdk>model>length>corner"
                                    syn_path = f"PDK>{first_dev_info['path']}"
                                    models_selected.append(syn_path)
                                debug_print(f"[DESIGN EQS] Synthesized models_selected "
                                            f"from all-custom corners: {models_selected}")
                    except Exception as e:
                        debug_print(f"[DESIGN EQS] Could not synthesize models_selected: {e}")

            if not models_selected:
                self.plot_widget.getPlotItem().setXRange(0, 1)
                self.plot_widget.getPlotItem().setYRange(0, 1)
                self.plot_widget.getPlotItem().setTitle("")
                self.plot_widget.getPlotItem().setLabel('left', "")
                self.plot_widget.getPlotItem().setLabel('bottom', "")
                self._is_updating = False
                return

            self.current_color_index = 0
            self.current_style_index = 0
            new_plot = True

            # Collect 3D results from all corners for joint rendering
            all_3d_results = []  # list of (results_3d, color, model_path, param1, param2, param3)

            for model in models_selected:
                model_tokens = model.split(">")
                pdk = model_tokens[1]
                model_name = model_tokens[2]
                length = model_tokens[3]
                corner = model_tokens[4]
                cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
                if equation_eval != None:
                    debug_print(f"[GRAPH] Equation eval mode for {model}")
                    continue

                param1 = self.combo_x.currentText()
                param2 = self.combo_y.currentText()

                color = self.tech_browser.get_color_for_path(model)
                style = Qt.PenStyle.SolidLine
                graph_pen = pg.mkPen(color=color, style=style, width=1)

                if self.is_device_params_mode:
                    unit1 = ""
                    unit2 = ""
                    if param1 in self.top_level_app.lookups_units_dict:
                        unit1 = self.top_level_app.lookups_units_dict[param1]
                    if param2 in self.top_level_app.lookups_units_dict:
                        unit2 = self.top_level_app.lookups_units_dict[param2]

                    # Create legend string that matches the format expected by set_corner_boldness
                    legend_str = f"PDK: {pdk}, L: {length}, corner: {corner}"
                    cid_corner.plot_processes_params_roar_plot_widget(param1=param1, param2=param2, param3=None, norm_type="",
                                                                      show_plot=True, new_plot=new_plot,
                                                                      roar_plot_widget=self.plot_widget,
                                                                      color=color, legend_str=legend_str, enable_3d=False,
                                                                      pen=graph_pen, unit1=unit1, unit2=unit2)
                else:
                    unit1 = ""
                    unit2 = ""
                    try:
                        from .equation_solver import ROAREquationSolver
                    except Exception:
                        from equation_solver import ROAREquationSolver

                    # Get device corners mapping from editor window
                    device_corners = {}
                    if self.top_level_app and hasattr(self.top_level_app, 'editor_window'):
                        try:
                            device_corners = self.top_level_app.editor_window.get_device_corners()
                            debug_print(f"[DESIGN EQS] Device corners mapping: {device_corners}")
                        except Exception as e:
                            debug_print(f"[DESIGN EQS] Could not get device corners: {e}")

                    # ── Build corner_dfs_dict with per-device DataFrames ──
                    # Only use device-namespaced keys ("M1::pdk>model>length>corner")
                    # when at least one device has CUSTOM (non-global) corners.
                    # When all devices are Global they all share the same tech-browser
                    # DataFrame, so use the legacy single-entry dict with a plain path
                    # key — this ensures that lookups with any device name (even
                    # misspelled ones) still resolve to data.
                    corner_dfs_dict = {}

                    any_custom = device_corners and any(
                        dc.get('corners') is not None
                        for dc in device_corners.values()
                    )

                    if any_custom and device_corners:
                        # Build corner tuples from instance-table corner data
                        tuples = self._build_corner_tuples(device_corners, models_selected)
                        if tuples:
                            # Find the first UN-USED tuple that contains the
                            # current outer-loop corner name.
                            matched_tuple = None
                            for ti, tup in enumerate(tuples):
                                if ti in self._custom_tuples_done:
                                    continue
                                for dev_name, cinfo in tup.items():
                                    if cinfo.get('corner_name') == corner:
                                        matched_tuple = tup
                                        self._custom_tuples_done.add(ti)
                                        break
                                if matched_tuple is not None:
                                    break

                            # When no tuple matched (all devices custom, or
                            # outer-loop corner is irrelevant), pick the first
                            # un-used tuple and mark it done.
                            if matched_tuple is None:
                                for ti, tup in enumerate(tuples):
                                    if ti not in self._custom_tuples_done:
                                        matched_tuple = tup
                                        self._custom_tuples_done.add(ti)
                                        break
                            if matched_tuple is None:
                                # All tuples already consumed — skip this
                                # outer-loop iteration.
                                continue

                            # Populate corner_dfs_dict with namespaced keys
                            for dev_name, cinfo in matched_tuple.items():
                                ns_key = f"{dev_name}::{cinfo['path']}"
                                corner_dfs_dict[ns_key] = cinfo['df']
                            debug_print(f"[DESIGN EQS] Per-device corner_dfs: {list(corner_dfs_dict.keys())}")

                    if not corner_dfs_dict:
                        # All-Global or fallback: use the global tech-browser corner
                        current_corner_path = f"{pdk}>{model_name}>{length}>{corner}"
                        corner_dfs_dict[current_corner_path] = cid_corner.df
                        debug_print(f"[DESIGN EQS] Global corner: {list(corner_dfs_dict.keys())}")

                    equation_solver = ROAREquationSolver(top_level_app=self.top_level_app, device_corners=device_corners)
                    equation_solver.corners = list(corner_dfs_dict.values())
                    expressions, constraints = self.top_level_app.editor_window.get_expressions_and_constraints()
                    syntax_errors = {}
                    for expression_sym in expressions:
                        expression = expressions[expression_sym]
                        err = equation_solver.add_equation(expression_sym, expression)
                        if err:
                            syntax_errors[expression_sym] = err

                    if syntax_errors:
                        # Highlight errors in the design editor and show popup
                        try:
                            ew = self.top_level_app.editor_window
                            ew.expression_editor.clear_error_highlights()
                            ew.constraint_editor.clear_error_highlights()
                            ew.expression_editor.highlight_error_rows(syntax_errors)
                        except Exception:
                            pass
                        from PyQt6.QtWidgets import QMessageBox
                        lines = [f"  • {s}: {m[:100]}" for s, m in syntax_errors.items()]
                        QMessageBox.warning(
                            self, "Syntax Errors",
                            "Cannot graph — fix the highlighted expressions first.\n\n"
                            + "\n".join(lines))
                        continue  # skip this corner iteration

                    # Pass corner_dfs_dict (with per-device namespaced keys)
                    result_matrix = equation_solver.evaluate_equations(symbols_to_add=[param1, param2], corner_dfs=corner_dfs_dict)
                    if not result_matrix or not isinstance(result_matrix, dict):
                        msg = f"Design Eq solver returned no results for {param1},{param2}"
                        debug_print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                        continue
                    if param1 not in result_matrix or param2 not in result_matrix:
                        msg = f"Design Eq results missing requested symbols: {param1} or {param2}. Available: {list(result_matrix.keys())}"
                        debug_print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                        continue

                    # Apply constraint filtering
                    constraint_mask = None
                    if constraints:
                        debug_print(f"[CONSTRAINT] Evaluating {len(constraints)} constraints")
                        # Evaluate all constraints
                        for constraint_name, constraint_expr in constraints.items():
                            try:
                                # Add constraint equation to solver
                                equation_solver.add_equation(constraint_name, constraint_expr)
                            except Exception as e:
                                debug_print(f"[CONSTRAINT] Error adding constraint '{constraint_name}': {e}")

                        # Evaluate constraints
                        constraint_symbols = list(constraints.keys())
                        if constraint_symbols:
                            try:
                                constraint_results = equation_solver.evaluate_equations(symbols_to_add=constraint_symbols, corner_dfs=corner_dfs_dict)
                                if constraint_results:
                                    # Determine base length safely (handle scalars)
                                    def _safe_length_for_key(key):
                                        val = result_matrix.get(key, None)
                                        if val is None:
                                            return 0
                                        try:
                                            arr = np.asarray(val).ravel()
                                            return int(arr.size)
                                        except Exception:
                                            # Fallback: scalar -> length 1
                                            return 1

                                    base_len = _safe_length_for_key(param1)
                                    if base_len == 0:
                                        debug_print(f"[CONSTRAINT] Warning: base length for {param1} is 0; skipping constraint filtering")
                                    else:
                                        # Create mask for points that meet ALL constraints
                                        constraint_mask = np.ones(base_len, dtype=bool)

                                        for constraint_name in constraint_symbols:
                                            if constraint_name in constraint_results:
                                                try:
                                                    constraint_values = np.asarray(constraint_results[constraint_name]).ravel()
                                                except Exception:
                                                    # If it can't be arrayed, treat as scalar
                                                    constraint_values = np.array([constraint_results[constraint_name]])

                                                # Constraint is met if value is True (non-zero)
                                                # Handle different shapes
                                                if constraint_values.size == 1:
                                                    # Scalar constraint applies to all points
                                                    met = bool(constraint_values[0])
                                                    constraint_mask &= met
                                                else:
                                                    # Per-point constraint
                                                    if constraint_values.size == constraint_mask.size:
                                                        constraint_mask &= (constraint_values != 0)
                                                    else:
                                                        debug_print(f"[CONSTRAINT] Warning: {constraint_name} shape mismatch: {constraint_values.size} vs {constraint_mask.size}")

                                                points_passing = np.sum(constraint_mask)
                                                total_points = constraint_mask.size
                                                debug_print(f"[CONSTRAINT] {constraint_name}: {points_passing}/{total_points} points pass")

                                        # Filter result_matrix based on constraint_mask
                                        try:
                                            points_before = _safe_length_for_key(param1)
                                        except Exception:
                                            points_before = 0

                                        for key in list(result_matrix.keys()):
                                            try:
                                                val_arr = np.asarray(result_matrix[key]).ravel()
                                                if val_arr.size == constraint_mask.size:
                                                    result_matrix[key] = val_arr[constraint_mask]
                                                else:
                                                    # If sizes mismatch but both are scalar and mask length is 1, respect mask
                                                    if val_arr.size == 1 and constraint_mask.size == 1:
                                                        if not constraint_mask[0]:
                                                            # No points pass, make empty array
                                                            result_matrix[key] = np.array([])
                                                        else:
                                                            # Keep the scalar as a 1-element array for consistency
                                                            result_matrix[key] = val_arr
                                                    else:
                                                        # Leave value as-is (cannot filter)
                                                        result_matrix[key] = val_arr
                                            except Exception:
                                                # If conversion fails, leave the original value
                                                pass

                                        try:
                                            points_after = int(np.asarray(result_matrix[param1]).ravel().size)
                                        except Exception:
                                            points_after = 0

                                        debug_print(f"[CONSTRAINT] Filtered {points_before - points_after} points, {points_after} remaining")

                                        if points_after == 0:
                                            debug_print(f"[CONSTRAINT] No points meet all constraints - skipping plot")
                                            continue
                            except Exception as e:
                                debug_print(f"[CONSTRAINT] Error evaluating constraints: {e}")
                                import traceback
                                traceback.print_exc()

                    params1 = result_matrix[param1]
                    params2 = result_matrix[param2]
                    try:
                        arr1 = np.asarray(params1)
                        arr2 = np.asarray(params2)
                        if arr1.ndim == 0:
                            nrows = cid_corner.df.shape[0] if hasattr(cid_corner, 'df') else (arr1.size if hasattr(arr1, 'size') else 1)
                            arr1 = np.full(nrows, float(arr1))
                        if arr2.ndim == 0:
                            nrows = cid_corner.df.shape[0] if hasattr(cid_corner, 'df') else (arr2.size if hasattr(arr2, 'size') else 1)
                            arr2 = np.full(nrows, float(arr2))
                        if arr1.ndim > 1:
                            arr1 = arr1.reshape(arr1.shape[0], -1)
                            if arr1.shape[1] == 1:
                                arr1 = arr1[:, 0]
                            else:
                                arr1 = arr1.ravel()
                        if arr2.ndim > 1:
                            arr2 = arr2.reshape(arr2.shape[0], -1)
                            if arr2.shape[1] == 1:
                                arr2 = arr2[:, 0]
                            else:
                                arr2 = arr2.ravel()
                        params1 = arr1.ravel()
                        params2 = arr2.ravel()
                    except Exception:
                        try:
                            params1 = np.asarray(params1).squeeze()
                            params2 = np.asarray(params2).squeeze()
                        except Exception:
                            pass
                    try:
                        params1 = np.asarray(params1)
                        params2 = np.asarray(params2)
                        if params1.size == 0 or params2.size == 0:
                            msg = f"Design Eq plotting: empty data for {param1}/{param2}"
                            print(msg)
                            try:
                                if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                    self.top_level_app.statusBar().showMessage(msg, 5000)
                            except Exception:
                                pass
                            continue
                        if params1.shape[0] != params2.shape[0]:
                            nmin = min(params1.shape[0], params2.shape[0])
                            params1 = params1[:nmin]
                            params2 = params2[:nmin]
                    except Exception:
                        pass
                    try:
                        # Check if 3D mode is enabled
                        is_3d_mode = (not self.is_device_params_mode and
                                     getattr(self, 'checkbox_3d', None) is not None and
                                     self.checkbox_3d.isChecked())

                        if is_3d_mode:
                            param3 = self.combo_z.currentText()
                            results_3d = None
                            try:
                                # ── 3D Surface: symbolic meshgrid evaluation ──
                                # 1) Evaluate ALL expressions so every intermediate
                                #    result is available as a 1-D vector.
                                all_expression_syms = list(expressions.keys())
                                result_matrix_all = equation_solver.evaluate_equations(
                                    symbols_to_add=all_expression_syms,
                                    corner_dfs=corner_dfs_dict
                                )

                                if (result_matrix_all is not None
                                        and param1 in result_matrix_all
                                        and param2 in result_matrix_all
                                        and param3 in result_matrix_all):

                                    # Get 1-D X / Y vectors
                                    x_data = np.asarray(result_matrix_all[param1]).ravel()
                                    y_data = np.asarray(result_matrix_all[param2]).ravel()

                                    unique_x = np.unique(x_data)
                                    unique_y = np.unique(y_data)

                                    # Limit grid resolution for performance
                                    max_grid_resolution = 40
                                    if len(unique_x) > max_grid_resolution:
                                        unique_x = np.linspace(unique_x[0], unique_x[-1], max_grid_resolution)
                                    if len(unique_y) > max_grid_resolution:
                                        unique_y = np.linspace(unique_y[0], unique_y[-1], max_grid_resolution)

                                    min_grid_size = 3
                                    if len(unique_x) >= min_grid_size and len(unique_y) >= min_grid_size:
                                        X_grid, Y_grid = np.meshgrid(unique_x, unique_y)

                                        # ── Helper: recursively resolve a symbol into a
                                        #    fully-expanded sympy expression whose only
                                        #    free symbols are either already-evaluated
                                        #    results or numeric constants. ──
                                        from sympy import Symbol as SympySymbol, sympify as sp_sympify
                                        from sympy.utilities.lambdify import lambdify

                                        def _resolve_expr(sym_name, eqs, _seen=None):
                                            """Return a sympy expression for *sym_name*
                                            with all intermediate equation symbols
                                            recursively substituted. Lookup equations
                                            (strings containing ':') are left as bare
                                            Symbol(sym_name) because they are terminal
                                            – their values come from result_matrix_all.
                                            """
                                            if _seen is None:
                                                _seen = set()
                                            if sym_name in _seen:
                                                return SympySymbol(sym_name)
                                            _seen.add(sym_name)
                                            eq_val = eqs.get(sym_name)
                                            if eq_val is None:
                                                # Not an equation – treat as terminal symbol
                                                return SympySymbol(sym_name)
                                            if isinstance(eq_val, str):
                                                # Lookup string like "kgm:M1" → terminal
                                                return SympySymbol(sym_name)
                                            # eq_val is a sympy expression. Substitute
                                            # each of *its* free symbols recursively.
                                            expr = eq_val
                                            for fs in list(expr.free_symbols):
                                                fs_name = str(fs)
                                                sub_expr = _resolve_expr(fs_name, eqs, _seen)
                                                if sub_expr != fs:
                                                    expr = expr.subs(fs, sub_expr)
                                            return expr

                                        def _get_device(sym_name, eqs):
                                            """Return the device name for a terminal
                                            lookup symbol, or None if it is not a
                                            lookup.  e.g. 'kcgs1' whose equation is
                                            'kcgs:M1' → 'M1'.
                                            """
                                            eq_val = eqs.get(sym_name)
                                            if isinstance(eq_val, str) and ':' in eq_val:
                                                parts = eq_val.split(':')
                                                if len(parts) == 2:
                                                    return parts[1].strip()
                                            return None

                                        # Determine which device the X and Y axes
                                        # belong to so that other lookups from the
                                        # same device can be interpolated along the
                                        # correct grid axis.
                                        x_device = _get_device(param1, equation_solver.equations)
                                        y_device = _get_device(param2, equation_solver.equations)
                                        debug_print(f"[3D GRID] X device: {x_device}, Y device: {y_device}")

                                        def _eval_on_grid(sym_name, eqs, result_map,
                                                          x_name, y_name, Xg, Yg,
                                                          x_dev, y_dev,
                                                          x_1d, y_1d):
                                            """Evaluate *sym_name* on the meshgrid.

                                            For terminal lookup symbols that share a
                                            device with the X or Y axis, their 1-D
                                            LUT values are interpolated along the
                                            matching grid axis instead of being
                                            collapsed to a scalar mean.

                                            Returns a 2-D numpy array shaped like Xg.
                                            """
                                            resolved = _resolve_expr(sym_name, eqs)
                                            free = list(resolved.free_symbols)
                                            debug_print(f"[3D GRID] Resolved '{sym_name}' -> {resolved}")
                                            debug_print(f"[3D GRID]   free symbols: {[str(s) for s in free]}")

                                            if not free:
                                                val = float(resolved)
                                                return np.full(Xg.shape, val)

                                            args = []
                                            for fs in free:
                                                name = str(fs)
                                                if name == x_name:
                                                    args.append(Xg)
                                                elif name == y_name:
                                                    args.append(Yg)
                                                elif name in result_map:
                                                    # Check if this symbol's lookup
                                                    # shares a device with X or Y.
                                                    sym_dev = _get_device(name, eqs)
                                                    val = result_map[name]
                                                    val_1d = np.asarray(val, dtype=np.float64).ravel()

                                                    if sym_dev and sym_dev == x_dev and val_1d.size == x_1d.size:
                                                        # Co-indexed with X axis – interpolate along X
                                                        sort_idx = np.argsort(x_1d)
                                                        interp_vals = np.interp(
                                                            Xg.ravel(),
                                                            x_1d[sort_idx],
                                                            val_1d[sort_idx]
                                                        ).reshape(Xg.shape)
                                                        args.append(interp_vals)
                                                        debug_print(f"[3D GRID]   '{name}' interpolated along X (device {sym_dev})")
                                                    elif sym_dev and sym_dev == y_dev and val_1d.size == y_1d.size:
                                                        # Co-indexed with Y axis – interpolate along Y
                                                        sort_idx = np.argsort(y_1d)
                                                        interp_vals = np.interp(
                                                            Yg.ravel(),
                                                            y_1d[sort_idx],
                                                            val_1d[sort_idx]
                                                        ).reshape(Yg.shape)
                                                        args.append(interp_vals)
                                                        debug_print(f"[3D GRID]   '{name}' interpolated along Y (device {sym_dev})")
                                                    else:
                                                        # No device match – use scalar mean
                                                        if isinstance(val, np.ndarray):
                                                            args.append(float(np.nanmean(val)))
                                                        else:
                                                            args.append(float(val))
                                                        debug_print(f"[3D GRID]   '{name}' used as scalar mean")
                                                else:
                                                    debug_print(f"[3D GRID]   WARNING: unknown symbol '{name}', using 0")
                                                    args.append(0.0)

                                            numpy_mods = ['numpy', {
                                                'sin': np.sin, 'cos': np.cos,
                                                'tan': np.tan, 'sqrt': np.sqrt,
                                                'exp': np.exp, 'log': np.log,
                                                'ln': np.log, 'abs': np.abs,
                                                'pi': np.pi, 'e': np.e,
                                            }]
                                            fn = lambdify(free, resolved, modules=numpy_mods)
                                            Z = fn(*args)
                                            if np.isscalar(Z):
                                                Z = np.full(Xg.shape, float(Z))
                                            return np.asarray(Z, dtype=np.float64)

                                        # ── Evaluate Z on the meshgrid ──
                                        Z_grid = _eval_on_grid(
                                            param3, equation_solver.equations,
                                            result_matrix_all,
                                            param1, param2, X_grid, Y_grid,
                                            x_device, y_device,
                                            x_data, y_data
                                        )

                                        debug_print(f"[3D GRID] Z_grid shape: {Z_grid.shape}, "
                                                    f"range: [{np.nanmin(Z_grid):.4g}, {np.nanmax(Z_grid):.4g}]")

                                        # ── Constraint filtering (NaN masking) ──
                                        if constraints:
                                            for constraint_name, constraint_expr in constraints.items():
                                                try:
                                                    equation_solver.add_equation(constraint_name, constraint_expr)
                                                    C_grid = _eval_on_grid(
                                                        constraint_name,
                                                        equation_solver.equations,
                                                        result_matrix_all,
                                                        param1, param2, X_grid, Y_grid,
                                                        x_device, y_device,
                                                        x_data, y_data
                                                    )
                                                    fail_mask = (C_grid == 0) | np.isnan(C_grid)
                                                    Z_grid = np.where(fail_mask, np.nan, Z_grid)
                                                    n_fail = int(np.sum(fail_mask))
                                                    debug_print(f"[CONSTRAINT 3D] {constraint_name}: "
                                                                f"{Z_grid.size - n_fail}/{Z_grid.size} pass")
                                                except Exception as e:
                                                    debug_print(f"[CONSTRAINT 3D] Error evaluating '{constraint_name}': {e}")

                                            if np.all(np.isnan(Z_grid)):
                                                debug_print("[CONSTRAINT 3D] No points meet all constraints")
                                                results_3d = None
                                            else:
                                                # Apply log scale to Z if LogZ is checked
                                                if getattr(self, 'checkbox_logz', None) and self.checkbox_logz.isChecked():
                                                    n_pos = int(np.sum(Z_grid > 0))
                                                    debug_print(f"[3D LOGZ] Applying log10 (with constraints): {n_pos}/{Z_grid.size} positive values")
                                                    Z_grid = np.where(Z_grid > 0, np.log10(Z_grid), np.nan)
                                                    debug_print(f"[3D LOGZ] After log10: range [{np.nanmin(Z_grid):.4g}, {np.nanmax(Z_grid):.4g}]")
                                                results_3d = (X_grid, Y_grid, Z_grid, 'surface')
                                        else:
                                            # Apply log scale to Z if LogZ is checked
                                            if getattr(self, 'checkbox_logz', None) and self.checkbox_logz.isChecked():
                                                n_pos = int(np.sum(Z_grid > 0))
                                                debug_print(f"[3D LOGZ] Applying log10 (no constraints): {n_pos}/{Z_grid.size} positive values")
                                                Z_grid = np.where(Z_grid > 0, np.log10(Z_grid), np.nan)
                                                debug_print(f"[3D LOGZ] After log10: range [{np.nanmin(Z_grid):.4g}, {np.nanmax(Z_grid):.4g}]")
                                            results_3d = (X_grid, Y_grid, Z_grid, 'surface')
                                    else:
                                        # Not enough unique values → scatter fallback
                                        z_data = np.asarray(result_matrix_all[param3]).ravel()
                                        # Apply log scale to Z if LogZ is checked
                                        if getattr(self, 'checkbox_logz', None) and self.checkbox_logz.isChecked():
                                            n_pos = int(np.sum(z_data > 0))
                                            debug_print(f"[3D LOGZ] Applying log10 (scatter): {n_pos}/{z_data.size} positive values")
                                            z_data = np.where(z_data > 0, np.log10(z_data), np.nan)
                                        results_3d = (x_data, y_data, z_data, 'scatter')
                                else:
                                    results_3d = None

                            except Exception as e:
                                debug_print(f"3D data preparation error: {e}")
                                import traceback
                                traceback.print_exc()
                                results_3d = None

                            if results_3d and self.gl_widget is not None:
                                # Collect for post-loop rendering with shared normalization
                                corner_color = self.tech_browser.get_color_for_path(model)
                                all_3d_results.append((results_3d, corner_color, model, param1, param2, param3))
                                new_plot = False
                                continue

                        # 2D plotting (only when NOT in 3D mode)
                        else:
                            try:
                                # Hide GL widget when not in 3D mode
                                if self.gl_widget is not None:
                                    self.gl_widget.setVisible(False)
                            except Exception:
                                pass
                            try:
                                self.plot_widget.show()
                            except Exception:
                                pass
                            # Create legend string for curve identification (used for boldening when selected)
                            legend_str = f"PDK: {pdk}, L: {length}, corner: {corner}"
                            curve = self.plot_widget.plot(params1, params2, pen=graph_pen, name=legend_str)
                            xlabel = param1 + "  [" + unit1 + "]"
                            ylabel = param2 + "  [" + unit2 + "]"
                            self.plot_widget.setLabel('bottom', xlabel)
                            self.plot_widget.setLabel('left', ylabel)
                            self.plot_widget.setTitle(f"{param2} vs {param1}")
                            self.plot_widget.getAxis('left').setStyle(autoExpandTextSpace=True)
                            self.plot_widget.getAxis('left').enableAutoSIPrefix(False)
                    except Exception as e:
                        msg = f"Plotting error for design eq {param1} vs {param2}: {e}"
                        print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                new_plot = False
                self.plot_widget.showGrid(x=True, y=True)

            # ── Post-loop: render all collected 3D results with shared normalization ──
            if all_3d_results and self.gl_widget is not None:
                try:
                    self.plot_widget.hide()
                    self.gl_widget.setVisible(True)

                    # 3D plots always use a black background
                    self.gl_widget.setBackgroundColor(0, 0, 0)

                    # Clear previous GL items
                    for it in list(self.gl_items):
                        try:
                            self.gl_widget.removeItem(it)
                        except Exception:
                            pass
                    self.gl_items.clear()


                    # Compute global min/max across ALL corners for consistent normalization
                    global_x_min = np.inf
                    global_x_max = -np.inf
                    global_y_min = np.inf
                    global_y_max = -np.inf
                    global_z_min = np.inf
                    global_z_max = -np.inf
                    for (res_3d, _color, _model, _p1, _p2, _p3) in all_3d_results:
                        if len(res_3d) == 4:
                            d1, d2, d3, _pt = res_3d
                        else:
                            d1, d2, d3 = res_3d
                        a1 = np.asarray(d1, dtype=float)
                        a2 = np.asarray(d2, dtype=float)
                        a3 = np.asarray(d3, dtype=float)
                        global_x_min = min(global_x_min, float(np.nanmin(a1)))
                        global_x_max = max(global_x_max, float(np.nanmax(a1)))
                        global_y_min = min(global_y_min, float(np.nanmin(a2)))
                        global_y_max = max(global_y_max, float(np.nanmax(a2)))
                        global_z_min = min(global_z_min, float(np.nanmin(a3)))
                        global_z_max = max(global_z_max, float(np.nanmax(a3)))

                    # Store normalization bounds on self for ROAR3DViewWidget to use
                    self._3d_global_x_min = global_x_min
                    self._3d_global_x_max = global_x_max
                    self._3d_global_y_min = global_y_min
                    self._3d_global_y_max = global_y_max
                    self._3d_global_z_min = global_z_min
                    self._3d_global_z_max = global_z_max

                    # Clear previously stored data points for mouse picking
                    if hasattr(self.gl_widget, '_all_norm_points'):
                        self.gl_widget._all_norm_points.clear()
                        self.gl_widget._all_orig_points.clear()
                    if hasattr(self.gl_widget, '_all_point_colors'):
                        self.gl_widget._all_point_colors.clear()

                    def _norm_global(arr, gmin, gmax):
                        """Normalize array to [-5, 5] using global min/max.

                        Handles edge-cases that arise with very small numbers
                        (e.g. 1e-12 … 1e-9), constant data, or non-finite bounds.
                        """
                        a = np.asarray(arr, dtype=np.float64)
                        gmin = float(gmin)
                        gmax = float(gmax)

                        # Guard against non-finite bounds (uninitialised inf, nan)
                        if not (np.isfinite(gmin) and np.isfinite(gmax)):
                            amin = float(np.nanmin(a)) if np.any(np.isfinite(a)) else 0.0
                            amax = float(np.nanmax(a)) if np.any(np.isfinite(a)) else 0.0
                            gmin, gmax = amin, amax

                        rng = gmax - gmin

                        if rng == 0:
                            # All data is the same value – place the surface at
                            # the middle of the viewport (z = 0).
                            return np.zeros_like(a)

                        # Use relative tolerance: if the range is tiny compared
                        # to the magnitude of the values we still want full
                        # [-5, 5] spread.  The key is to do the subtraction in
                        # float64 which gives ~15 significant digits – more than
                        # enough for 1e-12 scale numbers.
                        return (a - gmin) / rng * 10.0 - 5.0

                    from PyQt6.QtGui import QColor

                    def _ensure_bright(qcol):
                        """Ensure a QColor is bright enough to be visible on a black
                        background.  If the colour is too dark, boost its value
                        (brightness) while keeping hue and saturation."""
                        h, s, v, a = qcol.getHsvF()
                        # Boost value so it is at least 0.55, and push saturation
                        # up a bit so colours stay vivid.
                        v = max(v, 0.55)
                        s = max(s, 0.4) if s > 0.05 else s  # keep greys neutral
                        return QColor.fromHsvF(h, s, v, a)

                    # Render each corner's mesh/scatter
                    for (res_3d, corner_color, model_path, axis1, axis2, axis3) in all_3d_results:
                        if len(res_3d) == 4:
                            p1, p2, p3, plot_type = res_3d
                        else:
                            p1, p2, p3 = res_3d
                            plot_type = 'scatter'

                        # Resolve corner colour from tech browser and ensure visibility
                        try:
                            if isinstance(corner_color, QColor):
                                qcol = corner_color
                            elif hasattr(corner_color, 'color'):
                                pen_color = corner_color.color()
                                qcol = pen_color if isinstance(pen_color, QColor) else QColor(str(pen_color))
                            elif isinstance(corner_color, str):
                                qcol = QColor(corner_color)
                            else:
                                qcol = QColor('#00ff00')
                        except Exception:
                            qcol = QColor('#00ff00')
                        qcol = _ensure_bright(qcol)
                        r, g, b, _a = qcol.getRgbF()

                        if plot_type == 'surface' and hasattr(p1, 'shape') and len(p1.shape) == 2:
                            Xn = _norm_global(p1, global_x_min, global_x_max)
                            Yn = _norm_global(p2, global_y_min, global_y_max)
                            Zn = _norm_global(p3, global_z_min, global_z_max)

                            ny, nx = Xn.shape
                            nan_mask = np.isnan(Zn)
                            Zn_filled = np.where(nan_mask, 0.0, Zn)

                            verts = np.column_stack((Xn.ravel(), Yn.ravel(), Zn_filled.ravel())).astype(np.float32)
                            faces = []
                            flat_nan = nan_mask.ravel()
                            for i in range(ny - 1):
                                for j in range(nx - 1):
                                    v0 = i * nx + j
                                    v1 = v0 + 1
                                    v2 = v0 + nx
                                    v3 = v2 + 1
                                    if flat_nan[v0] or flat_nan[v1] or flat_nan[v2] or flat_nan[v3]:
                                        continue
                                    faces.append([v0, v1, v2])
                                    faces.append([v1, v3, v2])

                            if len(faces) > 0:
                                faces_arr = np.array(faces, dtype=np.uint32)
                                try:
                                    md = MeshData(vertexes=verts, faces=faces_arr)
                                    # Subtle bright edge tinted with the surface colour
                                    edge_color = (r * 0.6 + 0.4, g * 0.6 + 0.4, b * 0.6 + 0.4, 0.35)
                                    mesh = GLMeshItem(
                                        meshdata=md,
                                        smooth=False,
                                        drawFaces=True,
                                        drawEdges=True,
                                        edgeColor=edge_color,
                                        shader='shaded',
                                        glOptions='translucent'
                                    )
                                    mesh.setColor((r, g, b, 0.45))
                                    self.gl_widget.addItem(mesh)
                                    self.gl_items.append(mesh)
                                except Exception as e:
                                    debug_print(f"GL mesh creation failed: {e}")

                            # Register surface data points for 3-D marker mouse picking
                            if hasattr(self.gl_widget, '_all_norm_points'):
                                valid = ~nan_mask.ravel()
                                norm_pts = verts[valid].copy()
                                orig_pts = np.column_stack((
                                    np.asarray(p1, dtype=np.float64).ravel()[valid],
                                    np.asarray(p2, dtype=np.float64).ravel()[valid],
                                    np.asarray(p3, dtype=np.float64).ravel()[valid],
                                )).astype(np.float64)
                                self.gl_widget._all_norm_points.append(norm_pts)
                                self.gl_widget._all_orig_points.append(orig_pts)
                                if hasattr(self.gl_widget, '_all_point_colors'):
                                    self.gl_widget._all_point_colors.append((r, g, b, 1.0))
                        else:
                            # Scatter fallback
                            try:
                                xs_n = _norm_global(np.asarray(p1, dtype=float).ravel(), global_x_min, global_x_max)
                                ys_n = _norm_global(np.asarray(p2, dtype=float).ravel(), global_y_min, global_y_max)
                                zs_n = _norm_global(np.asarray(p3, dtype=float).ravel(), global_z_min, global_z_max)
                                pos = np.column_stack((xs_n, ys_n, zs_n)).astype(np.float32)
                                sp = GLScatterPlotItem(pos=pos, size=5, color=(r, g, b, 0.7))
                                self.gl_widget.addItem(sp)
                                self.gl_items.append(sp)

                                # Register scatter data points for 3-D marker mouse picking
                                if hasattr(self.gl_widget, '_all_norm_points'):
                                    self.gl_widget._all_norm_points.append(pos.astype(np.float64))
                                    orig_pts = np.column_stack((
                                        np.asarray(p1, dtype=np.float64).ravel(),
                                        np.asarray(p2, dtype=np.float64).ravel(),
                                        np.asarray(p3, dtype=np.float64).ravel(),
                                    ))
                                    self.gl_widget._all_orig_points.append(orig_pts)
                                    if hasattr(self.gl_widget, '_all_point_colors'):
                                        self.gl_widget._all_point_colors.append((r, g, b, 1.0))
                            except Exception as e:
                                debug_print(f"GL scatter creation failed: {e}")

                    # ── Draw 3-D axes with numbered ticks ──
                    try:
                        from pyqtgraph.opengl import GLLinePlotItem, GLTextItem

                        axis_color = (1.0, 1.0, 1.0, 0.6)
                        tick_color = (0.8, 0.8, 0.8, 0.5)
                        label_color = QColor(220, 220, 220)
                        dim_label_color = QColor(160, 160, 160)

                        # Axis endpoints in normalised space [-5, 5]
                        origin = np.array([-5, -5, -5], dtype=np.float32)

                        # --- helper: generate nice tick positions & labels ---
                        def _make_ticks(vmin, vmax, n_ticks=5):
                            """Return (normalised_positions[], label_strings[])
                            for *n_ticks* evenly-spaced values between vmin/vmax,
                            mapped into the [-5, 5] normalised range."""
                            if vmin == vmax or not (np.isfinite(vmin) and np.isfinite(vmax)):
                                return [0.0], [format_eng(vmin)]
                            raw = np.linspace(vmin, vmax, n_ticks)
                            rng = vmax - vmin
                            norms = [(v - vmin) / rng * 10.0 - 5.0 for v in raw]
                            labels = [format_eng(v) for v in raw]
                            return norms, labels

                        n_ticks = 5
                        tick_len = 0.25  # half-length of the small tick cross-bar

                        # ── X axis (along x, at y=-5, z=-5) ──
                        x_line = np.array([[-5, -5, -5], [5, -5, -5]], dtype=np.float32)
                        item = GLLinePlotItem(pos=x_line, color=axis_color, width=1.5, antialias=True)
                        self.gl_widget.addItem(item); self.gl_items.append(item)

                        xn, xl = _make_ticks(global_x_min, global_x_max, n_ticks)
                        for pos_n, lbl in zip(xn, xl):
                            # tick mark
                            tp = np.array([[pos_n, -5, -5 - tick_len],
                                           [pos_n, -5, -5 + tick_len]], dtype=np.float32)
                            ti = GLLinePlotItem(pos=tp, color=tick_color, width=1.0, antialias=True)
                            self.gl_widget.addItem(ti); self.gl_items.append(ti)
                            # label
                            t = GLTextItem(pos=np.array([pos_n, -5, -5.8], dtype=np.float64),
                                           text=lbl, color=dim_label_color)
                            self.gl_widget.addItem(t); self.gl_items.append(t)

                        # axis name
                        _a1 = all_3d_results[0][3]
                        t = GLTextItem(pos=np.array([0, -5, -7.0], dtype=np.float64),
                                       text=_a1, color=label_color)
                        self.gl_widget.addItem(t); self.gl_items.append(t)

                        # ── Y axis (along y, at x=-5, z=-5) ──
                        y_line = np.array([[-5, -5, -5], [-5, 5, -5]], dtype=np.float32)
                        item = GLLinePlotItem(pos=y_line, color=axis_color, width=1.5, antialias=True)
                        self.gl_widget.addItem(item); self.gl_items.append(item)

                        yn, yl = _make_ticks(global_y_min, global_y_max, n_ticks)
                        for pos_n, lbl in zip(yn, yl):
                            tp = np.array([[-5, pos_n, -5 - tick_len],
                                           [-5, pos_n, -5 + tick_len]], dtype=np.float32)
                            ti = GLLinePlotItem(pos=tp, color=tick_color, width=1.0, antialias=True)
                            self.gl_widget.addItem(ti); self.gl_items.append(ti)
                            t = GLTextItem(pos=np.array([-5, pos_n, -5.8], dtype=np.float64),
                                           text=lbl, color=dim_label_color)
                            self.gl_widget.addItem(t); self.gl_items.append(t)

                        _a2 = all_3d_results[0][4]
                        t = GLTextItem(pos=np.array([-5, 0, -7.0], dtype=np.float64),
                                       text=_a2, color=label_color)
                        self.gl_widget.addItem(t); self.gl_items.append(t)

                        # ── Z axis (along z, at x=-5, y=-5) ──
                        z_line = np.array([[-5, -5, -5], [-5, -5, 5]], dtype=np.float32)
                        item = GLLinePlotItem(pos=z_line, color=axis_color, width=1.5, antialias=True)
                        self.gl_widget.addItem(item); self.gl_items.append(item)

                        _z_is_log = (getattr(self, 'checkbox_logz', None)
                                     and self.checkbox_logz.isChecked())
                        if _z_is_log:
                            # Z data is already log10-transformed.  Generate
                            # tick positions in log10 space but show the
                            # *original* (anti-log) values as labels so the
                            # axis reads like a standard log scale.
                            zn, _ = _make_ticks(global_z_min, global_z_max, n_ticks)
                            # Convert normalised tick positions back to log10
                            # values, then to original domain values.
                            z_rng = global_z_max - global_z_min
                            if z_rng == 0:
                                zl = [format_eng(10 ** global_z_min)] * len(zn)
                            else:
                                zl = [format_eng(10 ** (global_z_min + (p + 5.0) / 10.0 * z_rng))
                                      for p in zn]
                        else:
                            zn, zl = _make_ticks(global_z_min, global_z_max, n_ticks)

                        for pos_n, lbl in zip(zn, zl):
                            tp = np.array([[-5 - tick_len, -5, pos_n],
                                           [-5 + tick_len, -5, pos_n]], dtype=np.float32)
                            ti = GLLinePlotItem(pos=tp, color=tick_color, width=1.0, antialias=True)
                            self.gl_widget.addItem(ti); self.gl_items.append(ti)
                            t = GLTextItem(pos=np.array([-6.0, -5, pos_n], dtype=np.float64),
                                           text=lbl, color=dim_label_color)
                            self.gl_widget.addItem(t); self.gl_items.append(t)

                        _a3 = all_3d_results[0][5]
                        if _z_is_log:
                            _a3 = f"{_a3} (log)"
                        t = GLTextItem(pos=np.array([-7.0, -5, 0], dtype=np.float64),
                                       text=_a3, color=label_color)
                        self.gl_widget.addItem(t); self.gl_items.append(t)


                    except Exception as e:
                        debug_print(f"3D axis drawing error: {e}")
                        import traceback; traceback.print_exc()

                    # Camera
                    try:
                        self.gl_widget.setCameraPosition(distance=20, elevation=30, azimuth=-135)
                    except Exception:
                        pass

                except Exception as e:
                    debug_print(f"3D post-loop rendering error: {e}")
                    import traceback
                    traceback.print_exc()

            # Fix for Y-axis log scale showing wrong exponents in Design Equations mode
            # When log mode is active, we need to force a proper recalculation of axis ranges
            # by temporarily disabling log mode, setting autorange, then re-enabling
            try:
                x_log = self.checkbox_logx.isChecked()
                y_log = self.checkbox_logy.isChecked()

                if x_log or y_log:
                    # Temporarily disable log mode to get proper range calculation
                    self.plot_widget.getPlotItem().setLogMode(x=False, y=False)

                    # Force autorange with log mode disabled
                    self.plot_widget.plotItem.autoRange()

                    # Re-enable log mode - this will now use the correct data ranges
                    self.plot_widget.getPlotItem().setLogMode(x=x_log, y=y_log)

                    # Force another autorange after log mode is set
                    self.plot_widget.plotItem.autoRange()
                else:
                    # Normal autorange when not in log mode
                    self.plot_widget.plotItem.autoRange()
            except Exception as e:
                debug_print(f"[LOG SCALE FIX] Error during axis range reset: {e}")
                # Fallback to simple autorange
                self.plot_widget.plotItem.autoRange()

            for marker_info in marker_positions:
                x, y = marker_info['pos']

                x_log = self.plot_widget.getPlotItem().getAxis('bottom').logMode
                y_log = self.plot_widget.getPlotItem().getAxis('left').logMode

                plot_x = np.log10(x) if x_log and x > 0 else x
                plot_y = np.log10(y) if y_log and y > 0 else y

                marker = pg.ScatterPlotItem(x=[plot_x], y=[plot_y], symbol='o', size=10, pen=pg.mkPen('r'), brush=pg.mkBrush('r'))
                self.plot_widget.plotItem.addItem(marker)

                text = pg.TextItem(f"({format_eng(x)}, {format_eng(y)})", anchor=(0.5, 1.5))
                text.setPos(plot_x, plot_y)
                self.plot_widget.plotItem.addItem(text)
                text.setFlags(text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)

                self.plot_widget.markers.append({"marker": marker, "text": text, "pos": (x, y)})

            for lm in line_marker_positions:
                vertical = lm['vertical']
                linear_pos = lm['linear_pos']
                selected = lm['selected']
                text_offsets = lm.get('text_offsets', {})
                axis = 'bottom' if vertical else 'left'
                log_mode = self.plot_widget.getPlotItem().getAxis(axis).logMode
                view_pos = np.log10(linear_pos) if log_mode and linear_pos > 0 else linear_pos
                line = pg.InfiniteLine(angle=90 if vertical else 0, movable=True, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine), hoverPen=pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4), pos=view_pos)
                self.plot_widget.plotItem.addItem(line)
                marker = {'line': line, 'vertical': vertical, 'texts': [], 'selected': selected, 'linear_pos': linear_pos, 'text_offsets': text_offsets}
                self.plot_widget.line_markers.append(marker)
                # Use closure to capture marker, ignore any signal arguments with *args
                line.sigPositionChanged.connect(lambda *args, m=marker: self.plot_widget.update_marker_labels(m))
                line.mouseReleaseEvent = lambda event, m=marker: self.plot_widget.select_marker(m)
                self.plot_widget.update_marker_labels(marker)
                if selected:
                    self.plot_widget.select_marker(marker)
        finally:
            self._is_updating = False
            # Update trace boldness based on current tech browser selection state
            # Skip during batch operations like restore to improve performance
            if not skip_post_processing:
                try:
                    if hasattr(self.tech_browser, 'update_all_selection_boldness'):
                        self.tech_browser.update_all_selection_boldness()
                except Exception:
                    pass
        return 0

    def add_tech_luts(self, dirname, pdk_name):
        self.tech_browser.add_tech_luts(dirname=dirname, pdk_name=pdk_name)

    def update_attachment_checkboxes(self):
        if not self.graph_grid:
            return
        if self not in self.graph_grid.lookup_windows:
            for cb in self.setting_checkboxes:
                cb.setEnabled(False)
                cb.setChecked(False)
            return
        my_index = self.graph_grid.lookup_windows.index(self)
        current_x = self.combo_x.currentText()
        for i in range(len(self.graph_grid.lookup_windows)):
            if i == my_index:
                self.setting_checkboxes[i].setEnabled(False)
                self.setting_checkboxes[i].setChecked(True)
            else:
                other = self.graph_grid.lookup_windows[i]
                same_x = current_x == other.combo_x.currentText()
                self.setting_checkboxes[i].setEnabled(same_x)
                if not same_x:
                    self.setting_checkboxes[i].setChecked(False)

    def get_attached_windows(self, visited=None):
        if visited is None:
            visited = set()
        if self in visited:
            return []
        visited.add(self)
        attached = []
        my_index = self.graph_grid.lookup_windows.index(self)
        for i, cb in enumerate(self.setting_checkboxes):
            if i != my_index and cb.isChecked():
                other = self.graph_grid.lookup_windows[i]
                attached.append(other)
                attached.extend(other.get_attached_windows(visited))
        return list(set(attached))


class ROARGraphGrid(QWidget):
    """Graph grid that contains four ROARLookupWindow instances arranged in a 2x2 splitter layout.

    This implementation was moved here to avoid circular imports between modules.
    """
    def __init__(self, parent=None, top_level_app=None, tech_dict=None):
        super().__init__(parent)
        self.lookup_windows = []
        layout = QVBoxLayout(self)
        self.top_level_app = top_level_app

        self.grid_splitter = QSplitter(Qt.Orientation.Vertical)
        self.grid_splitter.setChildrenCollapsible(True)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setChildrenCollapsible(True)

        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter.setChildrenCollapsible(True)

        # instantiate four lookup windows
        self.lookup_window_1 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_windows.append(self.lookup_window_1)
        self.lookup_window_2 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_windows.append(self.lookup_window_2)
        self.lookup_window_3 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_windows.append(self.lookup_window_3)
        self.lookup_window_4 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_windows.append(self.lookup_window_4)

        self.top_splitter.addWidget(self.lookup_window_1)
        self.top_splitter.addWidget(self.lookup_window_2)

        self.bottom_splitter.addWidget(self.lookup_window_3)
        self.bottom_splitter.addWidget(self.lookup_window_4)

        self.grid_splitter.addWidget(self.top_splitter)
        self.grid_splitter.setStretchFactor(0, 1)
        self.grid_splitter.addWidget(self.bottom_splitter)
        self.grid_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.grid_splitter)

    def keyPressEvent(self, event):
        """Handle keyboard events for the graph grid"""
        if event.key() == Qt.Key.Key_Escape:
            # Check if any window is in copy mode and cancel it
            in_copy_mode = False
            for window in self.lookup_windows:
                if window.copied_state is not None or window.copy_button.text() == "Paste":
                    in_copy_mode = True
                    break

            if in_copy_mode:
                # Cancel copy mode on all windows
                for window in self.lookup_windows:
                    window.cancel_copy_mode()
                event.accept()
                return

        # Pass to parent class for default handling
        super().keyPressEvent(event)

    def populate_from_app(self):
        try:
            app_tech = getattr(self.top_level_app, 'tech_dict', None)
            expr_symbols = []
            try:
                expressions, constraints = self.top_level_app.editor_window.get_expressions_and_constraints()
                expr_symbols = list(expressions.keys()) if expressions else []
            except Exception:
                expr_symbols = []

            for lookup_window in self.lookup_windows:
                try:
                    tb = getattr(lookup_window, 'tech_browser', None)
                    if tb is not None:
                        tb.tech_dict = app_tech if app_tech is not None else {}
                        tb.populate_from_tech_dict()
                        tb.startup = False
                    lookup_window.update_expression_symbols(expr_symbols)
                    lookup_window.update_combobox_items()
                except Exception:
                    pass
        except Exception:
            pass

