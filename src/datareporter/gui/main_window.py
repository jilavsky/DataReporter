"""Main window for DataReporter GUI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QThread, pyqtSignal
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

from datareporter.core.scanner import NexusRecord, scan_folders
from datareporter.core.reporter import generate_reports
from datareporter.gui.report_options import ReportOptions


class ScannerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, folders: list[str]) -> None:
        super().__init__()
        self.folders = folders

    def run(self) -> None:
        records = scan_folders(self.folders)
        self.finished.emit(records)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DataReporter")
        self.resize(1100, 700)

        self._records: List[NexusRecord] = []
        self._thread: Optional[ScannerThread] = None

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
        pick_output = QPushButton("Select Output...")
        pick_output.clicked.connect(self._pick_output)
        self.generate_btn = QPushButton("Generate Reports")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._generate)

        top_bar.addWidget(QLabel("Input:"))
        top_bar.addWidget(self.input_edit)
        top_bar.addWidget(pick_input)
        top_bar.addWidget(QLabel("Output:"))
        top_bar.addWidget(self.output_edit)
        top_bar.addWidget(pick_output)
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

        splitter.addWidget(tree_container)

        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        self.options = ReportOptions()
        options_layout.addWidget(self.options)
        splitter.addWidget(options_container)

        splitter.setSizes([700, 400])

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _pick_input(self) -> None:
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            paths = dlg.selectedFiles()
            if paths:
                self.input_edit.setText(paths[0])
                self._scan_input(paths[0])

    def _pick_output(self) -> None:
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        if dlg.exec():
            paths = dlg.selectedFiles()
            if paths:
                self.output_edit.setText(paths[0])
                self._update_generate()

    def _scan_input(self, folder: str) -> None:
        self.status.showMessage("Scanning...")
        self.generate_btn.setEnabled(False)
        self._thread = ScannerThread([folder])
        self._thread.finished.connect(lambda records: self._on_scanned(records))
        self._thread.start()

    def _on_scanned(self, records: List[NexusRecord]) -> None:
        self._records = records
        self.tree.clear()
        root = QTreeWidgetItem(self.tree, ["(root)", "", "", ""])
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        month_nodes: dict[str, QTreeWidgetItem] = {}
        for r in records:
            parts = [r.month, r.user, r.sample, r.technique]
            parent = root
            current_path = []
            for idx, part in enumerate(parts):
                if not part:
                    continue
                current_path.append(part)
                key = "/".join(current_path)
                if key in month_nodes:
                    parent = month_nodes[key]
                else:
                    is_file = (idx == len(parts) - 1)
                    node_type = "file" if is_file else ("technique" if idx == 3 else "folder")
                    node = QTreeWidgetItem(parent, [part, node_type, "1", f"{r.size_bytes} B" if is_file else ""])
                    node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    node.setCheckState(0, Qt.CheckState.Checked)
                    node.setData(0, Qt.ItemDataRole.UserRole, str(r.path if is_file else ""))
                    month_nodes[key] = node
                    parent = node

        self.tree.expandToDepth(1)
        self._update_generate()
        self.status.showMessage(f"Found {len(records)} HDF5 file(s)")

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
        self.generate_btn.setEnabled(bool(self.input_edit.text()) and bool(self.output_edit.text()))

    def _generate(self) -> None:
        self.status.showMessage("Generating reports...")
        QApplication.processEvents()

        out_dir = Path(self.output_edit.text())
        settings = self.options.settings()
        try:
            produced = generate_reports(self._records, out_dir, settings)
            self.status.showMessage(f"Generated {len(produced)} report(s) in {out_dir}")
        except Exception as exc:
            self.status.showMessage(f"Error: {exc}")


def _set_checked_recursive(item: QTreeWidgetItem, checked: bool) -> None:
    item.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
    for i in range(item.childCount()):
        _set_checked_recursive(item.child(i), checked)


from PyQt6.QtCore import Qt  # noqa: E402
