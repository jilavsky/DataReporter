# CLAUDE.md

Orientation file for AI agents working in this repository. It tells you *where*
things are and *what rules apply*, not what every function does.

DataReporter crawls a tree of instrument-reduced USAXS/SAXS/WAXS data (NXcanSAS
HDF5), renders intensity plots in parallel, and emits summaries as PDF,
Obsidian-flavoured Markdown, or ASCII (`Q I Idev`). Written for the APS 12-ID
folder layout, but it works from any level of it.

---

## 1. Commands

```bash
pip install -e ".[all]"     # dev install (gui + dev)
pytest                      # full suite (tests/, 36 tests, headless)
ruff check src/             # lint (line-length 100)
datareporter --help         # CLI
datareporter-gui            # GUI (requires the [gui] extra)
```

Sample input data lives in `data/`. Tests are headless and must stay that way —
none of them may import `datareporter.gui`.

---

## 2. Architecture

Expected folder layout of the input tree:

```
<YYYY>/<YYYY-MM>/<MM_DD_UserName>/<SampleName>/<SampleName>_<technique>/*.h5
technique ∈ {usaxs, saxs, waxs, usaxs_merged}
```

| Layer | Path | Responsibility | May import |
|---|---|---|---|
| **core** | `src/datareporter/core/` | Scanning, grouping, NeXus reading, the pipeline | numpy, h5py |
| **render** | `src/datareporter/render/` | Parallel matplotlib plotting (Agg only) | core, matplotlib |
| **writers** | `src/datareporter/writers/` | PDF / Markdown / ASCII emitters | core, render |
| **api** | `src/datareporter/api.py` | Stable facade used by both CLI and GUI | core, render, writers |
| **cli** | `src/datareporter/cli.py` | Command-line entry point | api |
| **gui** | `src/datareporter/gui/` | Thin Qt shell over `api` | Qt (via `gui/_qt.py`), api |

`core/scanner.py` does a *fast* scan that opens no HDF5 files — the GUI tree is
populated from it, so keep it cheap. `core/nexus.py` is the only module that
opens `.h5` files.

### Invariants — do not break these

1. **Nothing outside `gui/` imports Qt.** The CLI and writers must install and
   run with no Qt binding present. Verify:
   `grep -rl "PySide6\|PyQt6" src/datareporter --include=*.py` must return only
   `src/datareporter/gui/_qt.py`.
2. **All Qt imports go through `src/datareporter/gui/_qt.py`** — never
   `from PySide6 import ...` directly. It normalises the PySide6/PyQt6 fallback
   and `Signal`/`pyqtSignal`.
3. `render/plots.py` forces `matplotlib.use("Agg")` before importing pyplot.
   Matplotlib is a *core* dependency precisely because it pulls in no toolkit —
   keep it that way.
4. Long work runs on a `QThread` with a working Cancel. The GUI must not block.

---

## 3. Conventions

**Qt: PySide6, never PyQt6.** This repo used PyQt6 as a core dependency until
August 2026. It was migrated because pyirena, Matilda and MailToVault are all
PySide6, and PySide6 + PyQt6 in one environment breaks Qt platform-plugin
resolution (on macOS: "could not load the Qt platform plugin cocoa"). Do not
reintroduce PyQt6 outside the `_qt.py` fallback branch, and never as a
non-optional dependency.

**Scientific.** Q in Å⁻¹, intensity in cm⁻¹ where calibration exists. NXcanSAS
field names come from the files as written by Matilda/Irena — do not "tidy"
them. Single-letter physics names (`I`, `Q`) are idiomatic; `E741` is disabled.

**Code.** Python ≥3.10. Line length 100. `ruff` only — no black. Static version
in `pyproject.toml`. Qt lives in the `[gui]` extra.

**Testing.** New parsing or grouping logic needs a test in `tests/`. Tests must
not require a display or a Qt binding.

---

## 4. Where to look

| If you are… | Read |
|---|---|
| Getting oriented | `docs/architecture.md`, `docs/index.md` |
| Changing the folder-layout assumptions | `core/scanner.py`, `core/grouping.py` |
| Touching HDF5 reads | `core/nexus.py` |
| Adding an output format | `writers/`, then wire it into `api.py` and the CLI |
| Working on the GUI | `gui/main_window.py`, `gui/report_options.py`, `gui/_qt.py` |
| Looking for planned work | `PLAN.md` |

---

## 5. Maintaining this file

This is a map, not documentation. Update it when a layer is added or removed,
when an invariant in §2 changes, or when a command in §1 changes. Do not add
function signatures or per-release notes here — those rot in weeks.
