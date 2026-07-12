# DataReporter architecture

## Data flow

```
scan (fast, no HDF5)        core/scanner.py  -> list[Dataset]
  └─ filter (regex/blanks)  core/scanner.py
group by scope              core/grouping.py -> list[Group]
render images (parallel)    render/parallel.py + render/plots.py
  └─ workers read HDF5      core/nexus.py    -> curves + metadata
write documents             writers/{pdf,md}_writer.py
export raw data (parallel)  writers/ascii_writer.py
```

Orchestrated by `core/pipeline.py`; `api.py` is the public entry point that
the GUI (`gui/`), the CLI (`cli.py`), and user scripts all share.

## Modules

| Module | Responsibility |
|---|---|
| `core/model.py` | `Dataset` dataclass; technique inference from folder names |
| `core/scanner.py` | fast `os.walk` indexing, regex/blank filtering — never opens HDF5 |
| `core/nexus.py` | **all** HDF5 access: NXcanSAS `SASdata` discovery (desmeared USAXS preferred over `_SMR`), curve reading, `METADATA_KEYS` table |
| `core/grouping.py` | scope grouping; output path resolution for source/mirror/flat modes |
| `core/pipeline.py` | ties it together; progress + cancel callbacks; per-file errors collected, never fatal |
| `render/plots.py` | matplotlib rendering; `PLOT_STYLES` per technique |
| `render/parallel.py` | `ProcessPoolExecutor`; one task = one PNG; results carry per-dataset metadata back |
| `writers/pdf_writer.py` | grid pages of pre-rendered PNGs |
| `writers/md_writer.py` | Obsidian markdown + `Attachments/` |
| `writers/ascii_writer.py` | `.dat` export (own worker pool — needs raw arrays) |
| `config.py` | `ReportConfig` + settings persistence (`~/.datareporter.json`) |
| `api.py`, `cli.py`, `gui/` | thin user-facing layers over the pipeline |

## Key design decisions

**Scanning is metadata-free.** Classification uses folder names only, anchored
on the technique folder (`*_usaxs` etc.), so any scan-root depth works and the
tree appears instantly even for tens of thousands of files.

**The parallel work unit is one output image.** A render task carries 1–10
`(uid, path)` pairs; the worker opens the HDF5 files, reads curves and
metadata, renders one PNG named after a deterministic hash of the dataset
UIDs. Consequences:

* exact dataset ↔ image mapping (no filename guessing),
* HDF5 files are opened exactly once, in parallel,
* writers are pure assembly and need no HDF5 or matplotlib knowledge,
* metadata rides back with the render result, so documents get it for free.

**Errors are collected, not raised.** A corrupt file produces an error entry
in the final `RunReport` and the run continues.

**Scope and destination are orthogonal.** `group_datasets()` decides *what*
goes together; `resolve_output_dir()` decides *where* it lands. Adding a new
scope or output layout touches only `core/grouping.py`.

## How to extend

* **New metadata item**: add a line to `METADATA_KEYS` in `core/nexus.py`.
  Candidates are tried in order; `@sasentry/...` paths resolve relative to
  the SASentry that holds the plotted data, `@entry/...` from the file root.
* **Plot styling / new technique**: edit `PLOT_STYLES` (and `TECHNIQUES` in
  `core/model.py` for a new folder suffix).
* **New output format**: create `writers/xyz_writer.py` consuming
  `(png_path, caption, dataset info)` items, add the format to
  `config.FORMATS`, and hook it into the assembly loop in
  `core/pipeline.py`; add a checkbox in `gui/report_options.py`.
* **New GUI option**: extend `ReportConfig` (with validation), then map it in
  `ReportOptions.config()/to_dict()/from_dict()`.

## Threading / process model

* GUI: scan and generation run in `QThread`s; the pipeline reports progress
  via callback → Qt signal; Cancel sets a flag polled between images.
* Rendering/ASCII: `ProcessPoolExecutor` with `cpu_count() - 1` workers
  (`workers=1` forces in-process execution — used by tests and debugging).
  Worker functions are module-level, so spawn-based platforms (macOS,
  Windows) work.
