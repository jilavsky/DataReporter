"""Report options widget for the GUI."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ReportOptions(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        scope_group = QGroupBox("Scope")
        scope_layout = QVBoxLayout(scope_group)
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["sample", "user", "month", "technique", "file"])
        scope_layout.addWidget(self.scope_combo)
        layout.addWidget(scope_group)

        fmt_group = QGroupBox("Formats")
        fmt_layout = QVBoxLayout(fmt_group)
        self.pdf_check = QCheckBox("PDF")
        self.pdf_check.setChecked(True)
        self.md_check = QCheckBox("Obsidian Markdown")
        self.csv_check = QCheckBox("CSV")
        fmt_layout.addWidget(self.pdf_check)
        fmt_layout.addWidget(self.md_check)
        fmt_layout.addWidget(self.csv_check)
        layout.addWidget(fmt_group)

        pdf_opts = QGroupBox("PDF options")
        pdf_layout = QFormLayout(pdf_opts)
        self.pdf_meta_check = QCheckBox("Include metadata summary")
        self.pdf_meta_check.setChecked(True)
        pdf_layout.addRow(self.pdf_meta_check)
        layout.addWidget(pdf_opts)

        md_opts = QGroupBox("Obsidian options")
        md_layout = QFormLayout(md_opts)
        self.md_attach_check = QCheckBox("Use Attachments/ folder")
        self.md_attach_check.setChecked(True)
        md_layout.addRow(self.md_attach_check)
        layout.addWidget(md_opts)

        csv_opts = QGroupBox("CSV options")
        csv_layout = QFormLayout(csv_opts)
        self.csv_delim_combo = QComboBox()
        self.csv_delim_combo.addItems([",", "tab"])
        csv_layout.addRow("Delimiter:", self.csv_delim_combo)
        layout.addWidget(csv_opts)

        layout.addStretch(1)

    def settings(self) -> dict:
        delimiter = "," if self.csv_delim_combo.currentText() != "tab" else "\t"
        return {
            "scope": self.scope_combo.currentText(),
            "formats": self._selected_formats(),
            "pdf_grid": (2, 3),
            "pdf_metadata_summary": self.pdf_meta_check.isChecked(),
            "obsidian_attachments": self.md_attach_check.isChecked(),
            "obsidian_md_per_technique": False,
            "csv_delimiter": delimiter,
        }

    def _selected_formats(self) -> list[str]:
        formats: list[str] = []
        if self.pdf_check.isChecked():
            formats.append("pdf")
        if self.md_check.isChecked():
            formats.append("obsidian")
        if self.csv_check.isChecked():
            formats.append("csv")
        if not formats:
            formats.append("pdf")
        return formats
