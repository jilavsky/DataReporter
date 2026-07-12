"""Report options widget for the GUI."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ReportOptions(QWidget):
    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)

        # ── Scope Group (what goes together in a single output file) ──────────
        scope_group = QGroupBox("Scope")
        scope_layout = QVBoxLayout(scope_group)
        self.scope_combo = QComboBox()
        # Standard scopes group by a single level of the data hierarchy
        self.scope_combo.addItems([
            "sample", "user", "month", "technique", "file",
        ])
        scope_layout.addWidget(self.scope_combo)

        # Datasets-per-graph selector (only relevant for multi-file scopes)
        graph_row = QHBoxLayout()
        graph_row.addWidget(QLabel("Datasets per graph:"))
        self.datasets_spin = QSpinBox()
        self.datasets_spin.setRange(1, 10)
        self.datasets_spin.setSingleStep(2)
        self.datasets_spin.setValue(1)
        self.datasets_spin.setToolTip("Number of datasets to combine into one graph. Requires legend.")
        graph_row.addWidget(self.datasets_spin)
        graph_row.addStretch()
        scope_layout.addLayout(graph_row)

        layout.addWidget(scope_group)

        # ── Output Behavior Group (where output files are placed) ─────────────
        output_behavior_group = QGroupBox("Output Behavior")
        output_behavior_layout = QVBoxLayout(output_behavior_group)

        self.mirror_check = QCheckBox(
            "Mirror paths (reproduce source folder structure in output)"
        )
        self.mirror_check.setChecked(False)
        self.mirror_check.setToolTip(
            "When checked, the relative path from the input root to each group "
            "is reproduced under the user-selected output directory."
        )
        output_behavior_layout.addWidget(self.mirror_check)

        self.add_to_source_check = QCheckBox(
            "Add to source (write output into input location)"
        )
        self.add_to_source_check.setChecked(False)
        self.add_to_source_check.setToolTip(
            "When checked, output files are written directly into the input "
            "data tree at the appropriate group level. The user-selected output "
            "directory is ignored."
        )
        output_behavior_layout.addWidget(self.add_to_source_check)

        layout.addWidget(output_behavior_group)

        # ── Formats Group ─────────────────────────────────────────────────────
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
        # Grid rows/cols for single-dataset layout (ignored when datasets_per_graph > 1)
        grid_row = QHBoxLayout()
        grid_row.addWidget(QLabel("Grid:"))
        self.grid_rows_spin = QSpinBox()
        self.grid_rows_spin.setRange(1, 6)
        self.grid_rows_spin.setValue(2)
        grid_row.addWidget(self.grid_rows_spin)
        grid_row.addWidget(QLabel("x"))
        self.grid_cols_spin = QSpinBox()
        self.grid_cols_spin.setRange(1, 8)
        self.grid_cols_spin.setValue(3)
        grid_row.addWidget(self.grid_cols_spin)
        pdf_layout.addRow(grid_row)
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
            "mirror": self.mirror_check.isChecked(),
            "add_to_source": self.add_to_source_check.isChecked(),
            "formats": self._selected_formats(),
            # Grid layout for single-dataset PDF pages (rows x cols)
            "pdf_grid": (self.grid_rows_spin.value(), self.grid_cols_spin.value()),
            "pdf_metadata_summary": self.pdf_meta_check.isChecked(),
            "obsidian_attachments": self.md_attach_check.isChecked(),
            "obsidian_md_per_technique": False,
            "csv_delimiter": delimiter,
            # How many datasets to combine into one graph (1 = one graph per file)
            "datasets_per_graph": self.datasets_spin.value(),
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
