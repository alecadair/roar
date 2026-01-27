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

# Matplotlib imports for 3D plotting
import matplotlib
matplotlib.use('Qt5Agg')  # Use Qt5 backend for PyQt6 compatibility
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt


def format_eng(num):
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
    def __init__(self, *args, top_level_app=None, parent_lookup_window=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.top_level_app = top_level_app
        self.parent_lookup_window = parent_lookup_window
        self._mouse_inside = False

        # Add timer for debouncing marker label updates during dragging
        self._marker_update_timer = None
        self._pending_marker_updates = []  # Use list instead of set since dicts aren't hashable

        # Add legend and crosshair lines
        self.plotItem.addLegend()
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

        # Connect mouse events
        try:
            self.scene().sigMouseMoved.connect(self.on_mouse_moved)
            self.scene().sigMouseClicked.connect(self.on_mouse_clicked)
            self.plotItem.vb.sigStateChanged.connect(self.on_state_changed)
            self.plotItem.sigRangeChanged.connect(self.on_range_changed)
            self.plotItem.scene().itemChanged.connect(self.on_item_changed)
        except Exception:
            pass

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

    def on_mouse_clicked(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = event.scenePos()
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
        if min_dist_sq > 75**2: # 75 pixels tolerance
            return None, None

        return closest_curve, closest_point_index

    def is_close(self, x1, y1, x2, y2):
        try:
            p1 = self.plotItem.vb.mapViewToScene(pg.Point(x1, y1))
            p2 = self.plotItem.vb.mapViewToScene(pg.Point(x2, y2))
            return (p1.x() - p2.x())**2 + (p1.y() - p2.y())**2 < 10**2 # 10 pixels tolerance
        except Exception:
            return False

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

        # Update linear_pos based on current position
        if vertical:
            x_log = self.plotItem.getAxis('bottom').logMode
            marker['linear_pos'] = 10**pos if x_log else pos
        else:
            y_log = self.plotItem.getAxis('left').logMode
            marker['linear_pos'] = 10**pos if y_log else pos


        # remove old texts
        for text in marker['texts']:
            self.plotItem.removeItem(text)
        marker['texts'].clear()
        if 'summary_text' in marker:
            self.plotItem.removeItem(marker['summary_text'])
            del marker['summary_text']

        pos = line.value()
        text_list = []
        y_values = []
        x_values = []
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
                    y_values.append(y)
                else:
                    # Horizontal line at y=pos, find closest x
                    idx = np.argmin(np.abs(ydata - pos))
                    x = xdata[idx]
                    y = ydata[idx]
                    text = pg.TextItem(f"({format_eng(x)}, {format_eng(pos)})", anchor=(0.5, 0.5))
                    text.setPos(x, pos)
                    x_values.append(x)
                text_list.append(text)
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
                marker['texts'].append(text)

        # Add summary text for single marker
        if vertical and y_values:
            min_y = min(y_values)
            max_y = max(y_values)
            if (max_y + min_y) != 0:
                percent = 200 * (max_y - min_y) / (max_y + min_y)
                summary_text = pg.TextItem(f"ΔY: {percent:.1f}%", anchor=(0.5, 0.5))
                y_center = (self.plotItem.viewRange()[1][0] + self.plotItem.viewRange()[1][1]) / 2
                summary_text.setPos(pos, y_center)
                self.plotItem.addItem(summary_text)
                summary_text.setFlags(summary_text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
                marker['summary_text'] = summary_text
        elif not vertical and x_values:
            min_x = min(x_values)
            max_x = max(x_values)
            if (max_x + min_x) != 0:
                percent = 100 * (max_x - min_x) / ((max_x + min_x)/2)
                summary_text = pg.TextItem(f"ΔX: {percent:.1f}%", anchor=(0.5, 0.5))
                x_center = (self.plotItem.viewRange()[0][0] + self.plotItem.viewRange()[0][1]) / 2
                summary_text.setPos(x_center, pos)
                self.plotItem.addItem(summary_text)
                summary_text.setFlags(summary_text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
                marker['summary_text'] = summary_text

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
        self.checkbox_legend = QCheckBox("Legend")

        # store the radio layout on the instance so other methods can reference it
        self.radio_layout = QHBoxLayout()
        # Tighten radio layout margins so it doesn't add extra vertical padding
        self.radio_layout.setContentsMargins(0, 0, 0, 0)
        self.radio_layout.setSpacing(2)
        self.radio_layout.addWidget(self.radio_device_params)
        self.radio_layout.addWidget(self.radio_design_eq)
        self.radio_layout.addStretch()
        self.controls_layout.addLayout(self.radio_layout, 0, 0, 1, 3)
        self.controls_layout.addWidget(self.checkbox_legend, 0, 3)

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

        # Create matplotlib 3D canvas for superior 3D plotting
        try:
            self.mpl_figure = Figure(figsize=(8, 6), dpi=100)
            self.mpl_canvas = FigureCanvas(self.mpl_figure)
            self.mpl_canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.mpl_canvas.setVisible(False)
            self.mpl_ax = None  # Will be created when needed
            self.mpl_3d_items = []  # Track plotted items

            # Create navigation toolbar for better 3D interaction
            # This provides pan, zoom, and home buttons for better control
            self.mpl_toolbar = NavigationToolbar(self.mpl_canvas, self)
            self.mpl_toolbar.setVisible(False)  # Hidden by default, shown with 3D plots
        except Exception as e:
            print(f"Could not create matplotlib canvas: {e}")
            self.mpl_canvas = None
            self.mpl_figure = None
            self.mpl_ax = None
            self.mpl_3d_items = []
            self.mpl_toolbar = None

        # Keep old gl_widget for backward compatibility (but prefer matplotlib)
        try:
            self.gl_widget = None  # Deprecated in favor of matplotlib
            self.gl_items = []
        except Exception:
            self.gl_widget = None
            self.gl_items = []

        self.plot_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.plot_widget)
        if self.mpl_toolbar is not None:
            right_layout.addWidget(self.mpl_toolbar)  # Add toolbar above canvas
        if self.mpl_canvas is not None:
            right_layout.addWidget(self.mpl_canvas)
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

        # Update visibility of Z-axis and 3D controls
        self.label_z.setVisible(not is_device_params)
        self.combo_z.setVisible(not is_device_params)
        self.spin_z.setVisible(not is_device_params)
        self.checkbox_logz.setVisible(not is_device_params)
        self.checkbox_3d.setVisible(not is_device_params)
        self.checkbox_contour.setVisible(not is_device_params)

        self.checkbox_legend.setVisible(True)

        if is_device_params:
            items = list(self.top_level_app.lookups) if self.top_level_app else []
            self.combo_x.clear()
            self.combo_y.clear()
            self.combo_z.clear()
            self.combo_x.addItems(items)
            self.combo_y.addItems(items)
            self.combo_z.addItems(items)
            self.combo_x.setCurrentText("kgm")
            self.combo_y.setCurrentText("kcgs")
            self.combo_z.setCurrentText("iden")
        else:
            items = list(self.expression_symbols) if self.expression_symbols else []
            self.combo_x.clear()
            self.combo_y.clear()
            self.combo_z.clear()
            self.combo_x.addItems(items)
            self.combo_y.addItems(items)
            self.combo_z.addItems(items)

            if items:
                self.combo_x.setCurrentIndex(0)
                self.combo_y.setCurrentIndex(min(1, len(items) - 1))
                self.combo_z.setCurrentIndex(min(2, len(items) - 1))

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
        self.update_combobox_items()
        self.update_attachment_checkboxes()

    def on_background_color_changed(self):
        """Update the 3D plot background when the Black BG checkbox changes"""
        if self.mpl_canvas is not None and self.mpl_canvas.isVisible():
            # Redraw the 3D plot with new background color
            self.update_graph_from_tech_browser()

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

    def sync_log_checkboxes(self):
        x_log = self.plot_widget.getPlotItem().getAxis('bottom').logMode
        y_log = self.plot_widget.getPlotItem().getAxis('left').logMode

        self.checkbox_logx.setChecked(x_log)
        self.checkbox_logy.setChecked(y_log)

    def update_log_scale(self):
        self.plot_widget.getPlotItem().setLogMode(x=self.checkbox_logx.isChecked(), y=self.checkbox_logy.isChecked())
        # Reposition markers after log scale change
        x_log = self.checkbox_logx.isChecked()
        y_log = self.checkbox_logy.isChecked()
        for marker in self.plot_widget.line_markers:
            linear_pos = marker['linear_pos']
            if marker['vertical']:
                new_pos = np.log10(linear_pos) if x_log and linear_pos > 0 else linear_pos
            else:
                new_pos = np.log10(linear_pos) if y_log and linear_pos > 0 else linear_pos
            marker['line'].setPos(new_pos)
        for marker_info in self.plot_widget.markers:
            x, y = marker_info['pos']
            plot_x = np.log10(x) if x_log and x > 0 else x
            plot_y = np.log10(y) if y_log and y > 0 else y
            marker_info['marker'].setData(x=[plot_x], y=[plot_y])
            marker_info['text'].setPos(plot_x, plot_y)
        self.update_graph_from_tech_browser()

        # Synchronize log scale with attached windows
        if self.graph_grid:
            for attached_window in self.get_attached_windows():
                # Update log checkboxes in attached windows
                attached_window.checkbox_logx.setChecked(x_log)
                attached_window.checkbox_logy.setChecked(y_log)

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
            'checkbox_legend': self.checkbox_legend.isChecked(),
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

            # Restore radio button
            if state.get('is_device_params_mode', True):
                self.radio_device_params.setChecked(True)
            else:
                self.radio_design_eq.setChecked(True)

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
            self.checkbox_legend.setChecked(state.get('checkbox_legend', False))
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
            print(f"Error restoring state: {e}")

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
            print(f"Error restoring markers: {e}")

    def restore_tech_browser_checks(self, checked_paths):
        """Restore the checked state of items in the tech browser"""
        try:
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

        except Exception as e:
            print(f"Error restoring tech browser checks: {e}")

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

    def update_graph_from_tech_browser(self, equation_eval=None):
        if self._is_updating:
            return
        self._is_updating = True

        try:
            # Top-level try to ensure the finally block below always executes
            # (this was missing and caused a SyntaxError during import).
            models_selected = self.tech_browser.get_checked_item_paths()

            marker_positions = []
            for marker_info in self.plot_widget.markers:
                marker_positions.append(marker_info)

            line_marker_positions = []
            for m in self.plot_widget.line_markers:
                line_marker_positions.append({'vertical': m['vertical'], 'linear_pos': m['linear_pos'], 'selected': m['selected']})

            auto_fit = not self.plot_widget.plotItem.curves

            self.plot_widget.clear()
            self.plot_widget.markers.clear()

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

            for model in models_selected:
                model_tokens = model.split(">")
                pdk = model_tokens[1]
                model_name = model_tokens[2]
                length = model_tokens[3]
                corner = model_tokens[4]
                cid_corner = self.tech_browser.tech_dict[pdk][model_name][length]["corners"][corner]
                if equation_eval != None:
                    print("TODO")
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

                    cid_corner.plot_processes_params_roar_plot_widget(param1=param1, param2=param2, param3=None, norm_type="",
                                                                      show_plot=True, new_plot=new_plot,
                                                                      roar_plot_widget=self.plot_widget,
                                                                      color=color, legend_str=None, enable_3d=False,
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
                            print(f"[DESIGN EQS] Device corners mapping: {device_corners}")
                        except Exception as e:
                            print(f"[DESIGN EQS] Could not get device corners: {e}")

                    equation_solver = ROAREquationSolver(top_level_app=self.top_level_app, device_corners=device_corners)
                    equation_solver.corners = [cid_corner.df]
                    expressions, constraints = self.top_level_app.editor_window.get_expressions_and_constraints()
                    for expression_sym in expressions:
                        expression = expressions[expression_sym]
                        equation_solver.add_equation(expression_sym, expression)
                    result_matrix = equation_solver.evaluate_equations(symbols_to_add=[param1, param2], corner_dfs=[cid_corner.df])
                    if not result_matrix or not isinstance(result_matrix, dict):
                        msg = f"Design Eq solver returned no results for {param1},{param2}"
                        print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                        continue
                    if param1 not in result_matrix or param2 not in result_matrix:
                        msg = f"Design Eq results missing requested symbols: {param1} or {param2}. Available: {list(result_matrix.keys())}"
                        print(msg)
                        try:
                            if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                self.top_level_app.statusBar().showMessage(msg, 5000)
                        except Exception:
                            pass
                        continue
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
                                # For 3D surface plotting, we need to evaluate Z at all combinations of X and Y
                                # First, get X and Y data from the corner
                                result_matrix_xy = equation_solver.evaluate_equations(symbols_to_add=[param1, param2], corner_dfs=[cid_corner.df])

                                if result_matrix_xy is not None and param1 in result_matrix_xy and param2 in result_matrix_xy:
                                    # Get X and Y data
                                    x_data = np.asarray(result_matrix_xy[param1]).ravel()
                                    y_data = np.asarray(result_matrix_xy[param2]).ravel()

                                    # Get unique values for creating meshgrid
                                    unique_x = np.unique(x_data)
                                    unique_y = np.unique(y_data)

                                    # Limit grid resolution for performance (3D plots can be laggy with too many points)
                                    # Recommended: 20-40 points per axis for smooth interaction
                                    max_grid_resolution = 40  # Adjust this for performance vs quality tradeoff

                                    # Downsample if needed
                                    if len(unique_x) > max_grid_resolution:
                                        # Use linspace to get evenly distributed points
                                        unique_x = np.linspace(unique_x[0], unique_x[-1], max_grid_resolution)
                                        print(f"[PERFORMANCE] Downsampled X from {len(np.unique(x_data))} to {max_grid_resolution} points")

                                    if len(unique_y) > max_grid_resolution:
                                        unique_y = np.linspace(unique_y[0], unique_y[-1], max_grid_resolution)
                                        print(f"[PERFORMANCE] Downsampled Y from {len(np.unique(y_data))} to {max_grid_resolution} points")

                                    # Decide between surface and scatter plot
                                    # For surface: need enough unique values and Z must be a function of X and Y
                                    min_grid_size = 3  # Need at least 3x3 grid for meaningful surface

                                    if len(unique_x) >= min_grid_size and len(unique_y) >= min_grid_size:
                                        # Create meshgrid for surface plot
                                        X_grid, Y_grid = np.meshgrid(unique_x, unique_y)

                                        # Now we need to evaluate Z for ALL points in the meshgrid
                                        # We'll create a temporary dataframe with all combinations
                                        try:
                                            import pandas as pd
                                            # Flatten the grid to get all (X,Y) pairs
                                            x_flat = X_grid.ravel()
                                            y_flat = Y_grid.ravel()

                                            # Create a temporary DataFrame with these values
                                            # IMPORTANT: If param1/param2 are equations (e.g., kgm1 = kgm:M1),
                                            # we need to figure out the underlying column names
                                            temp_df = pd.DataFrame()

                                            # Helper function to get the actual column name
                                            def get_base_column_name(param_name, param_values):
                                                """
                                                If param_name is an equation like 'kgm1 = kgm:M1',
                                                extract the base column name 'kgm'.
                                                Otherwise, just use param_name as-is.
                                                """
                                                if param_name in equation_solver.equations:
                                                    eq = equation_solver.equations[param_name]
                                                    eq_str = str(eq)
                                                    # Check if it's a lookup (contains ':')
                                                    if ':' in eq_str:
                                                        # Extract the lookup variable (before ':')
                                                        base_name = eq_str.split(':')[0].strip()
                                                        print(f"[DEBUG] {param_name} is equation '{eq_str}' -> using base column '{base_name}'")
                                                        return base_name
                                                # Not an equation or not a lookup, use as-is
                                                return param_name

                                            # Get actual column names
                                            col1 = get_base_column_name(param1, x_flat)
                                            col2 = get_base_column_name(param2, y_flat)

                                            # Create temp_df with the correct column names
                                            temp_df[col1] = x_flat
                                            temp_df[col2] = y_flat

                                            # Also add param1 and param2 as columns if they're different
                                            # This handles cases where the equation solver expects both
                                            if col1 != param1:
                                                temp_df[param1] = x_flat
                                            if col2 != param2:
                                                temp_df[param2] = y_flat

                                            print(f"\n[DEBUG] Creating meshgrid for surface plot")
                                            print(f"  param1 ({param1}): {len(unique_x)} unique values")
                                            print(f"  param2 ({param2}): {len(unique_y)} unique values")
                                            print(f"  Grid size: {X_grid.shape}")
                                            print(f"  Total points: {len(x_flat)}")
                                            print(f"  param1 range: {np.min(x_flat)} to {np.max(x_flat)}")
                                            print(f"  param2 range: {np.min(y_flat)} to {np.max(y_flat)}")

                                            # Copy ALL other columns from original corner
                                            # This ensures any variables referenced by param3 equation are available
                                            # IMPORTANT: Don't overwrite the meshgrid columns!
                                            columns_to_preserve = set([param1, param2, col1, col2])
                                            for col in cid_corner.df.columns:
                                                if col not in columns_to_preserve:
                                                    # Use the first value as representative for other variables
                                                    temp_df[col] = cid_corner.df[col].iloc[0]

                                            print(f"  Preserved columns from overwrite: {columns_to_preserve}")

                                            print(f"  temp_df columns: {list(temp_df.columns)}")
                                            print(f"  temp_df shape: {temp_df.shape}")
                                            print(f"  {param1} in temp_df: {param1 in temp_df.columns}")
                                            print(f"  {param2} in temp_df: {param2 in temp_df.columns}")
                                            print(f"  {param1} unique values in temp_df: {len(temp_df[param1].unique())}")
                                            print(f"  {param2} unique values in temp_df: {len(temp_df[param2].unique())}")

                                            # Now evaluate Z using this grid
                                            result_matrix_3d = equation_solver.evaluate_equations(
                                                symbols_to_add=[param3],
                                                corner_dfs=[temp_df]
                                            )

                                            if result_matrix_3d is not None and param3 in result_matrix_3d:
                                                z_data = np.asarray(result_matrix_3d[param3]).ravel()

                                                print(f"\n[DEBUG] Z evaluation results:")
                                                print(f"  param3 ({param3}) shape: {z_data.shape}")
                                                print(f"  Z range: {np.min(z_data)} to {np.max(z_data)}")
                                                print(f"  Z unique values: {len(np.unique(z_data))}")
                                                if len(np.unique(z_data)) == 1:
                                                    print(f"  ⚠ WARNING: Z has only ONE unique value (flat plane)!")
                                                print(f"  First 5 Z values: {z_data[:5]}")
                                                print(f"  Last 5 Z values: {z_data[-5:]}")

                                                # Reshape Z to match the meshgrid
                                                try:
                                                    Z_grid = z_data.reshape(X_grid.shape)
                                                    results_3d = (X_grid, Y_grid, Z_grid, 'surface')
                                                    print(f"  ✓ Created surface plot: {X_grid.shape} grid")
                                                    print(f"  Z grid corner values:")
                                                    print(f"    Z[0,0]={Z_grid[0,0]}, Z[0,-1]={Z_grid[0,-1]}")
                                                    print(f"    Z[-1,0]={Z_grid[-1,0]}, Z[-1,-1]={Z_grid[-1,-1]}")
                                                except Exception as e:
                                                    print(f"Reshape failed: {e}, falling back to scatter")
                                                    # Fall back to scatter
                                                    results_3d = (x_data, y_data,
                                                                np.asarray(equation_solver.evaluate_equations([param3], [cid_corner.df])[param3]).ravel(),
                                                                'scatter')
                                            else:
                                                results_3d = None
                                        except Exception as e:
                                            print(f"Grid evaluation failed: {e}")
                                            import traceback
                                            traceback.print_exc()
                                            # Fall back to scatter plot with original data
                                            result_matrix_3d = equation_solver.evaluate_equations(
                                                symbols_to_add=[param1, param2, param3],
                                                corner_dfs=[cid_corner.df]
                                            )
                                            if result_matrix_3d is not None and param3 in result_matrix_3d:
                                                z_data = np.asarray(result_matrix_3d[param3]).ravel()
                                                results_3d = (x_data, y_data, z_data, 'scatter')
                                            else:
                                                results_3d = None
                                    else:
                                        # Not enough unique values for surface, use scatter/line plot
                                        result_matrix_3d = equation_solver.evaluate_equations(
                                            symbols_to_add=[param1, param2, param3],
                                            corner_dfs=[cid_corner.df]
                                        )
                                        if result_matrix_3d is not None and param3 in result_matrix_3d:
                                            z_data = np.asarray(result_matrix_3d[param3]).ravel()
                                            results_3d = (x_data, y_data, z_data, 'scatter')
                                        else:
                                            results_3d = None
                                else:
                                    results_3d = None

                            except Exception as e:
                                print(f"3D data preparation error: {e}")
                                import traceback
                                traceback.print_exc()
                                results_3d = None

                            if results_3d and self.mpl_canvas is not None:
                                try:
                                    self.plot_widget.hide()
                                except Exception:
                                    pass
                                try:
                                    self.mpl_canvas.setVisible(True)
                                    # Show toolbar for better 3D control
                                    if self.mpl_toolbar is not None:
                                        self.mpl_toolbar.setVisible(True)
                                except Exception:
                                    pass

                                # Unpack results (includes plot type)
                                if len(results_3d) == 4:
                                    p1, p2, p3, plot_type = results_3d
                                else:
                                    # Fallback for old format
                                    p1, p2, p3 = results_3d
                                    plot_type = 'scatter'

                                try:
                                    # Clear the figure only on first plot
                                    if new_plot:
                                        self.mpl_figure.clear()

                                    # Check if we need to create new axes
                                    is_contour_mode = self.checkbox_contour.isChecked()

                                    # Create appropriate subplot if needed
                                    if new_plot or self.mpl_ax is None:
                                        if is_contour_mode and plot_type == 'surface':
                                            # 2D contour plot
                                            self.mpl_ax = self.mpl_figure.add_subplot(111)
                                        else:
                                            # 3D plot
                                            self.mpl_ax = self.mpl_figure.add_subplot(111, projection='3d')

                                    # Set background color based on checkbox (only on first plot)
                                    is_black_bg = self.checkbox_black_bg.isChecked()
                                    if new_plot:
                                        if is_contour_mode and plot_type == 'surface':
                                            # 2D background
                                            if is_black_bg:
                                                self.mpl_figure.patch.set_facecolor('black')
                                                self.mpl_ax.set_facecolor('black')
                                            else:
                                                self.mpl_figure.patch.set_facecolor('white')
                                                self.mpl_ax.set_facecolor('white')
                                        else:
                                            # 3D background
                                            if is_black_bg:
                                                self.mpl_figure.patch.set_facecolor('black')
                                                self.mpl_ax.set_facecolor('black')
                                                self.mpl_ax.xaxis.pane.set_facecolor('black')
                                                self.mpl_ax.yaxis.pane.set_facecolor('black')
                                                self.mpl_ax.zaxis.pane.set_facecolor('black')
                                            else:
                                                self.mpl_figure.patch.set_facecolor('white')
                                                self.mpl_ax.set_facecolor('white')
                                                self.mpl_ax.xaxis.pane.set_facecolor('white')
                                                self.mpl_ax.yaxis.pane.set_facecolor('white')
                                                self.mpl_ax.zaxis.pane.set_facecolor('white')

                                    grid_color = 'gray'
                                    text_color = 'white' if is_black_bg else 'black'
                                    axis_color = 'white' if is_black_bg else 'black'

                                    # Check if contour mode is enabled
                                    is_contour_mode_check = self.checkbox_contour.isChecked()

                                    # Get corner-specific color
                                    corner_color = self.tech_browser.get_color_for_path(model)
                                    # Convert to matplotlib color format
                                    mpl_color = None

                                    # Handle different color types
                                    from PyQt6.QtGui import QColor
                                    if isinstance(corner_color, QColor):
                                        # QColor object - convert to hex string
                                        mpl_color = corner_color.name()
                                    elif hasattr(corner_color, 'color'):
                                        # pyqtgraph Pen object - extract color
                                        pen_color = corner_color.color()
                                        if isinstance(pen_color, QColor):
                                            mpl_color = pen_color.name()
                                    elif hasattr(corner_color, 'name'):
                                        # Object with name() method
                                        mpl_color = corner_color.name()
                                    elif isinstance(corner_color, str):
                                        # Already a string
                                        mpl_color = corner_color

                                    # Fallback to a color from a predefined list based on corner index
                                    if mpl_color is None:
                                        color_list = ['#ff0000', '#0000ff', '#00ff00', '#ff8800', '#ff00ff', '#00ffff']
                                        corner_index = models_selected.index(model) if model in models_selected else 0
                                        mpl_color = color_list[corner_index % len(color_list)]

                                    print(f"[COLOR DEBUG] Corner: {corner}, Color: {mpl_color}")

                                    # Plot based on plot type
                                    if plot_type == 'surface':
                                        from matplotlib import cm

                                        if is_contour_mode_check:
                                            # Create contour plot on XY plane with corner-specific color
                                            # Use alpha to allow multiple corners to be visible
                                            alpha_contour = 0.6 if not new_plot else 0.8

                                            # Create filled contour plot
                                            contour_filled = self.mpl_ax.contourf(p1, p2, p3, levels=15, alpha=alpha_contour)
                                            # Add contour lines with corner color
                                            contour_lines = self.mpl_ax.contour(p1, p2, p3, levels=15, colors=[mpl_color],
                                                                               linewidths=1.5, alpha=0.8)
                                            # Add labels to contour lines
                                            self.mpl_ax.clabel(contour_lines, inline=True, fontsize=7,
                                                             colors=[mpl_color])


                                            # Set labels only on first plot
                                            if new_plot:
                                                self.mpl_ax.set_xlabel(f'{param1}', fontsize=10, color=text_color, fontweight='bold')
                                                self.mpl_ax.set_ylabel(f'{param2}', fontsize=10, color=text_color, fontweight='bold')
                                                self.mpl_ax.set_title(f'Contour Plot: {param3} vs {param1} and {param2}',
                                                                    fontsize=12, color=text_color, fontweight='bold')

                                                # Customize tick colors
                                                self.mpl_ax.tick_params(axis='x', colors=text_color, labelsize=8)
                                                self.mpl_ax.tick_params(axis='y', colors=text_color, labelsize=8)

                                                # Set equal aspect ratio for better visualization
                                                self.mpl_ax.set_aspect('auto')
                                        else:
                                            # Plot as a 3D surface with corner-specific color
                                            # Create a custom colormap based on the corner color
                                            from matplotlib.colors import LinearSegmentedColormap
                                            import matplotlib.colors as mcolors

                                            # Convert hex color to RGB
                                            try:
                                                base_rgb = mcolors.to_rgb(mpl_color)
                                                # Create a colormap from dark to bright version of the corner color
                                                # Dark version (multiply by 0.3)
                                                dark_rgb = tuple(c * 0.3 for c in base_rgb)
                                                # Create custom colormap
                                                corner_cmap = LinearSegmentedColormap.from_list(
                                                    f'corner_{corner}',
                                                    [dark_rgb, base_rgb]
                                                )
                                            except:
                                                # Fallback to viridis if color conversion fails
                                                corner_cmap = cm.viridis

                                            surf = self.mpl_ax.plot_surface(p1, p2, p3, cmap=corner_cmap,
                                                                           alpha=0.7, edgecolor=mpl_color,
                                                                           linewidth=0.3, antialiased=True)
                                    else:
                                        # Plot as scatter points and lines with corner-specific color
                                        self.mpl_ax.scatter(p1, p2, p3, c=mpl_color, marker='o', s=50, alpha=0.8,
                                                           edgecolors=mpl_color, linewidth=0.5, label=f'{corner}')

                                        # Plot the line connecting points with same color
                                        self.mpl_ax.plot(p1, p2, p3, c=mpl_color, linewidth=1.5, alpha=0.7)

                                    # Set labels and customization (different for contour vs 3D)
                                    if not is_contour_mode or plot_type != 'surface':
                                        # These are for 3D plots or scatter plots
                                        if hasattr(self.mpl_ax, 'set_zlabel'):
                                            # 3D axis
                                            self.mpl_ax.set_xlabel(f'{param1}', fontsize=10, color=text_color, fontweight='bold')
                                            self.mpl_ax.set_ylabel(f'{param2}', fontsize=10, color=text_color, fontweight='bold')
                                            self.mpl_ax.set_zlabel(f'{param3}', fontsize=10, color=text_color, fontweight='bold')

                                            # Set title
                                            self.mpl_ax.set_title(f'3D Plot: {param3} vs {param1} and {param2}',
                                                                 fontsize=12, color=text_color, fontweight='bold', pad=20)

                                            # Customize grid
                                            self.mpl_ax.grid(True, linestyle='--', alpha=0.3, color=grid_color)

                                            # Customize tick colors
                                            self.mpl_ax.tick_params(axis='x', colors=text_color, labelsize=8)
                                            self.mpl_ax.tick_params(axis='y', colors=text_color, labelsize=8)
                                            self.mpl_ax.tick_params(axis='z', colors=text_color, labelsize=8)

                                            # Customize axis line colors
                                            self.mpl_ax.xaxis.line.set_color(axis_color)
                                            self.mpl_ax.yaxis.line.set_color(axis_color)
                                            self.mpl_ax.zaxis.line.set_color(axis_color)

                                            # Customize pane edges
                                            self.mpl_ax.xaxis.pane.set_edgecolor(grid_color)
                                            self.mpl_ax.yaxis.pane.set_edgecolor(grid_color)
                                            self.mpl_ax.zaxis.pane.set_edgecolor(grid_color)

                                            # Set pane transparency
                                            self.mpl_ax.xaxis.pane.set_alpha(0.1)
                                            self.mpl_ax.yaxis.pane.set_alpha(0.1)
                                            self.mpl_ax.zaxis.pane.set_alpha(0.1)

                                            # Add legend only for scatter plots (surface has colorbar)
                                            if plot_type != 'surface':
                                                legend = self.mpl_ax.legend(loc='upper right', fontsize=8, framealpha=0.8)
                                                if is_black_bg:
                                                    legend.get_frame().set_facecolor('black')
                                                    legend.get_frame().set_edgecolor('white')
                                                    for text in legend.get_texts():
                                                        text.set_color('white')
                                                else:
                                                    legend.get_frame().set_facecolor('white')
                                                    legend.get_frame().set_edgecolor('black')

                                            # Set viewing angle with origin (0,0) pointing at user
                                            # azim=-135: Positions view from front-right, looking towards origin
                                            # elev=30: Comfortable viewing angle from above
                                            self.mpl_ax.view_init(elev=30, azim=-135)

                                            # Improve mouse rotation sensitivity and control
                                            # Set mouse sensitivity for smoother rotation
                                            try:
                                                # Adjust the mouse sensitivity for better control
                                                # Lower values = slower rotation = more precise control
                                                self.mpl_ax.mouse_init(rotate_btn=1, zoom_btn=3)

                                                # Set distance for better zoom/perspective
                                                self.mpl_ax.dist = 10  # Default is 10, adjust if needed
                                            except Exception as e:
                                                pass  # mouse_init might not be available in all matplotlib versions

                                    # Auto-scale to fit data
                                    self.mpl_ax.autoscale(enable=True, axis='both', tight=True)

                                    # Add some padding to the limits
                                    x_range = np.max(p1) - np.min(p1)
                                    y_range = np.max(p2) - np.min(p2)
                                    z_range = np.max(p3) - np.min(p3)

                                    if x_range > 0:
                                        self.mpl_ax.set_xlim(np.min(p1) - 0.05*x_range, np.max(p1) + 0.05*x_range)
                                    if y_range > 0:
                                        self.mpl_ax.set_ylim(np.min(p2) - 0.05*y_range, np.max(p2) + 0.05*y_range)
                                    # Only set z limits for 3D plots
                                    if not is_contour_mode or plot_type != 'surface':
                                        if z_range > 0 and hasattr(self.mpl_ax, 'set_zlim'):
                                            self.mpl_ax.set_zlim(np.min(p3) - 0.05*z_range, np.max(p3) + 0.05*z_range)

                                    # Tight layout for better spacing
                                    self.mpl_figure.tight_layout()

                                    # Refresh the canvas
                                    self.mpl_canvas.draw()

                                    # Print axis value ranges to console for reference
                                    print(f"\n3D Plot Axis Ranges ({plot_type}):")
                                    print(f"  X ({param1}): {format_eng(np.min(p1))} to {format_eng(np.max(p1))}")
                                    print(f"  Y ({param2}): {format_eng(np.min(p2))} to {format_eng(np.max(p2))}")
                                    print(f"  Z ({param3}): {format_eng(np.min(p3))} to {format_eng(np.max(p3))}")
                                    if plot_type == 'surface':
                                        print(f"  Grid shape: {p1.shape}")
                                    else:
                                        print(f"  Total points: {len(p1) if hasattr(p1, '__len__') else p1.size}")
                                    print()

                                except Exception as e:
                                    msg = f"3D plotting error: {e}"
                                    print(msg)
                                    import traceback
                                    traceback.print_exc()
                                    try:
                                        if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                            self.top_level_app.statusBar().showMessage(msg, 5000)
                                    except Exception:
                                        pass
                                new_plot = False
                                continue

                        # 2D plotting (only when NOT in 3D mode)
                        else:
                            try:
                                # Hide matplotlib canvas when not in 3D mode
                                if self.mpl_canvas is not None:
                                    self.mpl_canvas.setVisible(False)
                                # Hide toolbar when not in 3D mode
                                if self.mpl_toolbar is not None:
                                    self.mpl_toolbar.setVisible(False)
                            except Exception:
                                pass
                            try:
                                self.plot_widget.show()
                            except Exception:
                                pass
                            curve = self.plot_widget.plot(params1, params2, pen=graph_pen, name=None)
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

            # Always autorange after plotting
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
                axis = 'bottom' if vertical else 'left'
                log_mode = self.plot_widget.getPlotItem().getAxis(axis).logMode
                view_pos = np.log10(linear_pos) if log_mode and linear_pos > 0 else linear_pos
                line = pg.InfiniteLine(angle=90 if vertical else 0, movable=True, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine), hoverPen=pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4), pos=view_pos)
                self.plot_widget.plotItem.addItem(line)
                marker = {'line': line, 'vertical': vertical, 'texts': [], 'selected': selected, 'linear_pos': linear_pos}
                self.line_markers.append(marker)
                line.sigPositionChanged.connect(lambda: self.update_marker_labels(marker))
                line.mouseReleaseEvent = lambda event, m=marker: self.select_marker(m)
                self.update_marker_labels(marker)
                if selected:
                    self.select_marker(marker)
        finally:
            self._is_updating = False
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

