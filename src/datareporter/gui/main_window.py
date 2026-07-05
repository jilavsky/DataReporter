"""Main window for DataReporter GUI."""

from __future__ import annotations

import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QThread, pyqtSignal

from datareporter.core.scanner import scan_folders
from datareporter.core.reporter import generate_reports


class ScannerThread(QThread):
    finished = pyqtSignal(list)

    def __init__(self, folders: list[str]):
        super().__init__()
        self.folders = folders

    def run(self) -> None:
        records = scan_folders(self.folders)
        self.finished.emit(records)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DataReporter")
        self.setMinimumSize(800, 600)

        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.pick_button = QPushButton("Select Folders...")
        self.pick_button.clicked.connect(self.pick_folders)

        self.run_button = QPushButton("Scan & Report")
        self.run_button.clicked.connect(self.run_scan)
        self.run_button.setEnabled(False)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        layout.addWidget(self.pick_button)
        layout.addWidget(self.run_button)
        layout.addWidget(self.log)
        self.setCentralWidget(widget)

        self._thread: ScannerThread | None = None

    def pick_folders(self) -> None:
        dlg = QFileDialog(self)
        dlg.setFileMode(QFileDialog.FileMode.Directory)
        dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setOption(QFileDialog.Option.ReadOnly, True)
        if dlg.exec():
            self.folders = dlg.selectedFiles()
            self.run_button.setEnabled(bool(self.folders))
            self.log.append(f"Selected: {', '.join(self.folders)}")

    def run_scan(self) -> None:
        if not hasattr(self, "folders") or not self.folders:
            return
        self.run_button.setEnabled(False)
        self.log.append("Scanning...")
        self._thread = ScannerThread(self.folders)
        self._thread.finished.connect(lambda records: self._on_scanned(records))
        self._thread.start()

    def _on_scanned(self, records: list) -> None:
        self.log.append(f"Found {len(records)} HDF5 file(s). Generating reports...")
        out = Path("reports")
        generate_reports(records, out, fmt="all")
        self.log.append(f"Reports written to: {out.resolve()}")
        self.run_button.setEnabled(True)


def launch() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
