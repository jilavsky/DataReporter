# Changelog

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
