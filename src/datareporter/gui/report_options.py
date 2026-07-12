"""Options panel for the DataReporter GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from datareporter.config import ReportConfig

#: (label shown in the GUI, scope value)
_SCOPES = [
    ("One file per sample (all techniques)", "sample"),
    ("One file per technique folder", "technique"),
    ("One file per data set", "dataset"),
    ("One file per user", "user"),
]

#: (label, mode value)
_MODES = [
    ("Next to the data (into the input tree)", "source"),
    ("Separate folder, mirror input structure", "mirror"),
    ("Separate folder, flat", "flat"),
]


class ReportOptions(QWidget):
    """Right-hand panel: scope, output mode, formats, and details."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)

        # ── Scope ──────────────────────────────────────────────────────
        scope_group = QGroupBox("Output scope")
        scope_layout = QFormLayout(scope_group)
        self.scope_combo = QComboBox()
        for label, value in _SCOPES:
            self.scope_combo.addItem(label, value)
        scope_layout.addRow(self.scope_combo)

        self.per_graph_combo = QComboBox()
        for n in (1, 3, 5, 10):
            self.per_graph_combo.addItem(str(n), n)
        self.per_graph_combo.setToolTip(
            "How many datasets are overlaid in one graph (same technique only)."
        )
        scope_layout.addRow("Datasets per graph:", self.per_graph_combo)
        layout.addWidget(scope_group)

        # ── Output destination ────────────────────────────────────────
        mode_group = QGroupBox("Output destination")
        mode_layout = QVBoxLayout(mode_group)
        self.mode_radios: list[QRadioButton] = []
        for label, value in _MODES:
            rb = QRadioButton(label)
            rb.setProperty("mode", value)
            mode_layout.addWidget(rb)
            self.mode_radios.append(rb)
        self.mode_radios[0].setChecked(True)
        layout.addWidget(mode_group)

        # ── Formats ───────────────────────────────────────────────────
        fmt_group = QGroupBox("Formats")
        fmt_layout = QVBoxLayout(fmt_group)
        self.pdf_check = QCheckBox("PDF")
        self.pdf_check.setChecked(True)
        self.md_check = QCheckBox("Markdown for Obsidian (with Attachments/)")
        self.ascii_check = QCheckBox("ASCII data files (Q, I, Idev)")
        for w in (self.pdf_check, self.md_check, self.ascii_check):
            fmt_layout.addWidget(w)
        layout.addWidget(fmt_group)

        # ── Details ───────────────────────────────────────────────────
        detail_group = QGroupBox("Details")
        detail_layout = QFormLayout(detail_group)
        grid_row = QHBoxLayout()
        self.grid_rows_spin = QSpinBox()
        self.grid_rows_spin.setRange(1, 6)
        self.grid_rows_spin.setValue(2)
        self.grid_cols_spin = QSpinBox()
        self.grid_cols_spin.setRange(1, 8)
        self.grid_cols_spin.setValue(3)
        grid_row.addWidget(self.grid_rows_spin)
        grid_row.addWidget(QLabel("×"))
        grid_row.addWidget(self.grid_cols_spin)
        grid_row.addStretch()
        detail_layout.addRow("PDF images per page:", grid_row)
        self.pdf_summary_check = QCheckBox("PDF summary page")
        self.pdf_summary_check.setChecked(True)
        detail_layout.addRow(self.pdf_summary_check)
        self.md_meta_check = QCheckBox("Metadata in Markdown")
        self.md_meta_check.setChecked(True)
        detail_layout.addRow(self.md_meta_check)
        layout.addWidget(detail_group)

        layout.addStretch(1)

    # ── config round-trip ─────────────────────────────────────────────
    def mode(self) -> str:
        for rb in self.mode_radios:
            if rb.isChecked():
                return rb.property("mode")
        return "source"

    def config(self, output_dir: str = "") -> ReportConfig:
        formats = []
        if self.pdf_check.isChecked():
            formats.append("pdf")
        if self.md_check.isChecked():
            formats.append("md")
        if self.ascii_check.isChecked():
            formats.append("ascii")
        return ReportConfig(
            scope=self.scope_combo.currentData(),
            mode=self.mode(),
            output_dir=Path(output_dir) if output_dir else None,
            formats=formats,
            per_graph=self.per_graph_combo.currentData(),
            pdf_grid=(self.grid_rows_spin.value(), self.grid_cols_spin.value()),
            pdf_summary=self.pdf_summary_check.isChecked(),
            md_metadata=self.md_meta_check.isChecked(),
        )

    def to_dict(self) -> dict:
        return {
            "scope": self.scope_combo.currentData(),
            "mode": self.mode(),
            "per_graph": self.per_graph_combo.currentData(),
            "formats": self.config().formats,
            "pdf_grid": [self.grid_rows_spin.value(), self.grid_cols_spin.value()],
            "pdf_summary": self.pdf_summary_check.isChecked(),
            "md_metadata": self.md_meta_check.isChecked(),
        }

    def from_dict(self, d: dict) -> None:
        idx = self.scope_combo.findData(d.get("scope", "sample"))
        if idx >= 0:
            self.scope_combo.setCurrentIndex(idx)
        for rb in self.mode_radios:
            rb.setChecked(rb.property("mode") == d.get("mode", "source"))
        idx = self.per_graph_combo.findData(d.get("per_graph", 1))
        if idx >= 0:
            self.per_graph_combo.setCurrentIndex(idx)
        formats = d.get("formats", ["pdf"])
        self.pdf_check.setChecked("pdf" in formats)
        self.md_check.setChecked("md" in formats)
        self.ascii_check.setChecked("ascii" in formats)
        grid = d.get("pdf_grid", [2, 3])
        if isinstance(grid, (list, tuple)) and len(grid) == 2:
            self.grid_rows_spin.setValue(int(grid[0]))
            self.grid_cols_spin.setValue(int(grid[1]))
        self.pdf_summary_check.setChecked(d.get("pdf_summary", True))
        self.md_meta_check.setChecked(d.get("md_metadata", True))
