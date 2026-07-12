"""Main window for DataReporter GUI."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from datareporter.core.scanner import NexusRecord, scan_folders_fast, list_directory
from datareporter.core.reporter import generate_reports
from datareporter.gui.report_options import ReportOptions
from datareporter.gui.settings import load_settings, save_settings


class ScannerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, folder: str) -> None:
        super().__init__()
        self.folder = folder

    def run(self) -> None:
        records = scan_folders_fast([self.folder])
        self.finished.emit(records)


class DirectoryListerThread(QThread):
    """Fast background directory listing — no HDF5 reads."""
    finished = pyqtSignal(list)

    def __init__(self, path: str) -> None:
        super().__init__()
        self.path = path

    def run(self) -> None:
        entries = list_directory(Path(self.path))
        self.finished.emit(entries)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DataReporter")
        self.resize(1100, 700)

        self._records: List[NexusRecord] = []
        # Active background threads
        self._scan_thread: Optional[ScannerThread] = None
        # Track which nodes have been fully expanded (children loaded)
        self._expanded_nodes: set[int] = set()
        # The root data directory for lazy listing
        self._data_root: Optional[Path] = None
        # Pending scan records waiting to be attached when a folder is expanded
        self._pending_records: List[NexusRecord] = []

        previous = load_settings()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Input folder")
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Output folder")

        pick_input = QPushButton("Select Input...")
        pick_input.clicked.connect(self._pick_input)
        self.pick_output_btn = QPushButton("Select Output...")
        self.pick_output_btn.clicked.connect(self._pick_output)
        self.generate_btn = QPushButton("Generate Reports")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._generate)

        top_bar.addWidget(QLabel("Input:"))
        top_bar.addWidget(self.input_edit)
        top_bar.addWidget(pick_input)
        top_bar.addWidget(QLabel("Output:"))
        top_bar.addWidget(self.output_edit)
        top_bar.addWidget(self.pick_output_btn)
        top_bar.addWidget(self.generate_btn)
        main_layout.addLayout(top_bar)

        splitter = QSplitter()
        main_layout.addWidget(splitter, stretch=1)

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Type", "Files", "Size"])
        self.tree.setColumnWidth(0, 280)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self._on_item_changed)
        tree_layout.addWidget(self.tree)

        btns = QHBoxLayout()
        self.expand_btn = QPushButton("Expand All")
        self.expand_btn.clicked.connect(self.tree.expandAll)
        self.collapse_btn = QPushButton("Collapse All")
        self.collapse_btn.clicked.connect(self.tree.collapseAll)
        self.check_visible_btn = QPushButton("Check Visible")
        self.check_visible_btn.clicked.connect(self._check_visible)
        btns.addWidget(self.expand_btn)
        btns.addWidget(self.collapse_btn)
        btns.addWidget(self.check_visible_btn)
        tree_layout.addLayout(btns)

        filter_bar = QHBoxLayout()
        self.grep_edit = QLineEdit()
        self.grep_edit.setPlaceholderText("Grep filter...")
        filter_btn = QPushButton("Filter")
        filter_btn.clicked.connect(self._apply_filter)
        self.remove_blanks_btn = QPushButton("Remove Blanks")
        self.remove_blanks_btn.clicked.connect(self._remove_blanks)
        self.only_blanks_btn = QPushButton("Only Blanks")
        self.only_blanks_btn.clicked.connect(self._only_blanks)
        filter_bar.addWidget(QLabel("Filter:"))
        filter_bar.addWidget(self.grep_edit)
        filter_bar.addWidget(filter_btn)
        filter_bar.addWidget(self.remove_blanks_btn)
        filter_bar.addWidget(self.only_blanks_btn)
        tree_layout.addLayout(filter_bar)

        splitter.addWidget(tree_container)

        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        self.options = ReportOptions()
        options_layout.addWidget(self.options)
        splitter.addWidget(options_container)

        splitter.setSizes([700, 400])

        self.status = QStatusBar()
        self._status_label = QLabel("Ready")
        self.status.addPermanentWidget(self._status_label)
        self.setStatusBar(self.status)

        if previous.get("last_input_dir"):
            self.input_edit.setText(previous["last_input_dir"])
        if previous.get("last_output_dir"):
            self.output_edit.setText(previous["last_output_dir"])

        # Restore persisted report options
        self.options.scope_combo.setCurrentText(previous.get("scope", "sample"))
        self.options.mirror_check.setChecked(previous.get("mirror", False))
        self.options.add_to_source_check.setChecked(previous.get("add_to_source", False))
        self.options.datasets_spin.setValue(previous.get("datasets_per_graph", 1))

        # Restore format checkboxes
        saved_formats = previous.get("formats", ["pdf", "obsidian", "csv"])
        self.options.pdf_check.setChecked("pdf" in saved_formats)
        self.options.md_check.setChecked("obsidian" in saved_formats)
        self.options.csv_check.setChecked("csv" in saved_formats)

        # Restore PDF grid settings
        pdf_grid = previous.get("pdf_grid")
        if isinstance(pdf_grid, tuple):
            rows, cols = pdf_grid
        elif isinstance(pdf_grid, str) and "x" in pdf_grid:
            try:
                r_str, c_str = pdf_grid.split("x", 1)
                rows, cols = int(r_str), int(c_str)
            except ValueError:
                rows, cols = 2, 3
        else:
            rows, cols = 2, 3
        self.options.grid_rows_spin.setValue(rows)
        self.options.grid_cols_spin.setValue(cols)

        # Restore remaining checkboxes
        self.options.pdf_meta_check.setChecked(previous.get("pdf_metadata_summary", True))
        self.options.md_attach_check.setChecked(previous.get("obsidian_attachments", True))
        csv_delim = previous.get("csv_delimiter", ",")
        self.options.csv_delim_combo.setCurrentText("\t" if csv_delim == "\t" else ",")

        self._last_input_dir = previous.get("last_input_dir", "")
        self._last_output_dir = previous.get("last_output_dir", "")

        # Wire add_to_source checkbox to disable output path controls
        self.options.add_to_source_check.toggled.connect(self._on_add_to_source_toggled)

    def _pick_input(self) -> None:
        start = self._last_input_dir or str(Path.home())
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setDirectory(start)
        if dlg.exec():
            paths = dlg.selectedFiles()
            if paths:
                self._last_input_dir = paths[0]
                self.input_edit.setText(paths[0])
                self._load_top_level(paths[0])

    def _pick_output(self) -> None:
        start = self._last_output_dir or str(Path.home())
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setDirectory(start)
        if dlg.exec():
            paths = dlg.selectedFiles()
            if paths:
                self._last_output_dir = paths[0]
                self.output_edit.setText(paths[0])
                self._update_generate()

    def _load_top_level(self, folder: str) -> None:
        """Show top-level folders immediately via fast directory listing.

        Then scan in the background so records are available when folders are expanded.
        """
        self._set_working("Loading...")
        self.generate_btn.setEnabled(False)
        self.tree.clear()
        self._expanded_nodes.clear()
        self._pending_records = []

        root = QTreeWidgetItem(self.tree, ["(root)", "", "", ""])
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        # Fast synchronous directory listing — no HDF5 reads, no recursion into subfolders
        entries = list_directory(Path(folder))
        self._data_root = Path(folder)

        for entry in entries:
            node = QTreeWidgetItem(root, [entry["name"], "folder", "", f"{entry['size_bytes']} B"])
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, Qt.CheckState.Checked)
            node.setData(0, Qt.ItemDataRole.UserRole, str(Path(folder) / entry["name"]))

        # Connect expand handler for lazy loading of subdirectories
        self.tree.itemExpanded.connect(self._on_item_expanded)

        self._update_generate()
        self._set_done(f"Top-level loaded — scanning in background...")

        # Start background scan to collect full records (HDF5 metadata reads)
        self._scan_thread = ScannerThread(folder)
        self._scan_thread.finished.connect(self._on_scan_finished)
        self._scan_thread.start()

    def _on_scan_finished(self, records: List[NexusRecord]) -> None:
        """Background scan completed — store records and build the full expandable tree."""
        self._records = records
        if not records:
            self._set_done("No HDF5 files found.")
            return
        # Replace placeholder root children with a fully-built folder hierarchy from scanned records.
        self._build_tree_from_records()
        self._expanded_nodes.clear()
        self._pending_records = list(records)
        self._update_generate()
        self._set_done(f"Found {len(records)} HDF5 file(s)")

    def _build_tree_from_records(self) -> None:
        """Build the complete folder hierarchy from scanned records.

        Walks each record's relative path and creates intermediate folder nodes so that
        every level of the data tree is visible and expandable immediately after scanning.
        Folders can contain both subfolders and files as children.
        """
        if not self._data_root or not self._records:
            return
        root = self.tree.invisibleRootItem()
        while root.childCount() > 0:
            root.takeChild(0)

        # Build a nested dict tree where each node stores:
        # {"path": Path, "children": {name: node}, "files": [NexusRecord]}
        tree_root: dict = {}
        for r in self._records:
            rel = r.path.relative_to(self._data_root)
            parts = list(rel.parts)

            # Create folder nodes for all path components except the last (the file).
            node = tree_root
            for i in range(len(parts) - 1):
                part = parts[i]
                if part not in node:
                    node[part] = {"path": self._data_root.joinpath(*parts[:i + 1]), "children": {}, "files": []}
                node = node[part]["children"]

            # The last path component is the file — attach it to its parent folder.
            file_name = parts[-1]
            if file_name not in node:
                node[file_name] = {"path": r.path, "children": {}, "files": [r]}
            else:
                node[file_name]["files"].append(r)

        # Recursively build QTreeWidgetItems from the nested dict.
        self._build_nodes_recursive(root, tree_root)

    def _build_nodes_recursive(self, parent: QTreeWidgetItem, tree_node: dict) -> None:
        """Recursively create QTreeWidgetItem children from a nested folder-tree dict."""
        for name in sorted(tree_node.keys()):
            info = tree_node[name]
            if info["files"]:
                # File node — show the first record's details (all records at this path are identical).
                r = info["files"][0]
                child = QTreeWidgetItem(parent, [r.filename, "file", "1", self._format_size(r.size_bytes)])
            else:
                # Folder node — aggregate counts and sizes from all descendant files.
                folder_records = []
                self._collect_files(info, folder_records)
                total_size = sum(r.size_bytes for r in folder_records)
                child = QTreeWidgetItem(parent, [name, "folder", str(len(folder_records)), self._format_size(total_size)])
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            child.setCheckState(0, Qt.CheckState.Checked)
            child.setData(0, Qt.ItemDataRole.UserRole, str(info["path"]))

    def _collect_files(self, node: dict, out: list) -> None:
        """Recursively collect all files from a subtree."""
        for name, info in node.items():
            out.extend(info["files"])
            self._collect_files(info["children"], out)

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes into human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """When a folder is expanded, load its children lazily."""
        node_id = id(item)
        if node_id in self._expanded_nodes:
            return  # Already loaded

        path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not path_str or not self._data_root:
            return

        path = Path(path_str)

        # If we have pending records from the background scan, try to use them first
        if self._pending_records:
            folder_records = [r for r in self._pending_records if str(r.path).startswith(str(path))]
            if folder_records:
                self._build_children_from_records(item, path, folder_records)
                self._expanded_nodes.add(node_id)
                # Remove records we just used so they don't leak to sibling folders
                self._pending_records = [r for r in self._pending_records if not str(r.path).startswith(str(path))]
                return

        # Fall back to fast directory listing (no HDF5 reads)
        entries = list_directory(path)
        self._expanded_nodes.add(node_id)
        self._build_children_from_entries(item, path, entries)

    def _build_children_from_records(self, parent: QTreeWidgetItem, path: Path, records: List[NexusRecord]) -> None:
        """Build child nodes from pre-scanned NexusRecords (has full metadata)."""
        while parent.childCount() > 0:
            parent.takeChild(0)

        # Group by next level folder name
        sub_groups: dict[str, list[NexusRecord]] = {}
        for r in records:
            rel = r.path.relative_to(path)
            parts = [p for p in rel.parts if p]
            key = parts[0] if len(parts) > 1 else r.technique or r.sample or r.user or "files"
            sub_groups.setdefault(key, []).append(r)

        for folder_name, sub_records in sorted(sub_groups.items()):
            total_size = sum(r.size_bytes for r in sub_records)
            child = QTreeWidgetItem(parent, [folder_name, "folder", str(len(sub_records)), self._format_size(total_size)])
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            child.setCheckState(0, Qt.CheckState.Checked)
            child.setData(0, Qt.ItemDataRole.UserRole, str(path / folder_name))

    def _build_children_from_entries(self, parent: QTreeWidgetItem, path: Path, entries: list[dict]) -> None:
        """Build child nodes from fast directory listing (no HDF5 metadata)."""
        while parent.childCount() > 0:
            parent.takeChild(0)

        for entry in entries:
            if entry["type"] == "folder":
                file_count = entry.get("_file_count", "")
                child = QTreeWidgetItem(parent, [entry["name"], "folder", str(file_count) if file_count else "", f"{entry['size_bytes']} B"])
            else:
                child = QTreeWidgetItem(parent, [entry["name"], "file", "1", f"{entry['size_bytes']} B"])
            child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            child.setCheckState(0, Qt.CheckState.Checked)
            child.setData(0, Qt.ItemDataRole.UserRole, str(path / entry["name"]))

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 0:
            return
        state = item.checkState(0)
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)

    def _check_visible(self) -> None:
        root = self.tree.invisibleRootItem()
        _set_checked_recursive(root, True)

    def _update_generate(self) -> None:
        has_input = bool(self.input_edit.text())
        # When add_to_source is checked, output path is not needed
        if self.options.add_to_source_check.isChecked():
            self.generate_btn.setEnabled(has_input)
        else:
            self.generate_btn.setEnabled(has_input and bool(self.output_edit.text()))

    def _on_add_to_source_toggled(self, checked: bool) -> None:
        """Disable output path controls when add_to_source is active."""
        self.output_edit.setEnabled(not checked)
        self.pick_output_btn.setEnabled(not checked)

    def _set_working(self, text: str) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet("background-color: red; color: white; font-weight: bold; padding: 3px;")
        self.status.repaint()

    def _set_done(self, text: str) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet("background-color: green; color: white; padding: 3px;")
        self.status.repaint()

    def _apply_filter(self) -> None:
        pattern = self.grep_edit.text().strip().lower()
        if not pattern:
            return
        root = self.tree.invisibleRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item.childCount() == 0:
                text = item.text(0).lower()
                item.setCheckState(0, Qt.CheckState.Checked if pattern in text else Qt.CheckState.Unchecked)
            stack.extend(item.child(i) for i in range(item.childCount()))

    def _remove_blanks(self) -> None:
        root = self.tree.invisibleRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item.childCount() == 0:
                text = item.text(0).lower()
                item.setCheckState(0, Qt.CheckState.Unchecked if "blank" in text else item.checkState(0))
            stack.extend(item.child(i) for i in range(item.childCount()))

    def _only_blanks(self) -> None:
        root = self.tree.invisibleRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item.childCount() == 0:
                text = item.text(0).lower()
                item.setCheckState(0, Qt.CheckState.Checked if "blank" in text else Qt.CheckState.Unchecked)
            stack.extend(item.child(i) for i in range(item.childCount()))

    def _checked_records(self) -> List[NexusRecord]:
        checked_paths = set()
        root = self.tree.invisibleRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item.checkState(0) == Qt.CheckState.Checked:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                if path:
                    checked_paths.add(path)
            stack.extend(item.child(i) for i in range(item.childCount()))
        return [r for r in self._records if str(r.path) in checked_paths]

    def _generate(self) -> None:
        self._set_working("Generating reports...")
        QApplication.processEvents()

        out_dir = Path(self.output_edit.text()) if not self.options.add_to_source_check.isChecked() else None
        settings = self.options.settings()
        input_root = Path(self.input_edit.text()) if self.input_edit.text() else None
        try:
            # Pass the full settings dict so all options (mirror, add_to_source,
            # datasets_per_graph, grid, etc.) flow through to the orchestrator.
            produced = generate_reports(
                self._checked_records(),
                out_dir or Path("."),  # placeholder when add_to_source is active
                fmt="all",  # formats are already in settings["formats"]
                scope=settings["scope"],
                settings=settings,
                input_root=input_root,
            )
            if self.options.add_to_source_check.isChecked():
                self._set_done(f"Generated {len(produced)} report(s) into input location")
            else:
                self._set_done(f"Generated {len(produced)} report(s) in {out_dir}")
        except Exception as exc:
            self.status.showMessage(f"Error: {exc}")

    def closeEvent(self, event) -> None:
        opts = self.options.settings()
        save_settings({
            "last_input_dir": self._last_input_dir,
            "last_output_dir": self._last_output_dir,
            **opts,
        })
        super().closeEvent(event)


def _set_checked_recursive(item: QTreeWidgetItem, checked: bool) -> None:
    item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    for i in range(item.childCount()):
        _set_checked_recursive(item.child(i), checked)


def launch() -> None:
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
