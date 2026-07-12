"""DataReporter main window.

Thin layer over :mod:`datareporter.api`: the tree shows the result of a
fast scan (no HDF5 files are opened), selection is checkboxes plus an
optional regex, and generation runs in a background thread with a
progress bar and a working Cancel button.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from datareporter import api
from datareporter.config import load_settings, save_settings
from datareporter.core.model import Dataset
from datareporter.core.pipeline import RunReport
from datareporter.gui.report_options import ReportOptions

_DATASET_ROLE = Qt.ItemDataRole.UserRole


class ScanThread(QThread):
    """Background fast scan (still sub-second for a month of data)."""

    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, folder: str) -> None:
        super().__init__()
        self._folder = folder

    def run(self) -> None:
        try:
            self.done.emit(api.scan(self._folder))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class GenerateThread(QThread):
    """Runs the pipeline; reports progress and honors cancellation."""

    progress = pyqtSignal(str, int, int)
    done = pyqtSignal(object)   # RunReport
    failed = pyqtSignal(str)

    def __init__(self, datasets: list[Dataset], config, input_root: Path) -> None:
        super().__init__()
        self._datasets = datasets
        self._config = config
        self._input_root = input_root
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            report = api.generate(
                self._datasets,
                config=self._config,
                input_root=self._input_root,
                progress=lambda p, d, t: self.progress.emit(p, d, t),
                cancel=lambda: self._cancelled,
            )
            self.done.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DataReporter")
        self.resize(1150, 720)

        self._datasets: list[Dataset] = []
        self._scan_thread: Optional[ScanThread] = None
        self._gen_thread: Optional[GenerateThread] = None

        settings = load_settings()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ── top bar: folders + actions ─────────────────────────────────
        top = QHBoxLayout()
        self.input_edit = QLineEdit(settings.get("last_input_dir", ""))
        self.input_edit.setPlaceholderText("Input data folder")
        pick_in = QPushButton("Input…")
        pick_in.clicked.connect(self._pick_input)
        self.output_edit = QLineEdit(settings.get("last_output_dir", ""))
        self.output_edit.setPlaceholderText("Output folder (for mirror/flat modes)")
        self.pick_out_btn = QPushButton("Output…")
        self.pick_out_btn.clicked.connect(self._pick_output)
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setEnabled(False)
        self.generate_btn.clicked.connect(self._generate)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        top.addWidget(QLabel("Input:"))
        top.addWidget(self.input_edit, stretch=2)
        top.addWidget(pick_in)
        top.addWidget(QLabel("Output:"))
        top.addWidget(self.output_edit, stretch=2)
        top.addWidget(self.pick_out_btn)
        top.addWidget(self.generate_btn)
        top.addWidget(self.cancel_btn)
        main_layout.addLayout(top)

        # ── splitter: tree | options ───────────────────────────────────
        splitter = QSplitter()
        main_layout.addWidget(splitter, stretch=1)

        tree_box = QWidget()
        tree_layout = QVBoxLayout(tree_box)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Files", "Size"])
        self.tree.setColumnWidth(0, 340)
        self.tree.setAlternatingRowColors(True)
        tree_layout.addWidget(self.tree)

        # filter row
        filt = QHBoxLayout()
        self.regex_edit = QLineEdit()
        self.regex_edit.setPlaceholderText("Regex on relative path, e.g.  AHM_.*usaxs")
        self.regex_edit.returnPressed.connect(self._apply_regex)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_regex)
        filt.addWidget(QLabel("Filter:"))
        filt.addWidget(self.regex_edit, stretch=1)
        filt.addWidget(apply_btn)
        tree_layout.addLayout(filt)

        btns = QHBoxLayout()
        for label, fn in (
            ("Check all", lambda: self._check_all(True)),
            ("Uncheck all", lambda: self._check_all(False)),
            ("Exclude blanks", self._exclude_blanks),
            ("Only blanks", self._only_blanks),
        ):
            b = QPushButton(label)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch()
        tree_layout.addLayout(btns)
        splitter.addWidget(tree_box)

        self.options = ReportOptions()
        self.options.from_dict(settings)
        for rb in self.options.mode_radios:
            rb.toggled.connect(self._update_controls)
        splitter.addWidget(self.options)
        splitter.setSizes([720, 420])

        # ── status bar with progress ───────────────────────────────────
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(320)
        self.progress_bar.setVisible(False)
        self.status.addPermanentWidget(self.progress_bar)
        self.status.showMessage("Select an input folder to scan.")

        if self.input_edit.text():
            self._start_scan(self.input_edit.text())
        self._update_controls()

    # ── folder pickers ─────────────────────────────────────────────────
    def _pick_input(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select input data folder", self.input_edit.text() or str(Path.home()))
        if folder:
            self.input_edit.setText(folder)
            self._start_scan(folder)

    def _pick_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select output folder", self.output_edit.text() or str(Path.home()))
        if folder:
            self.output_edit.setText(folder)
            self._update_controls()

    # ── scanning & tree ────────────────────────────────────────────────
    def _start_scan(self, folder: str) -> None:
        self.status.showMessage(f"Scanning {folder} …")
        self.generate_btn.setEnabled(False)
        self.tree.clear()
        self._scan_thread = ScanThread(folder)
        self._scan_thread.done.connect(self._scan_done)
        self._scan_thread.failed.connect(
            lambda msg: self.status.showMessage(f"Scan failed: {msg}"))
        self._scan_thread.start()

    def _scan_done(self, datasets: list[Dataset]) -> None:
        self._datasets = datasets
        self._build_tree()
        self.status.showMessage(f"Found {len(datasets)} data file(s).")
        self._update_controls()

    def _build_tree(self) -> None:
        """Build the folder tree; file rows carry their Dataset object."""
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        folders: dict[str, QTreeWidgetItem] = {}

        def folder_item(rel: Path) -> QTreeWidgetItem:
            key = str(rel)
            item = folders.get(key)
            if item is not None:
                return item
            parent = self.tree.invisibleRootItem() if str(rel.parent) in ("", ".") \
                else folder_item(rel.parent)
            item = QTreeWidgetItem(parent, [rel.name, "", ""])
            item.setFlags(item.flags()
                          | Qt.ItemFlag.ItemIsUserCheckable
                          | Qt.ItemFlag.ItemIsAutoTristate)
            item.setCheckState(0, Qt.CheckState.Checked)
            folders[key] = item
            return item

        counts: dict[str, int] = {}
        sizes: dict[str, int] = {}
        for d in self._datasets:
            rel = d.rel_path
            parent = folder_item(rel.parent) if str(rel.parent) not in ("", ".") \
                else self.tree.invisibleRootItem()
            item = QTreeWidgetItem(parent, [rel.name, "", _fmt_size(d.size_bytes)])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked)
            item.setData(0, _DATASET_ROLE, d)
            p = rel.parent
            while str(p) not in ("", "."):
                counts[str(p)] = counts.get(str(p), 0) + 1
                sizes[str(p)] = sizes.get(str(p), 0) + d.size_bytes
                p = p.parent

        for key, item in folders.items():
            item.setText(1, str(counts.get(key, 0)))
            item.setText(2, _fmt_size(sizes.get(key, 0)))
        self.tree.setUpdatesEnabled(True)

    # ── selection helpers ──────────────────────────────────────────────
    def _file_items(self) -> list[QTreeWidgetItem]:
        out = []
        stack = [self.tree.invisibleRootItem()]
        while stack:
            it = stack.pop()
            for i in range(it.childCount()):
                child = it.child(i)
                if child.data(0, _DATASET_ROLE) is not None:
                    out.append(child)
                stack.append(child)
        return out

    def _checked_datasets(self) -> list[Dataset]:
        return [it.data(0, _DATASET_ROLE) for it in self._file_items()
                if it.checkState(0) == Qt.CheckState.Checked]

    def _check_all(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for it in self._file_items():
            it.setCheckState(0, state)

    def _apply_regex(self) -> None:
        pattern_text = self.regex_edit.text().strip()
        if not pattern_text:
            return
        try:
            pattern = re.compile(pattern_text, re.IGNORECASE)
        except re.error as exc:
            self.status.showMessage(f"Invalid regex: {exc}")
            return
        n = 0
        for it in self._file_items():
            d: Dataset = it.data(0, _DATASET_ROLE)
            match = bool(pattern.search(str(d.rel_path)))
            it.setCheckState(0, Qt.CheckState.Checked if match else Qt.CheckState.Unchecked)
            n += match
        self.status.showMessage(f"Regex matched {n} file(s).")

    def _exclude_blanks(self) -> None:
        for it in self._file_items():
            if it.data(0, _DATASET_ROLE).is_blank():
                it.setCheckState(0, Qt.CheckState.Unchecked)

    def _only_blanks(self) -> None:
        for it in self._file_items():
            d: Dataset = it.data(0, _DATASET_ROLE)
            it.setCheckState(0, Qt.CheckState.Checked if d.is_blank()
                             else Qt.CheckState.Unchecked)

    # ── generation ─────────────────────────────────────────────────────
    def _update_controls(self) -> None:
        needs_output = self.options.mode() in ("mirror", "flat")
        self.output_edit.setEnabled(needs_output)
        self.pick_out_btn.setEnabled(needs_output)
        ready = bool(self._datasets) and self._gen_thread is None
        if needs_output:
            ready = ready and bool(self.output_edit.text())
        self.generate_btn.setEnabled(ready)

    def _generate(self) -> None:
        datasets = self._checked_datasets()
        if not datasets:
            QMessageBox.information(self, "DataReporter", "No files are checked.")
            return
        config = self.options.config(self.output_edit.text())
        try:
            config.validate()
        except ValueError as exc:
            QMessageBox.warning(self, "DataReporter", str(exc))
            return

        self._gen_thread = GenerateThread(datasets, config, Path(self.input_edit.text()))
        self._gen_thread.progress.connect(self._on_progress)
        self._gen_thread.done.connect(self._on_done)
        self._gen_thread.failed.connect(self._on_failed)
        self.generate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status.showMessage(f"Generating from {len(datasets)} file(s)…")
        self._gen_thread.start()

    def _cancel(self) -> None:
        if self._gen_thread is not None:
            self._gen_thread.cancel()
            self.status.showMessage("Cancelling…")

    def _on_progress(self, phase: str, done: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(done)
        self.status.showMessage(f"{phase}: {done}/{total}")

    def _on_done(self, report: RunReport) -> None:
        self._finish_generation()
        self.status.showMessage(report.summary())
        if report.errors:
            preview = "\n".join(report.errors[:15])
            if len(report.errors) > 15:
                preview += f"\n… and {len(report.errors) - 15} more"
            QMessageBox.warning(self, "Finished with errors",
                                f"{report.summary()}\n\n{preview}")

    def _on_failed(self, msg: str) -> None:
        self._finish_generation()
        self.status.showMessage("Generation failed.")
        QMessageBox.critical(self, "DataReporter", f"Generation failed:\n{msg}")

    def _finish_generation(self) -> None:
        self._gen_thread = None
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self._update_controls()

    # ── persistence ────────────────────────────────────────────────────
    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        settings = self.options.to_dict()
        settings["last_input_dir"] = self.input_edit.text()
        settings["last_output_dir"] = self.output_edit.text()
        save_settings(settings)
        if self._gen_thread is not None:
            self._gen_thread.cancel()
            self._gen_thread.wait(5000)
        super().closeEvent(event)


def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def launch() -> None:
    import sys

    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
