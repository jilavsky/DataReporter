# DataReporter

**Version 0.2.0**

DataReporter crawls a tree of instrument-reduced USAXS/SAXS/WAXS data (NXcanSAS
HDF5 files), renders intensity plots in parallel, and produces easy-to-inspect
summaries: **PDF** files, **Markdown for Obsidian** (with an `Attachments/`
image folder), and **ASCII data exports** (`Q I Idev`).

It expects the APS 12-ID USAXS folder layout, but works from any level of it:

```
<YYYY>/<YYYY-MM>/<MM_DD_UserName>/<SampleName>/<SampleName>_<technique>/*.h5
```

where `technique` is `usaxs`, `saxs`, `waxs`, or `usaxs_merged`.

## Installation

```bash
conda env create -f environment.yml     # or: pip install -e .
conda activate datareporter
```

## GUI

```bash
datareporter-gui        # or: python -m datareporter.gui.main_window
```

1. Pick an **Input** folder (any level: month, user, or sample). The tree
   appears immediately — no HDF5 file is opened during scanning.
2. Select files with the checkboxes (parent boxes toggle whole branches), a
   **regex filter** on relative paths, and the blank-handling buttons.
3. Choose the **output scope** (what goes into one file), the **output
   destination**, and the **formats**.
4. **Generate**. Rendering runs on all CPU cores; the progress bar and
   **Cancel** stay live. Errors are summarized at the end without aborting
   the run.

### Scope — how much goes into one output file

| Scope | Result |
|---|---|
| per sample | one file per sample, all techniques inside (typical) |
| per technique folder | one file per `Sample_usaxs`, `Sample_saxs`, … |
| per data set | one small file next to every measurement |
| per user | one big file per user folder |

**Datasets per graph** (1/3/5/10) overlays consecutive curves of the same
technique in a single graph with a legend.

### Output destination

| Mode | Result |
|---|---|
| next to the data | e.g. sample scope adds `SampleName.pdf`, `SampleName.md` + `Attachments/` inside each sample folder — a human-readable summary right beside the HDF5 files |
| mirror | reproduces the input folder structure under a separate output folder — ideal for importing into an Obsidian vault |
| flat | everything directly in the output folder, the path is encoded in the filename (`07_01_User_Sample.pdf`) |

ASCII export writes one `SampleName_ascii/` folder (or a single `.dat` for
dataset scope) at the same location.

## CLI / scripting

```bash
# PDFs next to the data, one per sample, 5 curves per graph
datareporter /data/2026/2026-07 --scope sample --formats pdf --per-graph 5

# Obsidian vault import: markdown, mirrored structure, blanks excluded
datareporter /data/2026/2026-07 --formats md --mode mirror \
    -o ~/Vault/Experiments --blanks exclude

# ASCII export of one user's samples matching a regex
datareporter /data/2026/2026-07 --select '07_01_.*AHM' --formats ascii \
    --mode flat -o ~/export

# Dry run: list what would be included
datareporter /data/2026/2026-07 --select 'CeOx' --list
```

Run `datareporter --help` for all options. The same functionality is available
from Python — suitable for an end-of-cycle batch job:

```python
from datareporter import api

datasets = api.scan("/data/2026/2026-07", select=r"AHM_.*", blanks="exclude")
report = api.generate(datasets, scope="sample", formats=["pdf", "md"],
                      mode="source", per_graph=5)
print(report.summary())
```

## Performance

Scanning never opens HDF5 files (a month with ~6 000 files indexes in
well under a second). Plot rendering — the expensive part — runs in a
process pool using all cores but one; each image maps to its source
datasets by a deterministic hash, and images are shared between the PDF
and Markdown writers so nothing is rendered twice.

## Extending

See [docs/architecture.md](docs/architecture.md). In particular:

* **New metadata item** → add one line to `METADATA_KEYS` in
  `src/datareporter/core/nexus.py`.
* **Plot styling** → `PLOT_STYLES` in `src/datareporter/render/plots.py`.
* **New output format** → add a module under `src/datareporter/writers/`
  and hook it into `core/pipeline.py`.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests build a synthetic NXcanSAS data tree, so they run anywhere; a smoke
test additionally uses the small real files in `data/`.
