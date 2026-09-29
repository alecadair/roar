"""Per-instance tech browsers for Design Equations mode.

In Design Eqs mode each instance in the instance table can carry its own LUT
corner selection.  This module presents those selections as a tab per instance
alongside the window's existing Global browser, and lets several instances be
linked so they always share one corner set.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QCheckBox, QLabel,
    QMenu, QDialog, QPushButton, QListWidget, QListWidgetItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer

try:
    from .roar_gui import ROARTechBrowser
except Exception:  # pragma: no cover - import style depends on launcher
    from roar_gui import ROARTechBrowser


GLOBAL_TAB_LABEL = "Global"


def corner_info_from_paths(paths):
    """Convert tech-browser paths into the instance table's corner records.

    Paths look like ``PDK>pdk>model>length>corner``.
    """
    corner_info = []
    for path in paths:
        parts = path.split(">")
        if len(parts) >= 5:
            corner_info.append({
                "name": parts[4],
                "path": path,
                "pdk": parts[1],
                "model": parts[2],
                "length": parts[3],
            })
        elif parts:
            corner_info.append({
                "name": parts[-1],
                "path": path,
                "pdk": None,
                "model": None,
                "length": None,
            })
    return corner_info


class InstanceCornerBrowser(QWidget):
    """A tech browser bound to one instance's corner selection."""

    def __init__(self, instance_name, top_level_app, tech_dict, owner_tabs, parent=None):
        super().__init__(parent)
        self.instance_name = instance_name
        self.top_level_app = top_level_app
        self._owner_tabs = owner_tabs
        self._applying = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        header = QHBoxLayout()
        self.global_check = QCheckBox("Use global corners")
        self.global_check.setToolTip(
            "When checked this instance follows the Global tab's corner selection.")
        self.global_check.toggled.connect(self._on_global_toggled)
        header.addWidget(self.global_check)
        header.addStretch()
        self.link_label = QLabel("")
        self.link_label.setStyleSheet("color: #888;")
        header.addWidget(self.link_label)
        layout.addLayout(header)

        # lookup_window=None keeps check changes from driving a graph redraw
        # directly; the owning tab widget decides when to refresh.
        self.browser = ROARTechBrowser(
            self, lookup_window=None, top_level_app=top_level_app, tech_dict=tech_dict)
        try:
            self.browser.populate_from_tech_dict()
        except Exception:
            pass
        self.browser.startup = False
        layout.addWidget(self.browser)

        self.browser.tree.itemChanged.connect(self._on_item_changed)

    # -- instance table <-> browser ------------------------------------

    def load_from_instance(self, corner_info):
        """Mirror the instance's stored corner selection into the tree."""
        self._applying = True
        try:
            use_global = corner_info is None
            self.global_check.blockSignals(True)
            self.global_check.setChecked(use_global)
            self.global_check.blockSignals(False)
            self.browser.setEnabled(not use_global)

            target_paths = set()
            if corner_info:
                for entry in corner_info:
                    if isinstance(entry, dict) and entry.get("path"):
                        target_paths.add(entry["path"])

            tree = self.browser.tree
            tree.blockSignals(True)
            try:
                self._apply_checks(tree.invisibleRootItem(), target_paths)
            finally:
                tree.blockSignals(False)
        finally:
            self._applying = False

    def _apply_checks(self, parent_item, target_paths):
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.childCount() == 0:
                path = self.browser.build_full_path(child)
                child.setCheckState(
                    0, Qt.CheckState.Checked if path in target_paths
                    else Qt.CheckState.Unchecked)
            else:
                self._apply_checks(child, target_paths)

    def checked_paths(self):
        try:
            return list(self.browser.get_checked_item_paths())
        except Exception:
            return []

    def apply_paths(self, paths):
        """Set the tree to exactly *paths* without emitting change notifications."""
        self._applying = True
        try:
            tree = self.browser.tree
            tree.blockSignals(True)
            try:
                self._apply_checks(tree.invisibleRootItem(), set(paths))
            finally:
                tree.blockSignals(False)
        finally:
            self._applying = False

    # -- signals --------------------------------------------------------

    def _on_global_toggled(self, checked):
        if self._applying:
            return
        self.browser.setEnabled(not checked)
        self._owner_tabs.on_browser_changed(self)

    def _on_item_changed(self, *_args):
        if self._applying:
            return
        self._owner_tabs.on_browser_changed(self)

    def current_corner_info(self):
        """None means 'use global', otherwise the explicit corner records."""
        if self.global_check.isChecked():
            return None
        return corner_info_from_paths(self.checked_paths())

    def set_link_text(self, text):
        self.link_label.setText(text)


class LinkInstancesDialog(QDialog):
    """Pick which instances share a corner selection with *source*."""

    def __init__(self, parent, source_name, candidates, already_linked):
        super().__init__(parent)
        self.setWindowTitle(f"Link corners with {source_name}")
        self.setMinimumWidth(260)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Instances linked to <b>{source_name}</b> share one corner selection."))

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for name in candidates:
            entry = QListWidgetItem(name)
            entry.setFlags(entry.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            entry.setCheckState(
                Qt.CheckState.Checked if name in already_linked
                else Qt.CheckState.Unchecked)
            self.list_widget.addItem(entry)
        layout.addWidget(self.list_widget)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Apply")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def selected_names(self):
        names = []
        for i in range(self.list_widget.count()):
            entry = self.list_widget.item(i)
            if entry.checkState() == Qt.CheckState.Checked:
                names.append(entry.text())
        return names


class InstanceBrowserTabs(QTabWidget):
    """Global tech browser plus one tab per instance in Design Eqs mode."""

    def __init__(self, lookup_window, parent=None):
        super().__init__(parent)
        self.lookup_window = lookup_window
        self._instance_browsers = {}   # instance name -> InstanceCornerBrowser
        self._link_groups = []         # list of sets of instance names
        self._syncing = False
        self._pending_refresh = False

        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setDocumentMode(True)
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)

    # -- setup ----------------------------------------------------------

    def set_global_browser(self, browser):
        self.addTab(browser, GLOBAL_TAB_LABEL)

    def _tech_dict(self):
        app = getattr(self.lookup_window, 'top_level_app', None)
        return getattr(app, 'tech_dict', None) if app is not None else None

    def _instance_table(self):
        app = getattr(self.lookup_window, 'top_level_app', None)
        editor = getattr(app, 'editor_window', None) if app is not None else None
        return getattr(editor, 'instance_table', None) if editor is not None else None

    # -- tab lifecycle ---------------------------------------------------

    def set_instance_tabs_enabled(self, enabled):
        """Design Eqs mode shows the per-instance tabs; Device Params hides them."""
        self.tabBar().setVisible(enabled)
        if enabled:
            self.rebuild_instance_tabs()
        else:
            self._remove_instance_tabs()
            self.setCurrentIndex(0)

    def _remove_instance_tabs(self):
        for index in range(self.count() - 1, 0, -1):
            widget = self.widget(index)
            self.removeTab(index)
            widget.deleteLater()
        self._instance_browsers.clear()

    def rebuild_instance_tabs(self):
        table = self._instance_table()
        if table is None:
            return

        try:
            names = [n for n in table.get_instance_names()]
        except Exception:
            return

        # Drop tabs for instances that no longer exist.
        for name in list(self._instance_browsers):
            if name not in names:
                widget = self._instance_browsers.pop(name)
                index = self.indexOf(widget)
                if index >= 0:
                    self.removeTab(index)
                widget.deleteLater()
                self._forget_instance(name)

        tech_dict = self._tech_dict()
        app = getattr(self.lookup_window, 'top_level_app', None)

        for name in names:
            browser = self._instance_browsers.get(name)
            if browser is None:
                browser = InstanceCornerBrowser(name, app, tech_dict, self)
                self._instance_browsers[name] = browser
                self.addTab(browser, name)
            browser.load_from_instance(self._corner_info_for(name))

        self._refresh_tab_labels()

    def _corner_info_for(self, instance_name):
        table = self._instance_table()
        if table is None or table.corners_column_index < 0:
            return None
        item = table.find_instance_item(instance_name)
        if item is None:
            return None
        return item.data(table.corners_column_index, Qt.ItemDataRole.UserRole)

    # -- change propagation ---------------------------------------------

    def on_browser_changed(self, source):
        """Write a tab's selection back to the instance table and its link group."""
        if self._syncing:
            return
        self._syncing = True
        try:
            table = self._instance_table()
            if table is None:
                return

            corner_info = source.current_corner_info()
            self._write_corners(table, source.instance_name, corner_info)

            group = self._group_for(source.instance_name)
            if group:
                paths = source.checked_paths()
                use_global = source.global_check.isChecked()
                for name in group:
                    if name == source.instance_name:
                        continue
                    peer = self._instance_browsers.get(name)
                    if peer is None:
                        continue
                    peer.global_check.blockSignals(True)
                    peer.global_check.setChecked(use_global)
                    peer.global_check.blockSignals(False)
                    peer.browser.setEnabled(not use_global)
                    peer.apply_paths(paths)
                    self._write_corners(table, name, peer.current_corner_info())
        finally:
            self._syncing = False

        self._schedule_graph_refresh()

    @staticmethod
    def _write_corners(table, instance_name, corner_info):
        item = table.find_instance_item(instance_name)
        if item is not None:
            table.update_corners_display(item, corner_info)

    def _schedule_graph_refresh(self):
        if self._pending_refresh:
            return
        self._pending_refresh = True

        def run():
            self._pending_refresh = False
            try:
                self.lookup_window.update_graph_from_tech_browser()
            except Exception:
                pass

        QTimer.singleShot(0, run)

    # -- link groups ------------------------------------------------------

    def _group_for(self, instance_name):
        for group in self._link_groups:
            if instance_name in group:
                return group
        return None

    def _forget_instance(self, instance_name):
        for group in list(self._link_groups):
            group.discard(instance_name)
            if len(group) < 2:
                self._link_groups.remove(group)

    def _on_tab_context_menu(self, pos):
        index = self.tabBar().tabAt(pos)
        if index <= 0:  # tab 0 is the Global browser
            return
        widget = self.widget(index)
        if not isinstance(widget, InstanceCornerBrowser):
            return

        menu = QMenu()
        link_action = menu.addAction("Link corners with…")
        group = self._group_for(widget.instance_name)
        unlink_action = menu.addAction("Unlink") if group else None

        chosen = menu.exec(self.tabBar().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == link_action:
            self._prompt_link(widget)
        elif unlink_action is not None and chosen == unlink_action:
            self._forget_instance(widget.instance_name)
            self._refresh_tab_labels()

    def _prompt_link(self, source):
        candidates = [n for n in self._instance_browsers if n != source.instance_name]
        if not candidates:
            return
        group = self._group_for(source.instance_name) or set()
        already = {n for n in group if n != source.instance_name}

        dialog = LinkInstancesDialog(self, source.instance_name, candidates, already)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        chosen = set(dialog.selected_names())
        self._forget_instance(source.instance_name)
        for name in chosen:
            self._forget_instance(name)

        if chosen:
            self._link_groups.append({source.instance_name} | chosen)
            # Linking adopts the source tab's selection for the whole group.
            self.on_browser_changed(source)

        self._refresh_tab_labels()

    def _refresh_tab_labels(self):
        labels = {}
        for number, group in enumerate(self._link_groups, start=1):
            for name in group:
                labels[name] = number

        for name, widget in self._instance_browsers.items():
            index = self.indexOf(widget)
            if index < 0:
                continue
            number = labels.get(name)
            if number:
                self.setTabText(index, f"🔗{number} {name}")
                peers = sorted(n for n in self._group_for(name) if n != name)
                widget.set_link_text("linked: " + ", ".join(peers))
                self.setTabToolTip(index, f"Corner selection shared with: {', '.join(peers)}")
            else:
                self.setTabText(index, name)
                widget.set_link_text("")
                self.setTabToolTip(index, "")
