"""Command-line interface.

Examples::

    # PDFs next to the data, one per sample
    datareporter /data/2026/2026-07 --scope sample --formats pdf --mode source

    # Obsidian vault import: mirror the tree into a separate folder
    datareporter /data/2026/2026-07 --formats md --mode mirror -o ~/Vault/Experiments

    # ASCII export of selected samples, 5 curves per graph in the PDFs
    datareporter /data/2026/2026-07 --select 'AHM_.*' --formats pdf,ascii --per-graph 5
"""

from __future__ import annotations

import argparse
import sys

from datareporter import api

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="datareporter",
        description="Generate PDF / Obsidian-Markdown / ASCII summaries of "
                    "USAXS/SAXS/WAXS reduced data trees.",
    )
    p.add_argument("root", help="Folder to scan (year, month, user, or sample level)")
    p.add_argument("--select", metavar="REGEX", default=None,
                   help="Case-insensitive regex on paths relative to ROOT")
    p.add_argument("--blanks", choices=["include", "exclude", "only"],
                   default="include", help="Blank measurement handling")
    p.add_argument("--scope", choices=["dataset", "technique", "sample", "user"],
                   default="sample", help="One output document per ... (default: sample)")
    p.add_argument("--formats", default="pdf",
                   help="Comma-separated: pdf, md, ascii (default: pdf)")
    p.add_argument("--mode", choices=["source", "mirror", "flat"], default="source",
                   help="source = write next to data; mirror = reproduce tree under "
                        "--output; flat = all files directly in --output")
    p.add_argument("--output", "-o", default=None,
                   help="Output directory (required for mirror/flat modes)")
    p.add_argument("--per-graph", type=int, default=1, metavar="N",
                   help="Datasets overlaid per graph, 1-10 (default: 1)")
    p.add_argument("--grid", default="2x3", metavar="RxC",
                   help="Images per PDF page (default: 2x3)")
    p.add_argument("--workers", type=int, default=None, metavar="N",
                   help="Parallel processes (default: CPU count - 1)")
    p.add_argument("--list", action="store_true",
                   help="Only list matching datasets, generate nothing")
    p.add_argument("--quiet", "-q", action="store_true", help="No progress output")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        rows, cols = (int(x) for x in args.grid.lower().split("x", 1))
    except ValueError:
        print(f"Invalid --grid '{args.grid}', expected e.g. 2x3", file=sys.stderr)
        return 2

    datasets = api.scan(args.root, select=args.select, blanks=args.blanks)
    if not datasets:
        print("No matching HDF5 files found.", file=sys.stderr)
        return 1
    if not args.quiet or args.list:
        print(f"{len(datasets)} dataset(s) selected under {args.root}")
    if args.list:
        for d in datasets:
            print(f"  {d.rel_path}")
        return 0

    def _progress(phase: str, done: int, total: int) -> None:
        if not args.quiet:
            print(f"\r{phase}: {done}/{total}", end="", flush=True)
            if done == total:
                print()

    report = api.generate(
        datasets,
        scope=args.scope,
        formats=[f.strip() for f in args.formats.split(",") if f.strip()],
        mode=args.mode,
        output_dir=args.output,
        per_graph=args.per_graph,
        pdf_grid=(rows, cols),
        workers=args.workers,
        input_root=args.root,
        progress=_progress,
    )

    print(report.summary())
    for err in report.errors[:20]:
        print(f"  ! {err}", file=sys.stderr)
    if len(report.errors) > 20:
        print(f"  ... and {len(report.errors) - 20} more error(s)", file=sys.stderr)
    return 0 if report.produced and not report.cancelled else 1


if __name__ == "__main__":
    raise SystemExit(main())
