# DataReporter — Rebuild Plan

Goal: reliable, fast, well-documented tool to crawl USAXS/SAXS/WAXS data trees,
render plots, and produce PDF / Obsidian-Markdown / ASCII summaries, driven by a
GUI or a scriptable API/CLI.

## Why rebuild the core

The current pipeline has structural defects that patching won't fix cleanly:

- Image cache keys are an MD5 of `data_arrays`, which are empty after the fast
  scan, so all records collide on one cache key.
- Images are matched back to records by fuzzy filename substrings and by zipping
  sorted directory listings against record lists — order-dependent.
- Two overlapping entry points (`reporter.py`, `report_orchestrator.py`) with
  inconsistent signatures; GUI passes `fmt="all"`, overriding user format choice.
- Report generation runs on the GUI thread; image rendering is strictly serial.
- CSV writer to be removed; no regex selection; no ASCII data export.

Repo layout, GUI shell, and the NXcanSAS discovery logic are kept/reused.

## Decisions (agreed)

- Rebuild core, keep repo.
- Always render plots from HDF5 (ignore instrument JPGs) — consistent styling.
- ASCII export: 3-column `Q  I  Idev` with commented header.
- Per-technique plot styles: USAXS/SAXS/merged log-log; WAXS linear Q, log I.
- Drop CSV entirely.
- Default image format: PNG (crisper line plots, Obsidian-friendly).

## Architecture

```
src/datareporter/
  api.py             # single public entry point: scan(), generate() — GUI & CLI are thin layers
  cli.py             # argparse CLI over api (replaces __main__ logic; __main__.py calls cli.main)
  config.py          # ReportConfig dataclass + JSON persistence (~/.datareporter.json)
  core/
    model.py         # Dataset dataclass: path, root, month, user, sample, technique, size
    scanner.py       # fast os.walk indexing — never opens HDF5; regex + predicate filtering
    nexus.py         # all HDF5 access: read_curves() (Q,I,Idev per NXcanSAS), read_metadata()
    grouping.py      # scope grouping + output-path resolution (source/mirror/flat)
    pipeline.py      # orchestration: group → parallel render → write; progress + cancel callbacks
  render/
    plots.py         # per-technique styles; render_image(datasets[, 1..10], out.png)
    parallel.py      # ProcessPoolExecutor pool: one task = one image (workers read HDF5 + render)
  writers/
    pdf_writer.py    # grid of pre-rendered PNGs, r×c per page, group title, optional metadata page
    md_writer.py     # Obsidian: one .md per group + Attachments/ folder
    ascii_writer.py  # one .dat per dataset, header + 3 columns
  gui/
    main_window.py   # tree + regex filter + options; generation in QThread with progress bar/cancel
    report_options.py
```

### Data model & flow

1. **Scan (instant):** `scanner.scan(root)` walks the tree, classifies each HDF5
   file by folder position → `Dataset(month, user, sample, technique)`.
   Technique inferred from folder suffix (`_usaxs`, `_saxs`, `_waxs`,
   `_usaxs_merged`); tolerant of partial trees (root can be month, user, or
   sample level).
2. **Select:** GUI checkboxes and/or regex field (`re.search` on relative
   path); same regex available as `--select` in CLI/API. Convenience filters:
   exclude/only `*blank*`.
3. **Group:** scope = `dataset | technique | sample | user`. Group key doubles
   as the relative output path.
4. **Render (parallel):** work units = images. With N datasets-per-graph
   (1/3/5/10), consecutive datasets *within the same technique group* are
   chunked. Each ProcessPool worker opens its HDF5 file(s), reads curves,
   renders one PNG into a per-run image directory with deterministic names
   (`<sha1(relpath)[:12]>.png`) → exact record↔image mapping, no guessing.
   USAXS files: use the desmeared subentry (skip `_SMR`) by default.
5. **Write:** writers consume `(group, [(image, [datasets])])` — pure assembly,
   no HDF5 access, no rendering.

### Output resolution (orthogonal to scope)

| Mode | Destination |
|---|---|
| `source` | next to data: `<input_tree>/<group_path>/<name>.pdf/.md` + `Attachments/` |
| `mirror` | `<output_dir>/<group_path>/...` (structure reproduced) |
| `flat`   | `<output_dir>/<name>.pdf` etc., name = full group key flattened |

ASCII export always produces one `.dat` per dataset placed per the same mode
(grouped into `<group>_ascii/` folders in flat mode to avoid filename floods).

### Metadata wiring (extensible)

`nexus.py` exposes `METADATA_KEYS: dict[str, list[str]]` — technique →
list of HDF5 paths (with fallbacks for `entry/Metadata` vs `entry/metadata`).
Ships minimal: sample title, thickness, transmission, SDD, wavelength,
timestamp. Shown in MD bullet lists / ASCII headers / optional PDF summary.
Adding a key later = one line in this table.

### Performance

- Fast scan: no HDF5 opens → tree appears in <1 s for a month (~6 000 files).
- Rendering: `ProcessPoolExecutor(max_workers=cpu_count()-1)`, matplotlib Agg
  per worker. ~6 000 curves at ~60–100 ms each → roughly 1 min on 8–10 cores
  vs ~10 min serial.
- Per-run image cache dir is reused across formats (PDF + MD share PNGs) and
  deleted afterwards (kept when MD needs Attachments — moved, not copied,
  when only MD is produced).
- GUI stays responsive: pipeline runs in a QThread; per-image progress signal
  drives a progress bar; cancel flag checked between chunks.

### GUI changes

- Tree: single fast scan builds full hierarchy (folders + files) with
  checkboxes; tri-state parents; file counts and sizes.
- Filter row: regex field (applies to checkboxes), Exclude blanks / Only blanks.
- Options: scope, datasets-per-graph (1/3/5/10), formats (PDF / Obsidian MD /
  ASCII), PDF grid r×c, output mode (source/mirror/flat), output dir.
- Progress bar + Cancel replace the red/green status hack; errors summarized
  in a dialog at the end (per-file failures never abort the run).
- Settings persisted between sessions.

### CLI / scripting

```bash
datareporter /path/to/2026-07 --scope sample --formats pdf,md \
    --mode source --per-graph 5 --select 'AHM_.*' --workers 8
```

```python
from datareporter import api
ds = api.scan("/data/2026/2026-07", select=r"AHM_.*")
api.generate(ds, scope="sample", formats=["pdf", "md"], mode="source")
```

Suited for an end-of-cycle cron/script run.

### Tests & docs

- Unit tests: scanner classification, regex select, grouping/output-path
  resolution, ASCII format, MD structure, PDF page math — using the small
  synthetic tree in `data/` (real HDF5 files already in repo).
- Smoke test: full pipeline on `data/` producing all three formats.
- Docs: rewritten README (install, GUI walkthrough, CLI, API), 
  `docs/architecture.md` (module map + how to extend: new format, new
  metadata key, new technique), CHANGELOG.

## Implementation order

1. `model.py`, `scanner.py`, `nexus.py` (+ tests) — solid foundation.
2. `grouping.py`, `plots.py`, `parallel.py` (+ tests).
3. `writers/` pdf, md, ascii (+ tests); remove csv.
4. `pipeline.py`, `api.py`, `cli.py`; delete `reporter.py`/`report_orchestrator.py`.
5. GUI rework on top of `api`.
6. Docs, README, CHANGELOG; end-to-end run against `data/` and a real month.
