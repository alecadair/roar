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
from PyQt6.QtGui import QColor, QCursor


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

    def add_vertical_marker(self, pos=None):
        if pos is None:
            cursor_pos = QCursor.pos()
            global_pos = self.mapToGlobal(QPoint(0, 0))
            local_pos = cursor_pos - global_pos
            if not self.rect().contains(local_pos):
                return  # not over the widget
            mouse_point = self.plotItem.vb.mapSceneToView(self.mapToScene(local_pos))
            pos = mouse_point.x()
        x_log = self.plotItem.getAxis('bottom').logMode
        linear_pos = 10**pos if x_log else pos
        line = pg.InfiniteLine(angle=90, movable=True, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine), hoverPen=pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4), pos=pos)
        self.plotItem.addItem(line)
        marker = {'line': line, 'vertical': True, 'texts': [], 'selected': False, 'linear_pos': linear_pos}
        self.line_markers.append(marker)
        line.sigPositionChanged.connect(lambda: self.update_marker_labels(marker))
        line.mouseReleaseEvent = lambda event, m=marker: self.select_marker(m)
        self.update_marker_labels(marker)

    def add_horizontal_marker(self, pos=None):
        if pos is None:
            cursor_pos = QCursor.pos()
            global_pos = self.mapToGlobal(QPoint(0, 0))
            local_pos = cursor_pos - global_pos
            if not self.rect().contains(local_pos):
                return  # not over the widget
            mouse_point = self.plotItem.vb.mapSceneToView(self.mapToScene(local_pos))
            pos = mouse_point.y()
        y_log = self.plotItem.getAxis('left').logMode
        linear_pos = 10**pos if y_log else pos
        line = pg.InfiniteLine(angle=0, movable=True, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine), hoverPen=pg.mkPen('gray', style=Qt.PenStyle.DashLine, width=4), pos=pos)
        self.plotItem.addItem(line)
        marker = {'line': line, 'vertical': False, 'texts': [], 'selected': False, 'linear_pos': linear_pos}
        self.line_markers.append(marker)
        line.sigPositionChanged.connect(lambda: self.update_marker_labels(marker))
        line.mouseReleaseEvent = lambda event, m=marker: self.select_marker(m)
        self.update_marker_labels(marker)

    def update_marker_labels(self, marker):
        line = marker['line']
        vertical = marker['vertical']
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
            if min_y != 0:
                percent = (max_y - min_y) / abs(min_y) * 100
                summary_text = pg.TextItem(f"ΔY: {percent:.1f}%", anchor=(0.5, 0.5))
                y_center = (self.plotItem.viewRange()[1][0] + self.plotItem.viewRange()[1][1]) / 2
                summary_text.setPos(pos, y_center)
                self.plotItem.addItem(summary_text)
                summary_text.setFlags(summary_text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
                marker['summary_text'] = summary_text
        elif not vertical and x_values:
            min_x = min(x_values)
            max_x = max(x_values)
            if min_x != 0:
                percent = (max_x - min_x) / abs(min_x) * 100
                summary_text = pg.TextItem(f"ΔX: {percent:.1f}%", anchor=(0.5, 0.5))
                x_center = (self.plotItem.viewRange()[0][0] + self.plotItem.viewRange()[0][1]) / 2
                summary_text.setPos(x_center, pos)
                self.plotItem.addItem(summary_text)
                summary_text.setFlags(summary_text.flags() | QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
                marker['summary_text'] = summary_text

    def on_marker_selected(self, marker, selected):
        # Optional: change appearance when selected
        pass

    def select_marker(self, marker):
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            to_remove = [m for m in self.line_markers if m.get('selected', False)]
            for m in to_remove:
                self.plotItem.removeItem(m['line'])
                for text in m['texts']:
                    self.plotItem.removeItem(text)
                if 'summary_text' in m:
                    self.plotItem.removeItem(m['summary_text'])
                self.line_markers.remove(m)
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
                    'y_vals': y_vals
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
                    'y_vals': y_vals
                }
                self.difference_items.append(diff_dict)

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
        self.spin_x.setMinimumWidth(120)
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
        self.spin_y.setMinimumWidth(120)
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
        self.spin_z.setMinimumWidth(120)
        self.spin_z.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.checkbox_logz = QCheckBox("LogZ")

        # Clear markers / update graph when changing axes
        self.combo_x.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.combo_y.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.combo_z.currentIndexChanged.connect(self.on_axis_selection_changed)

        self.controls_layout.addWidget(self.label_x, 1, 0)
        self.controls_layout.addWidget(self.combo_x, 1, 1)
        self.controls_layout.addWidget(self.spin_x, 1, 2)
        self.controls_layout.addWidget(self.checkbox_logx, 1, 3)

        self.controls_layout.addWidget(self.label_y, 2, 0)
        self.controls_layout.addWidget(self.combo_y, 2, 1)
        self.controls_layout.addWidget(self.spin_y, 2, 2)
        self.controls_layout.addWidget(self.checkbox_logy, 2, 3)

        self.controls_layout.addWidget(self.label_z, 3, 0)
        self.controls_layout.addWidget(self.combo_z, 3, 1)
        self.controls_layout.addWidget(self.spin_z, 3, 2)
        self.controls_layout.addWidget(self.checkbox_logz, 3, 3)

        # Set column stretch factors
        # Make the spinner column stretch (absorb extra space) while other columns remain tight
        self.controls_layout.setColumnStretch(0, 0)
        self.controls_layout.setColumnStretch(1, 0)
        self.controls_layout.setColumnStretch(2, 1) # Spinner column expands
        self.controls_layout.setColumnStretch(3, 0)

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

        try:
            self.gl_widget = gl.GLViewWidget()
            self.gl_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            try:
                self.gl_widget.opts['distance'] = 40
            except Exception:
                pass
            self.gl_widget.setVisible(False)
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

        self.checkbox_3d.stateChanged.connect(self._update_z_controls_state)
        self._update_z_controls_state()

        # Ensure combo boxes and visibility reflect the current radio selection
        self.update_combobox_items()

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

                    equation_solver = ROAREquationSolver(top_level_app=self.top_level_app)
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
                        if not self.is_device_params_mode and getattr(self, 'checkbox_3d', None) is not None and self.checkbox_3d.isChecked():
                            param3 = self.combo_z.currentText()
                            results_3d = None
                            try:
                                result_matrix_3d = equation_solver.evaluate_equations(symbols_to_add=[param1, param2, param3], corner_dfs=[cid_corner.df])
                                if result_matrix_3d is not None and param1 in result_matrix_3d and param2 in result_matrix_3d and param3 in result_matrix_3d:
                                    p1 = np.asarray(result_matrix_3d[param1]).ravel()
                                    p2 = np.asarray(result_matrix_3d[param2]).ravel()
                                    p3 = np.asarray(result_matrix_3d[param3]).ravel()
                                    results_3d = (p1, p2, p3)
                            except Exception:
                                results_3d = None

                            if results_3d and self.gl_widget is not None:
                                try:
                                    self.plot_widget.hide()
                                except Exception:
                                    pass
                                try:
                                    self.gl_widget.setVisible(True)
                                except Exception:
                                    pass

                                try:
                                    for item in list(self.gl_items):
                                        try:
                                            if self.gl_widget is not None:
                                                self.gl_widget.removeItem(item)
                                        except Exception:
                                            pass
                                    self.gl_items = []
                                except Exception:
                                    self.gl_items = []

                                p1, p2, p3 = results_3d
                                try:
                                    pts = np.vstack((p1, p2, p3)).T.astype(float)
                                    scatter = gl.GLScatterPlotItem(pos=pts, size=3, color=(1.0, 0.5, 0.0, 1.0), pxMode=False)
                                    if self.gl_widget is not None:
                                        self.gl_widget.addItem(scatter)
                                        self.gl_items.append(scatter)
                                except Exception as e:
                                    msg = f"3D plotting error: {e}"
                                    print(msg)
                                    try:
                                        if self.top_level_app and hasattr(self.top_level_app, 'statusBar'):
                                            self.top_level_app.statusBar().showMessage(msg, 5000)
                                    except Exception:
                                        pass
                                new_plot = False
                                continue

                        try:
                            if self.gl_widget is not None:
                                for item in list(self.gl_items):
                                    try:
                                        self.gl_widget.removeItem(item)
                                    except Exception:
                                        pass
                                self.gl_items = []
                                self.gl_widget.setVisible(False)
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
        finally:
            self._is_updating = False
        return 0

    def add_tech_luts(self, dirname, pdk_name):
        self.tech_browser.add_tech_luts(dirname=dirname, pdk_name=pdk_name)


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
        self.lookup_window_2 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_window_3 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)
        self.lookup_window_4 = ROARLookupWindow(parent=self, expand_callback=None, top_level_app=self.top_level_app, graph_grid=self)

        self.lookup_windows.extend([self.lookup_window_1, self.lookup_window_2, self.lookup_window_3, self.lookup_window_4])

        self.top_splitter.addWidget(self.lookup_window_1)
        self.top_splitter.addWidget(self.lookup_window_2)

        self.bottom_splitter.addWidget(self.lookup_window_3)
        self.bottom_splitter.addWidget(self.lookup_window_4)

        self.grid_splitter.addWidget(self.top_splitter)
        self.grid_splitter.setStretchFactor(0, 1)
        self.grid_splitter.addWidget(self.bottom_splitter)
        self.grid_splitter.setStretchFactor(1, 1)

        layout.addWidget(self.grid_splitter)

    def add_tech_luts(self, dirname, pdk_name):
        for lookup_window in self.lookup_windows:
            try:
                lookup_window.add_tech_luts(dirname=dirname, pdk_name=pdk_name)
            except Exception:
                pass

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

