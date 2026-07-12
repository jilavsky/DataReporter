# Changelog

## [0.2.0] - 2026-07-12

Complete rebuild of the pipeline core.

### Added
- Parallel plot rendering (`ProcessPoolExecutor`, all cores minus one); a
  full month of data renders in minutes instead of running serially.
- Deterministic dataset-to-image mapping via path hashes (replaces fragile
  filename matching and the broken data-array cache keys).
- ASCII data export (`Q I Idev` with commented metadata header), one `.dat`
  per dataset.
- Regex selection in GUI, CLI (`--select`), and API.
- Output modes: `source` (next to the data), `mirror` (reproduce tree under
  an output folder), `flat`.
- Scopes: per data set, per technique, per sample, per user.
- Datasets-per-graph overlays (1/3/5/10) with legends, per-technique plot
  styles (`PLOT_STYLES`), WAXS plotted on linear Q.
- Extensible high-level metadata table (`METADATA_KEYS` in `core/nexus.py`).
- Public scripting API (`datareporter.api`) shared by GUI and CLI.
- GUI: live progress bar, working Cancel, tri-state tree checkboxes,
  error summary dialog; generation runs in a background thread.
- Fallback to raw `QRS_data`/`Blank_data` arrays for files without a
  reduced SASdata group (e.g. blanks).
- Test suite with a synthetic NXcanSAS tree + smoke test on repo data.

### Removed
- CSV export.
- `core/reporter.py`, `core/report_orchestrator.py`, `io/` package
  (replaced by `core/pipeline.py`, `render/`, `writers/`).

### Fixed
- Reports generated from a fast scan no longer come out empty (image cache
  previously collapsed on identical hashes of empty data arrays).
- USAXS files: desmeared SASentry is used; slit-smeared `_SMR` is skipped.
- GUI no longer freezes during generation.

## [0.1.0] - 2026-07-05

### Added
- Initial working GUI with folder selection, scan tree with checkboxes, scope selection, and format toggles.
- Scanner that walks arbitrary folder depths and extracts `month`, `user`, `sample`, and `technique` by counting folder levels from the deepest.
- NXcanSAS-aware data extraction using `canSAS_class = "SASdata"` attribute lookup.
- Report generation:
  - Multi-page landscape PDFs with 2×3 image grids.
  - Obsidian-compatible Markdown reports with `Attachments/` folders.
  - Flat CSV/TSV exports with configurable delimiter.
- Grep filter, Remove Blanks, and Only Blanks buttons.
- Red/green status bar indicator during long operations.
- Settings persistence in `~/.datareporter/settings.json`.
- Separate remembered paths for input and output folder dialogs.
- CLI entry point with multi-format and scope support.

### Changed
- PDF writer now produces single multi-page files instead of `_01`, `_02` fragments.

### Notes
- First usable development release.
