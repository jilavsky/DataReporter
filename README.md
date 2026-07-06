# DataReporter

**Version 0.1.0**

DataReporter scans folders of scientific instrument data, discovers Nexus HDF5 files, extracts reduced small-angle scattering data, and generates reports in PDF, Obsidian Markdown, and CSV formats.

It is designed for folder layouts like:

```
<root>/YYYY_MM/<nn_nn_UserName>/<sampleName>/<technique>/*.hdf
```

where `technique` is typically one of `USAXS`, `SAXS`, `WAXS`, or `USAXS_merged`.

## Installation

### Conda environment

```bash
conda env create -f environment.yml
conda activate datareporter
```

### Editable install

```bash
pip install -e .
```

## Usage

### GUI

```bash
python -m datareporter.gui.main_window
```

or, if the entry point is installed:

```bash
datareporter-gui
```

1. Select an **Input folder** containing the measurement hierarchy.
2. Select an **Output folder** for reports.
3. Use the tree checkboxes to include/exclude samples or techniques.
4. Choose a **Scope** (`sample`, `technique`, `user`, `month`, or `file`) to control grouping.
5. Select output **Formats**: PDF, Obsidian Markdown, CSV, or any combination.
6. Click **Generate Reports**.

Filtering:
- **Grep filter** — type a substring and click *Filter* to check only matching files.
- **Remove Blanks** — unchecks any file whose name contains `blank` (case-insensitive).
- **Only Blanks** — keeps only files containing `blank`.

### CLI

```bash
python -m datareporter <folder> [--output <dir>] [--format <fmt>] [--scope <scope>]
```

`--format` accepts comma-separated values, e.g. `pdf,csv` or `all`.  
`--scope` accepts `sample`, `technique`, `user`, `month`, or `file`.

## Reports

### PDF
- Landscape A4, multi-page.
- 2×3 image grid per page.
- One PDF per group depending on selected scope.

### Obsidian Markdown
- One `report.md` per group, with an `Attachments/` folder of JPG plots.
- Images are linked with standard Markdown syntax.

### CSV
- Flat table with one row per HDF file.
- Columns include filename, month, user, sample, technique, size, metadata, and data arrays found.

## Data extraction

The scanner uses the NXcanSAS-aware extractor to locate reduced data groups by their `canSAS_class = "SASdata"` attribute, then reads `Q`, `I`, `Idev`, and `Qdev` arrays. Metadata from `entry/Metadata` is included in reports where available.

## Documentation

See the `docs/` folder for more details.
